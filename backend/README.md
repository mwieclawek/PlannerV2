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

2. Uruchom migracje:
   ```bash
   alembic upgrade head
   ```

3. Uruchom serwer (z katalogu głównego projektu):
   ```bash
   uvicorn backend.app.main:app --reload
   ```

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

## API Docs

Po uruchomieniu serwera dokumentacja jest dostępna pod:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

