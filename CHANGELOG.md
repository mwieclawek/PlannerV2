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

## [v2.2.0] - 2026-10-20

### Added
- **Moduły operacyjne WFM i rozszerzenia konfiguracji**:
  - Opcjonalny moduł zamknięcia dnia (`enable_daily_closeout`) w konfiguracji lokalu.
  - Warunkowe ukrywanie kafelka puli napiwków (Tip Pooling) na pulpicie, gdy moduł jest wyłączony w lokalu.
  - Konfigurowalny wymóg wykonania checklisty (`require_checklists_for_attendance`) przy rejestracji zakończenia czasu pracy (check-out).
  - Bezpośrednie prośby o wymianę zmian (A <-> B) wyświetlane priorytetowo na ekranie głównym (Home) u zaangażowanych pracowników oraz managera.
  - Moduły operacyjne: checklisty otwarcia/zamknięcia, rejestry i alerty HACCP, ewidencja płacowa (payroll) z maskowaniem danych wrażliwych oraz ogłoszenia zespołowe.
- **Web Push Notifications (FCM & PWA)**:
  - Dedykowany Service Worker Firebase dla przeglądarek (`frontend/web/firebase-messaging-sw.js`) z obsługą komunikatów w tle (`onBackgroundMessage`), systemowymi notyfikacjami oraz akcją powrotu do aplikacji (`notificationclick`).
  - Obsługa parametru `FCM_VAPID_KEY` w aplikacji Flutter (`PushService.vapidKey`).
  - Wieloplatformowa obsługa powiadomień w trybie pierwszoplanowym (Foreground) z podwójną sygnalizacją: natywnym powiadomieniem przeglądarki (HTML5 Notification API za pośrednictwem `package:web`) oraz widocznym banerem `MaterialBanner` (`ScaffoldMessenger`).
  - Interaktywny panel statusu i żądania uprawnień powiadomień w oknie dialogowym `NotificationBell`, spełniający wymóg bezpośredniego gestu użytkownika w przeglądarkach Safari iOS PWA oraz Chrome.
  - Optymalizacja konfiguracji PWA dla urządzeń Apple iOS: meta-tagi `apple-mobile-web-app-capable`, `apple-mobile-web-app-status-bar-style` oraz `apple-touch-icon`.
  - Konfiguracja reguł buforowania Nginx: wyłączenie pamięci podręcznej dla `/firebase-messaging-sw.js` oraz `/flutter_service_worker.js`.
- **Ujednolicona Obsługa Błędów Sieciowych i Walidacja Haseł**:
  - Moduł `ApiErrorHandler` oraz klasa `FriendlyDioException` w aplikacji Flutter tłumaczące kody statusu HTTP, listy błędów walidacji Pydantic 422 i wyjątki sieciowe na komunikaty w języku polskim.
  - Ujednolicona polityka silnych haseł: minimum 8 znaków, co najmniej jedna wielka litera oraz co najmniej jedna cyfra.
  - Walidacja reguł haseł po stronie formularzy frontendowych (`ApiErrorHandler.validatePassword`) oraz w schematach Pydantic backendu (`PasswordChangeRequest`, `ManagerCreateRequest`).

### Changed
- **Interfejs Użytkownika SaaS**:
  - Odświeżenie wyglądu pulpitów na nowoczesny interfejs kartowy SaaS z responsywnym bocznym paskiem nawigacyjnym (desktop hover sidebar) oraz obsługą preferencji zapamiętywania logowania (Remember Me).
  - Skrócenie identyfikatorów rewizji Alembic do 32 znaków oraz wprowadzenie testów integralności grafu migracji.

## [v2.1.2] - 2026-10-15

### Added
- **Trwała synchronizacja Google Calendar w przeglądarkach (Web)**:
  - Wdrożenie procedury pobierania jednorazowego kodu autoryzacyjnego serwera (`serverAuthCode`) w środowisku przeglądarkowym i wymiana na trwały token odświeżający (`offline refresh token`).
  - Automatyczne wznawianie wygasłych sesji synchronizacji grafików bez konieczności ponownego logowania przez użytkownika.

