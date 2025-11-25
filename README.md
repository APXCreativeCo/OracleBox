# OracleBox Android Controller

Android app to control a Raspberry Pi-based OracleBox over classic Bluetooth SPP.

## Features

- Connect to OracleBox via RFCOMM using UUID `00001101-0000-1000-8000-00805F9B34FB`.
- Send supported commands: `STATUS`, `SPEED`, `FASTER`, `SLOWER`, `DIR`, `START`, `STOP`, `LED`, `SOUND`.
- Display sweep status (direction, speed, LED modes, startup sound).
- Control sweep speed and direction.
- Control Sweep and Box LEDs (on/off/breath/breath_fast/heartbeat/strobe/flicker/random_burst/sweep).
- List available sounds, play selected sound, set startup sound.
- Show recent OK/ERR lines in a log view.

## Requirements

- Android Studio Flamingo or newer with Android SDK 36.
- Java 17 toolchain (uses Gradle wrapper).
- An Android device with classic Bluetooth and a paired Raspberry Pi running `oraclebox.py`.

## Build and Run (Android Studio)

1. Open the project in Android Studio.
2. Let the IDE sync and download dependencies.
3. Connect or select a device/emulator that supports Bluetooth.
4. Click Run (or Build > Make Project) to install and launch.

## Build and Run (CLI)

From the project root:

```
./gradlew assembleDebug        # builds APK
./gradlew installDebug         # installs on connected device
```

## Pi Setup (oraclebox.py)

1. Copy `oraclebox.py` to your Raspberry Pi.
2. Ensure Bluetooth SPP is enabled and the Pi is discoverable/pairable.
3. Start the script so it exposes the SPP service with UUID `00001101-0000-1000-8000-00805F9B34FB` and service name `OracleBox`.
4. Pair the Pi with your Android device before opening the app.

## App Flow

- Connection screen: enable Bluetooth, refresh paired devices, tap the Pi to connect, then open Controls.
- Control screen: refresh status, start/stop sweep, change direction and speed, set LED modes, manage sounds, and view the log.
- Device settings: adjust any device-level settings exposed by `DeviceSettingsActivity` (see `app/src/main/java/com/apx/oraclebox/ui/settings/DeviceSettingsActivity.kt`).

## Configuration

- To change the OracleBox UUID, edit `BluetoothClient.ORACLEBOX_UUID` in
  `app/src/main/java/com/apx/oraclebox/bt/BluetoothClient.kt`.
- To adjust permissions or SDK versions, edit `AndroidManifest.xml` and
  `app/build.gradle.kts`.

## Troubleshooting

- If a build fails on Windows with AccessDenied deleting `app/build`, close Android Studio windows pointing at `app/build`, delete `app/build` manually, then run `./gradlew clean` and retry.
- If the app cannot find the device, confirm the Pi is paired and the SPP service is running with the correct UUID.
