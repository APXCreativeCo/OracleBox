# OracleBox Ghost Hunting Hub

Android app to control a complete wireless paranormal investigation system built around a Raspberry Pi hub with ESP32-based satellite sensors.

## System Architecture

### OracleBox Hub (Raspberry Pi)
- **TEA5767 FM tuner** via I2C (`/dev/i2c-1`, addr `0x60`) for Spirit Box/SB7 sweep mode
- **GPIO-controlled LEDs**: Sweep LED (GPIO 17) and Box LED (GPIO 27) with multiple animation modes
- **Audio processing**: Real-time FX pipeline (bandpass filters, contrast, reverb, gain) via USB audio interface
- **WiFi Access Point**: Creates isolated hotspot for satellite device mesh network (no internet required)
- **Bluetooth RFCOMM**: Classic Bluetooth SPP for Android app control
- **Voice announcements**: Text-to-speech with vintage radio effects for investigation guidance
- **Event logging**: Captures and timestamps all sensor triggers from satellite devices

### Satellite Devices (ESP32-based)
The OracleBox acts as the "brain" coordinating wireless "sensor" devices that connect to its WiFi hotspot:

**REM-Pod Satellite**
- ESP32 microcontroller with WiFi
- SparkFun AT42QT1011 capacitive sensor (real REM-Pod EM field detection)
- Telescopic antenna for field sensitivity
- BMP280 sensor for temperature deviation alerts
- Active buzzer + LED indicators
- Battery powered for portable placement
- Transmits: EM field hits, strength levels (0-10), temperature anomalies

**Music Box Satellite**
- ESP32 microcontroller with WiFi
- AM312 PIR motion sensor
- Passive buzzer plays creepy chime melodies on trigger
- Battery powered for portable placement
- Transmits: Motion detection events with timestamps

### Android Controller (This App)
- Issues textual commands over classic Bluetooth (`STATUS`, `LED`, `SOUND`, `FX`, etc.)
- Voice-guided, vintage radio-themed UI for investigation modes
- Real-time monitoring of satellite sensor network
- Displays EM field graphs, motion events, and temperature deviations
- Voiced alerts: *"REM-Pod trigger — strength 3"* or *"Music Box activated in hallway"*

### Communication Flow
```
Android App <--Bluetooth--> Raspberry Pi Hub <--WiFi Mesh--> ESP32 Satellites
                            (OracleBox)            (REM-Pod, Music Box)
```

The Pi creates a WiFi hotspot, satellites connect directly — no router or internet needed. Perfect for investigating remote locations.

## Python Daemon (`oraclebox.py`)

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
- **Wireless Sensor Network**: Monitor ESP32 satellite devices (REM-Pod, Music Box) via Pi WiFi mesh
- **Voice Alerts**: Spoken notifications for sensor triggers - *"REM-Pod trigger — strength 3"* or *"Music Box activated in hallway"*
- **Multiple Investigation Modes**: Spirit Box, REM Pod monitoring, Music Box monitoring accessible from central hub
- **Event Logging**: Unified timeline of all sensor activity across Spirit Box and satellite devices
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
- **FX Controls with Real-Time Feedback**: All sliders display current values in gold text
  - **Bandpass Filters**: Low (200-1000 Hz) and High (2000-4000 Hz) with live Hz display
  - **Contrast**: Audio sharpening (0-50) for enhanced clarity
  - **Reverb**: Spacious echo effect (0-60) for ghostly atmosphere
  - **Output Gain**: Final volume boost/cut (-12 to +12 dB)
  - **Educational Descriptions**: Each slider includes plain-English explanation of its effect
- **Mixer Controls**: Speaker and microphone volume with real-time value displays

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

## Pi Setup (oraclebox.py)

1. Copy `oraclebox.py` to your Raspberry Pi at `/home/dylan/oraclebox/`.
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
- **Connection fails**: Verify `oraclebox.py` is running on Pi with correct UUID
- **Auto-connect not working**: Check if device MAC address is saved (disconnect/reconnect once)
- **Connection drops**: Ensure Pi Bluetooth service is stable, check system logs

### Voice Announcements
- **No sound on announcements**: Verify `/home/dylan/oraclebox/announcements/` directory exists with all 4 WAV files
- **Announcements too fast/slow**: Regenerate with adjusted `tempo` parameter in sox command
- **Poor audio quality**: Check 48kHz sampling rate and stereo channel configuration

### UI Issues
- **Logo not displaying**: Verify `@mipmap/sqlogo_foreground` resource exists
- **Back button not working**: Check activity launch modes and transition animations
- **Button state bugs**: Fixed - buttons now sync with device state via observer pattern (no manual toggling)
- **Slider values not visible**: Fixed - all sliders show real-time values in gold text with proper units

