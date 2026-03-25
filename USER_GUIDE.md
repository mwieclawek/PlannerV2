# 📖 Podręcznik Użytkownika — PlannerV2

> Kompleksowa instrukcja obsługi systemu do zarządzania grafikami pracy, zespołem i zamówieniami kuchennymi.

---

## 📑 Spis Treści

1. [Pierwsze Kroki](#1-pierwsze-kroki)  
2. [Panel Managera](#2-panel-managera)  
3. [Panel Pracownika](#3-panel-pracownika)  
4. [Moduł POS / Kitchen Display System](#4-moduł-pos--kitchen-display-system)  
5. [System Powiadomień](#5-system-powiadomień)  
6. [Konfiguracja Serwera i Pierwsze Logowanie](#6-konfiguracja-serwera-i-pierwsze-logowanie)
7. [Najczęstsze Pytania (FAQ)](#7-najczęstsze-pytania-faq)  
8. [Pomoc i Zgłaszanie Błędów](#8-pomoc-i-zgłaszanie-błędów)

---

## 1. Pierwsze Kroki

### 1.1 Kto może korzystać z systemu?

System rozróżnia dwie role:

| Rola | Uprawnienia |
|------|-------------|
| **Manager** | Pełna kontrola: konfiguracja, zespół, grafiki, obecności, POS, urlopy |
| **Pracownik** | Podgląd grafiku, zgłaszanie dostępności, obecność, giełda zmian, urlopy |

> **⚠️ Ważne**: Samodzielna rejestracja jest **wyłączona**. Konta tworzy wyłącznie Manager. Pierwszy Manager musi zostać utworzony przez API z użyciem kodu PIN.

### 1.2 Logowanie

1. Otwórz aplikację w przeglądarce lub na urządzeniu mobilnym.
2. Podaj swój **Login** (username) i **Hasło**.
3. Kliknij **„Zaloguj"**.

> **💡 Tip**: Jeśli aplikacja prosi o adres serwera, skontaktuj się z Managerem — może udostępnić konfigurację przez **kod QR** (ikona QR w panelu Managera).

#### Komunikaty logowania

| Komunikat | Znaczenie | Co robić |
|-----------|-----------|----------|
| *„Invalid credentials"* | Błędny login lub hasło | Sprawdź dane lub poproś Managera o reset hasła |
| *„Account is deactivated"* | Twoje konto jest wyłączone | Skontaktuj się z Managerem |
| *„Connection error"* | Brak połączenia z serwerem | Sprawdź adres serwera w ustawieniach |

### 1.3 Zmiana Hasła

Każdy użytkownik (Manager i Pracownik) może samodzielnie zmienić hasło:

1. Kliknij ikonę profilu (👤) → **„Zmień hasło"**.
2. Podaj stare hasło, nowe hasło (min. 6 znaków) i powtórz je.
3. Kliknij **„Zmień"**.

> **💡 Tip**: Jeśli zapomniałeś starego hasła, Manager może zresetować je w zakładce **Zespół**.

---

## 2. Panel Managera

Po zalogowaniu jako Manager widzisz dolny pasek nawigacji z 5 zakładkami:

| Ikona | Zakładka | Opis |
|-------|----------|------|
| 🏠 | **Home** | Dashboard — podgląd dziennego grafiku i statystyki |
| ⚙️ | **Konfiguracja** | Ustawienia restauracji, ról, zmian i wymagań |
| 📅 | **Grafik** | Tygodniowy grafik — generowanie, edycja, publikacja |
| ✅ | **Obecności** | Ewidencja czasu pracy, zatwierdzanie, eksport PDF |
| 👥 | **Zespół** | Zarządzanie pracownikami, statystyki, giełda zmian, urlopy |

Górny pasek zawiera:
- **❔ Pomoc** — dialog z instrukcjami
- **📱 QR** — generowanie kodu QR z adresem serwera (do udostępnienia pracownikom)
- **🔔 Powiadomienia** — lista powiadomień in-app
- **🍽️ Moduł POS** — przejście do systemu zamówień restauracyjnych
- **🚪 Wyloguj**

---

### 2.1 Home (Dashboard)

Główny ekran z widokiem kalendarza:

- **Kalendarz miesięczny** — kliknij dowolny dzień, aby zobaczyć szczegóły.
- **Lista zmian** — kto pracuje, na jakiej zmianie, w jakiej roli.
- **Statystyki dzienne** — liczba przypisanych pracowników.

> **💡 Tip**: Dashboard jest odświeżany automatycznie. Jeśli chcesz zobaczyć nowe dane, po prostu kliknij inny dzień i wróć.

---

### 2.2 Konfiguracja (⚙️)

Zakładka Konfiguracja składa się z **3 pod-zakładek**:

#### 📌 Pod-zakładka 1: Restauracja

Podstawowe dane Twojego lokalu:

| Pole | Opis | Wymagane |
|------|------|----------|
| Nazwa restauracji | np. „Kawiarnia Pod Lipą" | ✅ |
| Adres | np. „ul. Główna 15, Warszawa" | ❌ |
| Godziny otwarcia | Format HH:MM (np. 08:00) | ❌ |
| Godziny zamknięcia | Format HH:MM (np. 22:00) | ❌ |

Kliknij **„Zapisz ustawienia"** po wprowadzeniu zmian.

#### 📌 Pod-zakładka 2: Role i Zmiany

Tutaj definiujesz **stanowiska** (role) i **definicje zmian** — to fundamentalne elementy systemu. Bez nich generowanie grafiku nie jest możliwe.

##### Role (Stanowiska)

Role określają, **na jakim stanowisku** pracuje dana osoba (np. Barista, Kasjer, Kelner, Kucharz).

- Wpisz nazwę roli → kliknij **„Dodaj"**.
- Kolor jest przydzielany automatycznie.
- Rola pojawi się na liście poniżej.

> **⚠️ Ważne**: Po dodaniu roli, musisz **przypisać ją pracownikom** w zakładce Zespół. Algorytm przypisze do zmiany tylko osoby, które mają wymaganą rolę.

> **💡 Tip**: Nazwij role tak, jak wyglądają stanowiska w Twojej restauracji. Im dokładniej, tym lepiej algorytm dopasuje grafik.

##### Zmiany (Shift Definitions)

Zmiany określają **przedziały czasowe** pracy (np. „Rano" 08:00–16:00).

| Pole | Opis | Wymagane |
|------|------|----------|
| Nazwa zmiany | np. „Rano", „Popołudnie", „Wieczór" | ✅ |
| Start (HH:MM) | Godzina rozpoczęcia | ✅ |
| Koniec (HH:MM) | Godzina zakończenia | ✅ |
| Dni obowiązywania | Zaznacz dni tygodnia (Pn–Nd), domyślnie: wszystkie | ✅ |

- Kliknij **„Dodaj Zmianę"** → pojawi się na liście.
- Aby edytować: kliknij ikonę ✏️ → zmień dane → **„Zapisz"**.
- Aby usunąć: kliknij ikonę 🗑️.

> **⚠️ Ważne o nakładaniu się zmian**: System automatycznie pilnuje, by jeden pracownik nie był przypisany do dwóch zmian, które nakładają się o więcej niż 30 minut. Nakładanie ≤ 30 min jest dozwolone (np. przekazanie zmiany).

> **💡 Tip**: Jeśli np. zmiana „Międzyzmiana" obowiązuje tylko w sobotę i niedzielę, odznacz dni Pn–Pt. Dzięki temu algorytm nie będzie próbował przypisywać ludzi do tej zmiany w tygodniu.

#### 📌 Pod-zakładka 3: Wymagania Kadrowe

Wymagania kadrowe definiują, **ilu pracowników o danej roli potrzebujesz na każdą zmianę**.

System obsługuje dwa tryby:

| Tryb | Opis | Kiedy używać |
|------|------|-------------|
| **Tygodniowy (globalny)** | Jeden szablon na cały tydzień — identyczne zapotrzebowanie na każdą zmianę per dzień tygodnia | Gdy zapotrzebowanie jest stałe |
| **Konkretne daty** | Zapotrzebowanie na konkretne daty (nadpisuje szablon tygodniowy) | Na święta, imprezy, zmiany sezonowe |

**Jak ustawić wymagania:**
1. Przejdź do pod-zakładki **Wymagania**.
2. Wybierz tryb: **Tygodniowy** (przełącznik) lub **Per datę** (nawigacja tygodniowa ← →).
3. Siatka pokazuje: **Zmiana × Rola × Dzień**.
4. Kliknij komórkę i ustaw liczbę (np. „2" oznacza: potrzebuję 2 osoby o tej roli na tę zmianę).
5. Kliknij **„Zapisz wymagania"**.

> **⚠️ Ważne**: Wymagania kadrowe są **kluczowe** dla algorytmu! Jeśli ich nie ustawisz, algorytm nie będzie wiedział ile osób przypisać i może nie wygenerować żadnych przypisań.

> **💡 Tip**: Wymagania tygodniowe to „domyślny szablon". Jeśli w piątek potrzebujesz więcej ludzi niż zwykle, ustaw dla piątkowej daty wyższe wymaganie — nadpisze ono szablon.

> **💡 Tip**: Wartość wymagania działa jak „Cap" (limit górny). Jeśli ustawisz „2", algorytm przypisze **maksymalnie 2 osoby** na tę zmianę w tej roli. Jeśli dostępna jest tylko 1 osoba, przypisze 1 i wygeneruje ostrzeżenie.

---

### 2.3 Grafik (📅)

Serce systemu — tu widzisz tygodniowy grafik, generujesz go automatycznie lub edytujesz ręcznie.

#### Nawigacja

- Strzałki **← →** przełączają tygodnie.
- Tytuł pokazuje zakres dat: np. „30 mar – 5 kwi 2026".

#### Generowanie Automatyczne (AI Solver)

1. Kliknij **„Generuj grafik"**.
2. System uruchamia algorytm OR-Tools CP-SAT, który uwzględnia:
   - ✅ Dostępność pracowników (kto jest dostępny na daną zmianę)
   - ✅ Role (kto ma uprawnienia do danego stanowiska)
   - ✅ Wymagania kadrowe (ile osób na zmianę)
   - ✅ Cele godzinowe/zmianowe per pracownik
   - ✅ Aktualne godziny w miesiącu (MTD — month-to-date)
   - ✅ Nakładanie się zmian (blokuje konflikty > 30 min)
   - ✅ Dni obowiązywania zmian

3. Wynik pojawia się jako **Szkic (Draft)** — nie jest zapisany ani widoczny dla pracowników.

> **⚠️ Ważne o „miękkiej" logice algorytmu**: System **zawsze priorytetyzuje wypełnienie zmiany** nad limitami godzinowymi. Jeśli jedynym dostępnym pracownikiem jest osoba, która przekroczy swoje `target_hours_per_month`, algorytm **i tak ją przypisze**, ale spróbuje zminimalizować nadgodziny jeśli są alternatywy. Celem jest: **nigdy nie zostawiać pustej zmiany, jeśli jest ktokolwiek dostępny**.

> **💡 Tip**: Jeśli algorytm zwraca „infeasible" (brak rozwiązania), sprawdź:
> - Czy pracownicy złożyli dostępność na ten tydzień?
> - Czy pracownicy mają przypisane role odpowiadające wymaganiom?
> - Czy są jakiekolwiek wymagania kadrowe ustawione?

#### Ostrzeżenia kadrowe

Po wygenerowaniu grafiku, system pokaże ostrzeżenia, np.:
- 🔺 **„Brakuje: Barista (1)"** — nie udało się obsadzić 1 baristy na tę zmianę.

Ostrzeżenia pojawiają się, gdy:
- Brak dostępnych pracowników z wymaganą rolą.
- Wszystkie dostępne osoby już pracują na nakładającej się zmianie.

#### Edycja Ręczna

Po wygenerowaniu (lub na pustym grafiku):
1. Kliknij **„+ Dodaj"** w komórce (zmiana × dzień).
2. Wyświetli się lista pracowników z ich statusami dostępności:
   - 🟢 — dostępny/preferowany na tę zmianę
   - 🔴 — niedostępny
3. Wybierz pracownika i rolę.
4. Aby usunąć: kliknij na pracownika w komórce → potwierdź usunięcie.

> **💡 Tip**: Możesz mieszać tryby — wygenerować automatycznie, a potem ręcznie poprawić konkretne komórki.

#### Zapisywanie i Publikacja

| Akcja | Przycisk | Efekt |
|-------|----------|-------|
| **Zapisz** | „Zapisz zmiany" | Grafik jest zapisany w bazie, ale pracownicy go **nie widzą** |
| **Opublikuj** | „Opublikuj" | Grafik staje się **widoczny dla pracowników** + powiadomienie push |

> **⚠️ Ważne**: Jeśli opuścisz zakładkę Grafik z niezapisanymi zmianami, system pokaże ostrzeżenie: *„Masz niezapisane zmiany w grafiku. Czy chcesz je odrzucić?"*.

> **💡 Tip**: Cykl pracy z grafikiem:
> 1. Ustaw wymagania kadrowe (jednorazowo, potem się powtarzają)
> 2. Poczekaj aż pracownicy złożą dostępność
> 3. Generuj → Edytuj → Zapisz → Opublikuj

---

### 2.4 Obecności (✅)

Zarządzanie ewidencją czasu pracy.

#### Widok listy

- **Filtry**: zakres dat + status (Oczekujące / Zatwierdzone / Odrzucone / Wszystkie).
- Każdy wpis pokazuje: pracownika, datę, godziny wejścia/wyjścia, status.

#### Zatwierdzanie / Odrzucanie

Gdy pracownik zarejestruje obecność **poza grafikiem** (nieplanowana), wpis ma status **PENDING** i wymaga decyzji Managera:

| Przycisk | Efekt |
|----------|-------|
| ✅ **Zatwierdź** | Status → CONFIRMED, godziny wliczane do ewidencji |
| ❌ **Odrzuć** | Status → REJECTED, godziny nie są liczone |

> **💡 Tip**: Obecności z grafiku (planowane) są automatycznie CONFIRMED — nie wymagają zatwierdzenia.

#### Ręczne dodawanie

Kliknij **„+"** → wybierz pracownika, datę, godziny wejścia/wyjścia. Przydatne, gdy pracownik zapomniał zarejestrować obecność.

#### Eksport PDF

Kliknij ikonę PDF → zostanie pobrany plik z:
- Listą wszystkich obecności w zakresie dat (z filtrami).
- **Podsumowaniem godzin**: suma godzin per pracownik (tylko CONFIRMED).

> **💡 Tip**: Eksport PDF przydaje się do rozliczeń miesięcznych. Ustaw filtr na cały miesiąc i status „CONFIRMED".

---

### 2.5 Zespół (👥)

Zakładka Zespół składa się z kilku pod-zakładek dostępnych przez karty na górze ekranu.

#### Lista Pracowników

- Widoczni wszyscy aktywni pracownicy z przypisanymi rolami i podsumowaniem godzin.
- Przełącznik **„Pokaż nieaktywnych"** odkrywa dezaktywowane konta.

#### Tworzenie konta

Kliknij **„+"** → wypełnij:

| Pole | Opis | Wymagane |
|------|------|----------|
| Login (username) | Unikalna nazwa użytkownika | ✅ |
| Hasło | Min. 6 znaków | ✅ |
| Imię i Nazwisko | Wyświetlane w grafiku | ✅ |
| Email | Do kontaktu (opcjonalnie) | ❌ |

#### Dialog szczegółów pracownika

Kliknij na pracownika → dialog z opcjami:

| Akcja | Opis |
|-------|------|
| **Przypisz role** | Zaznacz stanowiska (np. Barista ✅, Kasjer ✅). Algorytm przypisze tylko do ról, które ma |
| **Edytuj dane** | Imię, nazwisko, email |
| **Cele godzinowe** | `target_hours_per_month` — preferowana liczba godzin/miesiąc |
| **Cele zmianowe** | `target_shifts_per_month` — preferowana liczba zmian/miesiąc |
| **Reset hasła** | Ustaw nowe hasło (np. gdy pracownik je zapomniał) |
| **Aktywacja / Dezaktywacja** | Wyłączenie wyłącza logowanie, ale nie kasuje danych |

> **⚠️ Ważne o celach**: Cele godzinowe/zmianowe to **miękkie wytyczne** dla algorytmu. Algorytm będzie **starał się** ich nie przekraczać, ale jeśli nie ma innej opcji, i tak przypisze pracownika — by zmiana nie została pusta.

> **💡 Tip**: Jeśli pracownik nie ma ustawionych celów (`target_hours_per_month` = puste), algorytm traktuje to jako „brak limitu" — może przypisać dowolną liczbę zmian.

#### Statystyki pracownika

Dostępne w dialogu szczegółów — pokazują:
- Godziny w bieżącym miesiącu
- Liczbę zmian w bieżącym miesiącu
- Status dostępności (czy złożył dostępność)

#### Giełda Zmian (zarządzanie)

Podgląd wszystkich otwartych ofert:
- Kto oddaje, jaką zmianę, kiedy.
- **Sugerowane zastępstwa** — system proponuje pracowników posortowanych wg dostępności.
- Kliknij **„Przydziel"** → wybierz zastępcę → zmiana zostanie przeniesiona.
- Kliknij **„Anuluj"** → zamknij ofertę bez przypisania.

> **💡 Tip**: Sugestie zastępstw są sortowane tak, by dostępni pracownicy z odpowiednią rolą byli na górze listy.

#### Urlopy

Widok wniosków urlopowych:
- Filtr po statusie: Oczekujące / Zatwierdzone / Odrzucone.
- **Zatwierdź** / **Odrzuć** — pracownik otrzyma powiadomienie push o decyzji.
- **Kalendarz urlopów** — miesięczny widok z oznaczonymi dniami urlopu.

#### Dostępność zespołu

Widok dostępności **wszystkich pracowników** na wybrany tydzień:
- Grid: pracownicy × zmiany × dni.
- Kolory: 🟢 Dostępny / 🔴 Niedostępny.

> **💡 Tip**: Sprawdź ten widok **przed generowaniem grafiku**, aby upewnić się, że pracownicy złożyli dostępność.

---

## 3. Panel Pracownika

Po zalogowaniu jako Pracownik widzisz dolny pasek z 4 zakładkami:

| Ikona | Zakładka | Opis |
|-------|----------|------|
| 📅 | **Mój Grafik** | Opublikowane zmiany, oddawanie zmian |
| 📝 | **Dostępność** | Zgłaszanie dostępności + wnioski urlopowe |
| ⏰ | **Obecność** | Rejestracja czasu pracy |
| 🔄 | **Giełda** | Przejmowanie zmian od innych pracowników |

Górny pasek zawiera:
- 🔔 **Powiadomienia**
- ❔ **Pomoc**
- 👤 **Menu profilu** (zmiana hasła, Google Calendar, moduł POS, wyloguj)

---

### 3.1 Mój Grafik (📅)

Widok kalendarza z opublikowanymi zmianami:

- **Tygodniowy widok** — strzałki ← → do nawigacji.
- Każda zmiana pokazuje: godziny, rolę, współpracowników na tej samej zmianie.
- **Podsumowanie godzin** — wyświetlane nad grafikiem:
  - Godziny w bieżącym tygodniu
  - Godziny w bieżącym miesiącu

#### Oddawanie zmian

1. Kliknij na swoją zmianę.
2. Kliknij **„Oddaj zmianę"**.
3. Zmiana trafi na **Giełdę** — widoczna dla Managera i kwalifikujących się pracowników.
4. Do momentu przejęcia lub anulowania, **nadal jesteś przypisany do tej zmiany**.

> **⚠️ Ważne**: Nie można oddać zmiany z przeszłości.

> **💡 Tip**: Po oddaniu zmiany możesz śledzić jej status w zakładce Giełda → „Moje oferty" (OPEN → TAKEN / CANCELLED).

#### Integracja z Google Calendar

Dostępna z menu profilu (👤) → **„Kalendarz Google"**:
- **Połącz** → logowanie przez Google → zmiany z grafiku synchronizują się automatycznie z Twoim kalendarzem.
- **Odłącz** → przerywa synchronizację.

> **💡 Tip**: Dzięki temu zobaczysz swoje zmiany bezpośrednio w Google Calendar, razem z innymi wydarzeniami.

---

### 3.2 Dostępność (📝)

**⭐ Kluczowa funkcja** — dzięki niej Manager wie, kiedy możesz pracować.

Zakładka Dostępność ma 2 pod-zakładki: **Dyspozycja** i **Wnioski urlopowe**.

#### Dyspozycja

Tygodniowy grid (dni × zmiany):

1. Nawigacja tygodniowa: strzałki ← →.
2. Kliknij komórkę, aby przełączyć status:

| Stan | Kolor | Znaczenie |
|------|-------|-----------|
| 🟢 **Dostępny** | Zielony | Mogę pracować na tej zmianie |
| 🔴 **Niedostępny** | Czerwony | Nie mogę pracować |

3. Kliknij **„Zapisz"** — preferencje zostaną wysłane.

> **⚠️ Ważne**: Jeśli **nie złożysz** dostępności na dany tydzień, algorytm **nie przypisze Cię do żadnej zmiany** w tym tygodniu! Algorytm interpretuje brak dyspozycji jako „pozycja nieznana" i bezpiecznie pomija.

> **💡 Tip**: Złóż dostępność jak najwcześniej — Manager generuje grafik na podstawie Twoich preferencji. Im wcześniej, tym lepiej!

> **💡 Tip**: Jeśli widzisz komunikat *„Brak zdefiniowanych zmian — skontaktuj się z menadżerem"*, oznacza to, że Manager jeszcze nie skonfigurował definicji zmian.

#### Wnioski Urlopowe

1. Kliknij **„Nowy wniosek"**.
2. Wypełnij:
   - **Data od** — pierwszy dzień urlopu
   - **Data do** — ostatni dzień urlopu (nie może być w przeszłości)
   - **Powód** — krótki opis (max. 500 znaków)
3. Wniosek trafi do Managera. Statusy:

| Status | Znaczenie |
|--------|-----------|
| **PENDING** | Oczekuje na decyzję Managera |
| **APPROVED** | Zatwierdzony |
| **REJECTED** | Odrzucony |
| **CANCELLED** | Anulowany przez Ciebie |

> **⚠️ Ważne**: Wniosek urlopowy **nie blokuje automatycznie** Twojej dostępności w grafiku. Zadbaj o oznaczenie się jako „Niedostępny" na okresy urlopowe w zakładce Dyspozycja.

> **💡 Tip**: Możesz anulować wniosek tylko w statusie PENDING. Po zatwierdzeniu lub odrzuceniu — nie.

---

### 3.3 Obecność (⏰)

Rejestracja czasu pracy:

1. Wybierz **datę** (domyślnie dzisiejsza).
2. Godzina wejścia (check-in) i wyjścia (check-out):
   - Jeśli byłeś **zaplanowany** na tę datę, system podpowie domyślne godziny z grafiku.
   - Możesz je zmienić, jeśli faktyczne godziny były inne.
3. Kliknij **„Zapisz"**.

#### Co się dzieje po zapisaniu?

| Sytuacja | Status wpisu | Wymagana akcja Managera? |
|----------|-------------|-------------------------|
| Byłeś zaplanowany na tę datę | **CONFIRMED** ✅ | ❌ (automatyczne) |
| **Nie** byłeś zaplanowany | **PENDING** ⏳ | ✅ (Manager musi zatwierdzić) |

> **⚠️ Ważne**: Możesz zarejestrować obecność tylko **raz na dzień**. Jeśli spróbujesz ponownie, zobaczysz komunikat *„Attendance already registered for this date"*.

> **💡 Tip**: Historia obecności jest widoczna pod formularzem rejestracji ze statusem każdego wpisu.

---

### 3.4 Giełda Zmian (🔄)

Giełda pozwala na **przejmowanie zmian** od innych pracowników.

#### Widok giełdy

Lista otwartych ofert z detalami:
- Kto oddaje zmianę
- Data, godziny, rola
- **Status konfliktu** — automatyczna weryfikacja:

| Oznaczenie | Znaczenie |
|------------|-----------|
| ✅ Brak konfliktu | Możesz bezpiecznie przejąć |
| ⚠️ Ten sam dzień | Masz już zmianę tego dnia, ale nie nakłada się > 30 min |
| 🚫 Nakładanie | Masz zmianę, która nakłada się o > 30 min — **nie możesz przejąć** |

- **Hint dostępności** — czy oznaczyłeś się jako dostępny na tę zmianę.

#### Przejmowanie zmiany

1. Znajdź ofertę na liście.
2. Kliknij **„Przejmij"**.
3. System sprawdzi konflikty:
   - Jeśli nakładanie > 30 min → **blokada** (*„You already have a shift that overlaps..."*).
   - Jeśli brak konfliktu → zmiana zostanie przeniesiona na Ciebie.
4. Oryginalny pracownik i managerowie otrzymają powiadomienie.

> **💡 Tip**: Badge na ikonie Giełda (🔴 liczba) informuje, ile zmian jest dostępnych do przejęcia.

> **⚠️ Ważne**: Nie możesz przejąć własnej oferty.

#### Moje oferty

Pod listą giełdy widzisz swoje oddawane zmiany i ich statusy (OPEN / TAKEN / CANCELLED).

---

## 4. Moduł POS / Kitchen Display System

System obsługi zamówień restauracyjnych. Dostęp z głównego panelu przez ikonę 🍽️ (Manager) lub menu profilu (Pracownik).

### 4.1 Wymagania wstępne

Przed rozpoczęciem pracy z POS, Manager musi:
1. **Dodać stoliki** — lista stolików restauracji.
2. **Skonfigurować menu** — pozycje z cenami i kategoriami.

#### Konfiguracja POS (tylko Manager)

**Stoliki:**
- Kliknij **„Dodaj stolik"** → podaj nazwę (np. „Stolik 1", „Stolik VIP", „Bar").
- Usunięcie stolika to **soft-delete** — znika z listy, ale zamówienia historyczne pozostają.

**Menu:**
- Kliknij **„Dodaj pozycję"** → podaj:

| Pole | Opis | Wymagane |
|------|------|----------|
| Nazwa | np. „Cappuccino", „Burger Classic" | ✅ |
| Cena | Format liczbowy (np. 14.50) | ✅ |
| Kategoria | SOUPS / MAINS / DESSERTS / DRINKS | ✅ |

- Menu można filtrować po kategoriach.
- Usunięcie pozycji to soft-delete — istniejące zamówienia zachowują snapshot nazwy i ceny.

### 4.2 Ekran Kelnera (Waiter)

Widok stolików i tworzenie zamówień:

1. **Wybierz stolik** z listy aktywnych stolików.
2. **Dodaj pozycje** z menu:
   - Wybierz kategorię → kliknij pozycję → ustaw ilość.
   - Opcjonalnie dodaj **notatki** (np. „bez cebuli", „extra sos").
3. **Zatwierdź zamówienie** → trafia do kuchni.

Po utworzeniu zamówienia, kelner widzi jego status:
- 🟡 PENDING → 🔵 IN_PROGRESS → 🟢 READY → ✅ DELIVERED

> **💡 Tip**: Cena i nazwa pozycji są „zamrożone" (snapshot) w momencie złożenia zamówienia. Nawet jeśli Manager zmieni cenę w menu, istniejące zamówienia zachowają starą cenę.

### 4.3 Kitchen Display System (KDS)

Ekran dla kuchni:

- **Lista zamówień** z wszystkimi pozycjami, ilościami i notatkami.
- **Numer stolika** widoczny na każdym zamówieniu.
- **Zmiana statusu** jednym kliknięciem:
  - PENDING → **„Zaczynam"** (IN_PROGRESS)
  - IN_PROGRESS → **„Gotowe"** (READY)
- **Auto-odświeżanie** co kilka sekund (polling).

#### Anulowanie zamówienia

- Zamówienie w statusie PENDING lub IN_PROGRESS może być anulowane.
- Zamówienie DELIVERED lub CANCELLED nie może być anulowane.

> **💡 Tip**: KDS najlepiej wyświetlić na tablecie lub monitorze w kuchni w trybie pełnoekranowym.

---

## 5. System Powiadomień

### 5.1 Powiadomienia In-App

- Ikona dzwonka (🔔) w górnym pasku — z badge'em pokazującym liczbę nieprzeczytanych.
- Kliknij → lista powiadomień z możliwością oznaczenia jako przeczytane.

### 5.2 Powiadomienia Push (FCM)

Na urządzeniach mobilnych (Android/iOS) system wysyła powiadomienia push:

| Zdarzenie | Kto otrzymuje |
|-----------|---------------|
| Opublikowanie grafiku | Przypisani pracownicy |
| Nowa zmiana wystawiona na giełdę | Managerowie + pracownicy z odpowiednią rolą |
| Zmiana przejęta z giełdy | Oddający pracownik + managerowie |
| Nowy wniosek urlopowy | Managerowie |
| Decyzja o urlopie (zatwierdzony/odrzucony) | Wnioskujący pracownik |

> **💡 Tip**: Upewnij się, że masz włączone powiadomienia na swoim urządzeniu, aby nie przegapić ważnych informacji!

---

## 6. Konfiguracja Serwera i Pierwsze Logowanie

### 6.1 Pierwszy raz — konfiguracja adresu

1. Aplikacja wyświetli ekran **Konfiguracja Serwera**.
2. Dwie opcje:
   - **Skanuj QR** — Manager generuje QR z ikoną 📱 w panelu.
   - **Ręcznie** — wpisz URL backendu (np. `http://192.168.1.100:8000`).

### 6.2 Tworzenie pierwszego Managera

Pierwszy Manager musi zostać utworzony przez API:

```
POST /auth/register
{
  "username": "admin",
  "password": "your_password",
  "full_name": "Jan Kowalski",
  "manager_pin": "1234"
}
```

> **⚠️ Ważne**: Kod PIN (`manager_pin`) musi odpowiadać zmiennej `MANAGER_REGISTRATION_PIN` serwera (domyślnie: `1234`).

---

## 7. Najczęstsze Pytania (FAQ)

### Grafik

**Q: Dlaczego algorytm nie przypisuje pracowników, mimo że są dostępni?**

Sprawdź kolejno:
1. ✅ Czy pracownicy złożyli **dostępność** na wybrany tydzień?
2. ✅ Czy mają przypisane **role** odpowiadające wymaganiom kadrowym?
3. ✅ Czy ustawiłeś **wymagania kadrowe** (ile osób potrzebujesz na zmianę)?
4. ✅ Czy zmiany mają ustawione **dni obowiązywania** obejmujące docelowy dzień?

**Q: Pracownik przekroczy limit godzin — czy algorytm go i tak przypisze?**

Tak. Limity godzinowe i zmianowe są traktowane jako „miękkie wytyczne". Algorytm priorytetyzuje wypełnienie zmiany. Ale jeśli ma wybór między dwiema osobami, wybierze tę, która jest dalej od limitu.

**Q: Co się stanie, jeśli wygeneruję grafik ponownie?**

Poprzedni szkic zostanie nadpisany. Jeśli grafik jest już **zapisany** w bazie, generowanie tworzy nowy szkic — dopiero po kliknięciu „Zapisz" nadpisze stary.

### Obecności

**Q: Pracownik nie był w grafiku, ale przyszedł do pracy. Co robić?**

Pracownik rejestruje obecność normalnie. Wpis pojawi się ze statusem PENDING — Manager musi go zatwierdzić w zakładce Obecności.

### Giełda

**Q: Pracownik oddał zmianę, ale nikt jej nie przejął. Co teraz?**

Pracownik nadal jest przypisany do zmiany. Manager może ręcznie przypisać zastępcę w panelu Giełda Zmian, lub pracownik może anulować ofertę.

**Q: Czy pracownik może przejąć zmianę, nawet jeśli oznaczył się jako niedostępny?**

Tak — system nie blokuje przejęcia na podstawie dostępności, tylko na podstawie **konfliktu zmian** (nakładanie > 30 min). Hint dostępności jest informacyjny.

---

## 8. Pomoc i Zgłaszanie Błędów

### Pomoc

W górnym pasku: ikona **❔** → dialog z najważniejszymi informacjami o obsłudze.

### Zgłoszenie błędu

1. Kliknij **❔** → **„Zgłoś błąd"**.
2. Wypełnij formularz:
   - **Tytuł** — krótki opis problemu
   - **Opis** — szczegóły, kroki do odtworzenia
3. Zgłoszenie automatycznie tworzy **Issue na GitHub** i trafia do zespołu technicznego.

### Polityka Prywatności

Dostępna z ekranu logowania — link na dole strony.
