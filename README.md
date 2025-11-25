# OracleBox Android Controller

Android app to control a Raspberry Pi–based OracleBox over classic Bluetooth SPP.

## Features

- Connect to OracleBox via RFCOMM using UUID `00001101-0000-1000-8000-00805F9B34FB`.
- Send supported commands: `STATUS`, `SPEED`, `FASTER`, `SLOWER`, `DIR`, `START`, `STOP`, `LED`, `SOUND`.
- Display sweep status (direction, speed, LED modes, startup sound).
- Control sweep speed and direction.
- Control Sweep and Box LEDs (on/off/breath/breath_fast/heartbeat/strobe/flicker/random_burst/sweep).
- List available sounds, play selected sound, set startup sound.
- Show recent OK/ERR lines in a log view.

## Assumptions

- Min SDK 24, target/compile SDK 36.
- Device supports classic Bluetooth and is already paired with the Raspberry Pi.
- Raspberry Pi runs `oraclebox.py` and exposes an SPP service with the UUID above and service name `OracleBox`.

## How to Use

1. Pair your Android device with the Raspberry Pi running `oraclebox.py`.
2. Build and install this app.
3. Launch the app; the Connection screen appears.
4. Enable Bluetooth using the toggle.
5. Tap **Scan / Refresh Paired Devices**.
6. Tap your Pi device in the list to connect.
7. Tap **Open Controls** to enter the control screen.

On the control screen you can:

- Tap **Refresh STATUS** to retrieve and display current sweep state.
- Use **Start/Stop** and **Dir Up/Down/Toggle** to control sweep.
- Select a speed preset or tap **FASTER/SLOWER**.
- Select Sweep/Box LED modes from the dropdowns or use **All LEDs Off**.
- Refresh the sound list, select a sound, **Play Selected**, or **Set as Startup**.

## Configuration

- To change the OracleBox UUID, edit `BluetoothClient.ORACLEBOX_UUID` in
  `app/src/main/java/com/apx/oraclebox/bt/BluetoothClient.kt`.
- To adjust permissions or SDK versions, edit `AndroidManifest.xml` and
  `app/build.gradle.kts`.
