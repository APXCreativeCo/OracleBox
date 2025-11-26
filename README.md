# OracleBox Android Controller

Android app to control a Raspberry Pi-based paranormal investigation device (OracleBox) over classic Bluetooth SPP.

## System Architecture

- **Raspberry Pi hardware** drives the TEA5767 FM tuner via I2C (`/dev/i2c-1`, addr `0x60`), animates the Sweep LED on GPIO 17 and Box LED on GPIO 27, and exposes a Bluetooth RFCOMM service.
- **`oraclebox_merged.py` daemon** runs on the Pi: handles sweeping, LED animations, sound playback (including voice announcements), and the Bluetooth command server the Android app talks to.
- **Android controller** (this app) issues textual commands over classic Bluetooth (`STATUS`, `LED`, `SOUND`, etc.) and provides a voice-guided, vintage radio-themed UI for investigation modes.
- **Audio path (current)** routes straight from the TEA5767 to an amp; future builds will loop through a USB audio interface for filtering/effects.

## Python Daemon (`oraclebox_merged.py`)

- Loads persisted state + LED presets from JSON (see `OracleBoxState`).
- Initializes hardware (I2C tuner, gpiozero LEDs), optionally plays a startup sound, and launches a sweep thread.
- Runs a Bluetooth SPP server (UUID `00001101-0000-1000-8000-00805F9B34FB`, service name `OracleBox`) that responds with `OK ...` / `ERR ...` lines.
- Manages two sound directories:
  - `/home/dylan/oraclebox/announcements/` - System voice files for navigation (not changeable via app)
  - `/home/dylan/oraclebox/sounds/` - User-uploadable sounds including startup sound
- Supported commands mirror this app's UI: `STATUS`, `SPEED`, `SLOWER`/`FASTER`, `DIR`, `START`, `STOP`, `LED <sweep|box> <mode>`, `SOUND <action>`, etc.

### OracleBoxState Snapshot

Persisted fields (written to `config.json`):

- `speed_ms` - actual sweep delay derived from `speed_index`.
- `direction` - `"up"` or `"down"`.
- `running` - whether the sweep thread should be active.
- `sweep_led_mode` / `box_led_mode` - LED animation presets (on/off/breath/breath_fast/heartbeat/strobe/flicker/random_burst/sweep).
- `startup_sound` - filename of the boot sound or empty for none.

## Features

### Core Functionality
- **Auto-Connect**: Automatically connects to saved OracleBox device on app launch with animated loading screen
- **Voice-Guided Navigation**: System announces mode selection and navigation with vintage radio-style voice effects
- **Multiple Investigation Modes**: Spirit Box, REM Pod (dev), Music Box (dev) accessible from central hub
- **Vintage Themed UI**: Uniform design across all pages with wood backgrounds, gothic gold accents, and consistent layouts

### Bluetooth Control
- Connect to OracleBox via RFCOMM using UUID `00001101-0000-1000-8000-00805F9B34FB`
- Send supported commands: `STATUS`, `SPEED`, `FASTER`, `SLOWER`, `DIR`, `START`, `STOP`, `LED`, `SOUND`
- Display sweep status (direction, speed, LED modes, startup sound)
- Show recent OK/ERR lines in a log view

### Spirit Box Mode
- **START SPIRIT BOX**: Dedicated start button with clean control flow
- Control sweep speed and direction with visual feedback
- Adjust sweep direction (up/down frequency)
- Real-time status cards showing current state
- Control Sweep and Box LEDs (on/off/breath/breath_fast/heartbeat/strobe/flicker/random_burst/sweep)

### Device Settings
- Upload, play, and manage startup sounds
- Set/clear startup sound with progress tracking
- Configure Bluetooth audio settings
- View device diagnostics and Pi connection status

### Animations & Transitions
- **Pulse**: Breathing logo animation during connection
- **Swoop**: 3x zoom transition on successful connection
- **Static Fade**: Tuning effect when switching investigation modes
- **Slide**: Dial-turning effect for settings navigation

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

## Pi Setup (oraclebox_merged.py)

1. Copy `oraclebox_merged.py` to your Raspberry Pi at `/home/dylan/oraclebox/`.
2. Create directory structure:
   ```bash
   mkdir -p /home/dylan/oraclebox/announcements
   mkdir -p /home/dylan/oraclebox/sounds
   ```
3. Copy voice announcement files to `/home/dylan/oraclebox/announcements/`:
   - `choose_method.wav`
   - `spirit_box.wav`
   - `rempod.wav`
   - `music_box.wav`
4. Ensure Bluetooth SPP is enabled and the Pi is discoverable/pairable.
5. Start the script so it exposes the SPP service with UUID `00001101-0000-1000-8000-00805F9B34FB` and service name `OracleBox`.
6. Pair the Pi with your Android device before opening the app.

### Voice File Generation
To regenerate voice announcements with vintage radio effects:
```bash
espeak-ng -v en -p 5 -s 70 -w [file]_raw.wav "[text]"
sox [file]_raw.wav -r 48000 -c 2 [file].wav tempo 1.0 \
  echo 0.8 0.9 100 0.5 echo 0.8 0.9 150 0.4 reverb 70 40 100 90 gain 10
rm [file]_raw.wav
```
Parameters: low pitch (5), slow speed (70 wpm), dual echo layers, 70% reverb, +10dB gain

