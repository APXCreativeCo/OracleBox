# Quick Reference: Project Organization

## ✅ What I Did

1. **Created `firmware/` folder** - ESP32 satellite device code
   - `firmware/esp32-rempod/` - REM-Pod with AT42QT1011 + BMP280
   - `firmware/esp32-musicbox/` - Music Box with AM312 PIR

2. **Created `pi/` folder** - Raspberry Pi hub code
   - Moved all Python scripts here (oraclebox.py, etc.)
   - Moved deploy script and setup instructions

3. **Added README files** for each component with:
   - Hardware specs and pin configurations
   - Setup instructions
   - Protocol documentation
   - Power consumption estimates

4. **Created PROJECT_STRUCTURE.md** - Visual guide to the repo layout

## ✅ Android Build Isolation

Your Android build **will not** touch the firmware or pi folders because:
- `settings.gradle.kts` only includes `:app` module
- Gradle only processes what's explicitly included
- `firmware/` and `pi/` are completely ignored by the build system

You can safely run `./gradlew assembleDebug` and it will only build the Android app.

## 📁 Current Structure

```
OracleBox/
├── app/                    ← Android app (Gradle builds this)
├── firmware/               ← ESP32 code (ignored by Gradle)
│   ├── esp32-rempod/
│   └── esp32-musicbox/
├── pi/                     ← Python daemon (ignored by Gradle)
├── gradle/                 ← Gradle wrapper
├── build.gradle.kts        ← Root build config
└── README.md               ← Main project docs
```

## 🚀 Next Steps

**For REM-Pod:**
1. Open `firmware/esp32-rempod/` in Arduino IDE or PlatformIO
2. Create `src/main.cpp` (or `.ino` if using Arduino IDE)
3. Install libraries: Adafruit_BMP280, ArduinoJson
4. Wire up AT42QT1011, BMP280, buzzer, LEDs per README

**For Music Box:**
1. Open `firmware/esp32-musicbox/` in Arduino IDE or PlatformIO
2. Create `src/main.cpp` (or `.ino`)
3. Install ArduinoJson library
4. Wire up AM312 PIR, passive buzzer, LEDs per README

**For Pi WiFi Hub:**
1. Follow `pi/README.md` to setup WiFi hotspot
2. Add socket server to `oraclebox.py` to receive satellite data
3. Deploy with `pi\deploy_to_pi.ps1`

Ready to start coding the ESP32 firmware? I can help with the Arduino sketches!