## Future Plans

### Audio Pipeline
- Add real-time audio visualization in app

### Investigation Modes & Satellite Integration
- **REM Pod Mode**: Real-time EM field strength visualization from ESP32 satellite
  - Graph display of field strength (0-10 scale)
  - Temperature deviation alerts from BMP280 sensor
  - Voice announcements for trigger events with strength levels
  - Multiple REM-Pod support with location labels
- **Music Box Mode**: Motion detection monitoring from ESP32 satellite
  - Event timeline showing trigger timestamps and locations
  - Visual indicator when chime melody is playing
  - Voice announcements for motion events
  - Multiple Music Box support for multi-room coverage
- **EVP Analysis Mode**: Waveform display and playback tools
- **Session Timeline**: Unified view of all sensor events (Spirit Box, REM-Pod, Music Box) with timestamps and annotations

### Recording & Analysis
- Session recording: `RECORD START/STOP/STATUS` commands
- Capture USB input to timestamped WAV/FLAC files
- In-app playback of recorded sessions
- Event marking and annotation during investigation
- Export sessions with metadata

### UI Enhancements
- ~~Effects stack controls once Pi audio pipeline is ready~~ **✅ COMPLETED**: FX controls with real-time value displays and descriptions
- FFT spectrum visualizer above FX sliders for live audio frequency display
- Preset management for LED patterns and sweep configurations
- Custom color themes and layout options
- Investigation session history viewer
- Multi-device support (connect to multiple OracleBoxes)

### Hardware Integration
- **ESP32 Satellite Network**: WiFi mesh with OracleBox as hub/access point
  - REM-Pod satellites with AT42QT1011 EM field sensors + BMP280 temperature
  - Music Box satellites with AM312 PIR motion sensors + chime melodies
  - Battery-powered for flexible placement in investigation areas
  - Auto-reconnect and health monitoring
- **Additional Sensor Support**:
  - Humidity sensors for environmental correlation
  - Laser grid triggers for motion detection
  - EMF meters (Gauss readings)
  - Geiger counter integration for radiation monitoring
- **Expandable Satellite Types**:
  - EVP recorders (distributed audio capture)
  - Static electricity detectors
  - Laser thermometers (temperature grid)
  - Vibration sensors (footstep detection)

## Documentation

- **APP_REVIEW_SUMMARY.md**: Complete layout and code review
- **ANDROID_PRESET_IMPLEMENTATION.md**: Preset system documentation
- **BLUETOOTH_ARCHITECTURE.md**: Bluetooth communication architecture and command protocol
- **FM_AUDIO_FIX_SUMMARY.md**: Audio pipeline fixes and improvements
- **FX_PRESET_SYSTEM.md**: Effects preset system documentation
- **VOICE_ANNOUNCEMENTS_NEEDED.md**: Voice system requirements and generation process

## Recent Updates (November 2025)

### System Architecture Evolution
Expanded from standalone Spirit Box to **complete wireless paranormal sensor network**:
- OracleBox Pi now acts as investigation hub with WiFi access point
- ESP32 satellite devices connect directly to Pi hotspot (no internet/router needed)
- Wireless mesh supports REM-Pod and Music Box satellites (more planned)
- Unified event logging and voice announcements for all sensor triggers

### UI/UX Improvements (Commit bab4084)
- **Button State Synchronization**: Fixed START/STOP/MUTE buttons to rely on status observer instead of manual toggling
- **Real-Time Value Displays**: All FX and mixer sliders now show current values in gold text with proper formatting
  - Bandpass filters display Hz values (200-1000 Hz low, 2000-4000 Hz high)
  - Gain displays dB with +/- sign (-12 to +12 dB)
  - Contrast, Reverb, and Volume display raw numeric values
- **Educational Descriptions**: Added plain-English explanations below each FX slider
- **Visual Depth**: Created `bg_dsilver_bubble_inset.xml` for recessed/sunken UI elements
- **Ghostly Animations**: Added `ghostly_flicker.xml` animation for supernatural atmosphere
- **Button Press Effects**: Created `bg_bakelite_button_pressed.xml` for tactile feedback

### Hardware Development Roadmap
**Phase 1 (Current)**: Spirit Box core with FX controls and LED animations  
**Phase 2 (In Progress)**: WiFi mesh network + REM-Pod satellite prototype  
**Phase 3 (Planned)**: Music Box satellite + multi-device support in app  
**Phase 4 (Future)**: EVP analysis, session recording, expandable satellite types
