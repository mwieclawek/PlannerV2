# PlannerV2 Frontend

Aplikacja Flutter (Web, PWA, Android, iOS) — interfejs użytkownika dla platformy PlannerV2.

## Uruchomienie Deweloperskie

```bash
cd frontend
flutter pub get
flutter run -d web-server --web-hostname=127.0.0.1 --web-port=5000
```

Dla powiadomień Web Push można przekazać klucz VAPID:
```bash
flutter run -d web-server --web-hostname=127.0.0.1 --web-port=5000 --dart-define=FCM_VAPID_KEY=twoj_klucz_vapid
```

## Architektura Technologiczna

| Warstwa | Technologia |
|---------|-------------|
| State Management | Riverpod (`flutter_riverpod`) |
| Routing | GoRouter z przekierowaniami na bazie ról i modułów |
| HTTP Client | Dio z interceptorami autoryzacji JWT |
| Error Handling | `ApiErrorHandler` + `FriendlyDioException` (polska lokalizacja błędów, walidacja haseł) |
| Secure Storage | `flutter_secure_storage` (tokeny JWT) |
| Config Storage | `shared_preferences` (adres backendu) |
| UI Framework | Material 3 + Google Fonts (Outfit, Inter) |
| Push Notifications | Firebase Cloud Messaging (Android/iOS) + Web Push (`firebase-messaging-sw.js`) |
| Web Interop | `package:web` + `dart:js_interop` (`WebNotificationHelper`) |
| Calendar | `calendar_view` |
| Scanner / QR | `mobile_scanner` + `qr_flutter` |

## Moduły i Ekrany

### Logowanie i Setup
- **Dual-Login**: Logowanie globalnym adresem e-mail LUB loginem z kodem lokalu (tenant slug).
- **Zarządzanie połączeniem**: Skanowanie kodu QR z adresem backendu lub ręczna konfiguracja.
- **Autofill**: Wskazówki autouzupełniania dla menedżerów haseł przeglądarek.

### Superadmin Dashboard (`/superadmin`)
- Zarządzanie lokalami w systemie (tworzenie, edycja parametrów i slug, zmiana statusu).
- Podgląd użytkowników ze wszystkich restauracji.
- Tworzenie pierwszych managerów lokali i awaryjny reset haseł.
- Podgląd i filtrowanie logów systemowych (per lokal, poziom logowania, wyszukiwanie fraz, analiza tracebacków, czyszczenie pliku).
- Bezpośredni skrót „Logi” na karcie każdej restauracji przełączający filtr na dany lokal.

### Manager Dashboard (zakładki)
- **Home (`home_tab.dart`)**: Kalendarz dzienny z podglądem obsady, bezpośrednie prośby o wymianę zmian.
- **Grafik (`scheduler_tab.dart`)**: Generator CP-SAT, tryb szkicu (Draft), batch save, publikacja z powiadomieniami push.
- **Zespół (`team_tab.dart`)**: Zarządzanie personelem, edycja e-maili, przypisywanie ról, cele godzinowe/zmianowe, reset haseł.
- **Ustawienia (`setup_tab.dart`)**: Konfiguracja stanowisk (ról), definicji zmian powiązanych z rolami, dane lokalu, strefy i stoliki POS, włączniki modułów (zamknięcie dnia, wymóg checklisty, ukrywanie tip poolingu).
- **Obecności (`attendance_approval_tab.dart`)**: Zatwierdzanie ewidencji czasu pracy, eksport raportu PDF.
- **Giełda (`giveaway_tab.dart`)**: Zarządzanie oddawanymi zmianami i sugerowane zastępstwa.

### Employee Dashboard (zakładki pracownicze)
- **Mój Grafik (`my_schedule_screen.dart`)**: Opublikowane zmiany, przełącznik widoku całego zespołu, bezpośrednia wymiana zmian z uprawnionym współpracownikiem (A <-> B) z priorytetowym banerem na ekranie głównym.
- **Dostępność (`AvailabilityViewTab`)**: Tygodniowy grid dyspozycji na zmiany zgodne ze stanowiskiem, wnioski urlopowe.
- **Obecność (`attendance_tab.dart`)**: Rejestracja check-in / check-out z domyślnymi godzinami z grafiku oraz opcjonalną weryfikacją checklisty lokalu.
- **Giełda (`GiveawaysScreen`)**: Przegląd otwartych ofert i bezpieczne przejmowanie zmian bez konfliktów czasowych.

### Ekosystem Gastronomiczny (POS i KDS)
- **POS (Kelner)**: Obsługa stref i stolików, zamówienia z podziałem na kursy, modyfikatory dań, płatności dzielone.
- **KDS (Kuchnia)**: Pacing engine (synchronizacja wydawania dań), kolejkowanie kaskadowe, pełna praca offline z bezpieczną synchronizacją batch.

### Komponenty Powiadomień i Web Push
- **`NotificationBell`**: Dzwonek z licznikiem nieprzeczytanych wiadomości, okno dialogowe z historią oraz interaktywny panel sprawdzania uprawnień przeglądarki i ponownego wywoływania zgody (`requestPermission()`) po kliknięciu.
- **Powiadomienia Pierwszoplanowe (Foreground)**: Równoczesne powiadomienie przeglądarki HTML5 oraz widoczny baner `MaterialBanner` u góry ekranu z poziomu `rootScaffoldMessengerKey`.
- **Service Worker (`web/firebase-messaging-sw.js`)**: Odbiór powiadomień w tle z ikoną i przywracaniem aktywnej karty aplikacji.

## Testowanie i Weryfikacja Jakości

```bash
# Uruchomienie wszystkich testów
flutter test

# Analiza statyczna kodu
flutter analyze

# Regeneracja mocków testowych (jeśli zmodyfikowano interfejsy)
dart run build_runner build --delete-conflicting-outputs
```

## Budowanie Aplikacji

### Web & PWA
```bash
flutter build web --release --dart-define=FCM_VAPID_KEY=twoj_klucz_vapid
```
Wygenerowane pliki znajdują się w `build/web`. Serwowane są przez Nginx z wyłączonym buforowaniem dla service workerów.

### Android
```bash
flutter build apk --release
flutter build appbundle --release
```
Szczegóły: [ANDROID_SETUP.md](ANDROID_SETUP.md)

### iOS
```bash
flutter build ios --release
```
Szczegóły: [iOS_SETUP.md](iOS_SETUP.md)
Aplikacja może być również instalowana jako PWA bezpośrednio z Safari (Add to Home Screen).
