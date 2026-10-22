# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v2.2.1] - 2026-10-22

### Added
- **Podgląd i filtrowanie logów systemowych w panelu Superadmina**:
  - Dedykowana zakładka „Logi systemowe” w panelu Superadmina z możliwością filtrowania logów per restauracja (tenant) oraz po poziomie logowania (`INFO`, `WARNING`, `ERROR`, `CRITICAL`, `DEBUG`).
  - Wyszukiwarka tekstowa, rozwijanie wieloliniowych tracebacków z możliwością kopiowania do schowka oraz przycisk czyszczenia logów.
  - Skrót „Logi” bezpośrednio na liście restauracji umożliwiający natychmiastowe przejście do logów danego lokalu.
  - Backendowy serwis `LogService` z mechanizmem `TenantLogFilter` wstrzykującym identyfikator restauracji `[tenant:X]` do każdego rekordu logów oraz rejestracją zapytań HTTP middleware.
  - Bezpieczne endpointy API `GET /sysadmin/logs` oraz `DELETE /sysadmin/logs` dostępne wyłącznie dla superadministratorów.

### Fixed
- **Zgodność z trybem stron pamięci 16 KB (Android 15+)**:
  - Aktualizacja CameraX do wersji `1.4.1` oraz wdrożenie Google Play Services unbundled ML Kit Barcode Scanning (`dev.steenbakker.mobile_scanner.useUnbundled=true`) eliminujące biblioteki natywne skompilowane z rozmiarem stron 4 KB.
- **Optymalizacje pipeline'u CI/CD i bazy danych**:
  - Zabezpieczenie `pg_dump` limitem czasowym oraz automatyczne zwalnianie transakcji `idle in transaction` blokujących migracje Alembic.
  - Zapewnienie buforowania logów w trybie unbuffered dla kontenerów backendowych.

## [v2.2.0] - 2026-10-15

### Added
- **Web Push Notifications (FCM & PWA)**:
  - Dedykowany Service Worker Firebase dla przeglądarek (`frontend/web/firebase-messaging-sw.js`) z obsługą komunikatów w tle (`onBackgroundMessage`), systemowymi notyfikacjami oraz akcją powrotu do aplikacji (`notificationclick`).
  - Obsługa parametru `FCM_VAPID_KEY` w aplikacji Flutter (`PushService.vapidKey`).
  - Wieloplatformowa obsługa powiadomień w trybie pierwszoplanowym (Foreground) z podwójną sygnalizacją: natywnym powiadomieniem przeglądarki (HTML5 Notification API za pośrednictwem `package:web`) oraz widocznym banerem `MaterialBanner` (`ScaffoldMessenger`).
  - Interaktywny panel statusu i żądania uprawnień powiadomień w oknie dialogowym `NotificationBell`, spełniający rygorystyczny wymóg bezpośredniego gestu użytkownika (User Gesture) w przeglądarkach Safari iOS PWA oraz Chrome.
  - Optymalizacja konfiguracji PWA dla urządzeń Apple iOS: uzupełnienie meta-tagów `apple-mobile-web-app-capable`, `apple-mobile-web-app-status-bar-style` oraz `apple-touch-icon`.
  - Konfiguracja reguł buforowania Nginx: wyłączenie pamięci podręcznej dla `/firebase-messaging-sw.js` oraz `/flutter_service_worker.js` za pomocą nagłówka `Cache-Control: no-cache, no-store, must-revalidate`.

- **Ujednolicona Obsługa Błędów Sieciowych i Walidacja Haseł**:
  - Utworzenie modułu `ApiErrorHandler` oraz klasy `FriendlyDioException` w aplikacji Flutter, tłumaczących kody statusu HTTP, listy błędów walidacji Pydantic 422, słowniki i ciągi tekstowe z backendu na czytelne komunikaty w języku polskim.
  - Wprowadzenie ujednoliconej polityki silnych haseł: minimum 8 znaków, co najmniej jedna wielka litera oraz co najmniej jedna cyfra.
  - Walidacja reguł haseł po stronie formularzy frontendowych (`ApiErrorHandler.validatePassword`) oraz w schematach Pydantic backendu (`PasswordChangeRequest`, `ManagerCreateRequest`).
  - Standaryzacja obsługi błędów na ekranie logowania, w panelu pracownika (zmiana hasła), w module zespołu managera (dodawanie pracownika, reset hasła) oraz w panelu Superadmina (tworzenie restauracji, dodawanie managera, reset hasła).

### Changed
- **Profesjonalizacja Dokumentacji**:
  - Usunięcie wszystkich emotikonów z plików dokumentacji repozytorium w celu zapewnienia spójnego, profesjonalnego formatowania.
  - Aktualizacja specyfikacji architektonicznej powiadomień wypychanych (`PUSH_ARCHITECTURE.md`).

## [v2.1.1] - 2026-10-15

