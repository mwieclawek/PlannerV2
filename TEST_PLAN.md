# Plan Testów

## Testy Automatyczne

### Backend (pytest)

```bash
cd backend
python -m pytest tests/ -v
```

Raport JUnit (dla Jenkins):
```bash
python -m pytest tests/ -v --junitxml=test-results/backend.xml
```

### Struktura Testów Backendowych

```
backend/tests/
├── conftest.py                    # Fixtures: client, session, auth_headers, employee_headers
├── test_api.py                    # Podstawowe testy API (rejestracja, login, CRUD)
├── test_auth_unit.py              # Testy jednostkowe: hash, verify, JWT, multi-tenant auth, walidacja haseł
├── test_employee.py               # Endpointy employee: dostępność, grafik, autoryzacja
├── test_manager_edge_cases.py     # Edge cases: role, zmiany z przypisanymi rolami, RBAC
├── test_manager_attendance.py     # Obecności: CRUD, filtrowanie, zatwierdzanie
├── test_manager_dashboard.py      # Dashboard: dashboard-home, statystyki
├── test_manager_users.py          # Zarządzanie użytkownikami: email, tworzenie, update
├── test_superadmin.py             # Testy panelu Superadmina i izolacji danych Tenantów
├── test_user_update.py            # Aktualizacja użytkownika: dane, cele, is_active
├── test_scheduler_unit.py         # Scheduler: generowanie, batch save, publish
├── test_solver_unit.py            # Solver CP-SAT: constraints, preferencje, warnings
├── test_solver_edge_cases.py      # Solver edge cases
├── test_pdf_export.py             # Eksport PDF obecności
├── test_sprint_features.py        # Testy sprint features
├── test_sprint_features_full.py   # Pełne testy sprint features
├── test_bug_reproduction.py       # Reprodukcja zgłoszonych bugów
├── test_kds.py                    # KDS: monotonic sync, pacing engine, anti-ghosting
└── test_kds_api.py                # KDS: integracja endpoint /pos/v2/kds/sync
```

### Pokrycie Testów Backendowych

| Moduł | Plik testowy | Zakres |
|-------|-------------|--------|
| Auth | `test_auth_unit.py` | Hashowanie haseł, weryfikacja, tworzenie/walidacja JWT, dual-login (email vs username+slug), walidacja siły haseł |
| API (podstawy) | `test_api.py` | Rejestracja, login, CRUD ról/zmian, generowanie grafiku |
| Employee | `test_employee.py` | Dostępność, grafik, autoryzacja |
| Manager (RBAC) | `test_manager_edge_cases.py` | Edge cases ról/zmian, kontrola dostępu, powiązanie zmian z rolami |
| Manager (Attendance) | `test_manager_attendance.py` | Obecności CRUD, filtry, zatwierdzanie/odrzucanie |
| Manager (Dashboard) | `test_manager_dashboard.py` | Dashboard home, statystyki |
| Manager (Users) | `test_manager_users.py` | Tworzenie użytkowników, dodawanie/edycja adresu email |
| Superadmin & Tenant | `test_superadmin.py` | Rola SUPERADMIN, tworzenie Tenantów (slug), globalny dashboard, izolacja po tenant_id, reset haseł managerów |
| User Update | `test_user_update.py` | Edycja użytkownika, cele godzinowe, is_active |
| Scheduler | `test_scheduler_unit.py` | Generowanie, batch save, publikacja, ręczne przypisania |
| Solver | `test_solver_unit.py` | CP-SAT: puste dane, brak wymagań, niedostępność, preferencje, dopasowanie ról, ostrzeżenia |
| Solver Edge | `test_solver_edge_cases.py` | Przypadki brzegowe solvera |
| PDF | `test_pdf_export.py` | Eksport PDF obecności |
| KDS Sync | `test_kds.py` | Monotoniczny sync batch: walidacja wag stanów, anti-ghosting VOIDED, audit log KDSEventLog |
| KDS Pacing | `test_kds.py` | Anchor-based pacing: obliczanie delay_start_sec per-kurs |
| KDS API | `test_kds_api.py` | Integracja POST /pos/v2/kds/sync: izolowana baza SQLite, JWT auth, pełny przepływ sync |

### Frontend (flutter test)

```bash
cd frontend
flutter test
```

### Struktura Testów Frontendowych

```
frontend/test/
├── api_error_handler_test.dart    # Testy ApiErrorHandler (walidacja haseł, mapowanie błędów Dio, Pydantic)
├── web_push_test.dart             # Testy WebNotificationHelper, PushService i VAPID
├── home_tab_test.dart             # Testy widoku domowego managera
├── my_schedule_test.dart          # Testy widoku grafiku pracownika (w tym widok całego zespołu)
├── team_tab_test.dart             # Testy zarządzania zespołem (dodawanie pracownika, dialog)
├── leave_requests_test.dart       # Testy obsługi wniosków urlopowych
├── requirements_test.dart         # Testy modeli wymagań kadrowych
└── widget_test.dart               # Testy modeli danych i parsowania JSON
```

---

## Testy Manualne

### Scenariusz 1: Logowanie i Zarządzanie Kontem
- [x] Zaloguj się jako manager (sprawdź dual-login: przez email lub username + Login ID / slug).
- [x] Utwórz konto pracownika (zakładka Zespół -> +).
- [x] Dodaj i wyedytuj adres email pracownika.
- [x] Przypisz pracownikowi rolę.
- [x] Zaloguj się jako pracownik (przez przypisany email lub username + slug).
- [x] Dezaktywuj konto pracownika (jako manager).
- [x] Sprawdź że dezaktywowany pracownik nie może się zalogować.

