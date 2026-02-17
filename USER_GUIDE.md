# Podręcznik Użytkownika — Planner V2

Witamy w systemie Planner V2 – narzędziu do zarządzania grafikami pracy i zespołem w gastronomii.

---

## Spis Treści

1. [Logowanie](#1-logowanie)
2. [Dla Managerów](#2-dla-managerów)
3. [Dla Pracowników](#3-dla-pracowników)
4. [Konfiguracja Serwera](#4-konfiguracja-serwera)
5. [Pomoc i Zgłaszanie Błędów](#5-pomoc-i-zgłaszanie-błędów)

---

## 1. Logowanie

Konta tworzy wyłącznie Manager — samodzielna rejestracja jest wyłączona.

1. Otwórz aplikację w przeglądarce.
2. Podaj swój **Login** (username) oraz **Hasło**.
3. Kliknij **"Zaloguj"**.

> **Uwaga**: Jeśli zapomniałeś hasła, skontaktuj się z Managerem — może je zresetować.

> **Uwaga**: Jeśli widzisz komunikat „Account is deactivated", Twoje konto zostało dezaktywowane. Skontaktuj się z Managerem.

---

## 2. Dla Managerów

Panel nawigacyjny (dolny pasek) zawiera 6 zakładek:
**Home** | **Grafik** | **Zespół** | **Ustawienia** | **Obecności** | **Zmiany**

### 2.1 Home (Dashboard)

Główny ekran — kalendarz z podglądem dziennego grafiku:
- Kliknij dzień, aby zobaczyć kto pracuje i na jakiej zmianie.
- Pasek górny: nazwa użytkownika, ikona pomocy (❔), wylogowanie.

### 2.2 Konfiguracja Systemu (zakładka Ustawienia)

#### Role (Stanowiska)
- Kliknij **+** → wpisz nazwę roli i wybierz kolor.
- Ikony ołówka (✏️) i kosza (🗑️) do edycji i usuwania.

#### Zmiany (Shift Definitions)
- Kliknij **+** → podaj nazwę (np. „Rano") i godziny (np. 08:00–16:00).
- Godziny zmian nie powinny konfliktować się dla jednej osoby.

#### Dane Lokalu
- Nazwa restauracji, adres, godziny otwarcia.

### 2.3 Zarządzanie Zespołem (zakładka Zespół)

- **Tworzenie konta**: kliknij **+** → podaj login, hasło, imię i nazwisko.
- **Kliknij na pracownika** → dialog szczegółów:
  - **Przypisz role** — zaznacz stanowiska, na których może pracować.
  - **Edytuj dane** — imię, email, cele godzinowe/zmianowe.
  - **Reset hasła** — gdy pracownik zapomni hasła.
  - **Aktywacja/Dezaktywacja** — wyłącz dostęp bez usuwania konta.

### 2.4 Grafik Pracy (zakładka Grafik)

1. **Nawigacja tygodniowa** — strzałki ← → do przełączania tygodni.
2. **Wymagania kadrowe** — ustaw ile osób o danej roli potrzebujesz na każdą zmianę.
3. **Generowanie automatyczne**:
   - Kliknij **"Generuj grafik"**.
   - System algorytmicznie dopasuje pracowników (uwzględnia dostępność, role, cele godzinowe).
   - Wynik pojawi się jako **Szkic (Draft)** — nie jest jeszcze widoczny dla pracowników.
4. **Edycja ręczna**:
   - Kliknij na komórkę → dodaj lub usuń pracownika ze zmiany.
   - Dodawaj/usuwaj pracowników w trybie szkicu.
5. **Zapisz** — kliknij **"Zapisz zmiany"** (batch save do bazy danych).
6. **Opublikuj** — kliknij **"Opublikuj"**. Dopiero wtedy pracownicy zobaczą grafik.

### 2.5 Obecności (zakładka Obecności)

- **Filtry**: zakres dat, status (Oczekujące / Zatwierdzone / Odrzucone).
- **Zatwierdzanie**: przycisk ✅ przy wpisie z nieplanowaną obecnością.
- **Odrzucanie**: przycisk ❌.
- **Ręczne dodawanie**: przycisk + do ręcznego wpisania obecności pracownika.
- **Eksport PDF**: przycisk do wygenerowania listy obecności w PDF.

### 2.6 Oddawanie Zmian (zakładka Zmiany)

Gdy pracownik chce oddać zmianę:
1. Prośba pojawia się na liście z detalami (kto, kiedy, jaka zmiana).
2. System sugeruje zastępców — posortowanych wg dostępności (zielony = dostępny).
3. Kliknij **"Przydziel"** → wybierz zastępcę.
4. Lub kliknij **"Anuluj"** → odrzuć prośbę.

---

## 3. Dla Pracowników

Panel nawigacyjny (dolny pasek) zawiera 3 zakładki:
**Grafik** | **Dostępność** | **Obecność**

### 3.1 Mój Grafik

- Kalendarz z opublikowanymi zmianami.
- Szczegóły zmiany: data, godziny, rola (stanowisko).
- **Oddawanie zmian**: kliknij na zmianę → **"Oddaj zmianę"**.
  - Prośba trafi do Managera. Dopóki Manager nie zatwierdzi, nadal jesteś przypisany!
  - Możesz anulować prośbę, dopóki nie została przydzielona.

### 3.2 Dostępność

Kluczowa funkcja — informujesz Managera, kiedy możesz pracować:

1. Przejdź do zakładki **Dostępność**.
2. Widok: tygodniowy grid (dni × zmiany).
3. Kliknij komórkę, aby przełączyć status:
   - ✅ **Preferuję** — chętnie przyjdę do pracy.
   - ⚪ **Neutralnie** — mogę pracować (domyślne).
   - ❌ **Niedostępny** — nie mogę pracować.
4. Kliknij **"Zapisz"** — system uwzględni preferencje przy generowaniu grafiku.

### 3.3 Obecność

Rejestruj swój czas pracy:

1. Wybierz datę.
2. Wpisz godzinę **wejścia** (check-in) i **wyjścia** (check-out).
   - System podpowie domyślne godziny z Twojego grafiku.
3. Kliknij **"Zapisz"**.
4. Wpis trafi do systemu. Jeśli nie byłeś zaplanowany, Manager musi zatwierdzić obecność.

---

## 4. Konfiguracja Serwera

Przy pierwszym uruchomieniu aplikacji (lub po zmianie serwera):

1. Pojawi się ekran **Konfiguracja serwera**.
2. **Skanuj QR** — manager może wygenerować kod QR z adresem serwera (ikona QR w ustawieniach).
3. **Ręcznie** — wpisz adres URL backendu (np. `http://192.168.1.100:8000`).

---

## 5. Pomoc i Zgłaszanie Błędów

W górnym pasku aplikacji znajduje się ikona pomocy (❔):

- **Pomoc**: najważniejsze informacje o obsłudze aplikacji.
- **Zgłoś błąd**: formularz (tytuł, opis, kroki do odtworzenia).
  - Zgłoszenie tworzy Issue na GitHub i trafia do zespołu technicznego.
