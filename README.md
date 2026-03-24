# 🗓️ PlannerV2 — Inteligentny System Planowania Grafików

<div align="center">

**Kompleksowa aplikacja do automatycznego generowania grafików pracy, zarządzania zespołem i obsługi zamówień kuchennych dla restauracji i lokali gastronomicznych.**

[![Backend](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)](backend/)
[![Frontend](https://img.shields.io/badge/Frontend-Flutter-02569B?logo=flutter)](frontend/)
[![Solver](https://img.shields.io/badge/Solver-OR--Tools-4285F4?logo=google)](https://developers.google.com/optimization)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-Jenkins-D24939?logo=jenkins)](Jenkinsfile)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## ✨ Funkcjonalności

### 👔 Panel Managera
| Moduł | Opis |
|-------|------|
| 🏠 **Dashboard** | Podgląd dziennego grafiku, kalendarz, statystyki zespołu |
| 🗓️ **Auto-Grafik** | Inteligentny generator OR-Tools CP-SAT z trybem szkicu (Draft → Save → Publish), ostrzeżenia kadrowe |
| ✏️ **Edycja grafiku** | Ręczne przypisanie/usunięcie pracowników, batch save, widok wymagań kadrowych |
| 👥 **Zarządzanie zespołem** | Tworzenie kont, przypisywanie ról, aktywacja/dezaktywacja, reset hasła, cele godzinowe/zmianowe |
| ⚙️ **Konfiguracja** | Role (stanowiska), definicje zmian z dniami obowiązywania, wymagania kadrowe (globalne i per-datę), dane lokalu, godziny otwarcia |
| 📋 **Obecności** | Ewidencja czasu pracy, zatwierdzanie/odrzucanie, ręczne dodawanie, eksport PDF |
| 🔄 **Giełda Zmian** | Zarządzanie prośbami o oddanie zmiany, sugerowane zastępstwa, przydzielanie/anulowanie |
| 🏖️ **Urlopy** | Przeglądanie wniosków urlopowych, zatwierdzanie/odrzucanie, widok kalendarza urlopów |
| 📊 **Podsumowania** | Miesięczne godziny i zmiany per pracownik, status dostępności |
| 🍽️ **POS** | Zarządzanie stołami restauracji, konfiguracja menu (kategorie: zupy, dania główne, desery, napoje) |
| 🐞 **Zgłaszanie błędów** | Integracja z GitHub Issues |

### 👤 Panel Pracownika
| Moduł | Opis |
|-------|------|
| 📅 **Mój Grafik** | Kalendarz z opublikowanymi zmianami, lista współpracowników na zmianę |
| 📝 **Dostępność** | Preferowany / Dostępny / Niedostępny — tygodniowy grid |
| ⏰ **Obecność** | Check-in / Check-out z domyślnymi godzinami z grafiku |
| 🔄 **Oddawanie zmian** | Zgłoszenie oddania, śledzenie statusu, przejmowanie zmian innych pracowników |
| 🏖️ **Urlopy** | Składanie wniosków urlopowych, śledzenie statusu |
| 🔔 **Powiadomienia** | In-app + Push (FCM) o publikacji grafiku, zmianach na giełdzie, urlopach |

### 🍳 Moduł POS / Kitchen Display System
| Moduł | Opis |
|-------|------|
| 🪑 **Stoły** | CRUD stolików restauracji (Manager) |
| 📋 **Menu** | Pozycje menu z kategoriami i cenami, soft-delete |
| 🛒 **Zamówienia (POS)** | Tworzenie zamówień dla stolika, snapshot cen i nazw pozycji |
| 📺 **Kitchen Display** | Widok kuchni: zamówienia w kolejce, zmiana statusu (PENDING → IN_PROGRESS → READY → DELIVERED) |
| ❌ **Anulowanie** | Anulowanie zamówień (soft-cancel) |

---

## 🛠️ Tech Stack

| Warstwa | Technologia |
|---------|-------------|
| Frontend | Flutter Web / Android / iOS |
| Backend | FastAPI + SQLModel + Pydantic v2 |
| Solver | Google OR-Tools (CP-SAT) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Migracje | Alembic |
| Auth | JWT (python-jose) + bcrypt |
| Push | Firebase Cloud Messaging (FCM) |
| Encryption | cryptography (Fernet) — tokeny Google |
| PDF | ReportLab |
| CI/CD | Jenkins + Docker |
| Proxy | Nginx (reverse proxy + static files) |

---

## 🚀 Szybki Start

```bash
# Backend
cd backend
python -m venv venv && venv\Scripts\activate  # Windows
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

---

## 📁 Struktura Projektu

```
PlannerV2/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI app + lifespan
│   │   ├── models.py              # SQLModel entities (20+ modeli)
│   │   ├── schemas.py             # Pydantic v2 schemas
│   │   ├── database.py            # Konfiguracja bazy danych
│   │   ├── auth_utils.py          # JWT + password hashing
│   │   ├── routers/
│   │   │   ├── auth.py            # Login, /me, change-password
│   │   │   ├── manager.py         # CRUD zespołu, ról, zmian, obecności, urlopy
│   │   │   ├── employee.py        # Grafik, dostępność, obecność, giełda, urlopy
│   │   │   ├── scheduler.py       # Generowanie, save, publish, assignment
│   │   │   ├── kitchen.py         # POS: stoły, menu, zamówienia (KDS)
│   │   │   ├── notifications.py   # Powiadomienia in-app + rejestracja FCM
│   │   │   ├── health.py          # Health check z weryfikacją migracji
│   │   │   └── bug_report.py      # Proxy do GitHub Issues API
│   │   └── services/
│   │       ├── solver.py           # OR-Tools constraint solver
│   │       ├── manager_service.py  # Logika biznesowa managera
│   │       ├── employee_service.py # Logika biznesowa pracownika
│   │       ├── scheduler_service.py# Operacje na grafiku
│   │       └── push_service.py     # Firebase Cloud Messaging
│   ├── alembic/                    # Migracje bazy danych
│   └── tests/                      # Testy (pytest)
├── frontend/
│   └── lib/
│       ├── screens/
│       │   ├── login_screen.dart
│       │   ├── server_setup_screen.dart
│       │   ├── privacy_policy_screen.dart
│       │   ├── manager/            # Dashboard + 8 zakładek
│       │   ├── employee/           # Dashboard + 5 ekranów
│       │   └── pos/                # POS: waiter, kds, orders, setup
│       ├── widgets/                # Reużywalne komponenty
│       ├── providers/              # Riverpod state management
│       ├── services/               # ApiService (Dio) + ConfigService
│       └── models/                 # Modele Dart
├── nginx/                          # Konfiguracja reverse proxy
├── docker-compose.yml              # PostgreSQL + Backend + Nginx
├── Jenkinsfile                     # CI/CD pipeline (DEV + PROD)
└── docs/
    ├── ARCHITECTURE.md             # Architektura systemu
    ├── USER_GUIDE.md               # Podręcznik użytkownika
    ├── QUICKSTART.md               # Instrukcja uruchomienia
    ├── UI_DESIGN.md                # Specyfikacja interfejsu
    ├── TEST_PLAN.md                # Plan testów
    └── PUSH_ARCHITECTURE.md        # Architektura powiadomień push
```

---

## 🔌 API — Główne Endpointy

### Auth (`/auth`)
| Metoda | Endpoint | Opis |
|--------|----------|------|
| `POST` | `/auth/token` | Login (OAuth2 password flow) |
| `POST` | `/auth/register` | Rejestracja managera (z PIN) |
| `GET` | `/auth/me` | Dane zalogowanego użytkownika |
| `PUT` | `/auth/change-password` | Zmiana hasła |

### Manager (`/manager`)
| Metoda | Endpoint | Opis |
|--------|----------|------|
| `CRUD` | `/manager/roles` | Role (stanowiska) |
| `CRUD` | `/manager/shifts` | Definicje zmian |
| `GET/POST` | `/manager/requirements` | Wymagania kadrowe |
| `GET/POST` | `/manager/users` | Lista / tworzenie pracowników |
| `PUT` | `/manager/users/{id}` | Aktualizacja użytkownika |
| `PUT` | `/manager/users/{id}/roles` | Przypisanie ról |
| `PUT` | `/manager/users/{id}/password` | Reset hasła |
| `GET` | `/manager/dashboard/home` | Dashboard z dziennym podglądem |
| `GET` | `/manager/users/{id}/stats` | Statystyki pracownika |
| `GET/POST` | `/manager/config` | Konfiguracja restauracji |
| `GET/POST` | `/manager/attendance` | Obecności (CRUD + filtrowanie) |
| `PUT` | `/manager/attendance/{id}/confirm` | Zatwierdzenie obecności |
| `PUT` | `/manager/attendance/{id}/reject` | Odrzucenie obecności |
| `GET` | `/manager/attendance/export` | Eksport PDF obecności |
| `GET` | `/manager/employee-hours` | Podsumowanie godzin miesięcznych |
| `GET` | `/manager/availability` | Dostępność wszystkich pracowników |
| `GET` | `/manager/schedules/available-employees` | Dostępni na zmianę |
| `GET/POST/DELETE` | `/manager/giveaways` | Giełda zmian (zarządzanie) |
| `GET/POST` | `/manager/leave-requests` | Wnioski urlopowe (przeglądanie + zatwierdzanie) |
| `GET` | `/manager/leave-requests/calendar` | Kalendarz urlopów |

### Employee (`/employee`)
| Metoda | Endpoint | Opis |
|--------|----------|------|
| `GET/POST` | `/employee/availability` | Moja dostępność |
| `GET` | `/employee/availability/status` | Status wysłanej dostępności |
| `GET` | `/employee/my-schedule` | Mój grafik |
| `GET` | `/employee/schedules/all` | Grafik całego zespołu |
| `GET` | `/employee/schedule-summary` | Podsumowanie godzin (tydzień/miesiąc) |
| `GET/POST` | `/employee/attendance` | Rejestracja i historia obecności |
| `GET` | `/employee/attendance/defaults/{date}` | Domyślne godziny z grafiku |
| `POST/DELETE` | `/employee/giveaway` | Oddaj / Anuluj zmianę |
| `GET` | `/employee/giveaways` | Dostępne zmiany na giełdzie |
| `POST` | `/employee/giveaways/{id}/claim` | Przejmij zmianę |
| `POST/GET/DELETE` | `/employee/leave-requests` | Wnioski urlopowe |
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

### Kitchen / POS (`/kitchen`)
| Metoda | Endpoint | Opis |
|--------|----------|------|
| `GET/POST/DELETE` | `/kitchen/tables` | CRUD stolików |
| `GET/POST/PUT/DELETE` | `/kitchen/menu` | CRUD pozycji menu |
| `POST` | `/kitchen/orders` | Utwórz zamówienie (kelner) |
| `GET` | `/kitchen/orders` | Lista zamówień (filtr po statusie/stoliku) |
| `GET` | `/kitchen/orders/{id}` | Szczegóły zamówienia |
| `PATCH` | `/kitchen/orders/{id}/status` | Zmiana statusu (KDS) |
| `DELETE` | `/kitchen/orders/{id}` | Anuluj zamówienie |

### Notifications (`/api/notifications`)
| Metoda | Endpoint | Opis |
|--------|----------|------|
| `GET` | `/api/notifications` | Moje powiadomienia |
| `PATCH` | `/api/notifications/{id}/read` | Oznacz jako przeczytane |
| `POST` | `/api/notifications/devices` | Rejestracja tokenu FCM |
| `DELETE` | `/api/notifications/devices/{token}` | Wyrejestrowanie urządzenia |

### Inne
| Metoda | Endpoint | Opis |
|--------|----------|------|
| `GET` | `/health` | Health check (DB + migracje) |
| `POST` | `/bug-report` | Zgłoszenie błędu → GitHub Issue |

---

## 🔧 Zmienne Środowiskowe

| Zmienna | Opis | Wymagana |
|---------|------|----------|
| `DATABASE_URL` | Connection string bazy danych | ✅ (prod) |
| `SECRET_KEY` | Klucz JWT | ✅ |
| `MANAGER_REGISTRATION_PIN` | PIN do rejestracji managera | ❌ (domyślnie `1234`) |
| `ENCRYPTION_KEY` | Klucz Fernet do szyfrowania tokenów Google | ❌ |
| `GOOGLE_CLIENT_ID` | OAuth 2.0 Client ID | ❌ |
| `GOOGLE_CLIENT_SECRET` | OAuth 2.0 Client Secret | ❌ |
| `GOOGLE_REDIRECT_URI` | OAuth 2.0 Redirect URI | ❌ |
| `GOOGLE_APPLICATION_CREDENTIALS` | Ścieżka do Firebase service account JSON | ❌ |
| `GITHUB_TOKEN` | Token do tworzenia Issues | ❌ |
| `GITHUB_REPO` | Repozytorium do Issues (format: `owner/repo`) | ❌ |

---

## 🚢 CI/CD & Deployment

Aplikacja wykorzystuje Jenkins do automatycznych wdrożeń:

- **DEV**: Wdrażany automatycznie z gałęzi `main`
- **PROD**: Wdrażany automatycznie po utworzeniu taga wersji (np. `v1.0.0`)

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:15
  backend:
    build: ./backend
    # Alembic migrations run on startup
  nginx:
    image: nginx:alpine
    ports: ["80:80"]
```

---

## 📚 Dokumentacja

| Dokument | Opis |
|----------|------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Architektura systemu, diagramy, modele danych |
| [USER_GUIDE.md](USER_GUIDE.md) | Podręcznik użytkownika (Manager + Pracownik + POS) |
| [QUICKSTART.md](QUICKSTART.md) | Instrukcja uruchomienia |
| [UI_DESIGN.md](UI_DESIGN.md) | Specyfikacja interfejsu |
| [TEST_PLAN.md](TEST_PLAN.md) | Plan testów |
| [PUSH_ARCHITECTURE.md](PUSH_ARCHITECTURE.md) | Architektura powiadomień push |

---

## 📄 Licencja

MIT License — zobacz [LICENSE](LICENSE)
