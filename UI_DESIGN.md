# Specyfikacja UI

## Paleta Kolorów

| Nazwa | Hex | Użycie |
|-------|-----|--------|
| Primary | `#006A6A` (Deep Teal) | Przyciski, akcenty, nawigacja |
| Primary Container | `#9CF4F4` (Light Mint) | Tła kontenerów wyróżnionych |
| Secondary | `#4A6363` (Muted Grey-Green) | Elementy drugorzędne |
| Success | `#2E7D32` | Potwierdzenia, status aktywny, dostępność preferowana |
| Warning | `#ED6C02` | Ostrzeżenia, status neutralny, powiadomienia zablokowane |
| Error | `#BA1A1A` | Błędy, niedostępność, odrzucone wnioski |
| Background | `#FAFDFC` (Ice White) | Tło aplikacji |
| Surface | `#F2FBFB` | Karty, dialogi, panele |
| On Surface | `#191C1C` | Tekst główny |

## Typografia

- **Nagłówki**: Google Fonts — Outfit / Inter
- **Treść**: Google Fonts — Inter
- **Rozmiary**: 12 / 14 / 16 / 20 / 24 / 32px

## Komponenty

### Przyciski
- `FilledButton` — główne akcje (Zapisz, Generuj, Opublikuj, Włącz powiadomienia)
- `OutlinedButton` — akcje drugorzędne (Anuluj, Filtruj, Wymień)
- `IconButton` — akcje inline (Edytuj, Usuń, Dodaj, Odśwież)
- `FloatingActionButton` — szybkie dodawanie (+)

### Formularze
- `TextField` z `OutlineInputBorder` (zaokrąglenie 10px, tło `surfaceContainerLow`)
- Walidacja inline z `errorText`
- Walidacja siły haseł: minimum 8 znaków, 1 wielka litera, 1 cyfra (`ApiErrorHandler.validatePassword`)
- `DropdownButtonFormField` dla select
- `TimePicker` dla godzin zmian

### Karty
- `Card` z zaokrągleniem 8–12px
- Obramowanie `BorderSide(color: outline.withValues(alpha: 0.2))`
- Padding wewnętrzny: 12–16px

### Dialogi
- `AlertDialog` — potwierdzenia, ostrzeżenia, usuwanie
- `SimpleDialog` — wybory (np. wybór pracownika)
- Customowe dialogi: `EmployeeDetailDialog`, `NotificationDialog`, `BugReportDialog`, `HelpDialog`, `QrConfigDialog`

### Banery i Powiadomienia
- `MaterialBanner` (`ScaffoldMessenger`) — wyrazisty baner u góry ekranu dla powiadomień pierwszoplanowych (Foreground Push), z przyciskiem zamknięcia i automatycznym wygaszaniem po 6 sekundach.
- `SnackBar` — komunikaty statusu, błędy sieciowe (floating, 4–5 sekund).
- Baner uprawnień Web Push — wbudowany w okno dialogowe `NotificationBell`, prezentujący stan uprawnień (aktywne, oczekujące na akceptację, zablokowane) z przyciskiem aktywacji.

### Chipy / Badge
- `Chip` z kolorem roli — identyfikacja pracowników na grafiku
- Status badge — kolorowe oznaczenie statusu (OPEN / TAKEN / CANCELLED)
- Unread badge — czerwony licznik nieprzeczytanych powiadomień nad ikoną dzwonka

---

## Ekrany

### Login (`/login`)
- Logo aplikacji (widget `AppLogo`)
- Obsługa architektury Multi-Tenancy (wielodostępność):
  - Logowanie za pomocą unikalnego adresu e-mail i hasła LUB
  - Logowanie za pomocą nazwy użytkownika (username), kodu lokalu (slug) i hasła
- Pola formularza: Kod restauracji (Login ID), Login lub Email, Hasło
- Wskazówki autouzupełniania (`AutofillGroup`) dla menedżerów haseł
- Przycisk: Zaloguj

### Server Setup (`/setup`)
- Skanowanie kodu QR z adresem serwera
- Ręczne wpisanie URL backendu
- Zapisywane w `ConfigService` (SharedPreferences)

---

### Superadmin Dashboard (`/#/superadmin`)
- Dostępne dla użytkowników o globalnej roli `SUPERADMIN`.
- Układ z dwiema głównymi zakładkami w AppBarze (`TabBar`):
  1. **Restauracje**:
     - Lista wszystkich restauracji (Tenantów) prezentowana w formie kart:
       - Przełącznik aktywności lokalu
       - Przycisk edycji nazwy i identyfikatora slug
       - Przycisk Użytkownicy — dialog listy kont powiązanych z lokalem wraz z funkcją resetu hasła managera
       - Przycisk Dodaj managera
       - Przycisk **Logi** — bezpośrednie przejście do zakładki logów z automatycznie ustawionym filtrem na dany lokal
     - Floating Action Button (+) do rejestracji nowej restauracji
  2. **Logi systemowe**:
     - Pasek wyboru restauracji (`DropdownButtonFormField`) z opcją „Wszystkie lokale”
     - Przełączniki poziomu logowania (`ChoiceChip`: Wszystkie, INFO, WARNING, ERROR, CRITICAL, DEBUG) z kodowaniem kolorystycznym
     - Pole wyszukiwania tekstowego w treści logów i ścieżkach
     - Karty logów z datą, poziomem, modułem, kontekstem lokalu oraz treścią
     - Obsługa rozwijania i zwijania wieloliniowych tracebacków błędów (stack trace) oraz kopiowania treści do schowka
     - Akcje w nagłówku: odświeżanie logów oraz czyszczenie pliku logów z dialogiem potwierdzenia

