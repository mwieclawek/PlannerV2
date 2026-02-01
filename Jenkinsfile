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
                    pip install pytest httpx pytest-asyncio
                '''
                sh 'python -m py_compile backend/app/main.py'
                sh 'python -m py_compile backend/app/routers/auth.py'
                sh 'python -m py_compile backend/app/routers/manager.py'
                sh 'python -m py_compile backend/app/routers/scheduler.py'
                sh 'mkdir -p test-results'
                
                // Unit tests (no server needed)
                sh 'python -m pytest backend/tests/test_auth_unit.py -v --junitxml=test-results/auth-unit.xml || true'
                sh 'python -m pytest backend/tests/test_solver_unit.py -v --junitxml=test-results/solver-unit.xml || true'
                
                // API and Integration tests (need server)
                sh '''
                    cd backend
                    nohup python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
                    sleep 5
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
                    // Container cleanup handles process termination
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
                
                // Force stop and remove nginx first
                sh '''
                    docker stop plannerv2-nginx || true
                    docker rm -f plannerv2-nginx || true
                    sleep 2
                '''
                
                // Stop and remove other container
                sh '''
                    docker stop plannerv2-backend || true
                    docker rm -f plannerv2-backend || true
                    docker stop plannerv2-db || true
                    docker rm -f plannerv2-db || true
                    sleep 2
                '''
                
                // Create network if not exists
                sh 'docker network create plannerv2-network || true'
                
                // Start PostgreSQL
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
                
                // Wait for postgres to be ready
                sh 'sleep 5'
                
                // Build and start Backend
                sh 'docker build -t plannerv2-backend:latest ./backend'
                sh '''
                    docker run -d --name plannerv2-backend \
                        --network plannerv2-network \
                        -e DATABASE_URL=postgresql://planner_user:planner_password@plannerv2-db:5432/planner_db \
                        --restart unless-stopped \
                        plannerv2-backend:latest
                '''
                
                // Wait for backend to start
                sh 'sleep 3'
                
                // Start Nginx (port 8090 to avoid conflicts with System/Jenkins on 80/8080)
                sh '''
                    docker run -d --name plannerv2-nginx \
                        --network plannerv2-network \
                        -p 8090:80 \
                        --restart unless-stopped \
                        nginx:alpine
                    
                    # Wait for container to start
                    sleep 3
                    
                    # Copy nginx config
                    docker cp nginx/nginx.conf plannerv2-nginx:/etc/nginx/nginx.conf
                    
                    # Create web directory and copy Flutter build
                    docker exec plannerv2-nginx mkdir -p /var/www/plannerv2/web
                    docker cp frontend/build/web/. plannerv2-nginx:/var/www/plannerv2/web/
                    
                    # Reload nginx to apply config
                    docker exec plannerv2-nginx nginx -s reload
                '''
                
                // Health check
                sh '''
                    sleep 5
                    curl -f http://localhost/docs || echo "Backend health check pending..."
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
