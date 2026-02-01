# Plan Testów

## Testy Automatyczne

### Backend (pytest)

```bash
cd PlannerV2
python -m pytest backend/tests/test_api.py -v
```

| Test | Opis | Status |
|------|------|--------|
| `test_api_reachable` | Sprawdza czy API odpowiada | ✅ |
| `test_register_employee` | Rejestracja pracownika | ✅ |
| `test_register_manager_without_pin_fails` | Manager bez PIN = 403 | ✅ |
| `test_login_success` | Logowanie z poprawnymi danymi | ✅ |
| `test_create_role` | Tworzenie roli | ✅ |
| `test_create_shift` | Tworzenie zmiany | ✅ |
| `test_create_duplicate_shift_fails` | Duplikat godzin = 400 | ✅ |
| `test_full_generation_flow` | Pełny cykl generowania grafiku | ✅ |

### Frontend (flutter test)

```bash
cd frontend
flutter test
```

| Test | Opis |
|------|------|
| Model parsing | JSON → Dart objects |

## Testy Manualne

### Scenariusz 1: Rejestracja i Logowanie
1. ✅ Otwórz aplikację
2. ✅ Zarejestruj managera (PIN: 1234)
3. ✅ Wyloguj się
4. ✅ Zaloguj ponownie

### Scenariusz 2: Konfiguracja
1. ✅ Dodaj role (Barista, Kucharz)
2. ✅ Dodaj zmiany (8:00-16:00, 16:00-24:00)
3. ✅ Sprawdź walidację duplikatów godzin
4. ✅ Edytuj istniejącą rolę
5. ✅ Usuń rolę

### Scenariusz 3: Zarządzanie Zespołem
1. ✅ Zarejestruj pracownika (bez PIN)
2. ✅ Przypisz mu rolę
3. ✅ Sprawdź czy widoczny w liście

### Scenariusz 4: Grafik
1. ✅ Kliknij "Generuj grafik"
2. ✅ Sprawdź czy przypisania są poprawne
3. ✅ Edytuj ręcznie (dodaj/usuń)
4. ✅ Sprawdź warning przy zmianie tygodnia
5. ✅ Zapisz zmiany

## CI/CD (Jenkins)

Pipeline w `Jenkinsfile` uruchamia:
1. Backend tests
2. Flutter analyze
3. Docker build
4. Deploy (opcjonalnie)
