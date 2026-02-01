# Planner V2 - User Guide

## 🎬 Scenariusz użycia

### Krok 1: Przygotowanie systemu (Manager)

**Jan Kowalski** jest managerem kawiarni "Coffee House". Właśnie zainstalował Planner V2.

1. **Rejestracja**
   - Otwiera aplikację
   - Klika "Nie masz konta? Zarejestruj się"
   - Wypełnia: jan.kowalski@coffeehouse.pl, hasło, "Jan Kowalski"
   - System tworzy konto typu EMPLOYEE (domyślnie)
   - Jan musi ręcznie zmienić w bazie danych na MANAGER lub użyć seed.py

2. **Konfiguracja ról**
   - Loguje się ponownie
   - Przechodzi do zakładki "Konfiguracja"
   - Dodaje role:
     - Barista (zielony)
     - Kelner (niebieski)
     - Kucharz (pomarańczowy)

3. **Konfiguracja zmian**
   - W tej samej zakładce dodaje zmiany:
     - Poranna: 06:00 - 14:00
     - Popołudniowa: 14:00 - 22:00

4. **Dodanie pracowników**
   - Pracownicy sami się rejestrują lub Jan tworzy im konta
   - Anna, Piotr, Maria rejestrują się przez aplikację

5. **Przypisanie kompetencji**
   - Jan używa API lub bazy danych aby przypisać:
     - Anna → Barista
     - Piotr → Barista, Kelner
     - Maria → Kucharz

### Krok 2: Pracownicy składają dyspozycyjność

**Anna Nowak** (Barista) otwiera aplikację w poniedziałek:

1. **Logowanie**
   - Email: anna@coffeehouse.pl
   - Hasło: (jej hasło)

2. **Widok kalendarza**
   - Widzi tydzień: 3-9 lutego 2026
   - Dla każdego dnia widzi 2 zmiany (Poranna, Popołudniowa)
   - Wszystkie są domyślnie szare (Brak preferencji)

3. **Ustawienie dostępności**
   - **Poniedziałek Poranna**: Klika → zmienia na zielony (Chcę)
   - **Poniedziałek Popołudniowa**: Klika → czerwony (Nie mogę)
   - **Wtorek Poranna**: Klika → zielony (Chcę)
   - **Środa**: Klika obie zmiany → żółty (Mogę)
   - **Czwartek**: Zostawia szare (Brak)
   - **Piątek Poranna**: Klika → zielony (Chcę)
   - **Sobota**: Klika obie → czerwony (Nie mogę - ma plany)
   - **Niedziela Popołudniowa**: Klika → żółty (Mogę)

4. **Zapisanie**
   - Klika duży niebieski przycisk "Zapisz zmiany"
   - Widzi zielony komunikat: "✓ Dostępność zapisana"

**Piotr i Maria** robią to samo dla swoich preferencji.

### Krok 3: Manager ustawia wymagania

**Jan** wraca do aplikacji:

1. **Określenie potrzeb**
   - Wie, że w weekend potrzebuje więcej osób
   - Używa API (lub przyszłego UI) aby ustawić:
     - Poniedziałek-Piątek Poranna: 1 Barista, 1 Kucharz
     - Poniedziałek-Piątek Popołudniowa: 2 Baristów, 1 Kucharz
     - Sobota-Niedziela: 2 Baristów na każdej zmianie, 1 Kucharz

### Krok 4: Generacja grafiku

**Jan** przechodzi do zakładki "Grafik":

1. **Wybór tygodnia**
   - Widzi: "3 lut - 9 lut 2026"
   - To jest tydzień, na który pracownicy złożyli dyspozycyjność

2. **Kliknięcie "Generuj Grafik (AI)"**
   - Przycisk pokazuje animację ładowania
   - Backend uruchamia Google OR-Tools
   - Solver analizuje:
     - ✅ Anna chce pracować w poniedziałek rano → przypisz
     - ✅ Piotr może w środę → przypisz jeśli potrzeba
     - ❌ Maria nie może w sobotę → nie przypisuj
     - ✅ Spełnij minimum 2 baristów w sobotę popołudniu
   
3. **Wynik**
   - Po 2-3 sekundach widzi:
     - "✓ Wygenerowano grafik (14 przypisań)"
   - System znalazł optymalne rozwiązanie

