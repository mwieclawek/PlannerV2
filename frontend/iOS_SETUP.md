# iOS Setup & Build Guide

Since this project was developed on Windows, the iOS specific files (like `Podfile` and potentially some generated Xcode configurations) might need initialization on a Mac.

## Prerequisites
- A Mac computer
- Xcode installed (latest version recommended)
- CocoaPods installed (`sudo gem install cocoapods`)
- Flutter SDK installed on the Mac

## Steps to Build for iOS

1.  **Clone/Copy the repository** to your Mac.

2.  **Navigate to the frontend directory**:
    ```bash
    cd frontend
    ```

3.  **Get Flutter dependencies**:
    ```bash
    flutter pub get
    ```

4.  **Initialize iOS Pods**:
    Navigate to the ios folder and install pods.
    ```bash
    cd ios
    # If Podfile is missing, this might fail or warn.
    # Usually flutter build ios generates it, but running pod install is safer if it exists.
    # If no Podfile exists yet, run:
    flutter build ios --no-codesign
    # This will generate the necessary iOS build files including Podfile.
    ```

5.  **Install Pods (if not done automatically)**:
    ```bash
    cd ios
    pod install
    cd ..
    ```

6.  **Open Workspace in Xcode**:
    Open the `result` of the pod install (the `.xcworkspace` file, NOT `.xcodeproj`).
    ```bash
    open ios/Runner.xcworkspace
    ```

7.  **Configure Signing**:
    - In Xcode, click on the **Runner** project in the left project navigator.
    - Select the **Runner** target.
    - Go to the **Signing & Capabilities** tab.
    - Select your **Team** (you may need to log in with your Apple ID).
    - Ensure a unique **Bundle Identifier** is set (e.g., `com.yourcompany.plannerV2`).

8.  **Run the App**:
    - Connect your iOS device or select a Simulator.
    - Click the **Play** button in Xcode or run via terminal:
      ```bash
      flutter run -d <device_id>
      ```

## Troubleshooting

### "Podfile not found"
If `ios/Podfile` is missing, running `flutter build ios --no-codesign` generates it.

### "IPCAccessError" or Keychain issues
The app uses `flutter_secure_storage` which relies on the iOS Keychain. In the Simulator, this usually works. On a real device, you must ensure your provisioning profile supports Keychain access (standard profiles do).

### Minimum iOS Version
If you encounter errors about deployment targets (e.g., `IPHONEOS_DEPLOYMENT_TARGET`), you may need to update the `Podfile` (after it is created) to uncomment and set the platform line:
```ruby
platform :ios, '13.0'
```
Then run `pod install` again.
