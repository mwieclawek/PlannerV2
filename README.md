# PlannerV2 - System Planowania Grafików

Aplikacja do automatycznego generowania grafików pracy dla restauracji i lokali gastronomicznych.

## Funkcjonalności

### Manager
- 🏠 **Dashboard** — podgląd dziennego grafiku, kalendarz, statystyki
- 🗓️ **Automatyczny generator grafików** — OR-Tools CP-SAT solver z trybem szkicu (Draft → Save → Publish)
- ✏️ **Edycja grafiku** — ręczne przypisanie/usunięcie pracowników, batch save
- 👥 **Zarządzanie zespołem** — tworzenie kont, przypisywanie ról, aktywacja/dezaktywacja, reset hasła, cele godzinowe
- ⚙️ **Konfiguracja restauracji** — role (stanowiska), definicje zmian, wymagania kadrowe, dane lokalu, **konfiguracja stolików i menu**
- 📋 **Obecności** — ewidencja czasu pracy, zatwierdzanie/odrzucanie, eksport do PDF
- 🔄 **Oddawanie zmian** — zarządzanie prośbami o oddanie zmiany, sugerowane zastępstwa
- 🐞 **Zgłaszanie błędów** — integracja z GitHub Issues

### Pracownik
- 📅 **Podgląd grafiku** — kalendarz z opublikowanymi zmianami
- 📝 **Zgłaszanie dostępności** — preferowane / neutralne / niedostępny
- ⏰ **Rejestracja obecności** — check-in / check-out
- 🔄 **Oddawanie zmian** — zgłoszenie oddania, śledzenie statusu

### Kelner (Point of Sale)
- 🍔 **Zarządzanie Zamówieniami** — przyjmowanie i modyfikacja zamówień od gości, wybór pozycji z menu
- 📋 **Widok Stolików** — przegląd otwartych rachunków i statusów stolików

### Kuchnia (Kitchen Display System)
- 👨‍🍳 **Realizacja Zamówień** — podgląd bieżących ticketów, oznaczanie etapów przygotowania (Oczekujące → W trakcie → Gotowe)

## Tech Stack

| Warstwa | Technologia |
|---------|-------------|
| Frontend | Flutter Web / Android / iOS |
| Backend | FastAPI + SQLModel |
| Solver | Google OR-Tools (CP-SAT) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Migracje | Alembic |
| Auth | JWT (python-jose) + bcrypt |
| PDF | ReportLab |
| CI/CD | Jenkins + Docker |
| Proxy | Nginx (reverse proxy + static files) |

## CI/CD Deployment Strategy

Aplikacja wykorzystuje Jenkins do automatycznych wdrożeń:
- **DEV (Development):** Wdrażany automatycznie z gałęzi `main`.
- **PROD (Produkcja):** Wdrażana automatycznie po utworzeniu taga wersji (np. `v1.0.0`).

## Szybki Start

```bash
# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
flutter pub get
flutter run -d web-server --web-port 5000
```

> **Uwaga**: Samodzielna rejestracja jest wyłączona. Konta tworzy wyłącznie Manager.
> Pierwszy manager musi być utworzony przez API: `POST /auth/register` z `manager_pin`.
> PIN managera konfiguruje się zmienną `MANAGER_REGISTRATION_PIN` (domyślnie `1234`).

## Struktura Projektu

```
PlannerV2/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + lifespan
│   │   ├── models.py            # SQLModel entities
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── database.py          # Konfiguracja bazy danych
│   │   ├── auth_utils.py        # JWT + password hashing
│   │   ├── routers/
│   │   │   ├── auth.py          # Login, /me, change-password
│   │   │   ├── manager.py       # CRUD zespołu, ról, zmian, obecności, giveaway
│   │   │   ├── employee.py      # Grafik, dostępność, obecność, giveaway
│   │   │   ├── scheduler.py     # Generowanie, save, publish, assignment
│   │   │   ├── kitchen.py       # Endpointy POS i KDS (stoliki, menu, zamówienia)
│   │   │   ├── health.py        # Health check z weryfikacją migracji
│   │   │   └── bug_report.py    # Proxy do GitHub Issues API
│   │   └── services/
│   │       ├── solver.py        # OR-Tools constraint solver
│   │       ├── manager_service.py
│   │       ├── employee_service.py
│   │       └── scheduler_service.py
│   ├── alembic/                 # Migracje bazy danych
│   └── tests/                   # Testy (pytest)
├── frontend/
│   └── lib/
│       ├── screens/
│       │   ├── login_screen.dart
│       │   ├── server_setup_screen.dart
│       │   ├── manager/         # Dashboard + 6 zakładek
│       │   ├── employee/        # Dashboard + 3 ekrany
│       │   └── pos/             # Ekrany Kelnera (POS) i Kuchni (KDS)
│       ├── widgets/             # Reużywalne komponenty
│       ├── providers/           # Riverpod state management
│       ├── services/            # ApiService (Dio) + ConfigService
│       └── models/              # Modele Dart
├── nginx/                       # Konfiguracja reverse proxy
├── docker-compose.yml           # PostgreSQL + Backend + Nginx
├── Jenkinsfile                  # CI/CD pipeline
└── docs/                        # Dokumentacja (ten plik i inne)
```

## API — Główne Endpointy

