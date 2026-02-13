# Android Setup & Build Guide

## Prerequisites
- Windows, macOS, or Linux
- Flutter SDK installed
- Android Studio installed with Android SDK and Command-line Tools
- Java Development Kit (JDK) installed (usually bundled with Android Studio)

## Configuration
- **Permissions**: `INTERNET` permission is already added to `AndroidManifest.xml`.
- **Queries**: `http` and `https` schemes are added for `url_launcher`.
- **Min SDK**: The app targets a minimum SDK version compatible with the plugins used.

## Building the App

### Debug APK
To build a debug APK for testing on an emulator or connected device:
```bash
flutter build apk --debug
```
The APK will be located at `build/app/outputs/flutter-apk/app-debug.apk`.

### Release APK
To build a release APK (signed with debug keys by default):
```bash
flutter build apk --release
```
The APK will be located at `build/app/outputs/flutter-apk/app-release.apk`.

### App Bundle (AAB)
For Google Play Store submission, build an App Bundle:
```bash
flutter build appbundle
```
The AAB will be located at `build/app/outputs/bundle/release/app-release.aab`.

## Production Signing
To sign the app for production:
1.  Create a keystore file.
2.  Create a `key.properties` file in `android/`.
3.  Update `android/app/build.gradle` to use the keystore.
    (See [Flutter documentation on deployment](https://docs.flutter.dev/deployment/android) for details).

## Troubleshooting
- **Gradle Errors**: Run `cd android && ./gradlew clean` (or `gradlew.bat clean` on Windows) and try again.
- **Dependency Issues**: Run `flutter pub get` and `flutter pub upgrade`.

## Running in Android Studio
1.  Open **Android Studio**.
2.  Select **Open** (or **File > Open**).
3.  Navigate to and select the `frontend/android` folder within your project.
    *   **Important**: Do not open the root `PlannerV2` or `frontend` folder as an Android project. You must select `frontend/android`.
4.  Click **OK**. Android Studio will import the project and sync with Gradle.
    *   This may take a few minutes. Watch the progress bar at the bottom.
5.  Once synced, you should see the `app` module in the configuration dropdown (top toolbar).
6.  Select an **Android Emulator** or a connected **Physical Device** from the device dropdown.
7.  Click the green **Run** (Play) button.
