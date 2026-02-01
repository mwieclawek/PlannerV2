# ⚡ Quick Start Guide

## 🚀 Uruchomienie w 5 minut

### Wymagania
- Python 3.9+
- Flutter 3.0+
- Docker Desktop (dla PostgreSQL)

### Krok 1: Backend (Terminal 1)
```bash
# Sklonuj/otwórz projekt
cd PlannerV2

# Zainstaluj zależności Python
pip install -r backend/requirements.txt

# Uruchom backend (Baza SQLite zostanie utworzona automatycznie)
uvicorn backend.app.main:app --reload
```

✅ Backend działa na: http://localhost:8000
📖 Dokumentacja API: http://localhost:8000/docs

### Krok 2: Seed Database (Terminal 2)
```bash
# Wypełnij bazę przykładowymi danymi
python backend/seed.py
```

✅ Utworzone konta:
- Manager: manager@planner.com / manager123
- Employee: anna@planner.com / employee123

### Krok 3: Frontend (Terminal 3)
```bash
cd frontend

# Zainstaluj zależności Flutter
flutter pub get

# Uruchom aplikację web
flutter run -d chrome
```

✅ Frontend działa w przeglądarce Chrome

## 🎯 Pierwsze kroki

1. **Zaloguj się jako Manager**
   - Email: manager@planner.com
   - Hasło: manager123

2. **Dodaj role i zmiany**
   - Zakładka "Konfiguracja"
   - Dodaj np. "Barista", "Kucharz"
   - Dodaj zmiany: "Poranna 06:00-14:00"

3. **Zaloguj się jako Pracownik** (nowa karta przeglądarki)
   - Email: anna@planner.com
   - Hasło: employee123

4. **Wypełnij dostępność**
   - Klikaj w komórki aby zmienić status
   - Zielony = Chcę, Żółty = Mogę, Czerwony = Nie mogę
   - Kliknij "Zapisz zmiany"

5. **Wróć jako Manager**
   - Zakładka "Grafik"
   - Kliknij "Generuj Grafik (AI)"
   - Zobacz wynik!

## 📚 Dalsze kroki

- [README.md](README.md) - Pełna dokumentacja
- [USER_GUIDE.md](USER_GUIDE.md) - Szczegółowy przewodnik użytkownika
- [API_EXAMPLES.md](API_EXAMPLES.md) - Przykłady API
- [ARCHITECTURE.md](ARCHITECTURE.md) - Architektura systemu
- [IMPLEMENTATION.md](IMPLEMENTATION.md) - Szczegóły implementacji

## ❓ Problemy?

### Backend nie startuje
- Sprawdź czy Docker Desktop jest uruchomiony
- Sprawdź czy port 8000 jest wolny
- Sprawdź czy PostgreSQL działa: `docker ps`

### Frontend nie kompiluje się
- Uruchom: `flutter doctor`
- Sprawdź czy Chrome jest zainstalowany
- Sprawdź czy wszystkie zależności są zainstalowane: `flutter pub get`

### Solver zwraca "infeasible"
- Za mało pracowników z odpowiednimi rolami
- Zbyt wysokie wymagania obsadowe
- Zbyt wiele osób niedostępnych

## 🎉 Gotowe!

Twoja aplikacja do automatycznego planowania grafików jest gotowa do użycia!
