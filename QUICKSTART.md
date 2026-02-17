# Szybki Start

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
# MANAGER_REGISTRATION_PIN=twoj_pin
# DATABASE_URL=sqlite:///./planner.db  (domyślnie)

# Uruchom migracje bazy danych
alembic upgrade head

# Uruchom serwer
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

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

## Pierwsza Konfiguracja

### Utworzenie konta managera

Samodzielna rejestracja jest **wyłączona**. Pierwszy manager musi być utworzony przez API:

```bash
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123",
    "full_name": "Administrator",
    "role_system": "MANAGER",
    "manager_pin": "1234"
  }'
```

> **Uwaga**: PIN managera można zmienić zmienną środowiskową `MANAGER_REGISTRATION_PIN`.

### Konfiguracja systemu

1. Zaloguj się na konto managera w aplikacji (http://127.0.0.1:5000)
2. Przejdź do zakładki **Ustawienia**:
   - Dodaj **role** (np. Barista, Kucharz, Kelner) — każda z przypisanym kolorem
   - Dodaj **zmiany** (np. Rano 08:00-16:00, Wieczór 16:00-24:00)
3. Przejdź do zakładki **Zespół**:
   - Kliknij **+** aby utworzyć konta pracowników
   - Przypisz pracownikom role (kliknij na pracownika → przypisz role)

### Generowanie Grafiku

1. Przejdź do zakładki **Grafik**
2. Ustaw **wymagania kadrowe** (ile osób na jakim stanowisku potrzebujesz w danym dniu)
3. Kliknij **"Generuj grafik"** — solver automatycznie dopasuje pracowników
4. Wynik pojawi się jako **szkic (Draft)** — edytuj ręcznie jeśli potrzeba
5. Kliknij **"Zapisz"** — zmiany zostaną zapisane w bazie danych
6. Kliknij **"Opublikuj"** — pracownicy zobaczą grafik w swoim panelu

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
- PostgreSQL jako baza danych produkcyjna
- Alembic migracje uruchamiane automatycznie przy starcie

## Zmienne Środowiskowe

| Zmienna | Domyślna | Opis |
|---------|----------|------|
| `DATABASE_URL` | `sqlite:///./planner.db` | URL bazy danych |
| `MANAGER_REGISTRATION_PIN` | `1234` | PIN do tworzenia konta managera |
| `GITHUB_TOKEN` | (brak) | Token GitHub do zgłaszania bugów |
| `SECRET_KEY` | (wbudowany) | Klucz JWT (zmienić w produkcji!) |

## Rozwiązywanie Problemów

| Problem | Rozwiązanie |
|---------|-------------|
| 401 Unauthorized | Token wygasł — wyloguj się i zaloguj ponownie |
| 403 „Rejestracja wyłączona" | Konta tworzy manager (zakładka Zespół → +) |
| 403 „Account is deactivated" | Manager musi aktywować konto pracownika |
| Pusty grafik po generowaniu | Sprawdź: pracownicy mają przypisane role? Wymagania kadrowe ustawione? |
| „Shift already exists" | Zmiany muszą mieć unikalne godziny |
| Frontend nie łączy się z backendem | Sprawdź konfigurację serwera (ustawienia → QR / ręczny URL) |
| Błąd migracji Alembic | `alembic upgrade head` — upewnij się że baza jest dostępna |
