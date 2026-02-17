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
├── test_auth_unit.py              # Testy jednostkowe: hash, verify, JWT
├── test_employee.py               # Endpointy employee: dostępność, grafik, autoryzacja
├── test_manager_edge_cases.py     # Edge cases: role, zmiany, RBAC
├── test_manager_attendance.py     # Obecności: CRUD, filtrowanie, zatwierdzanie
├── test_manager_dashboard.py      # Dashboard: dashboard-home, statystyki
├── test_manager_users.py          # Zarządzanie użytkownikami: tworzenie, update
├── test_user_update.py            # Aktualizacja użytkownika: dane, cele, is_active
├── test_scheduler_unit.py         # Scheduler: generowanie, batch save, publish
├── test_solver_unit.py            # Solver CP-SAT: constraints, preferencje, warnings
├── test_solver_edge_cases.py      # Solver edge cases
├── test_pdf_export.py             # Eksport PDF obecności
├── test_sprint_features.py        # Testy sprint features
├── test_sprint_features_full.py   # Pełne testy sprint features
├── test_bug_reproduction.py       # Reprodukcja zgłoszonych bugów
└── test_integration.py.disabled   # Testy E2E (wyłączone)
```

### Pokrycie Testów

| Moduł | Plik testowy | Zakres |
|-------|-------------|--------|
| Auth | `test_auth_unit.py` | Hashowanie haseł, weryfikacja, tworzenie/walidacja JWT |
| API (podstawy) | `test_api.py` | Rejestracja, login, CRUD ról/zmian, generowanie grafiku |
| Employee | `test_employee.py` | Dostępność, grafik, autoryzacja |
| Manager (RBAC) | `test_manager_edge_cases.py` | Edge cases ról/zmian, kontrola dostępu |
| Manager (Attendance) | `test_manager_attendance.py` | Obecności CRUD, filtry, zatwierdzanie/odrzucanie |
| Manager (Dashboard) | `test_manager_dashboard.py` | Dashboard home, statystyki |
| Manager (Users) | `test_manager_users.py` | Tworzenie użytkowników |
| User Update | `test_user_update.py` | Edycja użytkownika, cele godzinowe, is_active |
| Scheduler | `test_scheduler_unit.py` | Generowanie, batch save, publikacja, ręczne przypisania |
| Solver | `test_solver_unit.py` | CP-SAT: puste dane, brak wymagań, niedostępność, preferencje, dopasowanie ról, ostrzeżenia |
| Solver Edge | `test_solver_edge_cases.py` | Przypadki brzegowe solvera |
| PDF | `test_pdf_export.py` | Eksport PDF obecności |

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
1. ✅ Zaloguj się jako manager
2. ✅ Utwórz konto pracownika (zakładka Zespół → +)
3. ✅ Przypisz pracownikowi rolę
4. ✅ Zaloguj się jako pracownik
5. ✅ Dezaktywuj konto pracownika (jako manager)
6. ✅ Sprawdź że dezaktywowany pracownik nie może się zalogować

### Scenariusz 2: Konfiguracja
1. ✅ Dodaj role (Barista, Kucharz) z kolorami
2. ✅ Dodaj zmiany (8:00-16:00, 16:00-24:00)
3. ✅ Sprawdź walidację duplikatów godzin
4. ✅ Edytuj istniejącą rolę
5. ✅ Usuń rolę

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

## CI/CD (Jenkins)

Pipeline w `Jenkinsfile` uruchamia:
1. **Backend Tests** — `pytest tests/ -v --junitxml=test-results/backend.xml`
2. **Flutter Analyze** — `flutter analyze`
3. **Docker Build** — budowanie obrazów backend + nginx
4. **Deploy** — wdrożenie na serwer dev/staging
