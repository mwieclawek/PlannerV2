# PlannerV2 Backend

Backend dla aplikacji PlannerV2 napisany w Pythonie (FastAPI + SQLModel/PostgreSQL).

## Struktura projektu

- `app/`: Główny kod aplikacji
  - `main.py`: Punkt startowy aplikacji
  - `models.py`: Modele bazy danych (SQLModel)
  - `schemas.py`: Schematy Pydantic
  - `database.py`: Konfiguracja bazy danych
  - `routers/`: Endpointy API
- `alembic/`: Migracje bazy danych
  - `versions/`: Pliki migracji
  - `env.py`: Konfiguracja środowiska Alembic
- `tests/`: Testy automatyczne (pytest)

## Migracje bazy danych (Alembic)

Używamy Alembic do zarządzania schematem bazy danych.

### Generowanie nowej migracji

```bash
cd backend
alembic revision --autogenerate -m "opis zmiany"
```

### Uruchomienie migracji

```bash
alembic upgrade head
```

### Cofnięcie migracji

```bash
alembic downgrade -1
```

> **Uwaga:** W środowisku Docker migracje uruchamiane są automatycznie przy starcie kontenera.

## Uruchamianie

### Lokalnie

Wymagane: Python 3.11+, PostgreSQL (opcjonalnie, domyślnie SQLite).

1. Zainstaluj zależności:
   ```bash
   pip install -r requirements.txt
   ```

## Database Initialization

The application automatically initializes the database (creates tables) on startup if they do not exist. This applies to both SQLite (local development) and PostgreSQL (test/production environments), ensuring that the application can run in environments where Alembic migrations might not be executed automatically (e.g., Jenkins test stage).

## Testing

To run backend tests:

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v
```

Note: Integration tests in `tests/test_api.py` require a running backend server or valid database connection. The `conftest.py` is configured to use an in-memory SQLite database for isolated testing.

2. Uruchom migracje:
   ```bash
   alembic upgrade head
   ```

3. Uruchom serwer (z katalogu głównego projektu):
   ```bash
   uvicorn backend.app.main:app --reload --port 8080
   ```

### Algorytm Grafiku (Solver)
Ulepszony w lutym 2026:
- **Dwie zmiany dziennie**: Pracownik może dostać 2 zmiany tego samego dnia (tzw. split shift).
- **Zasady nakładania**: Dozwolone nakładanie się zmian do **30 minut** (na przekazanie zmiany). Powyżej 30 min blokowane.
- **Kary**: Algorytm preferuje 1 zmianę dziennie (kara punktowa za każdą kolejną), chyba że brakuje personelu.
- **Limity celów**: Respektuje `target_hours_per_month` i `target_shifts_per_month` dla każdego pracownika.

### Docker

Backend jest konteneryzowany przy użyciu pliku `Dockerfile`.

**Ważne:** 
- Migracje Alembic uruchamiane są automatycznie przy starcie kontenera
- Kod aplikacji znajduje się w `/app/backend/app`
- Zmienna `PYTHONPATH` jest ustawiona na `/app`

Budowanie i uruchamianie:
```bash
docker build -t plannerv2-backend .
docker run -p 8000:8000 -e DATABASE_URL=postgresql://user:pass@host/db plannerv2-backend
```

## Testowanie

Testy znajdują się w katalogu `tests/`.

Uruchamianie testów (z katalogu nadrzędnego `backend/`):
```bash
export PYTHONPATH=$PWD
pytest backend/tests/ -v
```

## Nowe endpointy (2026-02-10)

### GET /manager/attendance
Pobiera listę **wszystkich** obecności (nie tylko PENDING) z filtrowaniem po datach i opcjonalnie po statusie.

**Parametry query:**
- `start_date` (date, wymagany) — początek zakresu dat
- `end_date` (date, wymagany) — koniec zakresu dat
- `status` (string, opcjonalny) — filtr statusu: `PENDING`, `CONFIRMED`, `REJECTED`

**Przykład:**
```bash
GET /manager/attendance?start_date=2026-02-01&end_date=2026-02-28&status=PENDING
```

### GET /manager/employee-hours
Zwraca podsumowanie godzin pracy każdego pracownika w danym miesiącu, wraz z informacją czy złożył dyspozycję.

**Parametry query:**
- `month` (int, 1-12, wymagany) — miesiąc
- `year` (int, wymagany) — rok

**Zwraca:**
- `user_id`, `user_name`, `total_hours`, `shift_count`, `has_availability`
- Lista posortowana malejąco po `total_hours`

**Przykład:**
```bash
GET /manager/employee-hours?month=2&year=2026
```

## API Docs

Po uruchomieniu serwera dokumentacja jest dostępna pod:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

