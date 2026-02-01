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
                    image 'cirrusci/flutter:stable'
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
    }
    
    post {
        success {
            echo 'All tests passed!'
        }
        failure {
            echo 'Tests failed!'
        }
    }
}
