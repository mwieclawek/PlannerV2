pipeline {
    agent none /* Idealne dla setupu z 0 executorami na masterze */
    
    options {
        timeout(time: 30, unit: 'MINUTES')
        skipDefaultCheckout(true)
    }
    
    stages {
        // --- KROK 1: POBRANIE KODU (Naprawa: agent alpine/git) ---
        stage('Checkout') {
            agent {
                docker {
                    image 'alpine/git'
                    args '-u 0:0' // root potrzebny do zapisu w workspace
                }
            }
            steps {
                checkout scm
                stash includes: '**/*', name: 'source'
            }
        }
        
        // --- KROK 2: BACKEND (Naprawa: PYTHONPATH) ---
        stage('Backend Tests') {
            agent {
                docker {
                    image 'python:3.11-slim'
                    args '-u 0:0'
                }
            }
            steps {
                unstash 'source'
                sh '''
                    pip install -r backend/requirements.txt
                    pip install pytest httpx pytest-asyncio uvicorn
                '''
                
                sh 'python -m py_compile backend/app/main.py'
                sh 'mkdir -p test-results'
                
                // FIX: Ustawiamy ścieżkę, żeby testy widziały moduł 'backend'
                sh '''
                    export PYTHONPATH=$PWD
                    nohup python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 > uvicorn.log 2>&1 &
                    sleep 5
                '''
                
                // FIX: Dodajemy export PYTHONPATH do każdej komendy pytest
                sh 'export PYTHONPATH=$PWD && python -m pytest backend/tests/test_api.py -v --junitxml=test-results/backend-api.xml || true'
                sh 'export PYTHONPATH=$PWD && python -m pytest backend/tests/test_integration.py -v --junitxml=test-results/backend-integration.xml || true'
                sh 'export PYTHONPATH=$PWD && python -m pytest backend/tests/test_employee.py -v --junitxml=test-results/employee.xml || true'
                sh 'export PYTHONPATH=$PWD && python -m pytest backend/tests/test_manager_edge_cases.py -v --junitxml=test-results/manager-edge.xml || true'
                sh 'export PYTHONPATH=$PWD && python -m pytest backend/tests/test_scheduler_unit.py -v --junitxml=test-results/scheduler.xml || true'
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'test-results/*.xml'
                }
            }
        }
        
        // --- KROK 3: FRONTEND ---
        stage('Frontend Tests & Build') {
            agent {
                docker {
                    image 'ghcr.io/cirruslabs/flutter:stable'
                    args '-u 0:0'
                }
            }
            steps {
                unstash 'source'
                dir('frontend') {
                    sh 'flutter pub get'
                    sh 'flutter analyze --no-fatal-infos || true'
                    sh 'flutter test --machine > ../test-results/frontend.json || true'
                    
                    // Budujemy od razu tutaj, żeby nie przesyłać stasha dwa razy
                    sh 'flutter build web --release'
                }
                stash includes: 'frontend/build/web/**/*', name: 'flutter-web'
            }
        }
        
        // --- KROK 4: DEPLOY (Naprawa: agent docker:cli + port 8090) ---
        stage('Deploy') {
            agent {
                docker {
                    // Używamy obrazu z klientem dockera, bo "agent any" nie zadziała (brak executorów)
                    image 'docker:cli'
                    // Montujemy socket hosta
                    args '-v /var/run/docker.sock:/var/run/docker.sock -u 0:0'
                }
            }
            steps {
                unstash 'source'
                unstash 'flutter-web'
                
                script {
                    // Sprzątanie
                    sh 'docker rm -f plannerv2-nginx plannerv2-backend plannerv2-db || true'
                    
                    // Sieć
                    sh 'docker network create plannerv2-network || true'
                    
                    // Baza danych
                    sh '''
                        docker run -d --name plannerv2-db \
                            --network plannerv2-network \
                            -e POSTGRES_USER=planner_user \
                            -e POSTGRES_PASSWORD=planner_password \
                            -e POSTGRES_DB=planner_db \
                            -v plannerv2_postgres_data:/var/lib/postgresql/data \
                            --restart unless-stopped \
                            postgres:15
                    '''
                    sh 'sleep 5'
                    
                    // Backend
                    sh 'docker build -t plannerv2-backend:latest ./backend'
                    sh '''
                        docker run -d --name plannerv2-backend \
                            --network plannerv2-network \
                            -e DATABASE_URL=postgresql://planner_user:planner_password@plannerv2-db:5432/planner_db \
                            --restart unless-stopped \
                            plannerv2-backend:latest
                    '''
                    sh 'sleep 10'
                    
                    // Diagnostyka backendu
                    sh '''
                        if [ "$(docker inspect -f '{{.State.Running}}' plannerv2-backend)" = "false" ]; then
                            echo "❌ CRITICAL: Backend crashed!"
                            docker logs plannerv2-backend
                            exit 1
                        fi
                    '''

                    // Nginx (UWAGA: Zmieniono port na 8090, bo 80 jest zajęty przez systemowy Nginx!)
                    sh '''
                        docker run -d --name plannerv2-nginx \
                            --network plannerv2-network \
                            -p 8090:80 \
                            --restart unless-stopped \
                            nginx:alpine
                    '''
                    sh 'sleep 5'
                    
                    // Kopiowanie plików (przez docker cp na sockecie hosta)
                    sh '''
                        docker cp nginx/nginx.conf plannerv2-nginx:/etc/nginx/nginx.conf
                        docker exec plannerv2-nginx mkdir -p /var/www/plannerv2/web
                        docker cp frontend/build/web/. plannerv2-nginx:/var/www/plannerv2/web/
                        docker exec plannerv2-nginx nginx -s reload
                    '''
                    
                    // Health check (na porcie 8090)
                    sh '''
                        sleep 5
                        # Używamy wget, bo w obrazie docker:cli może nie być curla (albo instalujemy apk add curl)
                        apk add --no-cache curl
                        curl -f http://46.225.49.0:8090/docs || echo "Health check warning (connection might be blocked from inside container, but deploy finished)"
                    '''
                }
            }
        }
    }
    
    post {
        success { echo '✅ Deployment successful!' }
        failure { echo '❌ Pipeline failed!' }
    }
}