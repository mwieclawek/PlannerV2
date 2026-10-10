# Specyfikacja UI

## Paleta Kolorów

| Nazwa | Hex | Użycie |
|-------|-----|--------|
| Primary | `#4F46E5` (Indigo) | Przyciski, akcenty, nawigacja |
| Success | `#22C55E` | Potwierdzenia, dostępność PREFERRED |
| Warning | `#F59E0B` | Ostrzeżenia, status NEUTRAL |
| Error | `#EF4444` | Błędy, niedostępność, odrzucone |
| Background | `#F8FAFC` | Tło |
| Surface | `#FFFFFF` | Karty, dialogi |
| On Surface | `#1E293B` | Tekst główny |

## Typografia

- **Nagłówki**: Google Fonts — Outfit
- **Treść**: Google Fonts — Inter
- **Rozmiary**: 12 / 14 / 16 / 20 / 24 / 32px

## Komponenty

### Przyciski
- `ElevatedButton` — główne akcje (Zapisz, Generuj, Opublikuj)
- `OutlinedButton` — akcje drugorzędne (Anuluj, Filtruj)
- `IconButton` — akcje inline (Edytuj, Usuń, Dodaj)
- `FloatingActionButton` — szybkie dodawanie (+)

### Formularze
- `TextField` z `OutlineInputBorder`
- Walidacja inline z `errorText`
- `DropdownButtonFormField` dla select
- `TimePicker` dla godzin zmian

### Karty
- `Card` z `elevation: 2`
- Padding: 16px
- Border radius: 12px

### Dialogi
- `AlertDialog` — potwierdzenia, ostrzeżenia
- `SimpleDialog` — wybory (np. wybór pracownika)
- Customowe dialogi: `EmployeeDetailDialog`, `BugReportDialog`, `HelpDialog`, `QrConfigDialog`

### Chipy / Badge
- `Chip` z kolorem roli — identyfikacja pracowników na grafiku
- Status badge — kolorowe oznaczenie statusu (OPEN/TAKEN/CANCELLED)

---

## Ekrany

### Login (`/login`)
- Logo aplikacji (widget `AppLogo`)
- Obsługa architektury Multi-Tenancy (wielodostępność) - wiele restauracji na jednej instancji.
- Pola: **Kod restauracji** (Login ID), **Login lub Email**, **Hasło**
- Przycisk: **Zaloguj**
- Brak opcji samodzielnej rejestracji

### Server Setup (`/server-setup`)
- Skanowanie kodu QR z adresem serwera
- Ręczne wpisanie URL backendu
- Zapisywane w `ConfigService` (SharedPreferences)

---

### Superadmin Dashboard (`/#/superadmin`)
- Dostępne dla użytkowników o globalnej roli `SUPERADMIN`.
- Lista wszystkich restauracji (Tenantów) prezentowana w formie Kart.
- Karty restauracji oferują:
  - Toggla do edycji statusu.
  - Ikonę ołówka do edycji nazwy i slug (identyfikatora/kodu restauracji).
  - Przycisk **Użytkownicy** – otwiera okno dialogowe z listą użytkowników przypisanych do danej restauracji (wraz z opcją resetu hasła managera).
  - Przycisk **Dodaj managera**.
- Floating Action Button (+) pozwalający na akcję **Dodaj Restaurację**.

---

### Manager Dashboard (`/manager`)

Bottom Navigation Bar z 6 zakładkami:

| # | Ikona | Nazwa | Ekran |
|---|-------|-------|-------|
| 0 | 🏠 Home | Home | `HomeTab` |
| 1 | 📅 Calendar | Grafik | `SchedulerTab` |
| 2 | 👥 People | Zespół | `TeamTab` |
| 3 | ⚙️ Settings | Ustawienia | `SetupTab` |
| 4 | ✅ Check | Obecności | `AttendanceApprovalTab` |
| 5 | 🔄 Swap | Zmiany | `GiveawayTab` |

#### Home Tab
- **Kalendarz** (CalendarView) z dziennymi wydarzeniami
- Kliknięcie dnia → szczegóły: kto pracuje, na jakiej zmianie i roli
- Pasek nawigacyjny AppBar z nazwą użytkownika, ikonami Pomoc (❔) i Wyloguj

