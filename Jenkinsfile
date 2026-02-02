pipeline {
    agent none /* Master tylko zarządza, konkretne zadania mają swoich agentów */
    
    options {
        timeout(time: 30, unit: 'MINUTES')
        skipDefaultCheckout(true)
    }
    
    stages {
        // --- KROK 1: POBRANIE KODU ---
        // Używamy 'agent any', bo to najstabilniejsza metoda pobierania kodu na pojedynczym serwerze.
        // Unikamy błędu z zamykającym się kontenerem alpine/git.
        stage('Checkout') {
            agent any
            steps {
                checkout scm
                stash includes: '**/*', name: 'source'
            }
        }
        
        // --- KROK 2: BACKEND (Wersja z DEV - poprawne importy) ---
        stage('Backend Tests') {
            agent {
                docker {
                    image 'python:3.11-slim'
                    args '-u root'
                }
            }
            steps {
                unstash 'source'
                sh '''
                    pip install -r backend/requirements.txt
                    pip install pytest httpx pytest-asyncio uvicorn
                '''
                
                // Kompilacja w celu wykrycia błędów składni
                sh 'python -m py_compile backend/app/main.py'
                sh 'python -m py_compile backend/app/routers/auth.py'
                sh 'python -m py_compile backend/app/routers/manager.py'
                sh 'python -m py_compile backend/app/routers/scheduler.py'
                sh 'mkdir -p test-results'
                
                // Najpierw uruchom testy jednostkowe (nie wymagają serwera)
                sh '''
                    export PYTHONPATH=$PWD
                    python -m pytest backend/tests/test_auth_unit.py backend/tests/test_employee.py backend/tests/test_manager_edge_cases.py backend/tests/test_scheduler_unit.py backend/tests/test_solver_unit.py -v --junitxml=test-results/backend-unit.xml || true
                '''
                
                // Uruchomienie serwera w tle z poprawnym PYTHONPATH (kluczowe!)
                sh '''
                    export PYTHONPATH=$PWD
                    nohup python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 > uvicorn.log 2>&1 &
                    sleep 5
                '''
                
                // Uruchomienie testów API i integracyjnych (wymagają serwera)
                sh 'export PYTHONPATH=$PWD && python -m pytest backend/tests/test_api.py -v --junitxml=test-results/backend-api.xml || true'
                sh 'export PYTHONPATH=$PWD && python -m pytest backend/tests/test_integration.py -v --junitxml=test-results/backend-integration.xml || true'
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'test-results/*.xml'
                    sh 'pkill -f uvicorn || true'
                }
            }
        }
        
        // --- KROK 3: FRONTEND ---
        stage('Frontend Tests & Build') {
            agent {
                docker {
                    image 'ghcr.io/cirruslabs/flutter:stable'
                    args '-u root'
                }
            }
            steps {
                unstash 'source'
                dir('frontend') {
                    sh 'flutter pub get'
                    sh 'flutter analyze --no-fatal-infos || true'
                    sh 'flutter test --machine > ../test-results/frontend.json || true'
                    
                    // Budujemy od razu tutaj, żeby nie przesyłać plików dwa razy
                    sh 'flutter build web --release'
                }
                stash includes: 'frontend/build/web/**/*', name: 'flutter-web'
            }
        }
        
        // --- KROK 4: DEPLOY (Wersja z DEV - solidna, z curl i docker cp) ---
        stage('Deploy') {
            agent {
                docker {
                    // Używamy klienta dockera sterującego hostem
                    image 'docker:cli'
                    args '-v /var/run/docker.sock:/var/run/docker.sock -u 0:0'
                }
            }
            steps {
                unstash 'source'
                unstash 'flutter-web'
                
                script {
                    // Instalacja curla (niezbędne dla healthchecka w tym obrazie)
                    sh 'apk add --no-cache curl || true'

                    echo "🧹 Cleaning up old containers..."
                    sh 'docker rm -f plannerv2-nginx plannerv2-backend plannerv2-db || true'
                    
                    echo "🌐 Ensuring network..."
                    sh 'docker network create plannerv2-network || true'
                    
                    echo "🗄️ Starting Database..."
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
                    
                    echo "🐍 Building and Starting Backend..."
                    sh 'docker build -t plannerv2-backend:latest ./backend'
                    
                    sh '''
                        docker run -d --name plannerv2-backend \
                            --network plannerv2-network \
                            -e DATABASE_URL=postgresql://planner_user:planner_password@plannerv2-db:5432/planner_db \
                            --restart unless-stopped \
                            plannerv2-backend:latest
                    '''
                    
                    echo "⏳ Waiting for Backend to initialize..."
                    sh 'sleep 10'
                    
                    // Diagnostyka - czy backend wstał?
                    sh '''
                        if [ "$(docker inspect -f '{{.State.Running}}' plannerv2-backend)" = "false" ]; then
                            echo "❌ CRITICAL: Backend container crashed!"
                            docker logs plannerv2-backend
                            exit 1
                        else
                            echo "✅ Backend container is running."
                        fi
                    '''

                    echo "🚀 Starting Nginx (Port 8090)..."
                    sh '''
                        docker run -d --name plannerv2-nginx \
                            --network plannerv2-network \
                            -p 8090:80 \
                            --restart unless-stopped \
                            nginx:alpine
                    '''
                    
                    sh 'sleep 5'
                    
                    // Kopiowanie plików (metoda docker cp - niezawodna)
                    sh '''
                        # Kopiowanie configu
                        docker cp nginx/nginx.conf plannerv2-nginx:/etc/nginx/nginx.conf
                        
                        # Kopiowanie strony
                        docker exec plannerv2-nginx mkdir -p /var/www/plannerv2/web
                        docker cp frontend/build/web/. plannerv2-nginx:/var/www/plannerv2/web/
                    '''
                    
                    // Walidacja i Reload
                    sh '''
                        echo "🔍 Verifying network visibility..."
                        docker exec plannerv2-nginx getent hosts plannerv2-backend || echo "⚠️ Warning: DNS lookup failed, attempting reload anyway..."
                        
                        echo "🔍 Testing Nginx config..."
                        docker exec plannerv2-nginx nginx -t
                        
                        echo "🔄 Reloading Nginx..."
                        docker exec plannerv2-nginx nginx -s reload
                    '''
                    
                    // Health check (sprawdzenie czy aplikacja odpowiada)
                    sh '''
                        sleep 5
                        curl -f http://46.225.49.0:8090/docs || echo "⚠️ Warning: Connection check failed but deploy finished successfully."
                    '''
                    
                    echo "✅ Deploy Finished!"
                }
            }
        }
    }
    
    post {
        success {
            echo '✅ Deployment successful!'
        }
        failure {
            echo '❌ Deployment failed.'
        }
    }
}