# Planner V2 - Automated Staff Scheduling System

System do automatycznego generowania grafików pracy z wykorzystaniem Google OR-Tools.

## 🎯 Funkcjonalności

### Dla Pracowników
- 📅 Składanie dyspozycyjności na cały tydzień
- 🎨 Intuicyjny interfejs z kolorowym oznaczeniem statusów
- 📱 Responsywny design (mobile-first)
- 🔄 Łatwa zmiana preferencji (kliknięcie = zmiana statusu)

### Dla Managerów
- ⚙️ Definiowanie ról (Barista, Kucharz, etc.)
- ⏰ Konfiguracja zmian (godziny pracy)
- 📊 Ustawianie wymagań obsadowych
- 🤖 Automatyczna generacja grafiku (Google OR-Tools)

## 🏗️ Architektura

### Backend (Python)
- **Framework**: FastAPI
- **Database**: PostgreSQL
- **Auth**: JWT (Bearer Token)
- **Solver**: Google OR-Tools (CP-SAT)

### Frontend (Flutter)
- **Platforms**: Web, iOS, Android
- **State Management**: Riverpod
- **Routing**: GoRouter
- **HTTP Client**: Dio

## 🚀 Quick Start

### 1. Backend Setup

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run backend (uses SQLite by default)
uvicorn backend.app.main:app --reload
```

API będzie dostępne na: `http://localhost:8000`
Dokumentacja: `http://localhost:8000/docs`

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
flutter pub get

# Run on web
flutter run -d chrome
```

## 📖 Workflow

1. **Manager** definiuje role i zmiany w zakładce "Konfiguracja"
2. **Manager** ustawia wymagania (ile osób potrzeba na każdej zmianie)
3. **Pracownicy** logują się i wypełniają swoją dostępność
4. **Manager** klika "Generuj Grafik" - algorytm OR-Tools automatycznie przypisuje pracowników
5. System uwzględnia:
   - ✅ Preferencje pracowników (maksymalizuje "Chcę pracować")
   - ✅ Wymagania obsadowe (minimum osób na zmianie)
   - ✅ Ograniczenia (max 1 zmiana dziennie, brak pracy gdy "Nie mogę")

## 🔐 Pierwsze Kroki

1. Zarejestruj konto przez `/auth/register`
2. Domyślnie konto jest typu EMPLOYEE
3. Aby ustawić konto jako MANAGER, zmień `role_system` w bazie danych na `'MANAGER'`

## 🛠️ Technologie

**Backend:**
- FastAPI
- SQLModel
- PostgreSQL
- Google OR-Tools
- JWT Authentication

**Frontend:**
- Flutter 3.29+
- Riverpod
- GoRouter
- Dio
- Google Fonts
- flutter_secure_storage

## 📱 Rozszerzenie na Mobile

Aplikacja Flutter jest już gotowa do kompilacji na iOS i Android:

```bash
# Android
flutter build apk

# iOS
flutter build ios
```

## 🤝 Współpraca Backend-Frontend

- Backend: `http://localhost:8000`
- Frontend: Zmień `baseUrl` w `lib/services/api_service.dart` jeśli backend jest na innym adresie

## � Dokumentacja

- **[⚡ QUICKSTART.md](QUICKSTART.md)** - Szybki start w 5 minut
- **[📖 USER_GUIDE.md](USER_GUIDE.md)** - Szczegółowy przewodnik użytkownika
- **[🏗️ ARCHITECTURE.md](ARCHITECTURE.md)** - Architektura systemu i diagramy
- **[🔧 IMPLEMENTATION.md](IMPLEMENTATION.md)** - Szczegóły implementacji i TODO
- **[🌐 API_EXAMPLES.md](API_EXAMPLES.md)** - Przykłady użycia API

## �📝 Licencja

Projekt prywatny - Planner V2
