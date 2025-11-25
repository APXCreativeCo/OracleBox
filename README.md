# OracleBox Android Controller

Android app to control a Raspberry Pi-based OracleBox over classic Bluetooth SPP.

## System Architecture

- **Raspberry Pi hardware** drives the TEA5767 FM tuner via I2C (`/dev/i2c-1`, addr `0x60`), animates the Sweep LED on GPIO 17 and Box LED on GPIO 27, and exposes a Bluetooth RFCOMM service.
- **`oraclebox.py` daemon** runs on the Pi: handles sweeping, LED animations, sound playback, and the Bluetooth command server the Android app talks to.
- **Android controller** (this app) issues textual commands over classic Bluetooth (`STATUS`, `LED`, `SOUND`, etc.) and visualizes current sweep state.
- **Audio path (current)** routes straight from the TEA5767 to an amp; future builds will loop through a USB audio interface for filtering/effects.

## Python Daemon (`oraclebox.py`)

- Loads persisted state + LED presets from JSON (see `OracleBoxState`).
- Initializes hardware (I2C tuner, gpiozero LEDs), optionally plays a startup sound, and launches a sweep thread.
- Runs a Bluetooth SPP server (UUID `00001101-0000-1000-8000-00805F9B34FB`, service name `OracleBox`) that responds with `OK ...` / `ERR ...` lines.
- Supported commands mirror this app’s UI: `STATUS`, `SPEED`, `SLOWER`/`FASTER`, `DIR`, `START`, `STOP`, `LED <sweep|box> <mode>`, `SOUND <action>`, etc.

### OracleBoxState Snapshot

Persisted fields (written to `config.json`):

- `speed_ms` – actual sweep delay derived from `speed_index`.
- `direction` – `"up"` or `"down"`.
- `running` – whether the sweep thread should be active.
- `sweep_led_mode` / `box_led_mode` – LED animation presets (on/off/breath/breath_fast/heartbeat/strobe/flicker/random_burst/sweep).
- `startup_sound` – filename of the boot sound or empty for none.

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

## Future Plans

- Route audio through a USB interface for band-pass filtering (roughly 600–3500 Hz) and portal-style reverb/chorus.
- Accept external sweep sources (e.g., SB7 headphone out) as input for processing.
- Expand the Android UI with controls for effects stacks once the Pi pipeline is ready.
