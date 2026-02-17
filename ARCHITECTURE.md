# Architektura Systemu

## Diagram Komponentów

```
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND (Flutter Web/Mobile)               │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌───────────────┐  ┌───────────────────────┐  │
│  │ Login/Setup  │  │ Manager UI    │  │ Employee Dashboard    │  │
│  │             │  │ (6 zakładek)  │  │ (3 ekrany)           │  │
│  └─────────────┘  └───────────────┘  └───────────────────────┘  │
│                          │                                       │
│          ┌───────────────┼───────────────┐                      │
│          │  ApiService    │ ConfigService │                      │
│          │  (Dio + JWT)  │ (QR/Manual)   │                      │
│          └───────────────┴───────────────┘                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP/REST + JWT Bearer
┌──────────────────────────┼──────────────────────────────────────┐
│                      BACKEND (FastAPI)                           │
├──────────────────────────┼──────────────────────────────────────┤
│          ┌───────────────┴───────────────┐                      │
│          │         Routers Layer          │                      │
│          │  auth │ manager │ employee    │                      │
│          │  scheduler │ health │ bug     │                      │
│          └───────────────┬───────────────┘                      │
│                          │                                       │
│  ┌───────────────────────┼───────────────────────────────────┐  │
│  │              Services Layer                                │  │
│  │  ManagerService │ EmployeeService │ SchedulerService      │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │           SolverService (OR-Tools CP-SAT)           │  │  │
│  │  │  - Constraint Programming                           │  │  │
│  │  │  - Employee-Shift-Role Assignment                   │  │  │
│  │  │  - Availability & Requirements Matching             │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────┬───────────────────────────────────┘  │
│                          │                                       │
│          ┌───────────────┴───────────────┐                      │
│          │   SQLModel (ORM) + Alembic    │                      │
│          └───────────────┬───────────────┘                      │
└──────────────────────────┼──────────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              │ SQLite (dev) / Postgres │
              └─────────────────────────┘
```

## Modele Danych

| Model | Opis | Kluczowe pola |
|-------|------|---------------|
| `User` | Użytkownik systemu | `username`, `role_system` (MANAGER/EMPLOYEE), `is_active`, `target_hours_per_month`, `target_shifts_per_month` |
| `JobRole` | Stanowisko (Barista, Kucharz) | `name`, `color_hex` |
| `UserJobRoleLink` | Tabela łącząca User ↔ JobRole (M:N) | `user_id`, `role_id` |
| `ShiftDefinition` | Definicja zmiany (8:00-16:00) | `name`, `start_time`, `end_time`, `applicable_days` |
| `Availability` | Dostępność pracownika | `user_id`, `date`, `shift_def_id`, `status` (PREFERRED/NEUTRAL/UNAVAILABLE) |
| `StaffingRequirement` | Wymagania kadrowe | `shift_def_id`, `role_id`, `min_count`, `date`/`day_of_week` |
| `Schedule` | Przypisanie: kto, kiedy, gdzie | `date`, `user_id`, `shift_def_id`, `role_id`, `is_published` |
| `RestaurantConfig` | Konfiguracja lokalu (singleton) | `name`, `address`, `opening_hours` |
| `Attendance` | Rejestracja czasu pracy | `user_id`, `date`, `check_in`, `check_out`, `status` (PENDING/CONFIRMED/REJECTED), `was_scheduled` |
| `ShiftGiveaway` | Oddawanie zmian | `schedule_id`, `offered_by`, `taken_by`, `status` (OPEN/TAKEN/CANCELLED) |

## Warstwa Serwisów

| Serwis | Odpowiedzialność |
|--------|-----------------|
| `SolverService` | Generowanie grafiku (OR-Tools CP-SAT): ładowanie ograniczeń, uruchomienie solvera, zwrócenie propozycji |
| `ManagerService` | Operacje managera: CRUD ról/zmian/users, statystyki, giveaway management |
| `EmployeeService` | Operacje pracownika: dostępność, grafik, obecność |
| `SchedulerService` | Operacje na grafiku: zapis batch, listowanie, publikacja |

## Przepływ Generowania Grafiku

```mermaid
sequenceDiagram
    participant M as Manager
    participant F as Frontend
    participant B as Backend
    participant S as SolverService

    M->>F: Klik "Generuj grafik"
    F->>B: POST /scheduler/generate
    B->>S: solve(start_date, end_date, save=False)
    S->>S: Load: users, roles, shifts, requirements, availability
    S->>S: CP-SAT Solver (constraints + penalties)
    S-->>B: {status, schedules[], warnings[]}
    B-->>F: Draft schedule (nie zapisany do DB)
    F->>F: Display in grid (Draft Mode)
    M->>F: Ręczne edycje (dodaj/usuń)
    M->>F: Klik "Zapisz"
    F->>B: POST /scheduler/save_batch
    B-->>F: {status: saved, count}
    M->>F: Klik "Opublikuj"
    F->>B: POST /scheduler/publish
    B-->>F: {status: published, count}
    Note over F: Pracownicy widzą grafik
```

## Przepływ Oddawania Zmiany

```mermaid
sequenceDiagram
    participant E as Pracownik
    participant F as Frontend
    participant B as Backend
    participant M as Manager

    E->>F: Klik "Oddaj zmianę"
    F->>B: POST /employee/giveaway/{schedule_id}
    B-->>F: {id, status: OPEN}
    Note over B: Giveaway widoczny w panelu Managera
    M->>F: Widzi listę oddawanych zmian
    F->>B: GET /manager/giveaways
    B-->>F: Giveaways + sugerowane zastępstwa
    M->>F: Klik "Przydziel" (wybór zastępcy)
    F->>B: POST /manager/giveaways/{id}/reassign
    B-->>F: {status: TAKEN}
```

## Bezpieczeństwo

- **JWT Auth**: Tokeny ważne 60 min (bcrypt password hashing)
- **Manager PIN**: Konfigurowalny zmienną `MANAGER_REGISTRATION_PIN` (domyślnie `1234`)
- **Rejestracja wyłączona**: Konta tworzy wyłącznie Manager (`POST /manager/users`)
- **Aktywacja użytkowników**: Dezaktywowani użytkownicy nie mogą się zalogować (`is_active`)
- **Role-Based Access**: Manager vs Employee — middleware sprawdza `role_system`
- **CORS**: Skonfigurowany na `*` (dev), do zawężenia w produkcji

## Wdrożenie (Produkcja)

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:15
    # Persistent volume for data

  backend:
    build: ./backend
    # Alembic migrations run on startup
    # env: DATABASE_URL, MANAGER_REGISTRATION_PIN, GITHUB_TOKEN

  nginx:
    image: nginx:alpine
    ports: ["80:80"]
    # Reverse proxy: /api → backend, / → frontend static files
```

Pipeline CI/CD (Jenkins):
1. Backend tests (`pytest`)
2. Frontend analyze (`flutter analyze`)
3. Docker build & push
4. Deploy to dev/staging/prod