### Scenariusz 2: Konfiguracja
- [x] Dodaj role (Barista, Kucharz) z kolorami.
- [x] Dodaj zmiany i przypisz je do konkretnych ról (Role-Based Shifts).
- [x] Zaloguj się jako pracownik i upewnij się, że widzi w grafiku/dostępnościach tylko zmiany zgodne z jego rolami.
- [x] Sprawdź walidację duplikatów godzin.
- [x] Edytuj istniejącą rolę.
- [x] Usuń rolę.

### Scenariusz 3: Grafik — Pełny Cykl
- [x] Ustaw wymagania kadrowe.
- [x] Kliknij „Generuj grafik" (Draft).
- [x] Edytuj ręcznie (dodaj/usuń pracownika).
- [x] Zapisz zmiany (Batch Save).
- [x] Opublikuj grafik.
- [x] Sprawdź widoczność u pracownika.

### Scenariusz 4: Obecności
- [x] Pracownik rejestruje obecność (check-in/check-out).
- [x] Manager widzi wpisy w zakładce Obecności.
- [x] Manager zatwierdza/odrzuca.
- [x] Eksport PDF.

### Scenariusz 5: Oddawanie i Wymiana Zmian
- [x] Pracownik oddaje zmianę na giełdę.
- [x] Manager widzi prośbę w zakładce Zmiany i przydziela zastępstwo.
- [x] Bezpośrednia wymiana zmian: pracownik proponuje wymianę uprawnionemu koledze z zespołu.
- [x] Sprawdź aktualizację grafiku po zaakceptowaniu wymiany.

### Scenariusz 6: Walidacja Haseł i Obsługa Błędów Sieciowych
- [x] Przejdź do formularza zmiany hasła w panelu pracownika lub resetu hasła w panelu managera.
- [x] Wprowadź hasło krótsze niż 8 znaków -> zweryfikuj czytelny komunikat walidacji.
- [x] Wprowadź hasło bez wielkiej litery -> zweryfikuj czytelny komunikat walidacji.
- [x] Wprowadź hasło bez cyfry -> zweryfikuj czytelny komunikat walidacji.
- [x] Wprowadź poprawne hasło (np. Haslo123) -> zweryfikuj pomyślne zatwierdzenie.
- [x] Wywołaj celowy błąd sieciowy (np. brak łączności) -> zweryfikuj czytelny komunikat SnackBar w języku polskim.

### Scenariusz 7: Powiadomienia Web Push i PWA
- [x] Otwórz aplikację w przeglądarce i kliknij ikonę dzwonka (powiadomienia).
- [x] Zweryfikuj obecność karty z zachętą do włączenia powiadomień przeglądarkowych.
- [x] Kliknij przycisk „Włącz powiadomienia” (User Gesture) -> zaakceptuj monit przeglądarki.
- [x] Zweryfikuj aktualizację statusu na „Powiadomienia w przeglądarce są aktywne”.
- [x] Wyślij powiadomienie testowe (np. publikacja grafiku) -> zweryfikuj baner u góry ekranu i odświeżenie listy pod dzwonkiem.
- [x] Zweryfikuj instalację PWA na urządzeniu mobilnym (Safari iOS: Dodaj do ekranu początkowego).

### Scenariusz 8: POS v2 / KDS
- [ ] Zaloguj się jako manager -> utwórz strefy i stoliki w Manager Setup.
- [ ] Dodaj kategorie i pozycje menu z `prep_time_sec`.
- [ ] Dodaj grupy modyfikatorów (Stopień Wysmażenia).
- [ ] Zaloguj się jako kelner -> złóż zamówienie na Stolik 1 (2 kursy).
- [ ] Otwórz widok KDS -> sprawdź pacing metadata.
- [ ] Zmień stany pozycji: NEW -> PREPARING -> READY.
- [ ] Wyłącz Wi-Fi -> spróbuj zmienić stan offline -> włącz Wi-Fi -> batch sync.
- [ ] Sprawdź że stale updates są odrzucane (monotonic validation).
- [ ] Zapłać split payment (gotówka + karta).

### Scenariusz 9: Architektura Multi-Tenant i Superadmin
- [x] Zaloguj się na globalny dashboard (`/#/superadmin`) jako użytkownik z rolą `SUPERADMIN`.
- [x] Utwórz nową restaurację (Tenant), nadając jej unikalną nazwę i `slug` (Login ID).
- [x] Sprawdź poprawność widoku wszystkich użytkowników z różnych restauracji.
- [x] Dodaj pierwszego managera do nowo utworzonej restauracji.
- [x] Przetestuj funkcję resetowania hasła managera z panelu Superadmina.
- [x] Zaloguj się na nowo utworzonego managera za pomocą jego emaila oraz (w osobnej próbie) za pomocą username + Login ID.
- [x] Sprawdź izolację danych: upewnij się, że nowo dodany manager widzi wyłącznie pracowników, zmiany i dane swojej własnej restauracji (payload JWT zawiera poprawny `tenant_id`).

---

## CI/CD (Jenkins)

Pipeline w `Jenkinsfile` uruchamia:
1. **Backend Tests** — `pytest tests/ -v --junitxml=test-results/backend.xml`
2. **Flutter Analyze** — `flutter analyze`
3. **Flutter Tests** — `flutter test`
4. **Docker Build** — budowanie obrazów backend + nginx
5. **Deploy** — wdrożenie na serwer dev/staging
