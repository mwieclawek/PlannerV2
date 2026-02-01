# Szybki Start

## Wymagania

- Python 3.11+
- Flutter 3.x
- Node.js (opcjonalnie, dla narzędzi budowania)

## Uruchomienie Lokalne

### 1. Backend

```bash
cd PlannerV2

# Utwórz wirtualne środowisko (opcjonalnie)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Zainstaluj zależności
pip install -r backend/requirements.txt

# Uruchom serwer
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Backend będzie dostępny pod: http://127.0.0.1:8000
Dokumentacja API (Swagger): http://127.0.0.1:8000/docs

### 2. Frontend

```bash
cd PlannerV2/frontend

# Zainstaluj zależności
flutter pub get

# Uruchom serwer deweloperski
flutter run -d web-server --web-hostname=127.0.0.1 --web-port=5000
```

Aplikacja będzie dostępna pod: http://127.0.0.1:5000

## Pierwsza Konfiguracja

1. Otwórz http://127.0.0.1:5000
2. Kliknij "Zarejestruj się"
3. Wybierz "MANAGER" i podaj PIN: `1234`
4. Po zalogowaniu przejdź do zakładki "Ustawienia"
5. Dodaj role (np. Barista, Kucharz)
6. Dodaj zmiany (np. 08:00-16:00, 16:00-24:00)
7. Zarejestruj pracowników (jako EMPLOYEE, bez PIN)
8. Przypisz im role w zakładce "Zespół"

## Generowanie Grafiku

1. Przejdź do zakładki "Grafik"
2. Wybierz tydzień
3. Kliknij "Generuj grafik"
4. Edytuj ręcznie jeśli potrzeba
5. Kliknij "Zapisz zmiany"

## Docker (Produkcja)

```bash
docker-compose up -d
```

Aplikacja będzie dostępna pod: http://localhost (port 80)

## Rozwiązywanie Problemów

| Problem | Rozwiązanie |
|---------|-------------|
| "Invalid manager PIN" | Użyj PIN: `1234` |
| "Shift already exists" | Zmiany muszą mieć unikalne godziny |
| Pusty grafik | Sprawdź czy są pracownicy z przypisanymi rolami |
| 401 Unauthorized | Wyloguj się i zaloguj ponownie |
