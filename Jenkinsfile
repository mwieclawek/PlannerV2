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
                sh '''
                    export PYTHONPATH=$PWD
                    nohup python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 > uvicorn.log 2>&1 &
                    sleep 10
                '''
                sh 'export PYTHONPATH=$PWD && python -m pytest backend/tests/test_api.py -v --junitxml=test-results/backend-api.xml || true'
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'test-results/*.xml'
                    sh 'pkill -f uvicorn || true'
                }
            }
        }
        
        stage('Frontend Build') {
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

        stage('Deploy to DEV') {
            when {
                branch 'main'
            }
            agent {
                docker {
                    image 'docker:cli'
                    args '-v /var/run/docker.sock:/var/run/docker.sock -u 0:0'
                }
            }
            steps {
                unstash 'source'
                unstash 'flutter-web'
                script {
                    sh 'apk add --no-cache curl sed || true'
                    
                    echo "🧹 Sprzątanie DEV..."
                    sh 'docker rm -f plannerv2-nginx-dev plannerv2-backend-dev plannerv2-db-dev || true'
                    sh 'docker network create plannerv2-network || true'
                    
                    echo "🗄️ Start Bazy DEV..."
                    sh '''docker run -d --name plannerv2-db-dev --network plannerv2-network \
                          -e POSTGRES_USER=planner_user -e POSTGRES_PASSWORD=planner_password -e POSTGRES_DB=planner_db \
                          -v plannerv2_postgres_data_dev:/var/lib/postgresql/data --restart unless-stopped postgres:15'''
                    sh 'sleep 10' 
                    
                    echo "🐍 Backend DEV..."
                    sh 'docker build -t plannerv2-backend:dev ./backend'
                    
                    sh '''
                        docker run -d --name plannerv2-backend-dev --network plannerv2-network \
                        -e DATABASE_URL=postgresql://planner_user:planner_password@plannerv2-db-dev:5432/planner_db \
                        --restart unless-stopped plannerv2-backend:dev \
                        /bin/sh -c "ln -s /app /app/backend && export PYTHONPATH=/app && uvicorn app.main:app --host 0.0.0.0 --port 8000"
                    '''
                    sh 'sleep 10'
                    
                    // Healthcheck backendu
                    sh '''
                        if [ "$(docker inspect -f '{{.State.Running}}' plannerv2-backend-dev)" = "false" ]; then
                            echo "❌ CRITICAL: Backend DEV padł przed startem Nginxa! Logi:"
                            docker logs plannerv2-backend-dev
                            exit 1
                        fi
                    '''
                    
                    echo "🔧 Nginx DEV Setup..."
                    sh 'git checkout nginx/nginx.conf || true' 
                    sh "sed -i 's/plannerv2-backend/plannerv2-backend-dev/g' nginx/nginx.conf"
                    
                    // 1. Startujemy Nginxa z domyślnym konfigiem (żeby kontener działał i miał sieć)
                    sh 'docker run -d --name plannerv2-nginx-dev --network plannerv2-network -p 8091:80 --restart unless-stopped nginx:alpine'
                    
                    // 2. KLUCZOWY FIX: Pętla czekająca na DNS
                    // Nginx nie może zrobić reloadu, dopóki nie widzi backendu. Sprawdzamy to.
                    sh '''
                        echo "⏳ Czekam na widoczność Backendu w sieci Docker..."
                        for i in 1 2 3 4 5; do
                            if docker exec plannerv2-nginx-dev getent hosts plannerv2-backend-dev; then
                                echo "✅ DNS OK: Nginx widzi Backend!"
                                break
                            else
                                echo "⚠️ DNS jeszcze nie gotowy, czekam..."
                                sleep 5
                            fi
                        done
                    '''

                    // 3. Dopiero teraz kopiujemy i przeładowujemy
                    sh '''
                        # Foldery
                        docker exec plannerv2-nginx-dev mkdir -p /var/www/plannerv2/web
                        
                        # Frontend
                        docker cp frontend/build/web/. plannerv2-nginx-dev:/var/www/plannerv2/web/
                        
                        # Config
                        docker cp nginx/nginx.conf plannerv2-nginx-dev:/etc/nginx/nginx.conf
                        
                        # Reload (teraz powinno być bezpieczne)
                        echo "🔄 Reloading Nginx..."
                        docker exec plannerv2-nginx-dev nginx -s reload
                    '''
                    
                    echo "✅ DEV gotowy na porcie 8091"
                }
            }
        }
        
        stage('Deploy to PRODUCTION') {
            when {
                tag "v*"
            }
            agent {
                docker {
                    image 'docker:cli'
                    args '-v /var/run/docker.sock:/var/run/docker.sock -u 0:0'
                }
            }
            steps {
                unstash 'source'
                unstash 'flutter-web'
                script {
                    echo "🚀 DEPLOY PRODUKCJI: ${env.TAG_NAME}"
                    sh 'apk add --no-cache curl || true'
                    sh 'docker rm -f plannerv2-nginx plannerv2-backend plannerv2-db || true'
                    sh 'docker network create plannerv2-network || true'
                    
                    sh '''docker run -d --name plannerv2-db --network plannerv2-network \
                          -e POSTGRES_USER=planner_user -e POSTGRES_PASSWORD=planner_password -e POSTGRES_DB=planner_db \
                          -v plannerv2_postgres_data:/var/lib/postgresql/data --restart unless-stopped postgres:15'''
                    sh 'sleep 10'
                    
                    sh 'docker build -t plannerv2-backend:latest ./backend'
                    sh '''
                        docker run -d --name plannerv2-backend --network plannerv2-network \
                        -e DATABASE_URL=postgresql://planner_user:planner_password@plannerv2-db:5432/planner_db \
                        --restart unless-stopped plannerv2-backend:latest \
                        /bin/sh -c "ln -s /app /app/backend && export PYTHONPATH=/app && uvicorn app.main:app --host 0.0.0.0 --port 8000"
                    '''
                    sh 'sleep 10'
                    
                    sh '''
                        if [ "$(docker inspect -f '{{.State.Running}}' plannerv2-backend)" = "false" ]; then
                            echo "❌ Backend PROD padł! Logi:"
                            docker logs plannerv2-backend
                            exit 1
                        fi
                    '''
                    
                    sh 'git checkout nginx/nginx.conf || true'
                    
                    // PROD: Ta sama bezpieczna procedura
                    sh 'docker run -d --name plannerv2-nginx --network plannerv2-network -p 8090:80 --restart unless-stopped nginx:alpine'
                    
                    // Pętla czekająca na DNS dla Produkcji
                    sh '''
                        for i in 1 2 3 4 5; do
                            if docker exec plannerv2-nginx getent hosts plannerv2-backend; then
                                echo "✅ DNS OK"
                                break
                            else
                                sleep 5
                            fi
                        done
                    '''
                    
                    sh '''
                        docker exec plannerv2-nginx mkdir -p /var/www/plannerv2/web
                        docker cp frontend/build/web/. plannerv2-nginx:/var/www/plannerv2/web/
                        docker cp nginx/nginx.conf plannerv2-nginx:/etc/nginx/nginx.conf
                        docker exec plannerv2-nginx nginx -s reload
                    '''
                    
                    echo "✅ PRODUKCJA Wdrożona!"
                }
            }
        }
    }
    
    post {
        success { echo '✅ Pipeline OK' }
        failure { echo '❌ Pipeline FAILED' }
    }
}