### Fixed
- **Google Calendar Token Expiration & Re-auth**:
  - `get_google_calendar_status` weryfikuje teraz faktyczną ważność i możliwość odświeżenia tokena Google. W przypadku wygaśnięcia tokena zwraca stan braku połączenia z informacją o konieczności ponownej autoryzacji zamiast mylącego statusu „połączony”.
  - `sync_user_schedules` sprawdza ważność tokena przed rozpoczęciem synchronizacji i zwraca czytelne komunikaty o błędach w języku polskim w przypadku wygaśnięcia sesji lub niepowodzenia synchronizacji zmian.
  - Dialog Google Calendar w panelu pracownika poprawnie wyświetla stan wygaśnięcia sesji, umożliwia ponowne połączenie jednym kliknięciem oraz informuje o szczegółach błędów w komunikatach ostrzegawczych.
  - W `publish_schedule` synchronizacja kalendarza Google jest teraz zlecana dla wszystkich pracowników posiadających opublikowane zmiany w danym tygodniu (w tym przy ponownej publikacji grafiku), a nie tylko dla nowo utworzonych wpisów.

## [v2.1.0] - 2026-10-15

### Multi-Tenancy Architecture & Global Superadmin
- **Multi-Tenancy (Wielodostępność lokali)**:
  - Wprowadzenie modelu lokalu (`Tenant` / `RestaurantConfig`) z unikalnym identyfikatorem logowania (`slug` / Login ID).
  - Pełna izolacja danych w bazie: każdy zasób powiązany z `tenant_id`.
  - **Dual-Login**: Możliwość logowania za pomocą unikalnego adresu `email` LUB kombinacji `username` + `Login ID` (tenant slug).
  - Integracja tokenów JWT z identyfikatorem lokalu i uprawnieniami.
- **Panel Superadmina (SysAdmin Dashboard)**:
  - Globalny panel administracyjny pod ścieżką `/#/superadmin` dla kont z uprawnieniem `is_superadmin`.
  - Zarządzanie lokalami: rejestracja nowych restauracji, edycja parametrów lokalu, statystyki.
  - Globalne zarządzanie użytkownikami: tworzenie pierwszych kont menedżerów dla restauracji, awaryjny reset haseł.

### Harmonogram i Zarządzanie Grafikami
- **Direct Shift Swap (Bezpośrednia wymiana zmian)**:
  - Opcja „Wymień” przy zmianach współpracowników posiadających tę samą rolę w widoku zespołu.
  - Interaktywny wybór własnej zmiany do oddania z natychmiastową walidacją kolizji terminów.
  - Obieg akceptacji/odrzucenia propozycji wymiany w panelu pracownika i managera.
- **Draft Schedules & 11h Rest Warnings (Grafiki robocze)**:
  - Wprowadzenie statusu roboczego grafiku (`is_published`).
  - Ostrzeżenia przed naruszeniem kodeksowego 11-godzinnego odpoczynku dobowego między kolejnymi zmianami.
  - Opcja jednoklikowej publikacji grafiku dla zespołu.
- **Whole Team Schedule View (Widok całego zespołu)**:
  - Przełącznik widoku u pracownika („Moje zmiany” / „Cała załoga”) z podglądem pełnego grafiku lokalu.
- **Shift Audit Log (Historia i audyt zmian)**:
  - Tabela `shiftauditlog` rejestrująca każde utworzenie, zmianę godzin, edycję przypisania i usunięcie zmiany wraz z autorem operacji.
  - Podgląd historii zmian w panelu managera.
- **Giełda zmian (Giveaway Claims)**:
  - Wymuszenie walidacji ról: pracownik może przejąć zmianę z giełdy tylko wtedy, gdy posiada wymaganą dla niej rolę.

### Bezpieczeństwo i UX
- **Browser Password Saving (Obsługa menedżerów haseł)**:
  - Autofill hints (`AutofillHints.username`, `AutofillHints.password`) oraz struktura `AutofillGroup` na formularzu logowania.
- **Google Calendar Sync Hardening**:
  - Zabezpieczenie tokenów OAuth, bezpieczne wyzwalacze synchronizacji w tle i dedykowany in-memory test session context.
- **Uprawnienia i ochrona przed eskalacją**:
  - Blokada możliwości nadania uprawnień superadmina oraz modyfikacji `tenant_id` przez managera lokalu.
  - Automatyczne usuwanie tokenów FCM przy deaktywacji konta pracownika.

### Baza danych, CI/CD i Testy
- **PostgreSQL Compatibility**:
  - Dodanie biblioteki `psycopg[binary]` dla SQLAlchemy 2.1 i automatyczna normalizacja prefiksu `postgres://` na `postgresql://`.
  - Sekwencje PostgreSQL i obsługa transakcji w migracjach Alembic.
- **Migracja JWT**:
  - Pełna migracja z `python-jose` na `PyJWT`.
- **Stabilizacja testów i CI (Jenkins)**:
  - Uruchamianie pełnego pakietu 256 testów backendu w Jenkins CI z generowaniem raportów JUnit XML.
  - Dynamiczne generowanie kluczy `JWT_SECRET_KEY`, `ENCRYPTION_KEY` i `MANAGER_REGISTRATION_PIN` w locie w kontenerze CI.
  - Usunięcie pakietu `trio` i narzucenie `anyio_backend = "asyncio"`.
  - Rozwiązanie problemów stref czasowych (`datetime.now(timezone.utc)`) w `pos_service.py` oraz `test_kds.py`.
- **Porządki w repozytorium (Cleanup)**:
  - Usunięcie zbędnych plików tymczasowych, logów błędów i plików roboczych.
