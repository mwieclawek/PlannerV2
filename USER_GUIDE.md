# Podręcznik Użytkownika - Planner V2

Witamy w systemie Planner V2 – kompleksowym narzędziu do zarządzania grafikami, czasem pracy i zespołem w gastronomii. Niniejszy przewodnik pomoże Ci w pełni wykorzystać możliwości aplikacji, niezależnie od Twojej roli.

---

## Spis Treści

1.  [Wstęp](#wstęp)
2.  [Logowanie](#logowanie)
3.  [Dla Managerów](#dla-managerów)
    *   [Dashboard](#dashboard-managera)
    *   [Konfiguracja Systemu](#konfiguracja-systemu)
    *   [Zarządzanie Zespołem](#zarządzanie-zespołem)
    *   [Grafik Pracy](#grafik-pracy)
    *   [Oddawanie Zmian](#oddawanie-zmian-manager)
    *   [Zarządzanie Obecnością](#zarządzanie-obecnością)
    *   [Raporty](#raporty)
4.  [Dla Pracowników](#dla-pracowników)
    *   [Mój Grafik](#mój-grafik)
    *   [Oddawanie Zmian](#oddawanie-zmian-pracownik)
    *   [Dostępność](#dostępność)
    *   [Rejestracja Obecności](#rejestracja-obecności)
5.  [Pomoc i Zgłaszanie Błędów](#pomoc-i-zgłaszanie-błędów)

---

## 1. Wstęp

Planner V2 to aplikacja webowa ułatwiająca planowanie zmian, zarządzanie dostępnością pracowników oraz monitorowanie czasu pracy. System dzieli użytkowników na dwie główne role:
*   **Manager**: Pełna kontrola nad konfiguracją, grafikami, zespołem i raportami.
*   **Pracownik**: Dostęp do własnego grafiku, zgłaszanie dyspozycyjności i rejestracja wejść/wyjść.

Standardowy adres aplikacji (wersja lokalna): `http://127.0.0.1:5000` (może się różnić w zależności od wdrożenia).

---

## 2. Logowanie

Aby korzystać z systemu, musisz posiadać konto utworzone przez Managera. Rejestracja samodzielna jest wyłączona.

### Logowanie
1.  Otwórz aplikację w przeglądarce.
2.  Na ekranie startowym podaj swój **Login** oraz **Hasło**.
3.  Kliknij przycisk **"Zaloguj"**.

> **Uwaga**: Jeśli zapomniałeś hasła, skontaktuj się ze swoim Managerem.

---

## 3. Dla Managerów

Jako Manager masz dostęp do wszystkich funkcji administracyjnych. Panel nawigacyjny znajduje się u dołu ekranu (mobile) lub po lewej stronie (desktop).

### Dashboard Managera
Główny ekran po zalogowaniu. Znajdziesz tu szybki podgląd kluczowych informacji:
*   **Dzisiejszy Grafik**: Kto pracuje teraz, kto ma zaplanowaną zmianę.
*   **Oczekujące Wnioski**: Powiadomienia o niezatwierdzonych obecnościach.
*   **Statystyki**: Podsumowanie godzin w bieżącym miesiącu.

### Konfiguracja Systemu
W tej sekcji dostosujesz aplikację do potrzeb Twojego lokalu.

#### Role (Stanowiska)
Definiuj stanowiska pracy w Twoim zespole (np. Kelner, Barista, Kucharz).
*   **Dodawanie**: Kliknij "+", wpisz nazwę roli i wybierz kolor (ułatwia rozróżnianie na grafiku).
*   **Edycja/Usuwanie**: Użyj ikon ołówka lub kosza przy danej roli.

#### Zmiany (Shift Definitions)
Określ standardowe godziny pracy.
*   **Dodawanie**: Kliknij "+", podaj nazwę (np. "Rano", "Wieczór") oraz godziny rozpoczęcia i zakończenia (np. 08:00 - 16:00).
*   **Ważne**: Godziny zmian nie powinny na siebie nachodzić w sposób konfliktowy dla jednej osoby.

#### Ustawienia Lokalu
Zdefiniuj dane restauracji (nazwa, adres) oraz godziny otwarcia.

### Zarządzanie Zespołem
Zakładka **Zespół** pozwala na administrowanie pracownikami.
*   **Tworzenie Konta**: Kliknij przycisk dodawania (+), aby utworzyć konto dla nowego pracownika.
*   **Szczegóły Pracownika**: Kliknij na pracownika, aby:
    *   Przypisać mu role (stanowiska), na których może pracować.
    *   Zresetować hasło (jeśli pracownik je zapomni).
    *   **Aktywować/Dezaktywować**: Zablokuj dostęp pracownikom, którzy już nie pracują.
    *   Edytować dane osobowe i cele godzinowe.

### Grafik Pracy
Sercem systemu jest moduł planowania.
1.  **Widok**: Kalendarz z podziałem na dni lub Tygodniowy.
2.  **Wymagania Kadrowe**: Określ, ile osób na danym stanowisku jest potrzebnych w konkretny dzień (np. "Sobota Rano: 2x Barista").
3.  **Generowanie Automatyczne**:
    *   Kliknij przycisk **"Generuj grafik"**.
    *   System algorytmicznie dopasuje pracowników do wymagań, biorąc pod uwagę ich dostępność i role.
    *   Wynik pojawi się jako **Szkic (Draft)** – pracownicy go jeszcze nie widzą.
4.  **Edycja Ręczna**:
    *   Możesz ręcznie przesuwać, dodawać lub usuwać osoby ze zmian w trybie szkicu.
    *   Kliknij na komórkę zmiany, aby dodać/usunąć pracownika.
5.  **Publikacja**:
    *   Gdy grafik jest gotowy, kliknij **"Opublikuj"**.
    *   Dopiero wtedy pracownicy zobaczą swoje zmiany w aplikacji.

### Oddawanie Zmian (Manager)
W zakładce **Zmiany** (ikona strzałek) widzisz prośby pracowników o oddanie zmiany.
*   Rozwiń kartę, aby zobaczyć szczegóły.
*   System podpowie sugerowane zastępstwa, sortując pracowników według dostępności (Zielony = dostępny).
*   Kliknij **Przydziel**, aby zaakceptować zmianę osoby, lub **Anuluj oddanie**, aby odrzucić prośbę.

### Zarządzanie Obecnością
System pozwala na weryfikację rzeczywistego czasu pracy.
*   **Zatwierdzanie**: Jeśli pracownik odbił się w systemie w godzinach innych niż zaplanowane, lub przyszedł w dzień wolny, wpis trafi do sekcji "Do zatwierdzenia". Możesz go zaakceptować lub odrzucić.
*   **Historia**: Pełna lista wejść i wyjść z możliwością filtrowania po datach.

### Raporty
*   **Eksport PDF**: Możesz wygenerować listę obecności lub grafik do pliku PDF, gotowego do druku.
*   **Podsumowanie Godzin**: Tabela z sumą godzin przepracowanych przez każdego pracownika w wybranym miesiącu (ułatwia rozliczenia wypłat).

---

## 4. Dla Pracowników

Twój panel jest uproszczony i skupia się na Twojej pracy.

### Mój Grafik
Po zalogowaniu widzisz swój kalendarz pracy.
*   **Widok Tygodniowy**: Sprawdź, kiedy i w jakich godzinach pracujesz.
*   **Szczegóły Zmiany**: Data, godzina i rola (stanowisko), na którym masz pracować.

### Oddawanie Zmian (Pracownik)
Jeśli nie możesz przyjść na zaplanowaną zmianę:
1.  Kliknij na zmianę w swoim grafiku.
2.  Wybierz opcję **"Oddaj zmianę"**.
3.  Twoja prośba trafi do Managera, który znajdzie zastępstwo. Dopóki Manager nie zatwierdzi zmiany, nadal jesteś przypisany do grafiku!

### Dostępność
To kluczowa funkcja, dzięki której Manager wie, kiedy możesz pracować.
1.  Przejdź do zakładki **Dostępność**.
2.  Dla każdego dnia i zmiany w przyszłym tygodniu wybierz status:
    *   ✅ **Preferuję**: Chętnie przyjdę do pracy.
    *   ⚪ **Neutralnie**: Mogę pracować, jeśli trzeba (domyślne).
    *   ❌ **Niedostępny**: Nie mogę pracować w tym czasie.
3.  Pamiętaj, aby zapisywać zmiany! System bierze pod uwagę Twoje preferencje przy automatycznym układaniu grafiku.

### Rejestracja Obecności
Używaj tej funkcji, gdy przychodzisz i wychodzisz z pracy.
1.  Na ekranie głównym (Dashboard) znajdziesz sekcję "Rejestracja Czasu" (lub zakładkę Obecność).
2.  **Start Pracy**: Kliknij przycisk wejścia (Check-In). Czas zostanie zarejestrowany.
3.  **Koniec Pracy**: Po zakończeniu zmiany kliknij przycisk wyjścia (Check-Out).
4.  Twoje godziny trafią do systemu i po zatwierdzeniu przez Managera zostaną wliczone do wypłaty.

---

## 5. Pomoc i Zgłaszanie Błędów

W górnym pasku aplikacji znajdziesz ikonę znaku zapytania (❔).

*   **Pomoc**: Otwiera panel z najważniejszymi informacjami o obsłudze aplikacji.
*   **Zgłoś błąd**: Jeśli zauważysz błąd w działaniu programu, kliknij przycisk "Zgłoś błąd" w oknie pomocy.
    *   Wypełnij formularz (Tytuł, Opis, Kroki do odtworzenia).
    *   Zgłoszenie trafi bezpośrednio do zespołu technicznego.

---
