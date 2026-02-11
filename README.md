# PlannerV2 - System Planowania Grafików

Aplikacja do automatycznego generowania grafików pracy dla restauracji i lokali gastronomicznych.

## Funkcjonalności

### Manager
- 🗓️ **Automatyczny generator grafików** (OR-Tools constraint solver)
- 👥 **Zarządzanie zespołem** (role, zmiany, pracownicy)
- ✏️ **Edycja grafiku** - ręczne poprawki po wygenerowaniu
- ⚙️ **Konfiguracja restauracji** (nazwa, godziny otwarcia)

### Pracownik
- 📅 **Podgląd grafiku** na dany tydzień
- 📝 **Zgłaszanie dostępności** (preferowane/neutralne/niedostępny)

## Tech Stack

| Warstwa | Technologia |
|---------|-------------|
| Frontend | Flutter Web |
| Backend | FastAPI + SQLModel |
| Solver | Google OR-Tools |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Auth | JWT (python-jose) |

## Szybki Start

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --port 8080

# Frontend
cd frontend
flutter pub get
flutter run -d chrome --web-port 5000
```

**Rejestracja Managera:** PIN = `1234`

## Struktura Projektu

```
PlannerV2/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app
│   │   ├── models.py        # SQLModel entities
│   │   ├── routers/         # API endpoints
│   │   └── services/
│   │       └── solver.py    # OR-Tools constraint solver
│   └── tests/
├── frontend/
│   └── lib/
│       ├── screens/         # Manager & Employee views
│       ├── providers/       # Riverpod state
│       └── services/        # API client
├── nginx/                   # Production reverse proxy
├── docker-compose.yml
└── Jenkinsfile              # CI/CD pipeline
```

## API Endpoints

| Endpoint | Opis |
|----------|------|
| `POST /auth/register` | Rejestracja |
| `POST /auth/token` | Login (OAuth2) |
| `GET /manager/users` | Lista pracowników |
| `POST /manager/roles` | Dodaj rolę |
| `POST /manager/shifts` | Dodaj zmianę |
| `POST /scheduler/generate` | Generuj grafik (AI) |
| `POST /scheduler/save_batch` | Zapisz zmiany |

## Dokumentacja

- [QUICKSTART.md](QUICKSTART.md) - Szczegółowa instrukcja uruchomienia
- [ARCHITECTURE.md](ARCHITECTURE.md) - Architektura systemu
- [UI_DESIGN.md](UI_DESIGN.md) - Specyfikacja interfejsu
- [TEST_PLAN.md](TEST_PLAN.md) - Plan testów
- [USER_GUIDE.md](USER_GUIDE.md) - Podręcznik użytkownika

## Licencja

MIT License
