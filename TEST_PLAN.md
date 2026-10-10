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

### Struktura Testów

```
backend/tests/
├── conftest.py                    # Fixtures: client, session, auth_headers, employee_headers
├── test_api.py                    # Podstawowe testy API (rejestracja, login, CRUD)
├── test_auth_unit.py              # Testy jednostkowe: hash, verify, JWT, multi-tenant auth
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
├── test_kds_api.py                # KDS: integracja endpoint /pos/v2/kds/sync
└── test_integration.py.disabled   # Testy E2E (wyłączone)
```

### Pokrycie Testów

| Moduł | Plik testowy | Zakres |
|-------|-------------|--------|
| Auth | `test_auth_unit.py` | Hashowanie haseł, weryfikacja, tworzenie/walidacja JWT, **dual-login (email vs username+slug)** |
| API (podstawy) | `test_api.py` | Rejestracja, login, CRUD ról/zmian, generowanie grafiku |
| Employee | `test_employee.py` | Dostępność, grafik, autoryzacja |
| Manager (RBAC) | `test_manager_edge_cases.py` | Edge cases ról/zmian, kontrola dostępu, **powiązanie zmian z rolami** |
| Manager (Attendance) | `test_manager_attendance.py` | Obecności CRUD, filtry, zatwierdzanie/odrzucanie |
| Manager (Dashboard) | `test_manager_dashboard.py` | Dashboard home, statystyki |
| Manager (Users) | `test_manager_users.py` | Tworzenie użytkowników, **dodawanie/edycja adresu email** |
| **Superadmin & Tenant** | `test_superadmin.py` | **Rola SUPERADMIN, tworzenie Tenantów (slug), globalny dashboard, izolacja po tenant_id, reset haseł managerów** |
| User Update | `test_user_update.py` | Edycja użytkownika, cele godzinowe, is_active |
| Scheduler | `test_scheduler_unit.py` | Generowanie, batch save, publikacja, ręczne przypisania |
| Solver | `test_solver_unit.py` | CP-SAT: puste dane, brak wymagań, niedostępność, preferencje, dopasowanie ról, ostrzeżenia |
| Solver Edge | `test_solver_edge_cases.py` | Przypadki brzegowe solvera |
| PDF | `test_pdf_export.py` | Eksport PDF obecności |
| KDS Sync | `test_kds.py` | Monotoniczny sync batch: walidacja wag stanów, anti-ghosting VOIDED, audit log KDSEventLog |
| KDS Pacing | `test_kds.py` | Anchor-based pacing: obliczanie delay_start_sec per-kurs |
| KDS API | `test_kds_api.py` | Integracja POST /pos/v2/kds/sync: izolowana baza SQLite, JWT auth, pełny przepływ sync |

### Fixture'y (conftest.py)

| Fixture | Opis |
|---------|------|
| `session` | Sesja SQLModel z in-memory SQLite |
| `client` | AsyncClient do testów HTTP |
| `auth_headers` | Nagłówki z tokenem managera |
| `employee_headers` | Nagłówki z tokenem pracownika |
| `shift_definition` | Testowa definicja zmiany |
| `job_role` | Testowa rola |

### Frontend (flutter test)

```bash
cd frontend
flutter test
```

## Testy Manualne

### Scenariusz 1: Logowanie i Zarządzanie Kontem
1. ✅ Zaloguj się jako manager (sprawdź dual-login: przez email lub username + Login ID / slug)
2. ✅ Utwórz konto pracownika (zakładka Zespół → +)
3. ✅ Dodaj i wyedytuj adres email pracownika
4. ✅ Przypisz pracownikowi rolę
5. ✅ Zaloguj się jako pracownik (przez przypisany email lub username + slug)
6. ✅ Dezaktywuj konto pracownika (jako manager)
7. ✅ Sprawdź że dezaktywowany pracownik nie może się zalogować

### Scenariusz 2: Konfiguracja
1. ✅ Dodaj role (Barista, Kucharz) z kolorami
2. ✅ Dodaj zmiany i przypisz je do konkretnych ról (Role-Based Shifts)
3. ✅ Zaloguj się jako pracownik i upewnij się, że widzi w grafiku/dostępnościach tylko zmiany zgodne z jego rolami
4. ✅ Sprawdź walidację duplikatów godzin
5. ✅ Edytuj istniejącą rolę
6. ✅ Usuń rolę

### Scenariusz 3: Grafik — Pełny Cykl
1. ✅ Ustaw wymagania kadrowe
2. ✅ Kliknij „Generuj grafik" (Draft)
3. ✅ Edytuj ręcznie (dodaj/usuń pracownika)
4. ✅ Zapisz zmiany (Batch Save)
5. ✅ Opublikuj grafik
6. ✅ Sprawdź widoczność u pracownika

### Scenariusz 4: Obecności
1. ✅ Pracownik rejestruje obecność (check-in/check-out)
2. ✅ Manager widzi wpisy w zakładce Obecności
3. ✅ Manager zatwierdza/odrzuca
4. ✅ Eksport PDF

### Scenariusz 5: Oddawanie Zmian
1. ✅ Pracownik oddaje zmianę
2. ✅ Manager widzi prośbę w zakładce Zmiany
3. ✅ Manager przydziela zastępstwo
4. ✅ Sprawdź aktualizację grafiku

### Scenariusz 6: POS v2 / KDS
1. ⬜ Zaloguj się jako manager → utwórz strefy i stoliki w Manager Setup
2. ⬜ Dodaj kategorie i pozycje menu z `prep_time_sec`
3. ⬜ Dodaj grupy modyfikatorów (Stopień Wysmażenia)
4. ⬜ Zaloguj się jako kelner → złóż zamówienie na Stolik 1 (2 kursy)
5. ⬜ Otwórz widok KDS → sprawdź pacing metadata
6. ⬜ Zmień stany pozycji: NEW → PREPARING → READY
7. ⬜ Wyłącz Wi-Fi → spróbuj zmienić stan offline → włącz Wi-Fi → batch sync
8. ⬜ Sprawdź że stale updates są odrzucane (monotonic validation)
9. ⬜ Zapłać split payment (gotówka + karta)

### Scenariusz 7: Architektura Multi-Tenant i Superadmin
1. ✅ Zaloguj się na globalny dashboard (`/#/superadmin`) jako użytkownik z rolą `SUPERADMIN`.
2. ✅ Utwórz nową restaurację (Tenant), nadając jej unikalną nazwę i `slug` (Login ID).
3. ✅ Sprawdź poprawność widoku wszystkich użytkowników z różnych restauracji.
4. ✅ Dodaj pierwszego managera do nowo utworzonej restauracji.
5. ✅ Przetestuj funkcję resetowania hasła managera z panelu Superadmina.
6. ✅ Zaloguj się na nowo utworzonego managera za pomocą jego emaila oraz (w osobnej próbie) za pomocą username + Login ID.
7. ✅ Sprawdź izolację danych: upewnij się, że nowo dodany manager widzi wyłącznie pracowników, zmiany i dane swojej własnej restauracji (payload JWT zawiera poprawny `tenant_id`).

## CI/CD (Jenkins)

Pipeline w `Jenkinsfile` uruchamia:
1. **Backend Tests** — `pytest tests/ -v --junitxml=test-results/backend.xml`
2. **Flutter Analyze** — `flutter analyze`
3. **Docker Build** — budowanie obrazów backend + nginx
4. **Deploy** — wdrożenie na serwer dev/staging
