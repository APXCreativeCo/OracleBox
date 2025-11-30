# OracleBox Ghost Hunting Hub - Project Structure

This repository contains all components of the OracleBox wireless paranormal investigation system.

## Directory Structure

```
OracleBox/
├── app/                          # Android controller app
│   ├── src/main/                 # Main application code
│   ├── build.gradle.kts          # App-level build config
│   └── ...
│
├── firmware/                     # ESP32 satellite device firmware
│   ├── esp32-rempod/            # REM-Pod satellite (AT42QT1011 + BMP280)
│   │   ├── src/                 # Arduino sketch
│   │   ├── config.h             # WiFi and device settings
│   │   └── README.md            # Hardware specs and setup
│   │
│   └── esp32-musicbox/          # Music Box satellite (AM312 PIR)
│       ├── src/                 # Arduino sketch
│       ├── config.h             # WiFi and device settings
│       ├── melodies.h           # Chime pattern definitions
│       └── README.md            # Hardware specs and setup
│
├── pi/                           # Raspberry Pi hub daemon
│   ├── oraclebox.py             # Main hub daemon
│   ├── deploy_to_pi.ps1         # Deployment script
│   └── README.md                # Pi setup instructions
│
├── gradle/                       # Gradle wrapper (Android build only)
├── build.gradle.kts              # Root Android build config
├── settings.gradle.kts           # Android project settings
└── README.md                     # This file
```

## Build System Isolation

The Android Gradle build only processes `app/` and `gradle/` directories. The `firmware/` and `pi/` folders are **completely ignored** by the Android build system - they won't interfere with APK compilation.

## Development Workflow

### Android App
```bash
./gradlew assembleDebug          # Build from root directory
./gradlew installDebug           # Works as normal
```

### ESP32 Firmware
```bash
cd firmware/esp32-rempod
# Use Arduino IDE or PlatformIO to compile/upload
```

### Raspberry Pi
```bash
cd pi
.\deploy_to_pi.ps1              # Deploy from Windows
# Or manually: scp, ssh, systemctl restart
```

## Communication Flow

```
Android App <--Bluetooth SPP--> Raspberry Pi Hub <--WiFi Socket--> ESP32 Satellites
   (APK)                         (Python daemon)              (Arduino firmware)
```

## Getting Started

1. **Android App**: Open root folder in Android Studio, build `app/` module
2. **ESP32 Satellites**: Open `firmware/esp32-*/` in Arduino IDE or PlatformIO
3. **Raspberry Pi**: Follow `pi/README.md` for daemon setup and WiFi hotspot configuration

Each component has its own README with detailed setup instructions.