#### Scheduler Tab (Grafik)
- Nawigacja tygodniowa (← Tydzień →)
- **Grid**: Dni × Zmiany z chipami pracowników (kolor = rola)
- **Wymagania kadrowe**: edycja per dzień/zmiana/rola
- **Tryb Draft**: generowanie nie zapisuje do DB
- Przyciski: Generuj | Zapisz | Opublikuj
- Statystyki godzin per pracownik

#### Team Tab (Zespół)
- Lista pracowników z avatarami i rolami
- FAB (+) — tworzenie nowego konta pracownika
- Kliknięcie → `EmployeeDetailDialog`:
  - Przypisywanie ról (checkboxy)
  - Edycja danych (imię, **adres email**, cele godzinowe)
  - Reset hasła
  - Aktywacja / dezaktywacja (`is_active`)
- Filtr: aktywni / wszyscy

#### Setup Tab (Ustawienia)
- **Sekcja Role**: lista + formularz dodawania (nazwa + kolor)
- **Sekcja Zmiany**: lista + formularz (nazwa + godziny start/end). *Zmiany (ShiftDefinition) są teraz przypisane do konkretnych ról (JobRoles).*
- **Sekcja Restauracja**: nazwa, adres, godziny otwarcia
- Inline edycja i usuwanie (ikony ołówka/kosza)

#### Attendance Approval Tab (Obecności)
- Filtry: zakres dat, status (PENDING/CONFIRMED/REJECTED)
- Lista obecności z detalami (pracownik, data, godziny, status)
- Przyciski: Zatwierdź ✅ | Odrzuć ❌
- Ręczne dodawanie obecności
- Przycisk eksportu PDF

#### Giveaway Tab (Oddawanie Zmian)
- Lista otwartych próśb o oddanie zmiany
- Szczegóły: kto oddaje, jaka zmiana, data
- Sugerowane zastępstwa (sortowane wg dostępności)
- Przyciski: Przydziel | Anuluj

---

### Employee Dashboard (`/employee`)

Bottom Navigation Bar z 3 zakładkami:

| # | Ikona | Nazwa | Ekran |
|---|-------|-------|-------|
| 0 | 📅 Calendar | Grafik | `MyScheduleScreen` |
| 1 | 📝 Edit | Dostępność | `AvailabilityViewTab` |
| 2 | ⏰ Clock | Obecność | `AttendanceTab` |

#### My Schedule Screen
- Kalendarz z opublikowanymi zmianami
- Szczegóły zmiany: data, godziny, rola
- Opcja **"Oddaj zmianę"** (tworzy ShiftGiveaway)
- Status oddanych zmian (OPEN/TAKEN/CANCELLED)

#### Availability View Tab
- Grid: Dni × Zmiany (tydzień)
- **Widoczne są tylko zmiany istotne dla pracownika (powiązane z jego przypisanymi rolami).**
- Tap-to-toggle statusu: ✅ Preferuję → ⚪ Neutralnie → ❌ Niedostępny
- Nawigacja tygodniowa
- Przycisk Zapisz

#### Attendance Tab
- Formularz rejestracji obecności (data, check-in, check-out)
- Historia własnych wpisów ze statusem
- Domyślne godziny pobierane z grafiku

---

## Wspólne Widgety

| Widget | Opis |
|--------|------|
| `AppLogo` | Logo aplikacji |
| `AvailabilityGrid` | Grid dostępności z kolorowym kodowaniem |
| `ScheduleViewer` | Uniwersalny widok grafiku |
| `BugReportDialog` | Formularz zgłaszania błędów (→ GitHub Issues) |
| `HelpDialog` | Panel pomocy z FAQ |
| `QrConfigDialog` | Dialog generowania QR z adresem serwera |

## Responsywność

| Breakpoint | Layout |
|------------|--------|
| < 600px | Mobile — Bottom Navigation + stack |
| 600-1200px | Tablet — 2 kolumny |
| > 1200px | Desktop — sidebar + content |

## Animacje i UX

- Przejścia między ekranami: `PageRouteBuilder`
- Loading states: `CircularProgressIndicator`
- Snackbary: 3s auto-dismiss (sukces/błąd)
- Pull-to-refresh na listach
- Color-coded chipy i badge'e wg statusu
