# Architektura Systemu PlannerV2

## Diagram Komponentów

```mermaid
graph TD
    subgraph FRONTEND["FRONTEND (Flutter Web/Mobile)"]
        direction TB
        LOGIN["Login / Setup"]
        MANAGER_UI["Manager UI (6 zakładek)"]
        EMPLOYEE_UI["Employee Dashboard (3 ekrany)"]
        API_SVC["ApiService (Dio + JWT)"]
        CONFIG_SVC["ConfigService (QR / Manual)"]

        LOGIN --> API_SVC
        MANAGER_UI --> API_SVC
        EMPLOYEE_UI --> API_SVC
        MANAGER_UI --> CONFIG_SVC
    end

    API_SVC -- "HTTP/REST + JWT Bearer" --> ROUTERS

    subgraph BACKEND["BACKEND (FastAPI)"]
        direction TB
        ROUTERS["Routers Layer: auth | manager | employee | scheduler | health | bug"]
        SERVICES["Services Layer: ManagerService | EmployeeService | SchedulerService"]
        SOLVER["SolverService (OR-Tools CP-SAT)\n- Constraint Programming\n- Employee-Shift-Role Assignment\n- Availability & Requirements Matching"]
        ORM["SQLModel (ORM) + Alembic"]

        ROUTERS --> SERVICES
        SERVICES --> SOLVER
        SERVICES --> ORM
    end

    ORM --> DB["SQLite (dev) / PostgreSQL (prod)"]
```

## Modele Danych

```mermaid
erDiagram
    User {
        UUID id PK
        string username UK
        string email
        string password_hash
        string full_name
        enum role_system "MANAGER / EMPLOYEE"
        bool is_active
        int target_hours_per_month
        int target_shifts_per_month
        string google_access_token
        string google_refresh_token
    }

    JobRole {
        int id PK
        string name
        string color_hex
    }

    ShiftDefinition {
        int id PK
        string name
        time start_time
        time end_time
        string applicable_days
    }

    Availability {
        int id PK
        date date
        enum status "PREFERRED / NEUTRAL / UNAVAILABLE"
    }

    StaffingRequirement {
        int id PK
        int min_count
        date date
        int day_of_week
    }

    Schedule {
        UUID id PK
        date date
        bool is_published
    }

    Attendance {
        UUID id PK
        date date
        time check_in
        time check_out
        enum status "PENDING / CONFIRMED / REJECTED"
        bool was_scheduled
    }

    ShiftGiveaway {
        UUID id PK
        enum status "OPEN / TAKEN / CANCELLED"
    }

    RestaurantConfig {
        int id PK
        string name
        string address
        string opening_hours
    }

    User ||--o{ Availability : "has"
    User ||--o{ Schedule : "assigned to"
    User ||--o{ Attendance : "registers"
    User }o--o{ JobRole : "has roles (M:N via UserJobRoleLink)"
    ShiftDefinition ||--o{ Availability : "for shift"
    ShiftDefinition ||--o{ Schedule : "uses"
    ShiftDefinition ||--o{ StaffingRequirement : "requires"
    JobRole ||--o{ StaffingRequirement : "for role"
    JobRole ||--o{ Schedule : "as role"
    Schedule ||--o| ShiftGiveaway : "can be given away"
```

## Warstwa Serwisów

| Serwis | Odpowiedzialność |
|--------|-----------------|
| `SolverService` | Generowanie grafiku (OR-Tools CP-SAT): ładowanie ograniczeń (dostępność, wymagania, cele godzinowe MTD), uruchomienie solvera, zwrócenie propozycji z ostrzeżeniami |
| `ManagerService` | Operacje managera: CRUD ról/zmian/users, statystyki, giveaway management, edycja imion (first/last → full_name), podgląd dostępności na zmianę |
| `EmployeeService` | Operacje pracownika: dostępność (+ status endpoint), grafik z listą współpracowników, obecność, integracja Google Calendar (OAuth 2.0 token exchange) |
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
    S->>S: Fetch MTD hours (month-to-date)
    S->>S: CP-SAT Solver (constraints + soft penalties)
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

## Przepływ Integracji Google Calendar

```mermaid
sequenceDiagram
    participant E as Pracownik
    participant F as Frontend
    participant B as Backend
    participant G as Google OAuth

    E->>F: Klik "Połącz Google Calendar"
    F->>G: Redirect do Google Consent Screen
    G-->>F: Authorization code (auth_code)
    F->>B: POST /employee/google-calendar/auth {auth_code}
    B->>G: POST https://oauth2.googleapis.com/token
    Note over B,G: exchange auth_code for tokens
    G-->>B: {access_token, refresh_token}
    B->>B: Save tokens to User model
    B-->>F: {status: success}
```

## Bezpieczeństwo

- **JWT Auth**: Tokeny ważne 60 min (bcrypt password hashing)
- **Manager PIN**: Konfigurowalny zmienną `MANAGER_REGISTRATION_PIN` (domyślnie `1234`)
- **Rejestracja wyłączona**: Konta tworzy wyłącznie Manager (`POST /manager/users`)
- **Aktywacja użytkowników**: Dezaktywowani użytkownicy nie mogą się zalogować (`is_active`)
- **Role-Based Access**: Manager vs Employee — middleware sprawdza `role_system`
- **CORS**: Skonfigurowany na `*` (dev), do zawężenia w produkcji
- **Google OAuth 2.0**: Klucze (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`) przechowywane jako zmienne środowiskowe, nigdy w kodzie

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
    #       GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI

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
