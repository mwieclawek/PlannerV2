# PlannerV2 Backend

Backend systemu PlannerV2 — FastAPI + SQLModel + PostgreSQL / SQLite.

## Struktura Projektu

```
backend/
├── app/
│   ├── main.py                 # FastAPI app, CORS, lifespan, log_requests_middleware
│   ├── models.py               # SQLModel entities (modele Multi-Tenant, opcje lokalu, WFM)
│   ├── schemas.py              # Pydantic v2 schemas (walidacja haseł, logi, KDS sync)
│   ├── database.py             # Konfiguracja bazy danych (SQLite / PostgreSQL)
│   ├── auth_utils.py           # JWT creation/verification, password hashing, tenant context
│   ├── tenant_context.py       # ContextVar z aktualnym tenant_id dla loggera
│   ├── routers/
│   │   ├── auth.py             # Login (Dual-login), /me, change-password
│   │   ├── superadmin.py       # Global panel API: tenanci, managerowie, logi systemowe
│   │   ├── manager.py          # CRUD: role, zmiany, pracownicy, obecności, giveaway
│   │   ├── employee.py         # Grafik, dostępność, obecność, giveaway, Google Calendar
│   │   ├── scheduler.py        # Generowanie, batch save, publish, assignment
│   │   ├── pos.py              # POS v2: strefy, stoły, menu, zamówienia, KDS sync, płatności
│   │   ├── kitchen.py          # POS v1 (legacy): stoły, menu, zamówienia
│   │   ├── health.py           # Health check (DB + Alembic migration status)
│   │   ├── notifications.py    # Powiadomienia in-app + rejestracja urządzeń FCM
│   │   └── bug_report.py       # Proxy do GitHub Issues API
│   └── services/
│       ├── solver.py           # OR-Tools CP-SAT constraint solver
│       ├── log_service.py      # Agregacja, filtrowanie i inspekcja logów systemowych
│       ├── pos_service.py      # POS v2 logika biznesowa
│       ├── kds_service.py      # KDS: monotonic sync + pacing engine
│       ├── manager_service.py  # Logika biznesowa managera
│       ├── employee_service.py # Logika biznesowa pracownika
│       ├── scheduler_service.py # Operacje na grafiku
│       └── push_service.py     # Firebase Cloud Messaging (Android, iOS, Web)
├── alembic/                    # Migracje bazy danych
├── tests/                      # Zestaw testów automatycznych (pytest)
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

# Wygeneruj dane testowe (manager, pracownicy, menu, stoliki, grafiki)
python seed_test_data.py

# Uruchom serwer
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

> **Domyślne dane logowania po seedzie**:
> - Superadmin / Manager: `manager@default.pl` / `Manager123`
> - Pracownicy testowi: `anna`, `piotr`, `tomasz` / `Employee123`
> Wszystkie hasła podlegają regułom złożoności: min. 8 znaków, 1 wielka litera, 1 cyfra.

### Docker

```bash
docker build -t plannerv2-backend .
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host/db \
  -e SECRET_KEY=your_secret_key \
  plannerv2-backend
