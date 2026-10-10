# Szybki Start

## Nowa Architektura (Wielodostępność - Multi-Tenancy)

System PlannerV2 został rozbudowany o obsługę **wielu restauracji na jednej instancji** (model Tenant):
- Każda restauracja (Tenant) posiada swoją nazwę (`name`) oraz unikalny identyfikator logowania (`slug`, tzw. Login ID).
- **Logowanie (Dual-login)**: Użytkownicy mogą logować się na dwa sposoby:
  1. Za pomocą unikalnego, globalnego adresu `email` (i hasła).
  2. Za pomocą nazwy użytkownika (`username`) podając jednocześnie identyfikator restauracji (`slug`) oraz hasło.

## Wymagania

- Python 3.11+
- Flutter SDK 3.x+
- Git

## Uruchomienie Lokalne

### 1. Backend

```bash
cd backend

# Utwórz wirtualne środowisko (zalecane)
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

# Zainstaluj zależności
pip install -r requirements.txt

# (Opcjonalnie) Utwórz plik .env w katalogu backend/
# DATABASE_URL=sqlite:///./planner.db  (domyślnie)

# Uruchom migracje bazy danych
alembic upgrade head

# Wygeneruj dane testowe (tenanci, superadmin, managerowie, pracownicy itp.)
python seed_test_data.py

# Uruchom serwer
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

> **Domyślne dane logowania po wygenerowaniu danych (seed):**
> **Superadmin / Pierwszy Manager**: `manager@default.pl` / hasło: `Manager1`
> (Superadmin posiada również uprawnienia managera testowej restauracji).
>
> Pracownicy mogą logować się przypisanym emailem lub przez `username` + `Login ID` (tenant slug). Domyślne hasło pracowników testowych to `123`.

Backend będzie dostępny pod: http://127.0.0.1:8000
Dokumentacja API (Swagger): http://127.0.0.1:8000/docs

### 2. Frontend

```bash
cd frontend

# Zainstaluj zależności
flutter pub get

# Uruchom serwer deweloperski
flutter run -d web-server --web-hostname=127.0.0.1 --web-port=5000
```

Aplikacja będzie dostępna pod: http://127.0.0.1:5000

## Role i Konfiguracja Systemu

### 1. Panel Superadmina
W systemie dostępna jest rola globalna **SUPERADMIN**. Superadmin zarządza całą platformą z poziomu dedykowanego panelu dostępnego pod adresem: `/#/superadmin`.
Możliwości Superadmina:
- Tworzenie i edycja restauracji (Tenantów).
- Przegląd wszystkich użytkowników w systemie (niezależnie od restauracji).
- Dodawanie pierwszych managerów do nowo utworzonych restauracji.
- Resetowanie haseł managerów.

### 2. Panel Managera i Zarządzanie Pracownikami
Manager danej restauracji zarządza swoim lokalem:
- **Zarządzanie personelem:** Managerowie mogą teraz dodawać oraz edytować adresy email swoich pracowników (zakładka Zespół).
- **Konfiguracja ról i zmian:** Manager konfiguruje stanowiska (JobRoles) oraz zmiany (ShiftDefinition). Zmiany są przypisywane do ról, co oznacza, że pracownicy widzą tylko te zmiany (w grafiku i na liście zmian), które są powiązane z ich rolami.

## Przepływ Pracy (Workflow)

1. **Inicjalizacja (Superadmin)**: 
   - Superadmin tworzy nową restaurację (`name`, `slug`).
   - Następnie tworzy dla niej konto Managera podając adres email.
2. **Konfiguracja restauracji (Manager)**: 
   - Manager loguje się, tworzy Role (np. Kucharz, Kelner).
   - Tworzy definicje Zmian (np. "Poranna 08-16") i **przypisuje je do ról**.
   - Manager zaprasza/tworzy pracowników, podając ich imię, `username`, opcjonalnie `email`, oraz przypisując im odpowiednie Role.
3. **Generowanie Grafiku**: 
   - Manager ustala wymagania kadrowe na konkretne dni.
   - Algorytm dopasowuje pracowników m.in. uwzględniając ich dostępność oraz wymagane role dla danych zmian.
   - Manager weryfikuje szkic (Draft), zapisuje i publikuje grafik.
4. **Odbiór (Pracownik)**:
   - Pracownik loguje się (przez email, lub slug + username) i widzi w swoim panelu zmiany przypisane wyłącznie do jego stanowisk.

## Docker (Produkcja)

```bash
# Zbuduj frontend (wymagane przed docker-compose)
cd frontend
flutter build web

# Uruchom wszystkie kontenery
cd ..
docker-compose up -d
```

Aplikacja będzie dostępna pod: http://localhost (port 80)
- Nginx serwuje frontend i proxy'uje `/api` do backendu
- PostgreSQL używany jest jako baza danych
- Migracje Alembic uruchamiają się automatycznie przy starcie kontenerów

## Zmienne Środowiskowe

| Zmienna | Domyślna | Opis |
|---------|----------|------|
| `DATABASE_URL` | `sqlite:///./planner.db` | URL bazy danych |
| `GITHUB_TOKEN` | (brak) | Token GitHub do zgłaszania bugów |
| `SECRET_KEY` | (wbudowany) | Klucz JWT (zmienić w produkcji!) |

## Rozwiązywanie Problemów

| Problem | Rozwiązanie |
|---------|-------------|
| 401 Unauthorized | Token wygasł — wyloguj się i zaloguj ponownie |
| Nieudane logowanie użytkownika | Sprawdź czy użyto poprawnego formatu (email lub username+slug restauracji) |
| Pracownik nie widzi zmian | Zmiany (Role-Based Shifts) są teraz przypisane do ról. Upewnij się, że pracownik posiada rolę powiązaną z daną zmianą |
| Brak dostępu do `/superadmin` | Tylko użytkownik z uprawnieniem `SUPERADMIN` (np. ten z pliku seed) ma tam dostęp |
| Błąd migracji Alembic | `alembic upgrade head` — upewnij się że baza jest poprawnie skonfigurowana |
| Baza zablokowana (SQLite locked) | Zamknij uvicorn, odpal `python reset_db_alembic.py` i ponownie wygeneruj dane: `python seed_test_data.py` |
