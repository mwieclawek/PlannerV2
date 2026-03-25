# PlannerV2 Backend

Backend systemu PlannerV2 — FastAPI + SQLModel + PostgreSQL/SQLite.

## Struktura Projektu

```
backend/
├── app/
│   ├── main.py                 # FastAPI app, CORS, lifespan (auto-init DB)
│   ├── models.py               # SQLModel entities (30+ modeli)
│   ├── schemas.py              # Pydantic schemas (request/response + KDS sync)
│   ├── database.py             # Konfiguracja DB (SQLite/PostgreSQL)
│   ├── auth_utils.py           # JWT creation/verification, password hashing (pbkdf2_sha256)
│   ├── routers/
│   │   ├── auth.py             # Login, /me, change-password
│   │   ├── manager.py          # CRUD: role, zmiany, users, obecności, giveaway
│   │   ├── employee.py         # Grafik, dostępność, obecność, giveaway
│   │   ├── scheduler.py        # Generowanie, batch save, publish, assignment
│   │   ├── pos.py              # POS v2: strefy, stoły, menu, zamówienia, KDS sync, płatności
│   │   ├── kitchen.py          # POS v1 (legacy): stoły, menu, zamówienia
│   │   ├── health.py           # Health check (DB + Alembic migration status)
│   │   ├── notifications.py    # Powiadomienia in-app + FCM
│   │   └── bug_report.py       # Proxy do GitHub Issues API
│   └── services/
│       ├── solver.py           # OR-Tools CP-SAT constraint solver
│       ├── pos_service.py      # POS v2 logika biznesowa
│       ├── kds_service.py      # KDS: monotonic sync + pacing engine
│       ├── manager_service.py  # Logika biznesowa managera
│       ├── employee_service.py # Logika biznesowa pracownika
│       ├── scheduler_service.py # Operacje na grafiku
│       └── push_service.py     # Firebase Cloud Messaging
├── alembic/                    # Migracje bazy danych
│   ├── env.py
│   └── versions/               # Pliki migracji
├── tests/                      # Testy automatyczne
│   ├── test_kds.py            # Testy jednostkowe KDS (pacing, sync)
│   └── test_kds_api.py        # Testy integracyjne KDS endpoint
├── seed_test_data.py           # Generator danych testowych
├── reset_db_alembic.py         # Reset bazy + migracje
├── requirements.txt
├── alembic.ini
└── Dockerfile
```

## Uruchamianie

### Lokalnie

Wymagane: Python 3.11+

```bash
cd backend

# Zainstaluj zależności
pip install -r requirements.txt

# Uruchom migracje
alembic upgrade head

# Wygeneruj dane testowe (manager / pracownicy / menu / stoliki / grafiki)
python seed_test_data.py

# Uruchom serwer
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

> **Domyślne dane logowania**: `manager` / `manager123`
> Pozostałi pracownicy (anna, piotr, tomasz): hasło `123`.

### Docker

```bash
docker build -t plannerv2-backend .
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host/db \
  -e MANAGER_REGISTRATION_PIN=your_pin \
  plannerv2-backend
```

Migracje Alembic uruchamiane automatycznie przy starcie kontenera.

## Baza Danych

### Inicjalizacja
Aplikacja automatycznie tworzy tabele przy starcie (`init_db()` w lifespan), co zapewnia działanie w środowiskach bez Alembic (np. Jenkins test stage).

### Migracje (Alembic)

```bash
# Nowa migracja
alembic revision --autogenerate -m "opis zmiany"

# Uruchom migracje
alembic upgrade head