### Auth (`/auth`)
| Metoda | Endpoint | Opis |
|--------|----------|------|
| `POST` | `/auth/token` | Login (OAuth2 password flow) |
| `GET` | `/auth/me` | Dane zalogowanego użytkownika |
| `PUT` | `/auth/change-password` | Zmiana hasła |

### Manager (`/manager`)
| Metoda | Endpoint | Opis |
|--------|----------|------|
| `GET/POST/PUT/DELETE` | `/manager/roles` | CRUD ról (stanowisk) |
| `GET/POST/PUT/DELETE` | `/manager/shifts` | CRUD definicji zmian |
| `GET/POST` | `/manager/requirements` | Wymagania kadrowe |
| `GET/POST` | `/manager/users` | Lista / tworzenie pracowników |
| `PUT` | `/manager/users/{id}` | Aktualizacja użytkownika |
| `PUT` | `/manager/users/{id}/roles` | Przypisanie ról |
| `PUT` | `/manager/users/{id}/reset-password` | Reset hasła |
| `GET` | `/manager/dashboard-home` | Dashboard z dziennym podglądem |
| `GET` | `/manager/user-stats/{id}` | Statystyki pracownika |
| `GET` | `/manager/config` | Konfiguracja restauracji |
| `GET/POST` | `/manager/attendance` | Obecności (CRUD + filtrowanie) |
| `PUT` | `/manager/attendance/{id}/confirm` | Zatwierdzenie obecności |
| `PUT` | `/manager/attendance/{id}/reject` | Odrzucenie obecności |
| `GET` | `/manager/attendance/export-pdf` | Eksport PDF obecności |
| `GET` | `/manager/employee-hours` | Podsumowanie godzin miesięcznych |
| `GET` | `/manager/giveaways` | Lista oddawanych zmian |
| `POST` | `/manager/giveaways/{id}/reassign` | Przydzielenie zastępstwa |
| `POST` | `/manager/giveaways/{id}/cancel` | Anulowanie oddania |
| `GET` | `/manager/schedules/available-employees` | Lista dostępnych na konkretną zmianę |
| `GET` | `/manager/team-availability` | Dostępność całego zespołu |

### Employee (`/employee`)
| Metoda | Endpoint | Opis |
|--------|----------|------|
| `GET` | `/employee/availability` | Moja dostępność |
| `PUT` | `/employee/availability` | Aktualizacja dostępności |
| `GET` | `/employee/availability/status` | Status wysłanej dostępności |
| `GET` | `/employee/schedule` | Mój grafik |
| `GET` | `/employee/attendance-defaults` | Domyślne godziny check-in/out |
| `POST` | `/employee/attendance` | Rejestracja obecności |
| `GET` | `/employee/attendance` | Moja historia obecności |
| `POST` | `/employee/giveaway/{schedule_id}` | Oddaj zmianę |
| `DELETE` | `/employee/giveaway/{id}` | Anuluj oddanie |
| `GET` | `/employee/giveaways` | Moje oddania zmian |
| `POST` | `/employee/google-calendar/auth` | Integracja Google Calendar |

### Scheduler (`/scheduler`)
| Metoda | Endpoint | Opis |
|--------|----------|------|
| `POST` | `/scheduler/generate` | Generuj grafik (AI solver) |
| `POST` | `/scheduler/save_batch` | Zapisz zmiany (batch) |
| `GET` | `/scheduler/list` | Lista przypisań w zakresie dat |
| `POST` | `/scheduler/publish` | Opublikuj grafik |
| `POST` | `/scheduler/assignment` | Ręczne przypisanie |
| `DELETE` | `/scheduler/assignment/{id}` | Usuń przypisanie |

### Kuchnia / POS (`/kitchen`)
| Metoda | Endpoint | Opis |
|--------|----------|------|
| `GET/POST/PUT/DELETE` | `/kitchen/tables` | Zarządzanie stolikami |
| `GET/POST/PUT/DELETE` | `/kitchen/menu` | Zarządzanie pozycjami menu |
| `GET/POST/PUT/DELETE` | `/kitchen/orders` | Zarządzanie zamówieniami kelnerskimi |
| `POST/PUT/DELETE` | `/kitchen/orders/{id}/items` | Pozycje w zamówieniu |
| `PUT` | `/kitchen/orders/{id}/status` | Zmiana statusu całego zamówienia |

### Inne
| Metoda | Endpoint | Opis |
|--------|----------|------|
| `GET` | `/health` | Health check (DB + migracje) |
| `POST` | `/bug-report` | Zgłoszenie błędu → GitHub Issue |

## Dokumentacja

- [QUICKSTART.md](QUICKSTART.md) — Instrukcja uruchomienia
- [ARCHITECTURE.md](ARCHITECTURE.md) — Architektura systemu
- [UI_DESIGN.md](UI_DESIGN.md) — Specyfikacja interfejsu
- [TEST_PLAN.md](TEST_PLAN.md) — Plan testów
- [USER_GUIDE.md](USER_GUIDE.md) — Podręcznik użytkownika
- [backend/README.md](backend/README.md) — Dokumentacja backendu
- [frontend/README.md](frontend/README.md) — Dokumentacja frontendu
- [frontend/ANDROID_SETUP.md](frontend/ANDROID_SETUP.md) — Budowanie na Android
- [frontend/iOS_SETUP.md](frontend/iOS_SETUP.md) — Budowanie na iOS

## Licencja

MIT License
