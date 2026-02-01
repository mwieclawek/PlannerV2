---
description: Wytyczne dla agentów przy zmianach w kodzie projektu PlannerV2
---

# Wytyczne dla agentów

## 🚫 BEZWZGLĘDNE ZASADY

### 1. TESTOWANIE - ZASADY
- **NIGDY** nie używaj przeglądarki (Chrome/browser) do testowania, chyba że użytkownik o to poprosi
- **NIGDY** nie uruchamiaj serwera deweloperskiego do ręcznego testowania
- **ZAWSZE** napisz testy automatyczne do każdej wprowadzonej zmiany
- **ZAWSZE** uruchom testy automatyczne po zmianach (tylko dla zmienianego obszaru)

### 2. JEDEN PROMPT = JEDEN OBSZAR
- W jednym promptu pracujesz **ALBO** nad **backendem** **ALBO** nad **frontendem**
- **NIGDY** nie łącz zmian w obu obszarach w jednym promptu
- Jeśli zadanie wymaga zmian w obu, poinformuj użytkownika i poczekaj na kolejny prompt

### 3. DOKUMENTACJA JEST PRIORYTETEM
- **PRZED** rozpoczęciem pracy przeczytaj dokumentację:
  - `README.md` - główna dokumentacja projektu (dla użytkowników GitHub)
  - `QUICKSTART.md` - przewodnik szybkiego startu
  - `backend/README.md` - dokumentacja backendu
  - `frontend/README.md` - dokumentacja frontendu
  - `docs/` - dodatkowa dokumentacja projektu
- **PO** każdej zmianie zaktualizuj:
  - Dokumentację techniczną (backend/frontend README)
  - Dokumentację użytkownika (główne README.md, QUICKSTART.md) jeśli zmiana wpływa na użytkowanie

## 🧪 Zasady pisania testów

### Dobre praktyki testowania
1. **Testy regresji** - pisz testy tak, aby wykrywały regresje w przyszłych sprintach
2. **Testy jednostkowe** - testuj pojedyncze funkcje/metody w izolacji
3. **Testy integracyjne** - testuj interakcje między komponentami
4. **Przypadki brzegowe** - uwzględniaj edge cases, puste dane, błędne inputy
5. **Czytelne nazwy** - nazwy testów powinny opisywać co testują
6. **AAA Pattern** - Arrange (przygotuj), Act (wykonaj), Assert (sprawdź)

### NIE pisz testów które:
- ❌ Są napisane "byle przeszły" bez sensu biznesowego
- ❌ Testują tylko happy path bez edge cases
- ❌ Są zbyt powiązane z implementacją (łamią się przy refaktoringu)
- ❌ Mają niejasne asercje lub magiczne wartości

### Backend (Python/pytest)
```bash
# Uruchom testy backendu
cd backend
pytest tests/ -v
```

Struktura testów:
```
backend/
└── tests/
    ├── test_auth.py       # Testy autentykacji
    ├── test_api.py        # Testy endpointów API
    └── test_services.py   # Testy serwisów
```

### Frontend (Flutter)
```bash
# Uruchom testy frontendu
cd frontend
flutter test
```

Struktura testów:
```
frontend/
└── test/
    ├── widget_test.dart   # Testy widgetów
    ├── unit_test.dart     # Testy jednostkowe
    └── integration_test/  # Testy integracyjne
```

## 📋 Procedura pracy

1. **Przeczytaj dokumentację** odpowiednią dla obszaru (backend/frontend)
2. **Zrozum strukturę** projektu na podstawie dokumentacji
3. **Wykonaj zmiany** w kodzie
4. **Napisz testy automatyczne** do wprowadzonych zmian:
   - Testy jednostkowe dla nowych funkcji
   - Testy integracyjne dla nowych endpointów/widgetów
   - Testy regresji dla zmienionych funkcjonalności
5. **Uruchom testy automatyczne** (tylko dla zmienianego obszaru):
   - Backend: `pytest tests/ -v`
   - Frontend: `flutter test`
6. **Zaktualizuj dokumentację techniczną** - dodaj informacje o:
   - Nowych endpointach/komponentach
   - Zmienionych funkcjonalnościach
   - Nowych zależnościach
7. **Zaktualizuj dokumentację użytkownika** (jeśli dotyczy):
   - `README.md` - opis projektu, instalacja, konfiguracja
   - `QUICKSTART.md` - szybki start dla nowych użytkowników
   - Inne pliki `.md` w głównym katalogu

## 📁 Struktura projektu

```
PlannerV2/
├── README.md              # 📌 Główna dokumentacja dla GitHub (ZAWSZE aktualizuj!)
├── QUICKSTART.md          # 📌 Przewodnik szybkiego startu
├── backend/
│   ├── README.md          # Dokumentacja API i struktury backendu
│   ├── app/               # Kod aplikacji
│   └── tests/             # 🧪 Testy automatyczne backendu
├── frontend/
│   ├── README.md          # Dokumentacja komponentów i struktury frontendu
│   ├── lib/               # Kod aplikacji
│   └── test/              # 🧪 Testy automatyczne frontendu
└── docs/
    ├── api.md             # Szczegółowa dokumentacja API
    └── architecture.md    # Architektura systemu
```

## ⚠️ Przypomnienie

Każdy agent **MUSI**:
1. W pierwszej kolejności przeczytać dokumentację
2. Napisać testy do każdej zmiany (regresja, edge cases)
3. Uruchomić testy automatyczne przed zakończeniem
4. NIE używać przeglądarki do testowania (chyba że poproszony)