# Cofnij ostatnią
alembic downgrade -1
```

## Algorytm Grafiku (Solver)

OR-Tools CP-SAT solver z następującymi regułami:
- **Split shift**: pracownik może dostać do 2 zmian dziennie.
- **Nakładanie zmian**: dozwolone do 30 minut (na przekazanie).
- **Kary**: algorytm preferuje 1 zmianę/dzień (kara za każdą kolejną).
- **Cele**: respektuje `target_hours_per_month` i `target_shifts_per_month`.
- **Dostępność**: uwzględnia preferencje (PREFERRED > NEUTRAL > UNAVAILABLE).
- **Draft mode**: `solve(save=False)` — generuje bez zapisu do DB.

## API Endpoints

### Auth (`/auth`)
| Metoda | Endpoint | Opis |
|--------|----------|------|
| `POST` | `/auth/register` | Wyłączony (403) — konta tworzy manager |
| `POST` | `/auth/token` | Login (OAuth2 password flow) |
| `GET` | `/auth/me` | Dane zalogowanego użytkownika |
| `PUT` | `/auth/change-password` | Zmiana hasła |

### Manager (`/manager`)
| Metoda | Endpoint | Opis |
|--------|----------|------|
| `POST/GET/PUT/DELETE` | `/manager/roles` | CRUD ról (stanowisk) |
| `POST/GET/PUT/DELETE` | `/manager/shifts` | CRUD definicji zmian |
| `POST/GET` | `/manager/requirements` | Wymagania kadrowe |
| `GET` | `/manager/users` | Lista pracowników (`?include_inactive=true`) |
| `POST` | `/manager/users` | Tworzenie konta pracownika |
| `PUT` | `/manager/users/{id}` | Aktualizacja danych |
| `PUT` | `/manager/users/{id}/roles` | Przypisanie ról |
| `PUT` | `/manager/users/{id}/reset-password` | Reset hasła |
| `GET` | `/manager/user-stats/{id}` | Statystyki pracownika |
| `GET` | `/manager/dashboard-home` | Dashboard (dzienne podsumowanie) |
| `GET/PUT` | `/manager/config` | Konfiguracja restauracji |
| `GET` | `/manager/schedules/available-employees` | Dostępność pracowników na konkretną zmianę |
| `GET` | `/manager/team-availability` | Dostępność zespołu |
| `GET` | `/manager/attendance` | Obecności (filtry: daty, status) |
| `POST` | `/manager/attendance` | Ręczne dodanie obecności |
| `PUT` | `/manager/attendance/{id}/confirm` | Zatwierdzenie |
| `PUT` | `/manager/attendance/{id}/reject` | Odrzucenie |
| `GET` | `/manager/attendance/export-pdf` | Eksport PDF |
| `GET` | `/manager/employee-hours` | Godziny miesięczne pracowników |
| `GET` | `/manager/giveaways` | Lista oddawanych zmian |
| `POST` | `/manager/giveaways/{id}/reassign` | Przydzielenie zastępstwa |
| `POST` | `/manager/giveaways/{id}/cancel` | Anulowanie |

### Employee (`/employee`)
| Metoda | Endpoint | Opis |
|--------|----------|------|
| `GET` | `/employee/availability` | Moja dostępność |
| `PUT` | `/employee/availability` | Aktualizacja dostępności |
| `GET` | `/employee/availability/status` | Sprawdzenie statusu wysłania dostępności |
| `GET` | `/employee/schedule` | Mój grafik (nieaktualne/przestarzała nazwa w docsach, naprawiona na my-schedule w API) |
| `GET` | `/employee/my-schedule` | Mój grafik |
| `GET` | `/employee/schedules/all` | Pełny grafik całego zespołu ("Cała załoga") |
| `GET` | `/employee/attendance-defaults` | Domyślne godziny z grafiku |
| `POST` | `/employee/attendance` | Rejestracja obecności |
| `GET` | `/employee/attendance` | Historia obecności |
| `POST` | `/employee/giveaway/{schedule_id}` | Oddaj zmianę |
| `DELETE` | `/employee/giveaway/{id}` | Anuluj oddanie |
| `GET` | `/employee/giveaways` | Moje oddania |
| `POST` | `/employee/google-calendar/auth` | Podpięcie Google Calendar |

### Scheduler (`/scheduler`)
| Metoda | Endpoint | Opis |
|--------|----------|------|
| `POST` | `/scheduler/generate` | Generuj grafik (Draft, nie zapisuje) |
| `POST` | `/scheduler/save_batch` | Zapisz batch zmian |
| `GET` | `/scheduler/list` | Lista przypisań |
| `POST` | `/scheduler/publish` | Opublikuj grafik |
| `POST` | `/scheduler/assignment` | Ręczne przypisanie |
| `DELETE` | `/scheduler/assignment/{id}` | Usuń przypisanie |

### POS v2 (`/pos/v2`)
| Metoda | Endpoint | Opis |
|--------|----------|------|
| `CRUD` | `/pos/v2/zones` | Strefy restauracji |
| `CRUD` | `/pos/v2/tables` | Stoły ze strefami i pojemnością |
| `CRUD` | `/pos/v2/categories` | Dynamiczne kategorie menu |
| `CRUD` | `/pos/v2/menu` | Pozycje menu z `prep_time_sec` i modyfikatorami |
| `CRUD` | `/pos/v2/modifier-groups` | Grupy modyfikatorów |
| `POST/GET` | `/pos/v2/orders` | Zamówienia (tworzenie z kursami, lista) |
| `POST` | `/pos/v2/kds/sync` | **Batch sync KDS** (offline-first, monotonic weight validation) |
| `GET` | `/pos/v2/kds/items` | Lista pozycji KDS z metadanymi pacingu |
| `POST` | `/pos/v2/payments` | Płatności (multi-method split) |

### Kuchnia / POS v1 (`/kitchen`) — Legacy
| Metoda | Endpoint | Opis |
|--------|----------|------|
| `GET/POST/PUT/DELETE` | `/kitchen/tables` | CRUD stolików |
| `GET/POST/PUT/DELETE` | `/kitchen/menu` | CRUD pozycji menu |
| `GET/POST/PUT/DELETE` | `/kitchen/orders` | Zarządzanie zamówieniami |

### Inne
| Metoda | Endpoint | Opis |
|--------|----------|------|
| `GET` | `/health` | Health check (DB + migracje Alembic) |
| `POST` | `/bug-report` | Zgłoszenie błędu → GitHub Issue |

## Testowanie

```bash
cd backend
python -m pytest tests/ -v

# Z raportem JUnit
python -m pytest tests/ -v --junitxml=test-results/backend.xml
```

Testy korzystają z in-memory SQLite (izolowane fixture'y `db_session`).

### KDS Testy

```bash
# Testy jednostkowe (pacing, sync weights)
python -m pytest tests/test_kds.py -v

# Testy integracyjne (endpoint /pos/v2/kds/sync)
python -m pytest tests/test_kds_api.py -v
```

### Reset i Seed bazy danych

```bash
# Wykasowanie i odtworzenie schematu
python reset_db_alembic.py

# Wygenerowanie danych testowych (pracownicy, menu, stoliki, grafiki, zamówienia KDS)
python seed_test_data.py
```

## API Docs (Swagger)

Po uruchomieniu serwera:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