## [v2.1.1] - 2026-10-15

### Fixed
- **Google Calendar Token Expiration & Re-auth**:
  - `get_google_calendar_status` weryfikuje faktyczną ważność i możliwość odświeżenia tokena Google; w przypadku wygaśnięcia zwraca stan braku połączenia z informacją o konieczności ponownej autoryzacji.
  - `sync_user_schedules` sprawdza ważność tokena przed rozpoczęciem synchronizacji i zwraca czytelne komunikaty o błędach w języku polskim.
  - Okno dialogowe Google Calendar w panelu pracownika poprawnie wyświetla stan wygaśnięcia sesji i umożliwia ponowne połączenie.
  - W procedurze `publish_schedule` synchronizacja kalendarza Google jest zlecana dla wszystkich pracowników posiadających opublikowane zmiany w danym tygodniu (w tym przy ponownej publikacji).

## [v2.1.0] - 2026-10-15

### Added
- **Wielodostępność i Panel Superadmina**:
  - Wprowadzenie architektury Multi-Tenancy: model lokalu `Tenant` / `RestaurantConfig` z unikalnym identyfikatorem logowania (`slug`).
  - Pełna separacja zasobów bazodanowych za pomocą kolumny `tenant_id` i zależności `require_tenant`.
  - Tryb Dual-Login: logowanie globalnym adresem `email` LUB parą `username` + `Login ID` (slug).
  - Panel Superadmina pod ścieżką `/#/superadmin` do rejestracji restauracji, podglądu użytkowników i zarządzania kontami menedżerów.
- **Zarządzanie Zmianami i Grafikami**:
  - Bezpośrednia wymiana zmian (Direct Shift Swap) z poziomu widoku całego zespołu wraz z weryfikacją kolizji czasowych i ról.
  - Tryb szkicu grafiku (Draft Schedules: wygeneruj -> zapisz szkic -> opublikuj).
  - Rejestr audytu operacji na zmianach (Shift Audit Log).
  - Ostrzeżenia o naruszeniu 11-godzinnego odpoczynku dobowego w solverze grafików.

### Fixed
- Dostosowanie dialektu PostgreSQL do SQLAlchemy 2.x (`psycopg[binary]`) i normalizacja schematu połączeń.
- Rozwiązanie problemów ze strefami czasowymi w testach backendowych.

## [v2.0.0] - 2026-10-10

### Added
- **Multi-Tenant Architecture & Superadmin Panel**:
  - Fundamenty architektury wielodostępnej w modelach bazy danych i tokenach JWT.
  - Pierwsza wersja dedykowanego panelu Superadmina do obsługi wielu lokali gastronomicznych.
  - Izolacja danych operacyjnych (role, definicje zmian, pracownicy, grafiki, obecności).

### Security
- Migracja mechanizmów weryfikacji tokenów JWT do biblioteki PyJWT.
- Walidacja uprawnień administracyjnych na poziomie globalnym.

## [v1.7.3] - 2026-09-24

### Fixed
- **Google Calendar Conflict Handling**:
  - Obsługa tworzenia wydarzeń za pomocą żądania POST z automatycznym fallbackiem na PUT (aktualizacja) w przypadku napotkania błędu konfliktu HTTP 409.

## [v1.7.2] - 2026-09-24

### Added
- **Prezentacja i synchronizacja kalendarza**:
  - Dołączanie nazwy restauracji do tytułów wydarzeń tworzonych w Kalendarzu Google.
  - Automatyczna synchronizacja kalendarza w momencie przejęcia lub ponownego przypisania zmiany na giełdzie zmian.

## [v1.7.1] - 2026-09-24

### Fixed
- Usprawnienia automatycznej i ręcznej synchronizacji grafików z Kalendarzem Google.

## [v1.7.0] - 2026-09-24

### Added
- **Google Calendar Integration**:
  - Automatyczna i ręczna synchronizacja opublikowanych zmian pracowniczych z Kalendarzem Google.
  - Bezpieczne łączenie tokenów dostępowych OAuth 2.0 i szyfrowanie kluczy w bazie danych za pomocą biblioteki `cryptography` (Fernet).

