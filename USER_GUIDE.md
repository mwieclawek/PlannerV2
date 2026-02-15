# Podręcznik Użytkownika - Planner V2

Witamy w systemie Planner V2 – kompleksowym narzędziu do zarządzania grafikami, czasem pracy i zespołem w gastronomii. Niniejszy przewodnik pomoże Ci w pełni wykorzystać możliwości aplikacji, niezależnie od Twojej roli.

---

## Spis Treści

1.  [Wstęp](#wstęp)
2.  [Logowanie i Rejestracja](#logowanie-i-rejestracja)
3.  [Dla Managerów](#dla-managerów)
    *   [Dashboard](#dashboard-managera)
    *   [Konfiguracja Systemu](#konfiguracja-systemu)
    *   [Zarządzanie Zespołem](#zarządzanie-zespołem)
    *   [Grafik Pracy](#grafik-pracy)
    *   [Zarządzanie Obecnością](#zarządzanie-obecnością)
    *   [Raporty](#raporty)
4.  [Dla Pracowników](#dla-pracowników)
    *   [Mój Grafik](#mój-grafik)
    *   [Dostępność](#dostępność)
    *   [Rejestracja Obecności](#rejestracja-obecności)
5.  [FAQ i Rozwiązywanie Problemów](#faq-i-rozwiązywanie-problemów)

---

## 1. Wstęp

Planner V2 to aplikacja webowa ułatwiająca planowanie zmian, zarządzanie dostępnością pracowników oraz monitorowanie czasu pracy. System dzieli użytkowników na dwie główne role:
*   **Manager**: Pełna kontrola nad konfiguracją, grafikami, zespołem i raportami.
*   **Pracownik**: Dostęp do własnego grafiku, zgłaszanie dyspozycyjności i rejestracja wejść/wyjść.

Standardowy adres aplikacji (wersja lokalna): `http://127.0.0.1:5000` (może się różnić w zależności od wdrożenia).

---

## 2. Logowanie i Rejestracja

Aby korzystać z systemu, musisz posiadać konto.

### Logowanie
1.  Otwórz aplikację w przeglądarce.
2.  Na ekranie startowym podaj swój **Login (email)** oraz **Hasło**.
3.  Kliknij przycisk **"Zaloguj"**.

### Rejestracja Nowego Użytkownika
Jeśli nie masz jeszcze konta:
1.  Na ekranie logowania kliknij link **"Zarejestruj się"**.
2.  Wybierz swoją rolę: **Pracownik** lub **Manager**.
3.  Wypełnij formularz:
    *   **Nazwa użytkownika**: unikalny login w systemie.
    *   **Imię i nazwisko**: Twoje dane, widoczne w grafikach.
    *   **Email**: Adres do komunikacji.
    *   **Hasło**: Hasło do logowania.
4.  **Ważne dla Managerów**: Rejestracja konta Managera wymaga podania specjalnego kodu PIN: **`1234`**.
5.  Po pomyślnej rejestracji zostaniesz automatycznie przekierowany do panelu logowania.

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
*   **Lista Pracowników**: Widzisz wszystkich zarejestrowanych użytkowników.
*   **Szczegóły Pracownika**: Kliknij na pracownika, aby:
    *   Przypisać mu role (stanowiska), na których może pracować.
    *   Zresetować hasło (jeśli pracownik je zapomni).
    *   Edytować dane osobowe.
    *   Zobaczyć podsumowanie przepracowanych godzin i historię zmian.

### Grafik Pracy
Sercem systemu jest moduł planowania.
1.  **Widok**: Kalendarz tygodniowy z podziałem na dni i zmiany.
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
1.  Na ekranie głównym (Dashboard) znajdziesz sekcję "Rejestracja Czasu".
2.  **Start Pracy**: Kliknij przycisk wejścia (Check-In). Czas zostanie zarejestrowany.
3.  **Koniec Pracy**: Po zakończeniu zmiany kliknij przycisk wyjścia (Check-Out).
4.  Twoje godziny trafią do systemu i po zatwierdzeniu przez Managera zostaną wliczone do wypłaty.

---

## 5. FAQ i Rozwiązywanie Problemów

**P: Zapomniałem hasła. Co robić?**
O: Skontaktuj się ze swoim Managerem. Może on zresetować Twoje hasło w panelu "Zespół".

**P: Grafik jest pusty po wygenerowaniu.**
O: (Dla Managera) Sprawdź, czy:
1.  Zdefiniowane są **Wymagania Kadrowe** na ten tydzień.
2.  Pracownicy mają przypisane odpowiednie **Role**.
3.  Pracownicy zgłosili swoją **Dostępność** (nie są wszyscy "Niedostępni").

**P: Nie mogę zarejestrować konta Managera.**
O: Upewnij się, że podajesz poprawny kod PIN (domyślnie: `1234`). Jeśli został zmieniony, zapytaj administratora systemu.

**P: Dlaczego nie widzę zmian w grafiku?**
O: Jeśli jesteś pracownikiem - Manager mógł jeszcze nie **opublikować** grafiku (jest w trybie szkicu).
Jeśli jesteś Managerem - upewnij się, że wybrałeś poprawny tydzień w kalendarzu.

**P: Czy mogę zmienić swoją dostępność po wygenerowaniu grafiku?**
O: Tak, ale zmiana dostępności po publikacji grafiku nie usunie Cię automatycznie z zaplanowanej zmiany. Musisz poinformować Managera bezpośrednio.
