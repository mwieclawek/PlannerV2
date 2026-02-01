# PlannerV2 Backend

Backend dla aplikacji PlannerV2 napisany w Pythonie (FastAPI + SQLModel/PostgreSQL).

## Struktura projektu

- `app/`: Główny kod aplikacji
  - `main.py`: Punkt startowy aplikacji
  - `models.py`: Modele bazy danych (SQLModel)
  - `schemas.py`: Schematy Pydantic
  - `database.py`: Konfiguracja bazy danych
  - `routers/`: Endpointy API
- `tests/`: Testy automatyczne (pytest)

## Uruchamianie

### Lokalnie

Wymagane: Python 3.11+, PostgreSQL (opcjonalnie, domyślnie SQLite).

1. Zainstaluj zależności:
   ```bash
   pip install -r requirements.txt
   ```

2. Uruchom serwer (z katalogu głównego projektu):
   ```bash
   uvicorn backend.app.main:app --reload
   ```

### Docker

Backend jest konterneryzowany przy użyciu pliku `Dockerfile`.

**Ważne:** Ze względu na absolutne importy w kodzie (`from backend.app...`), struktura w kontenerze odwzorowuje strukturę pakietów:
- Kod aplikacji znajduje się w `/app/backend/app`
- Zmienna `PYTHONPATH` jest ustawiona na `/app`

Budowanie i uruchamianie:
```bash
docker build -t plannerv2-backend .
docker run -p 8000:8000 plannerv2-backend
```

## Testowanie

Testy znajdują się w katalogu `tests/`.

Uruchamianie testów (z katalogu nadrzędnego `backend/`):
```bash
# Ustaw PYTHONPATH na bieżący katalog (PlannerV2 base)
export PYTHONPATH=$PWD
pytest backend/tests/ -v
```

## API Docs

Po uruchomieniu serwera dokumentacja jest dostępna pod:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
