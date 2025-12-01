# ESP32 Music Box - Arduino IDE Version

**Hardware:** ESP32 Dev Module with CP2102 USB

## Quick Start

### 1. Install ArduinoJson Library
1. Open Arduino IDE 2.x
2. Go to **Tools → Manage Libraries**
3. Search for "ArduinoJson"
4. Install **ArduinoJson by Benoit Blanchon** (v7.x or latest)

### 2. Board Settings
1. Go to **Tools** menu and configure:
   - **Board:** "ESP32 Dev Module"
   - **Upload Speed:** 115200
   - **CPU Frequency:** 240MHz (WiFi/BT)
   - **Flash Size:** 4MB (32Mb)
   - **Partition Scheme:** Default 4MB with spiffs
   - **Port:** COM3 (or your CP2102 port)

### 3. Upload Firmware
1. Open `esp32-musicbox-arduino.ino` in Arduino IDE
2. Click **Upload** button (right arrow)
3. Wait for "Done uploading" message

### 4. Monitor Output
1. Go to **Tools → Serial Monitor**
2. Set baud rate to **115200**
3. You should see:
   ```
   >>> Music Box Satellite Starting...
   [*] Connecting to WiFi: OracleBox-Network
   ...
   [WARN] WiFi unavailable - operating standalone
   [OK] Music Box ready
   Device ID: musicbox_01
   Location: bedroom
   Melody: rosie
   
   [TIP] Wave hand over PIR sensor to trigger melody!
   ```

### 5. Test Hardware
- **Solid red LED** when idle (always on)
- **Wave hand over PIR sensor** (GPIO4) to trigger melody
- **RGB LED effects** change based on motion strength:
  - Quick pass: soft blue/purple fade
  - Lingering (3-8s): rainbow with red pulses
  - Very close (>8s): intense white strobes + red flicker
- **Buzzer** plays selected melody (default: Ring Around the Rosie)

## Pinout Reference

```
ESP32 Dev Module
================
GPIO27 ──→ Passive Buzzer (+ leg)
GPIO14 ──→ RGB LED Red
GPIO26 ──→ RGB LED Green
GPIO25 ──→ RGB LED Blue
GPIO4  ──→ PIR Sensor OUT (AM312)
3V3    ──→ PIR Sensor VCC
GND    ──→ PIR GND + RGB LED common cathode + Buzzer GND
VIN    ──→ AA Battery Pack + (through switch)
```

## Configuration

Edit these lines at the top of the .ino file:

```cpp
// Available melodies: "rosie", "twinkle_star", "lullaby", "carousel", 
//                     "creepy_doll", "weasel", "tiptoe", "oracle_waltz", "oracle_heartbeat"
#define MELODY "rosie"

// PIR cooldown time (ms)
#define PIR_HOLDTIME 5000

// WiFi settings (optional - device works standalone)
#define WIFI_SSID "OracleBox-Network"
#define WIFI_PASSWORD "yourpassword"
```

### Available Melodies
- **rosie** - Ring Around the Rosie (classic creepy)
- **oracle_waltz** - Original OracleBox theme (unsettling waltz)
- **oracle_heartbeat** - Short ominous chime pattern
- **lullaby** - Brahms Lullaby (slow/creepy)
- **carousel** - Repetitive music box tune
- **weasel** - Pop Goes the Weasel
- **tiptoe** - Tiptoe Through the Tulips
- **creepy_doll** - Descending melody box
- **twinkle_star** - Twinkle Twinkle Little Star

## Motion Strength System

The Music Box analyzes **how long the PIR sensor stays HIGH** and adapts RGB effects accordingly:

### Weak Trigger (< 3 seconds)
- **Behavior:** Quick pass-by, brief motion
- **LED Effect:** Soft blue/purple fade (calming, low intensity)
- **Use Case:** Someone walking past quickly

### Strong Trigger (3-8 seconds)
- **Behavior:** Lingering presence nearby
- **LED Effect:** Rainbow fade with red pulses every 3 notes
- **Use Case:** Someone standing in front of the box

### Extra-Strong Trigger (> 8 seconds)
- **Behavior:** Very close or prolonged presence
- **LED Effect:** Aggressive white strobes (every 4 notes) + fast red/orange flicker
- **Auto-Loop:** Melody replays immediately if PIR still HIGH
- **Use Case:** Something right in front of the sensor

## Startup Sequence

The device runs a 3-stage diagnostic on power-up:

1. **Hardware Check** - Cyan pulses + chirp tones
2. **Hub Connection** - Green (online) or Red flashes (offline)
3. **Battery Level** - Color-coded indicator:
   - Green: >75% (full)
   - Cyan: 50-75% (good)
   - Yellow: 25-50% (low)
   - Red flashing: <25% (critical)

## Standalone Operation

The Music Box **works completely without WiFi or hub**:
- ✅ PIR motion detection
- ✅ Melody playback
- ✅ RGB LED effects
- ✅ Strength-based responses
- ✅ Serial logging

WiFi/Hub features are **optional** and used only when available.

## Troubleshooting

**Upload fails:**
- Check COM port is correct (Tools → Port)
- Press and hold BOOT button while clicking Upload
- Try lower upload speed (115200)

**LED not solid red when idle:**
- Check 3.3V power is stable
- Verify ESP32 is running (Serial Monitor shows output)
- Red LED should be ON continuously when no motion detected

**PIR not triggering:**
- Check PIR VCC connected to 3V3 (not 5V)
- Wait 30 seconds after power-on for PIR to calibrate
- Check PIR OUT connected to GPIO4

**Buzzer silent:**
- Check passive buzzer (not active - no built-in oscillator)
- Verify buzzer + to GPIO27, - to GND
- Try different buzzer if available

**RGB LED not working:**
- Verify common-cathode RGB (shared GND, not shared +)
- Check wiring: R=GPIO14, G=GPIO26, B=GPIO25
- Test individual colors by changing code

**Strength effects not working:**
- Open Serial Monitor to see duration measurements
- Try holding hand in front of sensor for different lengths of time
- Check PIR sensitivity adjustment on sensor module

## Next Steps

Once hardware is verified:
1. Set up OracleBox Pi hub with WiFi hotspot
2. Configure WiFi credentials in code
3. Upload and test hub communication
4. View JSON events in Pi logs with strength data
5. Try different melodies to find your favorite creepy tune!
