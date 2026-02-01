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
