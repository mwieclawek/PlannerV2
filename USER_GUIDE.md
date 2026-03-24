# 📖 Podręcznik Użytkownika — PlannerV2

Witamy w systemie PlannerV2 – narzędziu do zarządzania grafikami pracy, zespołem i obsługą zamówień kuchennych w gastronomii.

---

## Spis Treści

1. [Logowanie](#1-logowanie)
2. [Dla Managerów](#2-dla-managerów)
3. [Dla Pracowników](#3-dla-pracowników)
4. [POS / Kitchen Display System](#4-pos--kitchen-display-system)
5. [Konfiguracja Serwera](#5-konfiguracja-serwera)
6. [Powiadomienia](#6-powiadomienia)
7. [Pomoc i Zgłaszanie Błędów](#7-pomoc-i-zgłaszanie-błędów)

---

## 1. Logowanie

Konta tworzy wyłącznie Manager — samodzielna rejestracja jest wyłączona.

1. Otwórz aplikację w przeglądarce lub na urządzeniu mobilnym.
2. Podaj swój **Login** (username) oraz **Hasło**.
3. Kliknij **„Zaloguj"**.

> **Uwaga**: Jeśli zapomniałeś hasła, skontaktuj się z Managerem — może je zresetować.

> **Uwaga**: Komunikat „Account is deactivated" oznacza dezaktywację konta — skontaktuj się z Managerem.

---

## 2. Dla Managerów

Panel nawigacyjny (dolny pasek) zawiera 8 zakładek:
**Home** | **Grafik** | **Zespół** | **Ustawienia** | **Obecności** | **Zmiany** | **Urlopy** | **Dostępność**

### 2.1 Home (Dashboard)

Główny ekran — kalendarz z podglądem dziennego grafiku:
- Kliknij dzień, aby zobaczyć kto pracuje i na jakiej zmianie.
- Statystyki: liczba pracowników, wypełnienie zmian.
- Pasek górny: nazwa użytkownika, ikona powiadomień (🔔), wylogowanie.

### 2.2 Konfiguracja Systemu (zakładka Ustawienia)

#### Role (Stanowiska)
- Kliknij **+** → wpisz nazwę roli i wybierz kolor.
- Ikony ołówka (✏️) i kosza (🗑️) do edycji i usuwania.

#### Zmiany (Shift Definitions)
- Kliknij **+** → podaj nazwę (np. „Rano") i godziny (np. 08:00–16:00).
- **Dni obowiązywania**: wybierz, w które dni tygodnia zmiana jest aktywna (np. tylko pon–pt).
- Godziny zmian nie powinny się nakładać dla jednej osoby.

#### Wymagania Kadrowe
- Ustaw zapotrzebowanie: ile osób o danej roli potrzebujesz na każdą zmianę.
- **Wymóg globalny**: ustawiany per dzień tygodnia (np. „poniedziałek: 2 baristów na rano").
- **Wymóg specyficzny**: ustawiany na konkretną datę (nadpisuje globalny).

#### Dane Lokalu
- Nazwa restauracji, adres.
- Godziny otwarcia per dzień tygodnia.

### 2.3 Zarządzanie Zespołem (zakładka Zespół)

- **Tworzenie konta**: kliknij **+** → podaj login, hasło, imię i nazwisko.
- **Kliknij na pracownika** → dialog szczegółów:
  - **Przypisz role** — zaznacz stanowiska, na których może pracować.
  - **Edytuj dane** — imię, nazwisko, email, cele godzinowe/zmianowe.
  - **Reset hasła** — gdy pracownik zapomni hasła.
  - **Aktywacja/Dezaktywacja** — wyłącz dostęp bez usuwania konta.
- **Statystyki pracownika**: godziny w miesiącu, liczba zmian, status dostępności.

### 2.4 Grafik Pracy (zakładka Grafik)

1. **Nawigacja tygodniowa** — strzałki ← → do przełączania tygodni.
2. **Wymagania kadrowe** — widoczne nad siatką grafiku, ostrzeżenia o brakach.
3. **Generowanie automatyczne**:
   - Kliknij **„Generuj grafik"**.
   - System algorytmicznie dopasuje pracowników (uwzględnia dostępność, role, cele godzinowe).
   - **Priorytet systemu**: zawsze wypełnić zmianę, nawet jeśli pracownik przekracza limit godzin. Limity traktowane są jako „miękkie" wytyczne.
   - Wynik pojawi się jako **Szkic (Draft)** — nie jest jeszcze widoczny dla pracowników.
   - **Ostrzeżenia**: system pokaże braki kadrowe (np. „Brakuje: Barista (1)").
4. **Edycja ręczna**:
   - Kliknij **„+ Dodaj"** → wybierz pracownika i rolę.
   - System pokaże listę dostępnych pracowników (posortowaną wg dostępności).
5. **Zapisz** — kliknij **„Zapisz zmiany"** (batch save do bazy danych).
6. **Opublikuj** — kliknij **„Opublikuj"**. Pracownicy zobaczą grafik i otrzymają powiadomienie push.

### 2.5 Obecności (zakładka Obecności)

- **Filtry**: zakres dat, status (Oczekujące / Zatwierdzone / Odrzucone).
- **Zatwierdzanie**: przycisk ✅ przy wpisie z nieplanowaną obecnością.
- **Odrzucanie**: przycisk ❌.
- **Ręczne dodawanie**: przycisk **+** do ręcznego wpisania obecności pracownika.
- **Eksport PDF**: przycisk do wygenerowania listy obecności w PDF (z podsumowaniem godzin).

### 2.6 Giełda Zmian (zakładka Zmiany)

Gdy pracownik chce oddać zmianę:
1. Prośba pojawia się na liście z detalami (kto, kiedy, jaka zmiana).
2. System sugeruje zastępców — posortowanych wg dostępności (zielony = dostępny).
3. Kliknij **„Przydziel"** → wybierz zastępcę.
4. Lub kliknij **„Anuluj"** → odrzuć prośbę.

> **Nowość**: Pracownicy mogą samodzielnie przejmować zmiany z giełdy (z automatyczną weryfikacją konfliktów).

### 2.7 Urlopy (zakładka Urlopy)

- Przeglądanie wniosków urlopowych pracowników.
- **Zatwierdzanie** (`Approve`) / **Odrzucanie** (`Reject`) wniosków.
- **Kalendarz urlopów**: widok miesięczny z oznaczonymi dniami urlopu.
- Pracownik otrzymuje powiadomienie push o decyzji.

### 2.8 Podgląd Dostępności (zakładka Dostępność)

- Widok dostępności wszystkich pracowników w wybranym tygodniu.
- Grid: pracownicy × zmiany × dni, z kolorowym oznaczeniem statusu.

---

## 3. Dla Pracowników

Panel nawigacyjny (dolny pasek) zawiera 5 zakładek:
**Grafik** | **Dostępność** | **Obecność** | **Giełda** | **Urlopy**

### 3.1 Mój Grafik

- Kalendarz z opublikowanymi zmianami.
- Szczegóły zmiany: data, godziny, rola (stanowisko), współpracownicy na tej samej zmianie.
- **Podsumowanie**: godziny w bieżącym tygodniu i miesiącu.
- **Oddawanie zmian**: kliknij na zmianę → **„Oddaj zmianę"**.
  - Prośba trafi do Managera i na giełdę. Dopóki nikt nie przejmie, nadal jesteś przypisany!
  - Możesz anulować prośbę, dopóki nie została przejęta.

### 3.2 Dostępność

Kluczowa funkcja — informujesz Managera, kiedy możesz pracować:

1. Przejdź do zakładki **Dostępność**.
2. Widok: tygodniowy grid (dni × zmiany).
3. Kliknij komórkę, aby przełączyć status:
   - 🟢 **Dostępny** — mogę pracować.
   - 🔴 **Niedostępny** — nie mogę pracować.
4. Kliknij **„Zapisz"** — system uwzględni preferencje przy generowaniu grafiku.

### 3.3 Obecność

Rejestruj swój czas pracy:

1. Wybierz datę.
2. Wpisz godzinę **wejścia** (check-in) i **wyjścia** (check-out).
   - System podpowie domyślne godziny z Twojego grafiku.
3. Kliknij **„Zapisz"**.
4. Jeśli nie byłeś zaplanowany, Manager musi zatwierdzić obecność.

### 3.4 Giełda Zmian

- **Oferowanie**: oddaj swoją zmianę na giełdę (z zakładki Grafik).
- **Przejmowanie**: przeglądaj dostępne zmiany innych pracowników.
  - System sprawdza konflikty (nakładające się zmiany > 30 min = blokada).
  - Widoczna informacja o Twojej dostępności na daną zmianę.
  - Kliknij **„Przejmij"** — zmiana zostanie przeniesiona na Ciebie.
- **Moje oferty**: śledzenie statusu oddawanych zmian (OPEN / TAKEN / CANCELLED).

### 3.5 Urlopy

Składanie wniosków urlopowych:

1. Kliknij **„Nowy wniosek"**.
2. Podaj datę początkową, końcową i powód.
3. Wniosek trafi do Managera.
4. Śledzenie statusu: PENDING → APPROVED / REJECTED.
5. Możliwość anulowania wniosku w statusie PENDING.
6. Otrzymasz powiadomienie push o decyzji Managera.

---

## 4. POS / Kitchen Display System

Moduł do obsługi zamówień restauracyjnych.

### 4.1 Konfiguracja (Manager)

Przed rozpoczęciem pracy:
1. **Stoliki**: dodaj stoliki w restauracji (nazwa, np. „Stolik 1", „Bar").
2. **Menu**: dodaj pozycje menu z kategoriami (Zupy, Dania Główne, Desery, Napoje) i cenami.

### 4.2 Ekran Kelnera (Waiter)

1. Wybierz stolik, przy którym obsługujesz gości.
2. Dodaj pozycje z menu do zamówienia (ilość, opcjonalne notatki).
3. Zatwierdź zamówienie → trafia do kuchni.
4. Śledź status zamówienia:
   - 🟡 **PENDING** — oczekuje na kuchnię
   - 🔵 **IN_PROGRESS** — w trakcie przygotowania
   - 🟢 **READY** — gotowe do podania
   - ✅ **DELIVERED** — podane gościowi

### 4.3 Kitchen Display System (KDS)

Ekran do kuchni wyświetlający zamówienia:
- Lista zamówień z pozycjami, notatkami i numerem stolika.
- Zmiana statusu jednym kliknięciem (PENDING → IN_PROGRESS → READY).
- Auto-odświeżanie co kilka sekund.

---

## 5. Konfiguracja Serwera

Przy pierwszym uruchomieniu aplikacji (lub po zmianie serwera):

1. Pojawi się ekran **Konfiguracja serwera**.
2. **Skanuj QR** — Manager może wygenerować kod QR z adresem serwera (ikona QR w ustawieniach).
3. **Ręcznie** — wpisz adres URL backendu (np. `http://192.168.1.100:8000`).

---

## 6. Powiadomienia

System wysyła powiadomienia dwoma kanałami:

### In-App (w aplikacji)
- Ikona dzwonka (🔔) w górnym pasku.
- Lista powiadomień z możliwością oznaczenia jako przeczytane.

### Push (na urządzenie mobilne)
- Działa przez **Firebase Cloud Messaging**.
- Wymagana zgoda na powiadomienia przy pierwszym uruchomieniu.
- Powiadomienia o: publikacji grafiku, zmianach na giełdzie, decyzjach urlopowych.

---

## 7. Pomoc i Zgłaszanie Błędów

W górnym pasku aplikacji znajduje się ikona pomocy (❔):

- **Pomoc**: najważniejsze informacje o obsłudze aplikacji.
- **Zgłoś błąd**: formularz (tytuł, opis, kroki do odtworzenia).
  - Zgłoszenie tworzy Issue na GitHub i trafia do zespołu technicznego.
- **Polityka prywatności**: dostępna z ekranu logowania.
