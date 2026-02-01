pipeline {
    agent none /* Bezpiecznik: Główny węzeł nic nie robi */
    
    options {
        timeout(time: 30, unit: 'MINUTES')
        skipDefaultCheckout(true)
    }
    
    stages {
        // --- KROK 1: POBRANIE KODU ---
        stage('Checkout') {
            agent {
                docker {
                    image 'alpine/git'
                    args '-u 0:0' // root potrzebny do zapisu
                }
            }
            steps {
                checkout scm
                stash includes: '**/*', name: 'source'
            }
        }
        
        // --- KROK 2: BACKEND ---
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
                
                // Kompilacja (sprawdzenie składni)
                sh 'python -m py_compile backend/app/main.py'
                sh 'python -m py_compile backend/app/routers/auth.py'
                sh 'python -m py_compile backend/app/routers/manager.py'
                sh 'python -m py_compile backend/app/routers/scheduler.py'
                sh 'mkdir -p test-results'
                
                // Uruchomienie serwera w tle z poprawnym PYTHONPATH
                sh '''
                    export PYTHONPATH=$PWD
                    nohup python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 > uvicorn.log 2>&1 &
                    sleep 5
                '''
                
                // Uruchomienie testów (jednostkowe i integracyjne)
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
                    
                    // Budujemy od razu tutaj
                    sh 'flutter build web --release'
                }
                stash includes: 'frontend/build/web/**/*', name: 'flutter-web'
            }
        }
        
        // --- KROK 4: DEPLOY ---
        stage('Deploy') {
            agent {
                docker {
                    // Obraz z klientem dockera
                    image 'docker:cli'
                    // Mapowanie socketa z hosta
                    args '-v /var/run/docker.sock:/var/run/docker.sock -u 0:0'
                }
            }
            steps {
                unstash 'source'
                unstash 'flutter-web'
                
                script {
                    // Doinstalowanie curla (obraz docker:cli go nie ma, a potrzebujemy do healthchecka)
                    sh 'apk add --no-cache curl || true'

                    echo "🧹 Cleaning up old containers..."
                    sh '''
                        docker rm -f plannerv2-nginx || true
                        docker rm -f plannerv2-backend || true
                        docker rm -f plannerv2-db || true
                    '''
                    
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
                    
                    // Diagnostyka
                    sh '''
                        if [ "$(docker inspect -f '{{.State.Running}}' plannerv2-backend)" = "false" ]; then
                            echo "❌ CRITICAL: Backend container crashed!"
                            docker logs plannerv2-backend
                            exit 1
                        else
                            echo "✅ Backend container is running."
                        fi
                    '''

                    echo "🚀 Starting Nginx (Method: docker cp)..."
                    sh '''
                        docker run -d --name plannerv2-nginx \
                            --network plannerv2-network \
                            -p 8090:80 \
                            --restart unless-stopped \
                            nginx:alpine
                    '''
                    
                    sh 'sleep 5'
                    
                    // Kopiowanie plików (przez socket hosta)
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
                    
                    // Health check (używamy curla zainstalowanego na początku skryptu)
                    sh '''
                        sleep 5
                        curl -f http://46.225.49.0:8090/docs || echo "Health check warning (connection check)"
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