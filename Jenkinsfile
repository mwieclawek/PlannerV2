pipeline {
    agent none 
    
    options {
        timeout(time: 30, unit: 'MINUTES')
        skipDefaultCheckout(true)
    }
    
    stages {
        // --- 1. POBRANIE KODU ---
        stage('Checkout') {
            agent any
            steps {
                checkout scm
                stash includes: '**/*', name: 'source'
            }
        }
        
        // --- 2. TESTY BACKENDU ---
        stage('Backend Tests') {
            agent {
                docker {
                    image 'python:3.11-slim'
                    args '-u root -v pip-cache:/root/.cache/pip'
                }
            }
            steps {
                unstash 'source'
                sh '''
                    pip install -r backend/requirements.txt
                    pip install pytest httpx pytest-asyncio
                '''
                sh 'python -m py_compile backend/app/main.py'
                sh 'mkdir -p test-results'
                // Usunięcie starej bazy SQLite (safety net)
                sh 'rm -f backend/*.db backend/app/*.db *.db'
                // Testy używają in-memory SQLite — nie potrzeba uruchamiać serwera
                sh 'export PYTHONPATH=$PWD:$PWD/backend && python -m pytest backend/tests/test_api.py -v -o asyncio_mode=auto --junitxml=test-results/backend-api.xml || true'
                sh 'export PYTHONPATH=$PWD:$PWD/backend && python -m pytest backend/tests/test_integration.py -v -o asyncio_mode=auto --junitxml=test-results/backend-integration.xml || true'
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'test-results/*.xml'
                }
            }
        }
        
        // --- 3. BUDOWANIE FRONTENDU (WEB) ---
        stage('Frontend Build (Web)') {
            agent {
                docker {
                    image 'ghcr.io/cirruslabs/flutter:stable'
                    args '-u root -v pub-cache:/root/.pub-cache'
                }
            }
            steps {
                unstash 'source'
                script {
                    def flutterEnv = "dev"
                    if (env.TAG_NAME?.startsWith("v")) {
                        flutterEnv = "prod"
                    }
                    dir('frontend') {
                        sh 'flutter clean'
                        sh 'flutter pub get'
                        sh "flutter build web --release --dart-define=ENV=${flutterEnv}"
                    }
                }
                stash includes: 'frontend/build/web/**/*', name: 'flutter-web'
            }
        }

        // --- 4. DEPLOY NA DEV (Branch main) ---
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
                    
                    echo "🧹 AGRESYWNE CZYSZCZENIE DEV..."
                    sh 'docker stop plannerv2-nginx-dev || true'
                    sh 'docker rm -f plannerv2-nginx-dev || true'
                    
                    sh 'docker stop plannerv2-backend-dev || true'
                    sh 'docker rm -f plannerv2-backend-dev || true'
                    
                    sh 'docker stop plannerv2-db-dev || true'
                    sh 'docker rm -f plannerv2-db-dev || true'
                    
                    sh 'docker network create plannerv2-network || true'
                    
                    echo "🗄️ Start Bazy DEV..."
                    sh '''docker run -d --name plannerv2-db-dev --network plannerv2-network \
                          -e POSTGRES_USER=planner_user -e POSTGRES_PASSWORD=planner_password -e POSTGRES_DB=planner_db \
                          -v plannerv2_postgres_data_dev:/var/lib/postgresql/data --restart unless-stopped postgres:15'''
                    sh 'sleep 10' 
                    
                    echo "🐍 Backend DEV..."
                    sh 'docker build -t plannerv2-backend:dev ./backend'
                    
                    withCredentials([
                        string(credentialsId: 'github-token', variable: 'GH_TOKEN'),
                        string(credentialsId: 'jwt-secret-key', variable: 'JWT_SECRET'),
                        string(credentialsId: 'manager-pin', variable: 'MGR_PIN'),
                        file(credentialsId: 'firebase-admin-key', variable: 'FIREBASE_KEY')
                    ]) {
                        sh """
                            docker run -d --name plannerv2-backend-dev --network plannerv2-network \\
                            -v \${env.FIREBASE_KEY}:/app/firebase-admin-key.json:ro \\
                            -e DATABASE_URL=postgresql://planner_user:planner_password@plannerv2-db-dev:5432/planner_db \\
                            -e GITHUB_TOKEN=\${env.GH_TOKEN} \\
                            -e JWT_SECRET_KEY=\${env.JWT_SECRET} \\
                            -e MANAGER_REGISTRATION_PIN=\${env.MGR_PIN} \\
                            -e ALLOWED_ORIGINS=http://46.225.49.0:8091 \\
                            -e GOOGLE_APPLICATION_CREDENTIALS=/app/firebase-admin-key.json \\
                            --restart unless-stopped plannerv2-backend:dev
                        """
                    }
                    sh 'sleep 10'
                    
                    sh '''
                        if [ "$(docker inspect -f '{{.State.Running}}' plannerv2-backend-dev)" = "false" ]; then
                            echo "❌ Backend DEV padł! Logi:"
                            docker logs plannerv2-backend-dev
                            exit 1
                        fi
                    '''
                    
                    echo "🔍 Weryfikacja migracji bazy danych DEV..."
                    sh '''
                        HEALTH_OK=false
                        for i in 1 2 3 4 5; do
                            HEALTH=$(docker exec plannerv2-backend-dev curl -sf http://localhost:8000/health 2>/dev/null || echo '{}')
                            echo "Health response: $HEALTH"
                            if echo "$HEALTH" | grep -q '"migration_current":true'; then
                                echo "✅ Migracje bazy DEV aktualne"
                                HEALTH_OK=true
                                break
                            else
                                echo "⚠️ Próba $i: Migracje nie gotowe, czekam..."
                                sleep 5
                            fi
                        done
                        if [ "$HEALTH_OK" = "false" ]; then
                            echo "❌ BŁĄD: Migracje bazy DEV nie zakończone!"
                            echo "🔍 Health response: $HEALTH"
                            docker logs plannerv2-backend-dev
                            exit 1
                        fi
                    '''
                    
                    echo "🔧 Nginx DEV Setup..."
                    sh 'git checkout nginx/nginx.conf || true' 
                    sh "sed -i 's/plannerv2-backend/plannerv2-backend-dev/g' nginx/nginx.conf"
                    
                    sh 'docker run -d --name plannerv2-nginx-dev --network plannerv2-network -p 8091:80 --restart unless-stopped nginx:alpine'
                    
                    sh '''
                        echo "⏳ Sprawdzam widoczność Backendu..."
                        DNS_OK=false
                        for i in 1 2 3 4 5 6; do
                            if docker exec plannerv2-nginx-dev ping -c 1 plannerv2-backend-dev; then
                                echo "✅ Połączenie OK!"
                                DNS_OK=true
                                break
                            else
                                echo "⚠️ Próba $i: Backend nie odpowiada, czekam..."
                                sleep 5
                            fi
                        done
                        
                        if [ "$DNS_OK" = "false" ]; then
                            echo "❌ BŁĄD SIECI: Nginx nie widzi Backendu."
                            echo "🔍 Logi Backendu:"
                            docker logs plannerv2-backend-dev
                            exit 1
                        fi
                    '''

                    sh '''
                        docker exec plannerv2-nginx-dev mkdir -p /var/www/plannerv2/web
                        docker exec plannerv2-nginx-dev mkdir -p /var/www/plannerv2/static
                        docker cp frontend/build/web/. plannerv2-nginx-dev:/var/www/plannerv2/web/
                        docker cp nginx/static/. plannerv2-nginx-dev:/var/www/plannerv2/static/
                        docker cp nginx/nginx.conf plannerv2-nginx-dev:/etc/nginx/nginx.conf
                        
                        echo "🔄 Przeładowanie Nginxa..."
                        docker exec plannerv2-nginx-dev nginx -s reload
                    '''
                    
                    echo "✅ DEV gotowy na porcie 8091"
                }
            }
        }
        
        // --- 5. DEPLOY NA PROD (Tylko Tagi v*) ---
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
                    
                    echo "🧹 AGRESYWNE CZYSZCZENIE PROD..."
                    sh 'docker stop plannerv2-nginx || true'
                    sh 'docker rm -f plannerv2-nginx || true'
                    sh 'docker stop plannerv2-backend || true'
                    sh 'docker rm -f plannerv2-backend || true'
                    sh 'docker stop plannerv2-db || true'
                    sh 'docker rm -f plannerv2-db || true'
                    
                    sh 'docker network create plannerv2-network || true'
                    
                    sh '''docker run -d --name plannerv2-db --network plannerv2-network \
                          -e POSTGRES_USER=planner_user -e POSTGRES_PASSWORD=planner_password -e POSTGRES_DB=planner_db \
                          -v plannerv2_postgres_data:/var/lib/postgresql/data --restart unless-stopped postgres:15'''
                    sh 'sleep 10'
                    
                    sh 'docker build -t plannerv2-backend:latest ./backend'
                    
                    withCredentials([
                        string(credentialsId: 'github-token', variable: 'GH_TOKEN'),
                        string(credentialsId: 'jwt-secret-key', variable: 'JWT_SECRET'),
                        string(credentialsId: 'manager-pin', variable: 'MGR_PIN'),
                        file(credentialsId: 'firebase-admin-key', variable: 'FIREBASE_KEY')
                    ]) {
                        sh """
                            docker run -d --name plannerv2-backend --network plannerv2-network \\
                            -v \${env.FIREBASE_KEY}:/app/firebase-admin-key.json:ro \\
                            -e DATABASE_URL=postgresql://planner_user:planner_password@plannerv2-db:5432/planner_db \\
                            -e GITHUB_TOKEN=\${env.GH_TOKEN} \\
                            -e JWT_SECRET_KEY=\${env.JWT_SECRET} \\
                            -e MANAGER_REGISTRATION_PIN=\${env.MGR_PIN} \\
                            -e ALLOWED_ORIGINS=https://restoplan.pl,http://46.225.49.0 \\
                            -e GOOGLE_APPLICATION_CREDENTIALS=/app/firebase-admin-key.json \\
                            --restart unless-stopped plannerv2-backend:latest
                        """
                    }
                    sh 'sleep 10'
                    
                    sh '''
                        if [ "$(docker inspect -f '{{.State.Running}}' plannerv2-backend)" = "false" ]; then
                            echo "❌ Backend PROD padł! Logi:"
                            docker logs plannerv2-backend
                            exit 1
                        fi
                    '''
                    
                    echo "🔍 Weryfikacja migracji bazy danych PROD..."
                    sh '''
                        HEALTH_OK=false
                        for i in 1 2 3 4 5; do
                            HEALTH=$(docker exec plannerv2-backend curl -sf http://localhost:8000/health 2>/dev/null || echo '{}')
                            echo "Health response: $HEALTH"
                            if echo "$HEALTH" | grep -q '"migration_current":true'; then
                                echo "✅ Migracje bazy PROD aktualne"
                                HEALTH_OK=true
                                break
                            else
                                echo "⚠️ Próba $i: Migracje nie gotowe, czekam..."
                                sleep 5
                            fi
                        done
                        if [ "$HEALTH_OK" = "false" ]; then
                            echo "❌ BŁĄD: Migracje bazy PROD nie zakończone!"
                            echo "🔍 Health response: $HEALTH"
                            docker logs plannerv2-backend
                            exit 1
                        fi
                    '''
                    
                    sh 'git checkout nginx/nginx.conf || true'
                    
                    sh 'docker run -d --name plannerv2-nginx --network plannerv2-network -p 8090:80 --restart unless-stopped nginx:alpine'
                    
                    sh '''
                        echo "⏳ Sprawdzam DNS dla Produkcji..."
                        DNS_OK=false
                        for i in 1 2 3 4 5; do
                            if docker exec plannerv2-nginx ping -c 1 plannerv2-backend; then
                                echo "✅ DNS OK"
                                DNS_OK=true
                                break
                            else
                                sleep 5
                            fi
                        done
                        
                        if [ "$DNS_OK" = "false" ]; then
                            exit 1
                        fi
                    '''
                    
                    sh '''
                        docker exec plannerv2-nginx mkdir -p /var/www/plannerv2/web
                        docker exec plannerv2-nginx mkdir -p /var/www/plannerv2/static
                        docker cp frontend/build/web/. plannerv2-nginx:/var/www/plannerv2/web/
                        docker cp nginx/static/. plannerv2-nginx:/var/www/plannerv2/static/
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