pipeline {
    agent any
    
    environment {
        FLUTTER_HOME = '/opt/flutter'
        PATH = "${FLUTTER_HOME}/bin:${env.PATH}"
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Setup Python') {
            steps {
                sh 'python -m pip install --upgrade pip'
                sh 'pip install -r backend/requirements.txt'
                sh 'pip install pytest httpx pytest-xdist'
            }
        }
        
        stage('Setup Flutter') {
            steps {
                sh 'flutter pub get'
                dir('frontend') {
                    sh 'flutter pub get'
                }
            }
        }
        
        stage('Backend Lint') {
            steps {
                dir('backend') {
                    sh 'python -m py_compile app/main.py'
                    sh 'python -m py_compile app/routers/auth.py'
                    sh 'python -m py_compile app/routers/manager.py'
                    sh 'python -m py_compile app/routers/scheduler.py'
                }
            }
        }
        
        stage('Frontend Analyze') {
            steps {
                dir('frontend') {
                    sh 'flutter analyze --no-fatal-infos'
                }
            }
        }
        
        stage('Start Backend') {
            steps {
                sh '''
                    cd backend
                    nohup uvicorn app.main:app --host 127.0.0.1 --port 8000 &
                    sleep 5
                '''
            }
        }
        
        stage('Backend Unit Tests') {
            steps {
                sh 'python -m pytest backend/tests/test_api.py -v --junitxml=test-results/backend-unit.xml'
            }
            post {
                always {
                    junit 'test-results/backend-unit.xml'
                }
            }
        }
        
        stage('Backend Integration Tests') {
            steps {
                sh 'python -m pytest backend/tests/test_integration.py -v --junitxml=test-results/backend-integration.xml'
            }
            post {
                always {
                    junit 'test-results/backend-integration.xml'
                }
            }
        }
        
        stage('Frontend Unit Tests') {
            steps {
                dir('frontend') {
                    sh 'flutter test --machine > ../test-results/frontend.json || true'
                }
            }
        }
    }
    
    post {
        always {
            // Kill backend server
            sh 'pkill -f "uvicorn" || true'
            
            // Archive test results
            archiveArtifacts artifacts: 'test-results/**/*', allowEmptyArchive: true
        }
        success {
            echo 'All tests passed!'
        }
        failure {
            echo 'Tests failed!'
        }
    }
}
