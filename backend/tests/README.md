# PlannerV2 Backend Tests

Zestaw testów automatycznych backendu FastAPI opartego na pytest i bazie SQLite in-memory.

## Struktura Testów

```
backend/tests/
├── conftest.py                    # Fixtures (client, session, auth_headers, mocki)
├── test_api.py                    # Podstawowe testy API (rejestracja, login, CRUD ról/zmian)
├── test_auth_unit.py              # Testy jednostkowe auth (JWT, haszowanie, walidacja haseł, dual-login)
├── test_employee.py               # Endpointy pracownika (dostępność, grafik, obecności)
├── test_manager_edge_cases.py     # Edge cases dla RBAC i powiązań ról ze zmianami
├── test_manager_attendance.py     # Ewidencja obecności (CRUD, filtry, zatwierdzanie)
├── test_manager_dashboard.py      # Dashboard managera i statystyki zespołu
├── test_manager_users.py          # Zarządzanie kontami personelu (w tym edycja emaila)
├── test_superadmin.py             # Panel Superadmina, zarządzanie lokalami, izolacja tenant_id
├── test_user_update.py            # Aktualizacja użytkownika (cele, status aktywności)
├── test_scheduler_unit.py         # Harmonogramowanie: generowanie, batch save, publikacja
├── test_solver_unit.py            # Solver CP-SAT: ograniczenia, odpoczynek 11h, kary
├── test_solver_edge_cases.py      # Przypadki brzegowe solvera
├── test_pdf_export.py             # Generowanie raportu PDF z obecności
├── test_kds.py                    # KDS: silnik pacingu, monotoniczny sync batch, anti-ghosting
└── test_kds_api.py                # Integracja endpointu /pos/v2/kds/sync
```

## Uruchamianie

### Wszystkie testy
```bash
cd backend
python -m pytest tests/ -v
```

### Poszczególne moduły
```bash
# Testy jednostkowe uwierzytelniania i walidacji
python -m pytest tests/test_auth_unit.py -v

# Testy solvera CP-SAT
python -m pytest tests/test_solver_unit.py -v

# Testy KDS i synchronizacji
python -m pytest tests/test_kds.py -v
python -m pytest tests/test_kds_api.py -v

# Testy uprawnień i tenantów
python -m pytest tests/test_superadmin.py -v
```

### Z raportami JUnit (dla Jenkins CI)
```bash
python -m pytest tests/ -v --junitxml=test-results/backend.xml
```

## Fixtures (conftest.py)

| Fixture | Opis |
|---------|------|
| `session` | Izolowana sesja SQLModel w pamięci (SQLite in-memory) |
| `client` | Klient asynchroniczny `httpx.AsyncClient` do testowania endpointów HTTP |
| `auth_headers` | Nagłówki żądania z tokenem autoryzacyjnym Managera |
| `employee_headers` | Nagłówki żądania z tokenem autoryzacyjnym Pracownika |
| `shift_definition` | Testowy rekord definicji zmiany |
| `job_role` | Testowy rekord roli stanowiskowej |

## Zakres Pokrycia Testowego

### Auth (`test_auth_unit.py`)
- Haszowanie haseł algorytmem pbkdf2_sha256
- Weryfikacja poprawności hasła
- Walidacja siły hasła (odrzucenie haseł krótszych niż 8 znaków, bez wielkiej litery lub bez cyfry)
- Generowanie i walidacja tokenów JWT z identyfikatorem `tenant_id`
- Logowanie podwójne: email lub username + tenant_slug

### API Basics (`test_api.py`)
- Rejestracja personelu przez managera
- Blokada rejestracji menedżera bez właściwego kodu PIN
- Uwierzytelnianie poprawnymi i błędnymi danymi
- Pełny obieg konfiguracji ról, zmian i generowania grafiku

### Employee (`test_employee.py`)
- Pobieranie i aktualizacja deklaracji dostępności
- Pobieranie grafiku indywidualnego oraz zespołu
- Weryfikacja uprawnień do chronionych zasobów pracowniczych

### Manager RBAC (`test_manager_edge_cases.py`)
- Izolacja uprawnień ról i definicji zmian
- Przypisanie zmian do określonych stanowisk
- Kontrola dostępu do operacji administracyjnych lokalu

### KDS i Pacing (`test_kds.py` & `test_kds_api.py`)
- Anchor-based pacing: wyliczanie opóźnienia rozpoczęcia dań w kursie
- Monotoniczny sync batch z walidacją wag stanów
- Blokowanie modyfikacji pozycji anulowanych (anti-ghosting)
- Rejestracja audytu w tabeli `KDSEventLog`
