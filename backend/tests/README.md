# PlannerV2 Backend Tests

## Struktura testów

```
backend/tests/
├── conftest.py              # Fixtures (client, session, auth_headers, etc.)
├── test_api.py              # Podstawowe testy API
├── test_integration.py      # Testy E2E pełnego workflow
├── test_auth_unit.py        # ✨ Testy jednostkowe auth_utils
├── test_employee.py         # ✨ Testy endpointów employee
├── test_manager_edge_cases.py # ✨ Edge cases dla manager
├── test_scheduler_unit.py   # ✨ Testy scheduler
└── test_solver_unit.py      # ✨ Testy solvera CP-SAT
```

## Uruchamianie testów

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

# Testy API (wymagają uruchomionego serwera)
python -m pytest tests/test_api.py -v
python -m pytest tests/test_employee.py -v
python -m pytest tests/test_manager_edge_cases.py -v
python -m pytest tests/test_scheduler_unit.py -v
python -m pytest tests/test_integration.py -v
```

### Z raportami JUnit (dla Jenkins)
```bash
python -m pytest tests/ -v --junitxml=test-results/backend.xml
```

## Fixtures dostępne w conftest.py

| Fixture | Opis |
|---------|------|
| `session` | Sesja SQLModel z in-memory SQLite |
| `client` | AsyncClient do testów HTTP |
| `auth_headers` | Nagłówki z tokenem managera |
| `employee_headers` | Nagłówki z tokenem pracownika |
| `shift_definition` | Testowa definicja zmiany |
| `job_role` | Testowa rola |

## Pokrycie testów

### Auth (`test_auth_unit.py`)
- ✅ Hashowanie haseł
- ✅ Weryfikacja haseł
- ✅ Tworzenie tokenów JWT
- ✅ Walidacja tokenów

### Employee (`test_employee.py`)
- ✅ Pobieranie dostępności
- ✅ Aktualizacja dostępności
- ✅ Pobieranie grafiku
- ✅ Autoryzacja

### Manager (`test_manager_edge_cases.py`)
- ✅ Edge cases dla ról
- ✅ Edge cases dla zmian
- ✅ Zarządzanie użytkownikami
- ✅ Kontrola dostępu (RBAC)

### Scheduler (`test_scheduler_unit.py`)
- ✅ Lista grafików
- ✅ Generowanie grafików
- ✅ Publikacja grafików
- ✅ Manualne przypisania
- ✅ Batch save

### Solver (`test_solver_unit.py`)
- ✅ Puste dane
- ✅ Brak wymagań
- ✅ Niedostępność pracowników
- ✅ Preferencje
- ✅ Max 1 zmiana dziennie
- ✅ Dopasowanie ról
- ✅ Ostrzeżenia o niedoborach
