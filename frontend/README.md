# Planner V2 Frontend

## Setup

1. **Install Dependencies**:
   ```bash
   flutter pub get
   ```

2. **Run on Web**:
   ```bash
   flutter run -d chrome
   ```

3. **Run on Android/iOS**:
   ```bash
   flutter run
   ```

## Features

### Employee View
- Interactive weekly availability calendar
- Color-coded status (Preferred, Neutral, Unavailable)
- Mobile-first responsive design
- Easy tap-to-toggle interface

### Manager View
- Role and shift configuration
- Schedule generation using OR-Tools
- Week-by-week planning
- **Zarządzanie Zespołem**: Dodawanie pracowników, przypisywanie ról.
- **Auto-kolor Ról**: Automatyczne generowanie kolorów role.
- **Obecności**: Ewidencja czasu pracy, zatwierdzanie/odrzucanie, eksport do PDF.
- **Scheduler**: Automatyczne generowanie grafiku z podglądem statystyk godzin.
- **Calendar View**: Wizualny podgląd grafiku dziennego na ekranie domowym.

### Testing
```bash
# Run unit & widget tests
flutter test
# Re-generate mocks if needed
dart run build_runner build --delete-conflicting-outputs
```

## Architecture

- **State Management**: Riverpod
- **Routing**: GoRouter with auth-based redirects
- **HTTP**: Dio with JWT interceptors
- **Storage**: flutter_secure_storage for tokens
- **UI**: Material 3 with Google Fonts

## Build for Production

### Web
```bash
flutter build web
```

### Android
```bash
flutter build apk
```

### iOS
```bash
flutter build ios
```