## App Flow

### Connection Flow
1. **Launch App** → Auto-connects to saved device (if available) with pulsing logo animation
2. **Connection Screen** → Enable Bluetooth, refresh paired devices, tap OracleBox to connect
3. **Swoop Transition** → Successful connection triggers 3x zoom animation to Mode Selection

### Investigation Flow
1. **Mode Selection Hub** → Voice announces "Choose Your Investigation Method"
2. **Select Mode Card** → Tap Spirit Box/REM Pod/Music Box (announces mode name)
3. **Mode Page** → Press START button to begin investigation
4. **Active Investigation** → Controls appear, real-time status updates, LED management
5. **Back Navigation** → Return to Mode Selection with static fade transition

### Pages Overview
- **ConnectionActivity**: Bluetooth pairing and device connection with auto-connect
- **ModeSelectionActivity**: Central hub with voice-guided mode selection
- **ControlActivity**: Spirit Box controller with sweep controls and LED management
- **RemPodActivity**: REM Pod mode controller (in development)
- **MusicBoxActivity**: Music Box mode controller (in development)
- **DeviceSettingsActivity**: Startup sounds, Bluetooth audio, device diagnostics

### Voice Announcements
- `choose_method.wav` - Plays when entering Mode Selection
- `spirit_box.wav` - Announces Spirit Box mode
- `rempod.wav` - Announces REM Pod mode
- `music_box.wav` - Announces Music Box mode
- All announcements use vintage radio effects (echo, reverb, gain)

## Configuration

### Bluetooth
- To change the OracleBox UUID, edit `BluetoothClient.ORACLEBOX_UUID` in `app/src/main/java/com/apx/oraclebox/bt/BluetoothClient.kt`
- Default UUID: `00001101-0000-1000-8000-00805F9B34FB` (standard SPP UUID)

### App Settings
- Permissions and SDK versions: `AndroidManifest.xml` and `app/build.gradle.kts`
- Animation durations: `app/src/main/res/anim/*.xml` (default: 300-500ms)
- Color theme: Gothic Gold (#D7B972), Ghost Surface, Bakelite accents
- Layout spacing: 22dp before logo, 72dp logo size, 18sp text

### Sound Directories on Pi
- **Announcements**: `/home/dylan/oraclebox/announcements/` (system files, read-only from app)
- **User Sounds**: `/home/dylan/oraclebox/sounds/` (uploadable via Device Settings)

## Troubleshooting

### Build Issues
- **AccessDenied on Windows**: Close Android Studio windows pointing at `app/build`, delete `app/build` manually, run `./gradlew clean` and retry
- **Gradle sync failures**: Ensure Java 17 toolchain is installed and configured
- **Missing dependencies**: Run `./gradlew --refresh-dependencies`

### Connection Issues
- **Device not found**: Confirm Pi is paired in Android Bluetooth settings
- **Connection fails**: Verify `oraclebox_merged.py` is running on Pi with correct UUID
- **Auto-connect not working**: Check if device MAC address is saved (disconnect/reconnect once)
- **Connection drops**: Ensure Pi Bluetooth service is stable, check system logs

### Voice Announcements
- **No sound on announcements**: Verify `/home/dylan/oraclebox/announcements/` directory exists with all 4 WAV files
- **Announcements too fast/slow**: Regenerate with adjusted `tempo` parameter in sox command
- **Poor audio quality**: Check 48kHz sampling rate and stereo channel configuration

### UI Issues
- **Logo not displaying**: Verify `@mipmap/sqlogo_foreground` resource exists
- **Back button not working**: Check activity launch modes and transition animations
- **Controls hidden after start**: This is intentional - press START button to show controls

## Future Plans

### Audio Pipeline
- Route audio through USB interface for band-pass filtering (600-3500 Hz)
- Implement portal-style reverb/chorus effects
- Accept external sweep sources (SB7 headphone out) as input for processing
- Add real-time audio visualization in app

### Investigation Modes
- **REM Pod Mode**: Complete implementation with EMF detection visualization
- **Music Box Mode**: Complete implementation with trigger detection
- Add EVP analysis mode with waveform display
- Implement session timeline with marked events

### Recording & Analysis
- Session recording: `RECORD START/STOP/STATUS` commands
- Capture USB input to timestamped WAV/FLAC files
- In-app playback of recorded sessions
- Event marking and annotation during investigation
- Export sessions with metadata

### UI Enhancements
- Effects stack controls once Pi audio pipeline is ready
- Preset management for LED patterns and sweep configurations
- Custom color themes and layout options
- Investigation session history viewer
- Multi-device support (connect to multiple OracleBoxes)

### Hardware Integration
- Support for additional sensors (temperature, humidity, barometric pressure)
- External trigger inputs (motion sensors, laser grids)
- Integration with other paranormal investigation equipment
- Wireless mesh networking for multi-room investigations

## Documentation

- **APP_REVIEW_SUMMARY.md**: Complete layout and code review
- **ANDROID_PRESET_IMPLEMENTATION.md**: Preset system documentation
- **FM_AUDIO_FIX_SUMMARY.md**: Audio pipeline fixes and improvements
- **FX_PRESET_SYSTEM.md**: Effects preset system documentation
- **VOICE_ANNOUNCEMENTS_NEEDED.md**: Voice system requirements and generation process
