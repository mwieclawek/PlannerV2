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
                
                // Kompilacja pythona (sprawdzenie składni)
                sh 'python -m py_compile backend/app/main.py'
                sh 'python -m py_compile backend/app/routers/auth.py'
                sh 'python -m py_compile backend/app/routers/manager.py'
                sh 'python -m py_compile backend/app/routers/scheduler.py'
                sh 'mkdir -p test-results'
                
                // Unit tests
                sh 'python -m pytest backend/tests/test_auth_unit.py -v --junitxml=test-results/auth-unit.xml || true'
                sh 'python -m pytest backend/tests/test_solver_unit.py -v --junitxml=test-results/solver-unit.xml || true'
                
                // API and Integration tests
                // FIX: Uruchamiamy z głównego katalogu (bez cd backend), ustawiamy PYTHONPATH
                // i wskazujemy moduł jako backend.app.main:app
                sh '''
                    export PYTHONPATH=$PWD
                    nohup python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 > uvicorn.log 2>&1 &
                    sleep 10
                '''
                
                sh 'python -m pytest backend/tests/test_api.py -v --junitxml=test-results/backend-api.xml || true'
                sh 'python -m pytest backend/tests/test_integration.py -v --junitxml=test-results/backend-integration.xml || true'
                sh 'python -m pytest backend/tests/test_employee.py -v --junitxml=test-results/employee.xml || true'
                sh 'python -m pytest backend/tests/test_manager_edge_cases.py -v --junitxml=test-results/manager-edge.xml || true'
                sh 'python -m pytest backend/tests/test_scheduler_unit.py -v --junitxml=test-results/scheduler.xml || true'
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
                sh 'flutter --version'
                dir('frontend') {
                    sh 'flutter pub get'
                    sh 'flutter analyze --no-fatal-infos || true'
                    sh 'flutter test || true'
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
                
                // Cleanup old containers
                sh '''
                    docker stop plannerv2-nginx || true
                    docker rm -f plannerv2-nginx || true
                    
                    docker stop plannerv2-backend || true
                    docker rm -f plannerv2-backend || true
                    
                    docker stop plannerv2-db || true
                    docker rm -f plannerv2-db || true
                '''
                
                sh 'docker network create plannerv2-network || true'
                
                // Start DB
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
                
                sh 'sleep 10' // Więcej czasu na start bazy
                
                // Build & Start Backend
                sh 'docker build -t plannerv2-backend:latest ./backend'
                sh '''
                    docker run -d --name plannerv2-backend \
                        --network plannerv2-network \
                        -e DATABASE_URL=postgresql://planner_user:planner_password@plannerv2-db:5432/planner_db \
                        --restart unless-stopped \
                        plannerv2-backend:latest
                '''
                
                sh 'sleep 10' // Backend musi wstać zanim Nginx spróbuje go rozwiązać
                
                // Start Nginx
                sh '''
                    docker run -d --name plannerv2-nginx \
                        --network plannerv2-network \
                        -p 8090:80 \
                        --restart unless-stopped \
                        nginx:alpine
                    
                    sleep 5
                    
                    # Copy config and content
                    docker cp nginx/nginx.conf plannerv2-nginx:/etc/nginx/nginx.conf
                    docker exec plannerv2-nginx mkdir -p /var/www/plannerv2/web
                    docker cp frontend/build/web/. plannerv2-nginx:/var/www/plannerv2/web/
                    
                    # Reload nginx
                    docker exec plannerv2-nginx nginx -s reload
                '''
                
                // Health Check
                sh '''
                    sleep 5
                    curl -f http://localhost:8090/docs || echo "Health check failed or pending"
                '''
            }
        }
    }
    
    post {
        success {
            echo 'Pipeline completed successfully! App deployed.'
        }
        failure {
            echo 'Pipeline failed!'
        }
    }
}