# Planner V2 Frontend

Aplikacja Flutter (Web / Android / iOS) — interfejs użytkownika dla PlannerV2.

## Setup

```bash
cd frontend
flutter pub get
flutter run -d web-server --web-hostname=127.0.0.1 --web-port=5000
```

## Architektura

| Warstwa | Technologia |
|---------|-------------|
| State Management | Riverpod (`flutter_riverpod`) |
| Routing | GoRouter z auth-based redirects |
| HTTP Client | Dio z JWT interceptors |
| Secure Storage | `flutter_secure_storage` (tokeny JWT) |
| Config Storage | `shared_preferences` (URL serwera) |
| UI Framework | Material 3 + Google Fonts (Outfit, Inter) |
| Calendar | `calendar_view` |
| QR | `mobile_scanner` + `qr_flutter` |

## Funkcjonalności

### Ekran Logowania
- Login (username) + hasło
- Brak samodzielnej rejestracji

### Konfiguracja Serwera
- Skanowanie QR z adresem backendu
- Ręczne wpisanie URL
- Zapis w `ConfigService` (`SharedPreferences`)

### Manager Dashboard (6 zakładek)

| Zakładka | Plik | Opis |
|----------|------|------|
| Home | `home_tab.dart` | Kalendarz dzienny, podgląd grafiku |
| Grafik | `scheduler_tab.dart` | Generator AI, tryb Draft, batch save, publikacja |
| Zespół | `team_tab.dart` | CRUD pracowników, przypisywanie ról, aktywacja/dezaktywacja |
| Ustawienia | `setup_tab.dart` | CRUD ról, zmian, dane restauracji |
| Obecności | `attendance_approval_tab.dart` | Zatwierdzanie obecności, eksport PDF |
| Zmiany | `giveaway_tab.dart` | Oddawanie zmian, sugerowane zastępstwa |

### Employee Dashboard (3 zakładki)

| Zakładka | Plik | Opis |
|----------|------|------|
| Grafik | `my_schedule_screen.dart` | Podgląd zmian, oddawanie zmian |
| Dostępność | (AvailabilityGrid widget) | Grid tygodniowy, tap-to-toggle |
| Obecność | `attendance_tab.dart` | Rejestracja check-in/check-out |

### Widgety Reużywalne

| Widget | Opis |
|--------|------|
| `AppLogo` | Logo aplikacji |
| `AvailabilityGrid` | Interaktywny grid dostępności |
| `ScheduleViewer` | Wizualny podgląd grafiku |
| `BugReportDialog` | Formularz zgłaszania błędów (→ GitHub) |
| `HelpDialog` | Panel pomocy w aplikacji |
| `QrConfigDialog` | Generator QR z adresem serwera |

### Serwisy

| Serwis | Opis |
|--------|------|
| `ApiService` | Klient HTTP (Dio), interceptory JWT, wszystkie wywołania API |
| `ConfigService` | Zarządzanie konfiguracją (URL serwera) |

## Testowanie

```bash
# Testy jednostkowe i widgetowe
flutter test

# Analiza statyczna
flutter analyze

# Regeneracja mocków
dart run build_runner build --delete-conflicting-outputs
```

## Budowanie

### Web
```bash
flutter build web
```

### Android
```bash
flutter build apk          # Debug/Release APK
flutter build appbundle     # App Bundle (Google Play)
```
Szczegóły: [ANDROID_SETUP.md](ANDROID_SETUP.md)

### iOS
```bash
flutter build ios
```
Szczegóły: [iOS_SETUP.md](iOS_SETUP.md)
