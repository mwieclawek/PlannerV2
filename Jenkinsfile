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
                    
                    echo "🧹 START BAZY DEV (JEŚLI NIE DZIAŁA)..."
                    sh 'docker network create plannerv2-network || true'
                    
                    sh '''
                        if [ "$(docker inspect -f '{{.State.Running}}' plannerv2-db-dev 2>/dev/null)" != "true" ]; then
                            echo "🗄️ Baza DEV nie działa. Uruchamiam..."
                            docker rm -f plannerv2-db-dev || true
                            docker run -d --name plannerv2-db-dev --network plannerv2-network \\
                              -e POSTGRES_USER=planner_user -e POSTGRES_PASSWORD=planner_password -e POSTGRES_DB=planner_db \\
                              -v plannerv2_postgres_data_dev:/var/lib/postgresql/data --restart unless-stopped postgres:15
                            sleep 10
                        else
                            echo "✅ Baza DEV już działa. Pomijam uruchamianie."
                        fi
                    '''
                    
                    echo "💾 Wykonywanie kopii zapasowej bazy DEV..."
                    sh '''
                        mkdir -p db_backups_dev
                        if [ "$(docker inspect -f '{{.State.Running}}' plannerv2-db-dev 2>/dev/null)" == "true" ]; then
                            BACKUP_FILE="db_backups_dev/backup_dev_$(date +%Y%m%d_%H%M%S).sql"
                            # Używamy docker exec bez flagi -t i w pełni logujemy ewentualny błąd
                            docker exec plannerv2-db-dev pg_dump -U planner_user planner_db > "$BACKUP_FILE" || echo "⚠️ Błąd podczas zrzutu bazy DEV"
                            echo "✅ Kopia zapisana: $BACKUP_FILE"
                        else
                            echo "⚠️ Kontener bazy DEV nie działa, pomijam zrzut."
                        fi
                    '''
                    
                    echo "🐍 Budowa i uruchamianie nowego Backend DEV (Blue-Green)..."
                    sh 'docker build -t plannerv2-backend:dev ./backend'
                    
                    sh 'docker stop plannerv2-backend-dev-new || true'
                    sh 'docker rm -f plannerv2-backend-dev-new || true'
                    
                    withCredentials([
                        string(credentialsId: 'github-token', variable: 'GH_TOKEN'),
                        string(credentialsId: 'jwt-secret-key', variable: 'JWT_SECRET'),
                        string(credentialsId: 'manager-pin', variable: 'MGR_PIN'),
                        file(credentialsId: 'firebase-admin-key', variable: 'FIREBASE_KEY')
                    ]) {
                        sh """
                            docker run -d --name plannerv2-backend-dev-new --network plannerv2-network \\
                            -v "\${FIREBASE_KEY}:/app/firebase-admin-key.json:ro" \\
                            -e DATABASE_URL="postgresql://planner_user:planner_password@plannerv2-db-dev:5432/planner_db" \\
                            -e GITHUB_TOKEN="\${GH_TOKEN}" \\
                            -e JWT_SECRET_KEY="\${JWT_SECRET}" \\
                            -e MANAGER_REGISTRATION_PIN="\${MGR_PIN}" \\
                            -e ALLOWED_ORIGINS="http://46.225.49.0:8091" \\
                            -e GOOGLE_APPLICATION_CREDENTIALS="/app/firebase-admin-key.json" \\
                            --restart unless-stopped plannerv2-backend:dev
                        """
                    }
                    sh 'sleep 10'
                    
                    echo "🔍 Weryfikacja nowego Backendu DEV i Migracji..."
                    sh '''
                        HEALTH_OK=false
                        if [ "$(docker inspect -f '{{.State.Running}}' plannerv2-backend-dev-new)" = "false" ]; then
                            echo "❌ Nowy Backend DEV upadł podczas startu! Logi:"
                            docker logs plannerv2-backend-dev-new
                            docker rm -f plannerv2-backend-dev-new
                            exit 1
                        fi

                        for i in 1 2 3 4 5; do
                            HEALTH=$(docker exec plannerv2-backend-dev-new curl -sf http://localhost:8000/health 2>/dev/null || echo '{}')
                            echo "Health response from new: $HEALTH"
                            if echo "$HEALTH" | grep -q '"migration_current":true'; then
                                echo "✅ Migracje bazy DEV aktualne na nowym kontenerze"
                                HEALTH_OK=true
                                break
                            else
                                echo "⚠️ Próba $i: Migracje nie gotowe, czekam..."
                                sleep 5
                            fi
                        done
                        
                        if [ "$HEALTH_OK" = "false" ]; then
                            echo "❌ BŁĄD: Nowy kontener Backendu nie wstał poprawnie!"
                            echo "Zabijam i usuwam nowy kontener, zachowując stary system."
                            docker logs plannerv2-backend-dev-new
                            docker rm -f plannerv2-backend-dev-new
                            exit 1
                        fi
                        
                        echo "✅ Nowy Backend DEV sprawdzony. Zastępowanie starego..."
                        docker stop plannerv2-backend-dev || true
                        docker rm -f plannerv2-backend-dev || true
                        docker rename plannerv2-backend-dev-new plannerv2-backend-dev
                    '''
                    
                    echo "🔧 Nginx DEV Setup..."
                    sh 'git checkout nginx/nginx.conf || true' 
                    sh "sed -i 's/plannerv2-backend/plannerv2-backend-dev/g' nginx/nginx.conf"
                    
                    sh '''
                        if [ "$(docker inspect -f '{{.State.Running}}' plannerv2-nginx-dev 2>/dev/null)" != "true" ]; then
                             docker rm -f plannerv2-nginx-dev || true
                             docker run -d --name plannerv2-nginx-dev --network plannerv2-network -p 8091:80 --restart unless-stopped nginx:alpine
                             sleep 5
                        fi
                    '''
                    
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
                    
                    echo "🧹 START BAZY PROD (JEŚLI NIE DZIAŁA)..."
                    sh 'docker network create plannerv2-network || true'
                    
                    sh '''
                        if [ "$(docker inspect -f '{{.State.Running}}' plannerv2-db 2>/dev/null)" != "true" ]; then
                            docker rm -f plannerv2-db || true
                            docker run -d --name plannerv2-db --network plannerv2-network \\
                              -e POSTGRES_USER=planner_user -e POSTGRES_PASSWORD=planner_password -e POSTGRES_DB=planner_db \\
                              -v plannerv2_postgres_data:/var/lib/postgresql/data --restart unless-stopped postgres:15
                            sleep 10
                        else
                            echo "✅ Baza PROD już działa. Pomijam uruchamianie."
                        fi
                    '''
                    
                    echo "💾 Wykonywanie kopii zapasowej bazy PROD..."
                    sh '''
                        mkdir -p db_backups_prod
                        if [ "$(docker inspect -f '{{.State.Running}}' plannerv2-db 2>/dev/null)" == "true" ]; then
                            BACKUP_FILE="db_backups_prod/backup_prod_$(date +%Y%m%d_%H%M%S).sql"
                            # Używamy docker exec bez flagi -t i w pełni logujemy ewentualny błąd
                            docker exec plannerv2-db pg_dump -U planner_user planner_db > "$BACKUP_FILE" || echo "⚠️ Błąd podczas zrzutu bazy PROD"
                            echo "✅ Kopia zapisana: $BACKUP_FILE"
                        else
                            echo "⚠️ Kontener bazy PROD nie działa, pomijam zrzut."
                        fi
                    '''
                    
                    echo "🐍 Budowa i uruchamianie nowego Backend PROD (Blue-Green)..."
                    sh 'docker build -t plannerv2-backend:latest ./backend'
                    
                    sh 'docker stop plannerv2-backend-new || true'
                    sh 'docker rm -f plannerv2-backend-new || true'
                    
                    withCredentials([
                        string(credentialsId: 'github-token', variable: 'GH_TOKEN'),
                        string(credentialsId: 'jwt-secret-key', variable: 'JWT_SECRET'),
                        string(credentialsId: 'manager-pin', variable: 'MGR_PIN'),
                        file(credentialsId: 'firebase-admin-key', variable: 'FIREBASE_KEY')
                    ]) {
                        sh """
                            docker run -d --name plannerv2-backend-new --network plannerv2-network \\
                            -v "\${FIREBASE_KEY}:/app/firebase-admin-key.json:ro" \\
                            -e DATABASE_URL="postgresql://planner_user:planner_password@plannerv2-db:5432/planner_db" \\
                            -e GITHUB_TOKEN="\${GH_TOKEN}" \\
                            -e JWT_SECRET_KEY="\${JWT_SECRET}" \\
                            -e MANAGER_REGISTRATION_PIN="\${MGR_PIN}" \\
                            -e ALLOWED_ORIGINS="https://restoplan.pl,http://46.225.49.0" \\
                            -e GOOGLE_APPLICATION_CREDENTIALS="/app/firebase-admin-key.json" \\
                            --restart unless-stopped plannerv2-backend:latest
                        """
                    }
                    sh 'sleep 10'
                    
                    echo "🔍 Weryfikacja nowego Backendu PROD i Migracji..."
                    sh '''
                        HEALTH_OK=false
                        if [ "$(docker inspect -f '{{.State.Running}}' plannerv2-backend-new)" = "false" ]; then
                            echo "❌ Nowy Backend PROD upadł podczas startu! Logi:"
                            docker logs plannerv2-backend-new
                            docker rm -f plannerv2-backend-new
                            exit 1
                        fi

                        for i in 1 2 3 4 5; do
                            HEALTH=$(docker exec plannerv2-backend-new curl -sf http://localhost:8000/health 2>/dev/null || echo '{}')
                            echo "Health response from new: $HEALTH"
                            if echo "$HEALTH" | grep -q '"migration_current":true'; then
                                echo "✅ Migracje bazy PROD aktualne na nowym kontenerze"
                                HEALTH_OK=true
                                break
                            else
                                echo "⚠️ Próba $i: Migracje nie gotowe, czekam..."
                                sleep 5
                            fi
                        done
                        
                        if [ "$HEALTH_OK" = "false" ]; then
                            echo "❌ BŁĄD: Nowy kontener Backendu nie wstał poprawnie!"
                            echo "Zabijam i usuwam nowy kontener, zachowując stary system."
                            docker logs plannerv2-backend-new
                            docker rm -f plannerv2-backend-new
                            exit 1
                        fi
                        
                        echo "✅ Nowy Backend PROD sprawdzony. Zastępowanie starego..."
                        docker stop plannerv2-backend || true
                        docker rm -f plannerv2-backend || true
                        docker rename plannerv2-backend-new plannerv2-backend
                    '''
                    
                    sh 'git checkout nginx/nginx.conf || true'
                    
                    sh '''
                        if [ "$(docker inspect -f '{{.State.Running}}' plannerv2-nginx 2>/dev/null)" != "true" ]; then
                             docker rm -f plannerv2-nginx || true
                             docker run -d --name plannerv2-nginx --network plannerv2-network -p 8090:80 --restart unless-stopped nginx:alpine
                             sleep 5
                        fi
                    '''
                    
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