## [v1.6.7] - 2026-09-23

### Fixed
- Precyzyjne wyodrębnianie szczegółowych komunikatów o błędach Google OAuth z odpowiedzi biblioteki Dio we frontendzie.

## [v1.6.6] - 2026-09-23

### Added
- Dynamiczne wstrzykiwanie zmiennych `APP_VERSION` oraz `BUILD_DATE` podczas kompilacji produkcyjnej Flutter Web w pipeline Jenkins.
- Prezentacja numeru wersji i daty budowy na ekranie logowania.
- Obsługa dat ze świadomością stref czasowych (timezone-aware datetimes) oraz widok harmonogramu zespołu dla pracowników.

## [v1.6.5] - 2026-07-25

### Added
- **POS v2 & KDS Offline-First**:
  - Nowy backend POS v2 z mechanizmem synchronizacji offline-first dla tabletów kuchennych KDS.
  - Silnik Pacing Engine synchronizujący czasy przygotowania poszczególnych dań w kursach.
  - Globalny tryb serwisowy (Kill Switch / Maintenance Mode) blokujący logowanie do aplikacji.

### Fixed
- Poprawka wartości domyślnej typu boolean w migracji PostgreSQL (użycie `true` zamiast `1`).

## [v1.6.4] - 2026-03-25

### Added
- Przełącznik aktywacji modułu POS w konfiguracji restauracji.
- Schematy bazy danych dla modułów POS i KDS (stoliki, strefy sali, menu dań, modyfikatory i zamówienia kuchenne).

### Fixed
- Konfiguracja Nginx: dodanie brakującego proxy dla ścieżki `/kitchen` zapobiegające zwracaniu odpowiedzi HTML zamiast JSON.
- Obsługa pustych lub niepoprawnych danych godzin otwarcia lokalu podczas zapisu konfiguracji.

## [v1.6.3] - 2026-03-02

### Added
- Rozdzielenie okna przypisywania pracowników w grafiku na edytowalny stan UNAVAILABLE oraz zablokowany stan ALREADY_SCHEDULED.

## [v1.6.2] - 2026-03-02

### Fixed
- Usunięcie rozbieżności w sugerowaniu zastępstw przy oddawaniu zmian na giełdzie.
- Ustawienie domyślnego fallbacku solvera grafików na status UNKNOWN.

## [v1.6.1] - 2026-03-02

### Added
- Automatyczne tworzenie kopii zapasowych bazy danych (`pg_dump`) w Jenkinsie przed wdrożeniem nowych kontenerów.
- Migracja zarządzania stanem frontendu na Riverpod.
- Wdrożenie zaawansowanego algorytmu harmonogramowania Google OR-Tools CP-SAT.
- Konfiguracja środowiska budowania aplikacji Android.

## [v1.6.0] - 2026-02-25

### Added
- Statyczne podstrony `/privacy` i `/about` na potrzeby weryfikacji aplikacji w Google OAuth.
- Odświeżenie wyglądu zakładek `SchedulerWrapperTab` oraz `AttendanceApprovalTab`.

## [v1.5.4] - 2026-02-25

### Fixed
- Otwieranie linków do polityki prywatności w nowej karcie przeglądarki w celu uniknięcia pobierania pliku HTML na platformie Web.
- Poprawka aliasów ścieżek statycznych w konfiguracji Nginx.

## [v1.5.3] - 2026-02-24

### Security
- Utwardzenie bezpieczeństwa backendu: pobieranie sekretów JWT ze środowiska, restrykcyjna biała lista CORS, polityka złożoności haseł, hashowanie kodów PIN managera, obsługa tokenów odświeżających.

### Added
- Moduł wniosków urlopowych pracownika z weryfikacją dostępności po stronie managera.
- Przepisywanie testów integracyjnych na asynchroniczne fixtures `pytest`.

## [v1.5.2] - 2026-02-23

