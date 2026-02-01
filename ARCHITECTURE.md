# Planner V2 - Project Structure

```
PlannerV2/
├── backend/                      # Python FastAPI Backend
│   ├── app/
│   │   ├── models.py            # SQLModel database models
│   │   ├── database.py          # Database connection
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── auth_utils.py        # JWT authentication
│   │   ├── routers/             # API endpoints
│   │   │   ├── auth.py          # /auth/* (login, register)
│   │   │   ├── manager.py       # /manager/* (roles, shifts, requirements)
│   │   │   ├── employee.py      # /employee/* (availability)
│   │   │   └── scheduler.py     # /scheduler/* (generate schedule)
│   │   └── services/
│   │       └── solver.py        # Google OR-Tools solver logic
│   ├── requirements.txt         # Python dependencies
│   └── seed.py                  # Database seeding script
│
├── frontend/                     # Flutter Web/Mobile App
│   ├── lib/
│   │   ├── main.dart            # App entry point
│   │   ├── models/
│   │   │   └── models.dart      # Data models (User, Role, Shift, etc.)
│   │   ├── services/
│   │   │   └── api_service.dart # HTTP client with Dio
│   │   ├── providers/
│   │   │   └── providers.dart   # Riverpod state management
│   │   ├── utils/
│   │   │   └── router.dart      # GoRouter configuration
│   │   ├── screens/
│   │   │   ├── login_screen.dart
│   │   │   ├── employee/
│   │   │   │   └── employee_dashboard.dart
│   │   │   └── manager/
│   │   │       ├── manager_dashboard.dart
│   │   │       ├── setup_tab.dart
│   │   │       └── scheduler_tab.dart
│   │   └── widgets/
│   │       └── availability_grid.dart  # Interactive calendar
│   ├── pubspec.yaml             # Flutter dependencies
│   └── README.md
│
├── docker-compose.yml           # PostgreSQL container
├── README.md                    # Main documentation
├── IMPLEMENTATION.md            # Implementation details
└── .gitignore

```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Flutter Frontend                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Employee   │  │   Manager    │  │    Login     │      │
│  │  Dashboard   │  │  Dashboard   │  │    Screen    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                          │                                   │
│                    ┌─────▼─────┐                            │
│                    │ Riverpod  │                            │
│                    │ Providers │                            │
│                    └─────┬─────┘                            │
│                          │                                   │
│                    ┌─────▼─────┐                            │
│                    │    Dio    │                            │
│                    │ API Client│                            │
│                    └─────┬─────┘                            │
└──────────────────────────┼───────────────────────────────────┘
                           │ HTTP + JWT
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │     Auth     │  │   Manager    │  │   Employee   │      │
│  │   Router     │  │   Router     │  │   Router     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                          │                                   │
│                    ┌─────▼─────┐                            │
│                    │ SQLModel  │                            │
│                    │  Models   │                            │
│                    └─────┬─────┘                            │
│                          │                                   │
│  ┌──────────────────────▼────────────────────┐             │
│  │         Google OR-Tools Solver             │             │
│  │  (Constraint Programming - CP-SAT)         │             │
│  └────────────────────────────────────────────┘             │
└──────────────────────────┬───────────────────────────────────┘
                           │ SQL
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                    PostgreSQL Database                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  users │ job_roles │ shifts │ availability │ schedule│   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow

### Employee submitting availability:
1. Employee opens app → Flutter loads availability grid
2. Taps cells to change status (Preferred/Neutral/Unavailable)
3. Clicks "Save" → Dio sends POST to `/employee/availability`
4. Backend validates and saves to PostgreSQL
5. Returns success → UI shows confirmation

### Manager generating schedule:
1. Manager clicks "Generate Schedule" button
2. Flutter sends POST to `/scheduler/generate` with date range
3. Backend:
   - Fetches all availabilities from DB
   - Fetches staffing requirements
   - Runs OR-Tools CP-SAT solver
   - Saves generated schedule to DB
4. Returns result (success/infeasible) → UI shows feedback

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Flutter 3.29 | Cross-platform UI (Web, iOS, Android) |
| State | Riverpod | Reactive state management |
| Routing | GoRouter | Declarative routing with auth |
| HTTP | Dio | REST API client with interceptors |
| Backend | FastAPI | Modern Python web framework |
| ORM | SQLModel | Type-safe database models |
| Database | PostgreSQL | Relational database |
| Solver | OR-Tools | Constraint optimization |
| Auth | JWT | Stateless authentication |
| Container | Docker | Database containerization |