```

Migracje Alembic uruchamiane są automatycznie przy starcie kontenera.

## Baza Danych

### Inicjalizacja
Aplikacja tworzy tabele przy starcie (`init_db()` w lifespan), co zapewnia natychmiastowe działanie w środowiskach bez Alembic (np. w pipeline testowym Jenkins).

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

OR-Tools CP-SAT solver z regułami:
- **Role-Based Shifts**: pracownik przypisywany wyłącznie do zmian zgodnych z posiadanymi rolami.
- **Split shift**: pracownik może dostać do 2 zmian dziennie.
- **Nakładanie zmian**: dozwolone do 30 minut (na przekazanie stanowiska).
- **Odpoczynek dobowy**: minimalna przerwa 11 godzin między kolejnymi dniami pracy.
- **Cele**: respektuje `target_hours_per_month` i `target_shifts_per_month`.
- **Dostępność**: uwzględnia deklarowane preferencje (PREFERRED > NEUTRAL > UNAVAILABLE).
- **Draft mode**: `solve(save=False)` — generuje szkic bez zapisu do bazy.

## Główne Grupy API

### Auth (`/auth`)
| Metoda | Endpoint | Opis |
|--------|----------|------|
| `POST` | `/auth/token` | Logowanie (Dual-login: email lub username+tenant_slug) |
| `POST` | `/auth/register` | Rejestracja pierwszego managera z kodem PIN |
| `GET` | `/auth/me` | Dane zalogowanego użytkownika (tenant_id, role) |
| `PUT` | `/auth/change-password` | Zmiana hasła (walidacja min. 8 znaków, 1 wielka litera, 1 cyfra) |

### Superadmin (`/sysadmin`)
| Metoda | Endpoint | Opis |
|--------|----------|------|
| `GET/POST` | `/sysadmin/restaurants` | Lista i tworzenie lokali (Tenants) |
| `PUT` | `/sysadmin/restaurants/{id}` | Edycja danych lokalu |
| `PUT` | `/sysadmin/restaurants/{id}/status` | Aktywacja / dezaktywacja lokalu |
| `POST` | `/sysadmin/restaurants/{id}/managers` | Tworzenie managera dla lokalu |
| `GET` | `/sysadmin/users` | Wgląd w bazę wszystkich użytkowników w systemie |
| `PUT` | `/sysadmin/users/{id}/reset-password` | Awaryjny reset hasła |

### Manager (`/manager`)
| Metoda | Endpoint | Opis |
|--------|----------|------|
| `CRUD` | `/manager/roles` | CRUD ról (stanowisk) |
| `CRUD` | `/manager/shifts` | CRUD definicji zmian powiązanych z rolami |
| `POST/GET` | `/manager/requirements` | Wymagania kadrowe |
| `GET/POST` | `/manager/users` | Lista i tworzenie pracowników |
| `PUT` | `/manager/users/{id}` | Aktualizacja danych pracownika (w tym email) |
| `PUT` | `/manager/users/{id}/roles` | Przypisanie ról |
| `PUT` | `/manager/users/{id}/reset-password` | Reset hasła pracownika |
| `GET` | `/manager/dashboard-home` | Dashboard (dzienne podsumowanie) |
| `GET/PUT` | `/manager/config` | Konfiguracja restauracji |
| `GET` | `/manager/attendance` | Ewidencja obecności (filtry: daty, status) |
| `PUT` | `/manager/attendance/{id}/confirm` | Zatwierdzenie obecności |
| `PUT` | `/manager/attendance/{id}/reject` | Odrzucenie obecności |
| `GET` | `/manager/attendance/export-pdf` | Eksport raportu PDF |

### Employee (`/employee`)
| Metoda | Endpoint | Opis |
|--------|----------|------|
| `GET/PUT` | `/employee/availability` | Moja dostępność na zmiany zgodne z rolami |
| `GET` | `/employee/my-schedule` | Mój grafik |
| `GET` | `/employee/schedules/all` | Grafik całego zespołu |
| `POST` | `/employee/attendance` | Rejestracja obecności |
| `POST` | `/employee/giveaway/{schedule_id}` | Oddanie zmiany na giełdę |
| `GET` | `/employee/giveaways` | Lista dostępnych zmian na giełdzie |
| `POST` | `/employee/giveaways/{id}/claim` | Przejęcie zmiany |
| `POST` | `/employee/google-calendar/auth` | Integracja Google Calendar (autoryzacja offline) |

### Notifications (`/api/notifications`)
| Metoda | Endpoint | Opis |
|--------|----------|------|
| `GET` | `/api/notifications` | Lista moich powiadomień |
| `PATCH` | `/api/notifications/{id}/read` | Oznaczenie jako przeczytane |
| `POST` | `/api/notifications/devices` | Rejestracja tokenu urządzenia (Android, iOS, Web FCM) |
| `DELETE` | `/api/notifications/devices/{token}` | Wyrejestrowanie urządzenia przy wylogowaniu |

## Testowanie

```bash
cd backend
python -m pytest tests/ -v

# Z raportem JUnit dla Jenkins
python -m pytest tests/ -v --junitxml=test-results/backend.xml
```

Testy uruchamiane są w pamięci (SQLite in-memory) z użyciem izolowanych fixture'ów sesji.