### Added
- Inicjalizacja usług Firebase oraz Firebase Crashlytics.
- Utworzenie wieloplatformowych zestawów ikon i brandingu Planista dla platform Android oraz iOS.

## [v1.5.1] - 2026-02-20

### Added
- Widget siatki dostępności (`AvailabilityGrid`) umożliwiający pracownikom intuicyjne deklarowanie dyspozycyjności na poszczególne dni i zmiany.
- Zakładki managera do podglądu dyspozycyjności całego zespołu oraz giełdy oddawania zmian.

## [v1.5.0] - 2026-02-18

### Added
- Moduł zatwierdzania obecności przez managera z możliwością ręcznego wprowadzania wpisów i eksportem do formatu PDF.
- Nowy zestaw testów integracyjnych API uwierzytelniania i harmonogramowania.

### Fixed
- Solver grafików: uwzględnianie pracowników posiadających status dyspozycyjności `AVAILABLE`.

## [v1.4.2] - 2026-02-14

### Added
- Obsługa konfiguracji adresu serwera za pomocą kodu QR (`ConfigService`) oraz wprowadzania ręcznego.
- Integracja ze statystykami Google Analytics.
- Wstępna konfiguracja Gradle dla aplikacji mobilnej Android.

## [v1.4.1] - 2026-02-13

### Added
- Zarządzanie personelem — interfejsy API i widoki managera do przeglądania statystyk, godzin oraz edycji danych pracowników.

## [v1.4.0] - 2026-02-12

### Added
- Panel statystyk obsady w generatorze grafiku.
- Eksport zestawień czasu pracy do formatu PDF.
- Automatyczne dopasowywanie kolorów dla stanowisk pracowniczych.

### Fixed
- Rozwiązanie problemów z wtyczkami przeglądarkowymi Flutter poprzez czyszczenie środowiska (`flutter clean`) w potoku CI/CD.
- Wymuszenie unieważniania pamięci podręcznej przeglądarek (`cache busting`) dla pliku `flutter_bootstrap.js`.

## [v1.3.1] - 2026-02-10

### Fixed
- Wsteczna kompatybilność weryfikacji haseł zahashowanych za pomocą bcrypt dla istniejących kont na produkcji.
- Poprawki w testach jednostkowych dotyczące przejścia z adresu e-mail na nazwę użytkownika (`username`).

## [v1.3.0] - 2026-02-10

### Added
- Wprowadzenie pola `username` w tabeli użytkowników z zachowaniem opcjonalności adresu `email`.
- Wydłużenie okresu ważności tokenów dostępowych JWT do 24 godzin.
- Wdrożenie automatycznych migracji Alembic przy uruchamianiu kontenera bazy danych.

## [v1.2.0] - 2026-02-09

### Added
- RestoPlan V2 — system ewidencji czasu pracy (rejestracja wejść i wyjść pracowników).
- Widok dostępności zespołu dla managera i podział aplikacji na zakładki funkcyjne.

## [v1.0.4] - 2026-02-08

### Fixed
- Pętla oczekiwania na rozwiązywanie nazw DNS dla kontenera backendu przed załadowaniem konfiguracji Nginx.

## [v1.0.3] - 2026-02-08

### Changed
- Usprawnienie procedury wdrażania kontenera Nginx w potoku Jenkins przy użyciu poleceń `docker run -d` oraz `docker exec`.

## [v1.0.2] - 2026-02-08

### Added
- Podstawowe pulpity pracownika i managera z obsługą logowania, tygodniowym grafikiem, zgłaszaniem dyspozycji i rejestracją obecności.

## [v1.0] - 2026-02-06

### Added
- Pierwsza wersja produkcyjna aplikacji: backend FastAPI z bazą SQLite/PostgreSQL, interfejs Flutter Web, integracja Nginx oraz potok wdrażania CI/CD.

## [v0.1] - 2026-02-03

### Added
- Początkowa implementacja aplikacji PlannerV2: silnik harmonogramowania, zarządzanie personelem oraz rozdzielenie etapów wdrażania środowisk DEV i PRODUCTION w Jenkinsfile.
