# PlannerV2 Backend Tests

## Struktura Testów

```
backend/tests/
├── conftest.py                    # Fixtures (client, session, auth, etc.)
├── test_api.py                    # Podstawowe testy API
├── test_auth_unit.py              # Testy jednostkowe auth (JWT, hash)
├── test_employee.py               # Endpointy employee
├── test_manager_edge_cases.py     # Edge cases dla manager RBAC
├── test_manager_attendance.py     # Obecności: CRUD, filtry, zatwierdzanie
├── test_manager_dashboard.py      # Dashboard home, statystyki
├── test_manager_users.py          # Tworzenie użytkowników
├── test_user_update.py            # Aktualizacja: dane, cele, is_active
├── test_scheduler_unit.py         # Scheduler: generowanie, batch, publish
├── test_solver_unit.py            # Solver CP-SAT: constraints, warnings
├── test_solver_edge_cases.py      # Solver: przypadki brzegowe
├── test_pdf_export.py             # Eksport PDF obecności
├── test_sprint_features.py        # Testy sprint features
├── test_sprint_features_full.py   # Pełne testy sprint features
├── test_bug_reproduction.py       # Reprodukcja zgłoszonych bugów
└── test_integration.py.disabled   # Testy E2E (wyłączone)
```

## Uruchamianie

### Wszystkie testy
```bash
cd backend
python -m pytest tests/ -v
```

### Poszczególne moduły
```bash
# Testy jednostkowe (nie wymagają serwera)
python -m pytest tests/test_auth_unit.py -v
python -m pytest tests/test_solver_unit.py -v

# Testy API
python -m pytest tests/test_api.py -v
python -m pytest tests/test_employee.py -v
python -m pytest tests/test_manager_edge_cases.py -v
python -m pytest tests/test_manager_attendance.py -v
python -m pytest tests/test_manager_dashboard.py -v
python -m pytest tests/test_manager_users.py -v
python -m pytest tests/test_user_update.py -v
python -m pytest tests/test_scheduler_unit.py -v
python -m pytest tests/test_pdf_export.py -v
```

### Z raportami JUnit (dla Jenkins)
```bash
python -m pytest tests/ -v --junitxml=test-results/backend.xml
```

## Fixtures (conftest.py)

| Fixture | Opis |
|---------|------|
| `session` | Sesja SQLModel z in-memory SQLite |
| `client` | AsyncClient do testów HTTP |
| `auth_headers` | Nagłówki z tokenem managera |
| `employee_headers` | Nagłówki z tokenem pracownika |
| `shift_definition` | Testowa definicja zmiany |
| `job_role` | Testowa rola |

## Pokrycie Testów

### Auth (`test_auth_unit.py`)
- ✅ Hashowanie haseł (bcrypt)
- ✅ Weryfikacja haseł
- ✅ Tworzenie tokenów JWT
- ✅ Walidacja tokenów

### API Basics (`test_api.py`)
- ✅ Rejestracja pracownika
- ✅ Manager bez PIN = 403
- ✅ Login z poprawnymi danymi
- ✅ CRUD ról i zmian
- ✅ Pełny cykl generowania grafiku

### Employee (`test_employee.py`)
- ✅ Pobieranie/aktualizacja dostępności
- ✅ Pobieranie grafiku
- ✅ Autoryzacja endpointów

### Manager RBAC (`test_manager_edge_cases.py`)
- ✅ Edge cases dla ról i zmian
- ✅ Zarządzanie użytkownikami
- ✅ Kontrola dostępu (RBAC)

### Attendance (`test_manager_attendance.py`)
- ✅ CRUD obecności
- ✅ Filtrowanie po datach i statusie
- ✅ Zatwierdzanie/odrzucanie

### Dashboard (`test_manager_dashboard.py`)
- ✅ Dashboard home endpoint
- ✅ Statystyki użytkowników

### Users (`test_manager_users.py`, `test_user_update.py`)
- ✅ Tworzenie kont pracowników
- ✅ Aktualizacja danych i celów godzinowych
- ✅ Aktywacja/dezaktywacja (is_active)

### Scheduler (`test_scheduler_unit.py`)
- ✅ Generowanie grafików (Draft mode)
- ✅ Batch save
- ✅ Publikacja
- ✅ Ręczne przypisania/usuwanie

### Solver (`test_solver_unit.py`, `test_solver_edge_cases.py`)
- ✅ Puste dane / brak wymagań
- ✅ Niedostępność pracowników
- ✅ Preferencje (PREFERRED > NEUTRAL)
- ✅ Dopasowanie ról
- ✅ Ostrzeżenia o niedoborach
- ✅ Przypadki brzegowe

### PDF (`test_pdf_export.py`)
- ✅ Eksport PDF obecności