---

### Manager Dashboard (`/manager`)

Pasek nawigacyjny z zakładkami:

| Indeks | Etykieta | Ekran |
|--------|----------|-------|
| 0 | Home | `HomeTab` |
| 1 | Grafik | `SchedulerTab` |
| 2 | Zespół | `TeamTab` |
| 3 | Ustawienia | `SetupTab` |
| 4 | Obecności | `AttendanceApprovalTab` |
| 5 | Zmiany | `GiveawayTab` |

#### Home Tab
- Kalendarz z dziennymi wydarzeniami
- Podgląd dnia: lista pracowników, zmian i stanowisk
- Pasek górny: dzwonek powiadomień, pomoc, konfiguracja QR, moduł POS, wylogowanie

#### Scheduler Tab (Grafik)
- Nawigacja tygodniowa (poprzedni / następny tydzień)
- Siatka dni i zmian z chipami pracowników
- Wymagania kadrowe per dzień / zmiana / rola
- Tryb szkicu (Draft): generowanie bez natychmiastowego zapisu
- Ostrzeżenia o 11-godzinnym odpoczynku dobowym oraz brakach kadrowych
- Przyciski akcji: Generuj, Zapisz, Opublikuj

#### Team Tab (Zespół)
- Lista pracowników z avatarami i rolami
- Przycisk dodawania pracownika
- Okno dialogowe pracownika:
  - Przypisywanie ról
  - Edycja danych (imię, adres e-mail, cele godzinowe)
  - Reset hasła z walidacją złożoności
  - Aktywacja / dezaktywacja konta

#### Setup Tab (Ustawienia)
- Sekcja Role: lista stanowisk, kolory
- Sekcja Zmiany: godziny rozpoczęcia i zakończenia, powiązanie z konkretnymi rolami
- Sekcja Restauracja: dane lokalu, godziny otwarcia

#### Attendance Approval Tab (Obecności)
- Filtry: zakres dat, status (PENDING / CONFIRMED / REJECTED)
- Lista ewidencji czasu pracy z przyciskami zatwierdzenia i odrzucenia
- Ręczne dodawanie wpisów i eksport raportu PDF

#### Giveaway Tab (Giełda Zmian)
- Lista otwartych zgłoszeń oddania zmiany
- Sugerowane zastępstwa na podstawie dostępności i uprawnień
- Akcje przydzielenia zastępstwa i anulowania zgłoszenia

---

### Employee Dashboard (`/employee`)

Pasek nawigacyjny z zakładkami:

| Indeks | Etykieta | Ekran |
|--------|----------|-------|
| 0 | Grafik | `MyScheduleScreen` |
| 1 | Dostępność | `AvailabilityViewTab` |
| 2 | Obecność | `AttendanceTab` |

#### My Schedule Screen
- Kalendarz z opublikowanymi zmianami
- Przełącznik widoku: „Moje zmiany” / „Cała załoga”
- Funkcja oddania zmiany na giełdę
- Funkcja bezpośredniej wymiany zmian z uprawnionym współpracownikiem

#### Availability View Tab
- Siatka dni i zmian (widoczne wyłącznie zmiany zgodne z przypisanymi rolami pracownika)
- Przełącznik statusu: Preferuję / Neutralnie / Niedostępny
- Zapisywanie deklaracji dostępności

#### Attendance Tab
- Rejestracja obecności (check-in / check-out) z domyślnymi godzinami z grafiku
- Historia zarejestrowanych obecności i status ich zatwierdzenia

---

## Wspólne Komponenty i Widgety

| Widget | Opis |
|--------|------|
| `NotificationBell` | Dzwonek powiadomień z licznikiem, dialogiem listy powiadomień i panelem uprawnień Web Push |
| `AppLogo` | Logo systemu |
| `AvailabilityGrid` | Siatka dostępności z oznaczeniem stanów |
| `ScheduleViewer` | Uniwersalna przeglądarka grafiku |
| `BugReportDialog` | Formularz zgłaszania usterek do GitHub Issues |
| `HelpDialog` | Panel pomocy i wskazówek |
| `QrConfigDialog` | Generator kodu QR z parametrami połączenia |

## Responsywność

| Szerokość | Układ |
|-----------|-------|
| < 600px | Mobile: dolny pasek nawigacji, widok jednokolumnowy |
| 600–1200px | Tablet: siatki dwukolumnowe, adaptacyjne dialogi |
| > 1200px | Desktop / Web: pełna siatka kalendarza, nawigacja horyzontalna |

## Komunikacja Błędów i Dostępność

- Wszystkie błędy sieciowe prezentowane są w języku polskim za pośrednictwem `ApiErrorHandler`.
- Błędy walidacji formularzy (w tym złożoności hasła) wyświetlane są inline pod polami tekstowymi oraz w komunikatach SnackBar.
- Komunikaty powiadomień pierwszoplanowych pojawiają się w nieinwazyjnym banerze u góry ekranu z możliwością natychmiastowego zamknięcia.