4. **Publikacja** (przyszła funkcja)
   - Jan klika "Opublikuj"
   - Pracownicy mogą teraz zobaczyć grafik w swojej aplikacji

### Krok 5: Pracownicy sprawdzają grafik

**Anna** otwiera aplikację:

1. **Widok grafiku** (przyszła funkcja)
   - Widzi swoje przypisane zmiany:
     - Poniedziałek 06:00-14:00 (Barista)
     - Wtorek 06:00-14:00 (Barista)
     - Piątek 06:00-14:00 (Barista)
   - Razem: 24 godziny w tym tygodniu

2. **Eksport** (przyszła funkcja)
   - Może pobrać PDF z grafikiem
   - Dodać do kalendarza Google

## 🔄 Cykl tygodniowy

1. **Niedziela/Poniedziałek**: Pracownicy składają dyspozycyjność na następny tydzień
2. **Wtorek**: Manager generuje grafik
3. **Środa**: Manager publikuje grafik
4. **Czwartek-Niedziela**: Pracownicy pracują według grafiku

## 💡 Wskazówki

### Dla Pracowników
- ✅ Wypełniaj dyspozycyjność wcześnie (nie czekaj do ostatniej chwili)
- ✅ Używaj "Chcę" dla preferowanych zmian - system to uwzględni
- ✅ Używaj "Nie mogę" tylko gdy naprawdę nie możesz (nie nadużywaj)
- ✅ "Mogę" = jesteś dostępny, ale nie jest to Twoja preferencja

### Dla Managerów
- ✅ Ustaw realistyczne wymagania (nie więcej niż masz pracowników)
- ✅ Przypisz pracownikom odpowiednie role (kompetencje)
- ✅ Jeśli solver zwraca "infeasible":
  - Zmniejsz wymagania
  - Poproś pracowników o większą elastyczność
  - Zatrudnij więcej osób
- ✅ Możesz ręcznie edytować grafik po wygenerowaniu (przyszła funkcja)

## ❓ FAQ

**Q: Co jeśli zapomniałem wypełnić dostępność?**
A: System traktuje to jako "Brak preferencji" - możesz zostać przypisany, ale z niższym priorytetem.

**Q: Czy mogę zmienić dostępność po wygenerowaniu grafiku?**
A: Tak, ale manager będzie musiał wygenerować grafik ponownie.

**Q: Ile zmian mogę mieć dziennie?**
A: Maksymalnie 1 zmianę dziennie (ograniczenie systemu).

**Q: Co jeśli nikt nie chce pracować w sobotę?**
A: Solver może zwrócić "infeasible" - manager musi wtedy negocjować z pracownikami lub zmniejszyć wymagania.

**Q: Czy system uwzględnia równomierny podział godzin?**
A: Tak, funkcja celu minimalizuje różnice w liczbie godzin między pracownikami (można to dostosować).

## 🎯 Przykładowy wynik

Po wygenerowaniu grafiku dla tygodnia 3-9 lutego:

| Dzień | Zmiana | Anna (Barista) | Piotr (Barista/Kelner) | Maria (Kucharz) |
|-------|--------|----------------|------------------------|-----------------|
| Pon | Poranna | ✅ | - | ✅ |
| Pon | Popołudniowa | - | ✅ | ✅ |
| Wt | Poranna | ✅ | - | ✅ |
| Wt | Popołudniowa | - | ✅ | - |
| Śr | Poranna | - | ✅ | ✅ |
| Śr | Popołudniowa | ✅ | - | ✅ |
| Czw | Poranna | ✅ | - | ✅ |
| Czw | Popołudniowa | - | ✅ | - |
| Pt | Poranna | ✅ | - | ✅ |
| Pt | Popołudniowa | - | ✅ | ✅ |
| Sob | Poranna | - | ✅ | ✅ |
| Sob | Popołudniowa | - | ✅ | - |
| Nd | Poranna | ✅ | - | ✅ |
| Nd | Popołudniowa | - | ✅ | ✅ |

**Podsumowanie:**
- Anna: 6 zmian × 8h = 48h
- Piotr: 8 zmian × 8h = 64h
- Maria: 10 zmian × 8h = 80h

System automatycznie zoptymalizował grafik uwzględniając preferencje i wymagania!
