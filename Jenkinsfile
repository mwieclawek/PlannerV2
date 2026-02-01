pipeline {
    agent none
    
    options {
        timeout(time: 30, unit: 'MINUTES')
        skipDefaultCheckout(true)
    }
    
    stages {
        stage('Checkout') {
            agent any
            steps {
                checkout scm
                stash includes: '**/*', name: 'source'
            }
        }
        
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
                
                sh 'python -m py_compile backend/app/main.py'
                sh 'mkdir -p test-results'
                
                // Testy z poprawnym PYTHONPATH
                sh '''
                    export PYTHONPATH=$PWD
                    nohup python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 > uvicorn.log 2>&1 &
                    sleep 5
                '''
                
                sh 'export PYTHONPATH=$PWD && python -m pytest backend/tests/test_api.py -v --junitxml=test-results/backend-api.xml || true'
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'test-results/*.xml'
                }
            }
        }
        
        stage('Frontend Tests') {
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
                }
            }
        }
        
        stage('Build Flutter Web') {
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
                    sh 'flutter build web --release'
                }
                stash includes: 'frontend/build/web/**/*', name: 'flutter-web'
            }
        }
        
        stage('Deploy') {
            agent any
            steps {
                unstash 'source'
                unstash 'flutter-web'
                
                script {
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
                    
                    // Diagnostyka Backendu - sprawdzamy czy żyje
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
                    // 1. Startujemy czystego Nginxa (bez montowania wolumenów, bo to psuje ścieżki)
                    sh '''
                        docker run -d --name plannerv2-nginx \
                            --network plannerv2-network \
                            -p 8090:80 \
                            --restart unless-stopped \
                            nginx:alpine
                    '''
                    
                    // 2. Dajemy chwilę na start sieci
                    sh 'sleep 5'
                    
                    // 3. Kopiujemy pliki
                    sh '''
                        # Kopiowanie configu
                        docker cp nginx/nginx.conf plannerv2-nginx:/etc/nginx/nginx.conf
                        
                        # Kopiowanie strony
                        docker exec plannerv2-nginx mkdir -p /var/www/plannerv2/web
                        docker cp frontend/build/web/. plannerv2-nginx:/var/www/plannerv2/web/
                    '''
                    
                    // 4. Walidacja i Reload
                    // Testujemy config PRZED reloadem, żeby zobaczyć błędy składni
                    // Sprawdzamy czy DNS widzi backend (ping check)
                    sh '''
                        echo "🔍 Verifying network visibility..."
                        docker exec plannerv2-nginx getent hosts plannerv2-backend || echo "⚠️ Warning: DNS lookup failed, attempting reload anyway..."
                        
                        echo "🔍 Testing Nginx config..."
                        docker exec plannerv2-nginx nginx -t
                        
                        echo "🔄 Reloading Nginx..."
                        docker exec plannerv2-nginx nginx -s reload
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