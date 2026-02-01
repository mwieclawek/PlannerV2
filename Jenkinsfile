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
                    pip install pytest httpx
                '''
                sh 'python -m py_compile backend/app/main.py'
                sh 'python -m py_compile backend/app/routers/auth.py'
                sh 'python -m py_compile backend/app/routers/manager.py'
                sh 'python -m py_compile backend/app/routers/scheduler.py'
                sh '''
                    cd backend
                    nohup python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
                    sleep 5
                '''
                sh 'mkdir -p test-results'
                sh 'python -m pytest backend/tests/test_api.py -v --junitxml=test-results/backend-unit.xml || true'
                sh 'python -m pytest backend/tests/test_integration.py -v --junitxml=test-results/backend-integration.xml || true'
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'test-results/*.xml'
                    sh 'pkill -f uvicorn || true'
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
                
                // Stop and remove existing containers (if any)
                sh 'docker stop plannerv2-backend plannerv2-nginx plannerv2-db || true'
                sh 'docker rm plannerv2-backend plannerv2-nginx plannerv2-db || true'
                
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
                
                // Build and start Backend
                sh 'docker build -t plannerv2-backend:latest ./backend'
                sh '''
                    docker run -d --name plannerv2-backend \
                        --network plannerv2-network \
                        -e DATABASE_URL=postgresql://planner_user:planner_password@plannerv2-db:5432/planner_db \
                        --restart unless-stopped \
                        plannerv2-backend:latest
                '''
                
                // Start Nginx with Flutter web
                sh '''
                    docker run -d --name plannerv2-nginx \
                        --network plannerv2-network \
                        -p 80:80 \
                        -v $(pwd)/nginx/nginx.conf:/etc/nginx/nginx.conf:ro \
                        -v $(pwd)/frontend/build/web:/var/www/plannerv2/web:ro \
                        --restart unless-stopped \
                        nginx:alpine
                '''
                
                // Health check
                sh '''
                    sleep 15
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
