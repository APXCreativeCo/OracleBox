# ESP32 REM-Pod Satellite (REM-Pod v3 Style)

Arduino IDE firmware for ESP32-based REM-Pod paranormal detection device with EM field sensing, temperature monitoring, and 5-LED visual feedback system.

---

## Quick Start

### 1. Install Required Libraries

Open Arduino IDE → **Tools** → **Manage Libraries**, then install:

- **ArduinoJson** by Benoit Blanchon (v7.x)
- **Adafruit BMP280 Library** by Adafruit
- **Adafruit Unified Sensor** by Adafruit

### 2. Board Configuration

- **Board:** ESP32 Dev Module
- **Upload Speed:** 115200
- **CPU Frequency:** 240MHz
- **Flash Size:** 4MB
- **Partition Scheme:** Default
- **Port:** COM3 (or your CP2102 port)

### 3. Upload Firmware

1. Open `esp32-rempod-arduino.ino` in Arduino IDE
2. Connect ESP32 via USB (CP2102)
3. Select correct COM port
4. Click **Upload**
5. Open **Serial Monitor** (115200 baud) to view startup sequence

**Note:** Serial output is only available during the startup/debug phase. After calibration begins, Serial is disabled to free GPIO1 (TX0) for LED5_BLUE control.

---

## Hardware Pinout

### ESP32 Dev Module (38-pin) Pin Mapping

#### LEFT SIDE (Odd Pins)
```
Pin 1  - EN             : UNUSED
Pin 3  - GPIO36         : UNUSED (input-only)
Pin 5  - GPIO39         : UNUSED (input-only)
Pin 7  - GPIO35         : UNUSED (input-only)
Pin 9  - GPIO34         : UNUSED (input-only)
Pin 11 - GPIO32         : LED1 RED (front-left)
Pin 13 - GPIO33         : LED1 GREEN (front-left)
Pin 15 - GPIO25         : LED1 BLUE (front-left)
Pin 17 - GPIO26         : LED2 RED (back-left)
Pin 19 - GPIO27         : Active Buzzer +
Pin 21 - GPIO14         : LED2 GREEN (back-left)
Pin 23 - GPIO12         : AT42QT1011 LED output
Pin 25 - GPIO13         : LED2 BLUE (back-left)
Pin 27 - GND            : Battery -, LEDs -, Buzzer -, Sensors GND
Pin 29 - VIN            : Battery + (AA pack)
```

#### RIGHT SIDE (Even Pins)
```
Pin 2  - GPIO23         : LED3 RED (front-right)
Pin 4  - GPIO22         : BMP280 SCL (I2C)
Pin 6  - GPIO01 (TX0)   : LED5 BLUE (center) - only after Serial.end()
Pin 8  - GPIO03 (RX0)   : UNUSED (leave free)
Pin 10 - GPIO21         : BMP280 SDA (I2C)
Pin 12 - GPIO19         : LED3 GREEN (front-right)
Pin 14 - GPIO18         : LED3 BLUE (front-right)
Pin 16 - GPIO05         : LED4 RED (back-right)
Pin 18 - GPIO17         : LED4 GREEN (back-right)
Pin 20 - GPIO16         : LED4 BLUE (back-right)
Pin 22 - GPIO04         : AT42QT1011 OUTPUT (main REM detect)
Pin 24 - GPIO02         : LED5 RED (center "main dome")
Pin 26 - GPIO15         : LED5 GREEN (center)
Pin 28 - GND            : Shared ground rail
Pin 30 - 3V3            : AT42 VDD + BMP280 VCC
```

### Power Connections
- **VIN (Pin 29):** Battery pack positive (+)
- **GND (Pins 27/28):** Battery pack negative (-), all LED cathodes, buzzer negative, sensor grounds
- **3V3 (Pin 30):** Powers AT42QT1011 and BMP280 sensors (onboard regulator from VIN)

---

## Sensor Wiring

### AT42QT1011 (SparkFun Capacitive Touch Breakout)

**Purpose:** EM/REM field detection via capacitive sensing with telescopic antenna

| AT42 Pin | ESP32 Pin | Description |
|----------|-----------|-------------|
| VDD | 3V3 (Pin 30) | Power supply |
| GND | GND (Pin 28) | Ground |
| OUT | GPIO4 (Pin 22) | Main detection output (HIGH when field detected) |
| LED | GPIO12 (Pin 23) | Mirror of onboard LED |
| PAD | External antenna | Telescopic antenna (not connected to ESP32) |

### GY-BMP280 (Temperature + Pressure Sensor)

**Purpose:** Environmental monitoring for temperature deviations

| BMP280 Pin | ESP32 Pin | Description |
|------------|-----------|-------------|
| VCC | 3V3 (Pin 30) | Power supply |
| GND | GND (Pin 28) | Ground |
| SCL | GPIO22 (Pin 4) | I2C clock |
| SDA | GPIO21 (Pin 10) | I2C data |
| CSB | Not connected | Leave floating (I2C mode) |
| SDO | Not connected | Leave floating |

---

## RGB LED Layout

The REM-Pod uses **5 full RGB LEDs** (common-cathode) arranged around the device:

| LED | Position | Red Pin | Green Pin | Blue Pin |
|-----|----------|---------|-----------|----------|
| **LED1** | Front-Left | GPIO32 | GPIO33 | GPIO25 |
| **LED2** | Back-Left | GPIO26 | GPIO14 | GPIO13 |
| **LED3** | Front-Right | GPIO23 | GPIO19 | GPIO18 |
| **LED4** | Back-Right | GPIO5 | GPIO17 | GPIO16 |
| **LED5** | Center "Dome" | GPIO2 | GPIO15 | GPIO1 (TX0)* |

**\*Note:** LED5_BLUE uses GPIO1 (TX0), which is the Serial transmit pin. To avoid flickering during startup, the firmware uses Serial for debug output, then calls `Serial.end()` before calibration to free TX0 for LED control.

**All LED cathodes** connect to GND (Pin 27 or 28).

---

## Startup Sequence (3 Phases)

### Phase 1: Boot + Debug (Serial ON)

**Duration:** ~5 seconds  
**Serial Output:** 115200 baud

The device performs hardware initialization and diagnostics:

1. **Hardware Self-Test**
   - Rainbow sweep across all 5 LEDs
   - White flash confirmation
   - Buzzer chirp test

2. **BMP280 Initialization**
   - I2C communication test
   - Sensor configuration
   - Error handling if not found

3. **AT42QT1011 Check**
   - Read initial OUT state
   - Confirm sensor ready

4. **WiFi Connection Attempt**
   - Connect to "OracleBox-Network"
   - **Success:** Green flash on all LEDs + single beep
   - **Failure:** Red flash on all LEDs + double beep (continues in standalone mode)

5. **Battery Level Check**
   - Display current battery percentage
   - Log to Serial Monitor

---

### Phase 2: Calibration (Serial OFF)

**Duration:** 8 seconds  
**Serial Output:** Disabled after this phase begins

```
[OK] Calibration starting, disabling Serial output...
```

After this message, `Serial.end()` is called to free TX0 (GPIO1) for LED5_BLUE.

**What Happens:**
- **Environmental Baseline Sampling:**
  - BMP280 temperature and pressure averaged over calibration window
  - AT42 noise level monitoring
  - Establishes thresholds for deviation detection

- **LED Animation During Calibration:**
  - **Outer LEDs (1-4):** Breathing teal/purple wave pattern
  - **Center LED (5):** Rotating hue scan (red → green → blue → red)

- **Completion Signal:**
  - Brief green pulse on all LEDs
  - Transition to armed state

---

### Phase 3: Armed / Idle

**Visual State:** Center LED (LED5) glows dim purple (10,0,10)

**Behavior:**
- Outer LEDs (1-4) remain off
- Center LED shows subtle "heartbeat" pulse every 2 seconds
- Device is now actively monitoring for REM field triggers and temperature deviations
- Ready beeps (double chirp)

---

## REM Field Detection (AT42QT1011)

### How It Works

The AT42QT1011 capacitive touch sensor is connected to a telescopic antenna, creating a proximity/EM field detector similar to commercial REM-Pods.

**Detection Logic:**
1. ESP32 polls AT42 OUT pin (GPIO4) every **30ms**
2. **HIGH state:** `triggerCount++` (max 10)
3. **LOW state:** `triggerCount--` (min 0)
4. **Trigger threshold:** `triggerCount >= 3`
5. **Strength mapping:** triggerCount → 1-10 scale
6. **Cooldown:** 2 seconds between events

### Visual Response by Strength

#### Low Strength (1-3)
- **LEDs:** Center (LED5) + Front-Left (LED1) flicker purple
- **Pattern:** 5 flickers, 50ms on/off
- **Buzzer:** 100-200ms tone

#### Medium Strength (4-6)
- **LEDs:** Center (LED5) + Front-Left (LED1) + Back-Left (LED2) flicker red
- **Pattern:** 8 flickers, 40ms on/off
- **Buzzer:** 300-500ms tone

#### High Strength (7-10)
- **LEDs:** All 5 LEDs flicker bright purple
- **Pattern:** 12 flickers, 30ms on/off
- **Buzzer:** 600-800ms tone

### Hub Communication

When REM event triggers, device sends JSON via WiFi (if connected):

```json
{
  "device": "rempod",
  "id": "rempod_01",
  "location": "hallway",
  "event": "em_trigger",
  "strength": 7,
  "temperature": 68.5,
  "pressure": 1013.25,
  "battery": 85,
  "timestamp": 12345
}
```

---

## Temperature Deviation Detection (BMP280)

### How It Works

BMP280 monitors ambient temperature every **5 seconds** and compares to baseline established during calibration.

**Trigger Condition:** `|currentTemp - baselineTemp| >= 2.0°F`

**Temperature is in Fahrenheit** (converted from BMP280's Celsius output)

### Visual Response (LED-Only, No Buzzer)

#### Cooling Event (Temp Drop ≥2°F)
- **Color:** Blue/Cyan flashes
- **Pattern:** 
  - Outer LEDs (1-4): Cyan (0, 100, 255)
  - Center LED (5): Bright blue (0, 150, 255)
  - 6 flashes, 150ms on/off
- **Purpose:** Indicates potential paranormal "cold spot"

#### Warming Event (Temp Rise ≥2°F)
- **Color:** Orange/Red flashes
- **Pattern:**
  - Outer LEDs (1-4): Orange (255, 100, 0)
  - Center LED (5): Orange-red (255, 50, 0)
  - 6 flashes, 150ms on/off
- **Purpose:** Indicates environmental temperature increase

### Hub Communication

Temperature deviation events send JSON:

```json
{
  "device": "rempod",
  "id": "rempod_01",
  "location": "hallway",
  "event": "temp_deviation",
  "strength": 25,
  "temperature": 66.3,
  "pressure": 1013.25,
  "battery": 85,
  "timestamp": 12346
}
```

**Note:** `strength` field contains `abs(tempDelta) * 10` (e.g., 2.5°F deviation = strength 25)

---

## Configuration

### Device Identity

Edit at top of `.ino` file:

```cpp
#define DEVICE_ID "rempod_01"      // Change for multiple units
#define LOCATION "hallway"         // Physical location
```

### Detection Sensitivity

```cpp
// REM Detection
#define AT42_POLL_INTERVAL 30       // ms between checks (lower = more responsive)
#define TRIGGER_THRESHOLD 3         // triggerCount needed to fire event (lower = more sensitive)
#define MAX_TRIGGER_COUNT 10        // max strength level
#define COOLDOWN_TIME 2000          // ms between REM events

// Temperature
#define TEMP_CHECK_INTERVAL 5000    // ms between temp checks
#define TEMP_DEVIATION_THRESHOLD 2.0  // °F deviation to trigger event (lower = more sensitive)
```

### WiFi/Hub Settings

```cpp
#define WIFI_SSID "OracleBox-Network"
#define WIFI_PASSWORD "yourpassword"
#define HUB_IP "192.168.4.1"
#define HUB_PORT 8888
```

### Calibration Time

```cpp
#define CALIBRATION_TIME 8000       // ms calibration window (default 8 seconds)
```

---

## Standalone Operation

The REM-Pod is designed to work **completely standalone** without WiFi or a hub:

- ✅ REM field detection works independently
- ✅ Temperature monitoring works independently  
- ✅ LED visual feedback always active
- ✅ Buzzer alerts always active
- ✅ Battery monitoring continues
- ⚠️ JSON events only sent if WiFi available (silent failure if not)

**Use Case:** Deploy in remote locations without network infrastructure. All detection features remain fully functional.

---

## Troubleshooting

### Serial Monitor Shows Nothing After "Calibration starting..."

**This is normal!** Serial is intentionally disabled after calibration to free GPIO1 (TX0) for LED5_BLUE control. If you need debug output during operation, comment out the `Serial.end()` line (but LED5_BLUE will flicker).

### BMP280 Not Found Error

**Check Wiring:**
- VCC → 3V3 (Pin 30)
- GND → GND (Pin 28)
- SCL → GPIO22 (Pin 4)
- SDA → GPIO21 (Pin 10)

**I2C Address:** Firmware tries `0x76`. If your module uses `0x77`, change in code:
```cpp
if (!bmp.begin(0x77)) {  // Try 0x77 instead
```

### AT42 Always Triggering / Never Triggering

**Calibration Issue:**
- Ensure area is clear during 8-second calibration
- Keep hands/objects away from antenna
- If noise is too high, increase `TRIGGER_THRESHOLD` in config

**Antenna Connection:**
- Verify antenna is connected to AT42 PAD terminal
- Antenna should be ~12" telescopic whip for best sensitivity

### LED5 (Center LED) Blue Channel Not Working

**TX0 Conflict:**
- Make sure `Serial.end()` is called during calibration
- If you added debug code that re-enables Serial, LED5_BLUE will conflict
- Verify GPIO1 is set to OUTPUT mode after `Serial.end()`

### WiFi Won't Connect

**Standalone Mode:**
- Device will flash red LEDs + double beep
- Continues operating without hub connection
- All detection features still work locally

**To Fix:**
- Verify "OracleBox-Network" SSID is broadcasting
- Check password in `WIFI_PASSWORD` define
- Ensure ESP32 is in range of WiFi AP

### Random False REM Triggers

**Electromagnetic Interference:**
- Keep away from power supplies, motors, fluorescent lights
- Increase `TRIGGER_THRESHOLD` from 3 to 5 or higher
- Increase `COOLDOWN_TIME` to reduce sensitivity

**Antenna Positioning:**
- Ensure antenna is isolated from metal surfaces
- Keep REM-Pod at least 6" away from walls/furniture

### Temperature Readings Incorrect

**BMP280 Calibration:**
- Allow 10+ minutes for sensor to stabilize after power-on
- BMP280 may self-heat slightly, causing +1-2°F offset
- Compare readings with known accurate thermometer and adjust baseline manually if needed

---

## Battery Management

### Current Implementation

Firmware includes **simulated battery drain** for testing:

```cpp
int readBattery() {
  static int simBattery = 100;
  simBattery -= random(0, 2);
  if (simBattery < 0) simBattery = 0;
  return simBattery;
}
```

### Adding Real Battery Monitoring

To implement actual voltage sensing:

1. Add voltage divider to GPIO34 (input-only pin):
   ```
   Battery + ──[10kΩ]──┬── GPIO34
                        │
                     [10kΩ]
                        │
                       GND
   ```

2. Uncomment/modify `readBattery()`:
   ```cpp
   int readBattery() {
     int rawValue = analogRead(34);
     float voltage = (rawValue / 4095.0) * 3.3 * 2; // *2 for voltage divider
     int percent = map(voltage * 100, 320, 420, 0, 100); // 3.2V-4.2V range
     return constrain(percent, 0, 100);
   }
   ```

### Low Battery Warning

When battery drops below 20%:
- Center LED pulses dim yellow (50, 50, 0)
- Sends `"low_battery"` event to hub (if connected)

---

## LED Behavior Summary

| State | Outer LEDs (1-4) | Center LED (5) | Buzzer |
|-------|------------------|----------------|---------|
| **Startup Test** | Rainbow sweep | Rainbow sweep | 2 chirps |
| **WiFi Connected** | Green flash | Green flash | 1 beep |
| **WiFi Failed** | Red flash | Red flash | 2 beeps |
| **Calibration** | Breathing teal/purple | Rotating hue scan | Silent |
| **Armed/Idle** | Off | Dim purple (10,0,10) + heartbeat | Silent |
| **REM Low (1-3)** | LED1 purple flicker | Purple flicker | 100-200ms |
| **REM Mid (4-6)** | LED1+2 red flicker | Red flicker | 300-500ms |
| **REM High (7-10)** | All bright purple flicker | Bright purple flicker | 600-800ms |
| **Temp Drop** | Cyan flash | Bright blue pulse | Silent |
| **Temp Rise** | Orange flash | Orange-red pulse | Silent |
| **Low Battery** | Off | Dim yellow pulse | Silent |

---

## Advanced: Hub Integration

### JSON Event Format

All events sent to hub follow this schema:

```json
{
  "device": "rempod",           // Always "rempod"
  "id": "rempod_01",            // Device ID (configurable)
  "location": "hallway",        // Location string (configurable)
  "event": "<event_type>",      // See event types below
  "strength": <0-10>,           // Event intensity (0 for temp events)
  "temperature": <float>,       // Current temp in °F
  "pressure": <float>,          // Current pressure in hPa
  "battery": <0-100>,           // Battery percentage
  "timestamp": <int>            // Seconds since boot
}
```

### Event Types

| Event | Description | Strength Value |
|-------|-------------|----------------|
| `em_trigger` | REM/EM field detection | 1-10 (proximity strength) |
| `temp_deviation` | Temperature change | `abs(tempDelta) * 10` |
| `low_battery` | Battery below threshold | 0 |

### TCP Protocol

- **Host:** 192.168.4.1 (default hub IP)
- **Port:** 8888
- **Protocol:** TCP socket
- **Format:** Single-line JSON string + newline
- **Timeout:** 1 second connection timeout
- **Error Handling:** Silent failure, continues standalone operation

---

## Performance Characteristics

- **AT42 Poll Rate:** 30ms (33 checks/second)
- **Temp Check Rate:** 5 seconds
- **Battery Check Rate:** 60 seconds
- **REM Cooldown:** 2 seconds minimum between events
- **Calibration Time:** 8 seconds on boot
- **WiFi Timeout:** 3 seconds (10 × 300ms attempts)

---

## Comparison to Commercial REM-Pod v3

| Feature | Commercial REM-Pod v3 | ESP32 REM-Pod Satellite |
|---------|----------------------|------------------------|
| **EM Field Detection** | Proprietary radiating antenna | AT42QT1011 capacitive + telescopic antenna |
| **Visual Feedback** | 5-LED graduated proximity | 5 full RGB LEDs (15 colors) |
| **Audio Alert** | Beeping alarm | Active buzzer with variable duration |
| **Temperature Sensing** | Optional (some models) | Built-in BMP280 with deviation alerts |
| **Data Logging** | None (standalone only) | WiFi + JSON hub integration |
| **Battery** | 9V alkaline | AA pack (4-6 cells recommended) |
| **Calibration** | Manual button | Automatic 8-second boot sequence |
| **Portability** | Handheld design | Modular satellite for multi-room deployment |

---

## Future Enhancements

Possible additions for next firmware revision:

- [ ] **EMF Sensor Integration:** Add dedicated EMF meter (e.g., AS3935 lightning sensor for EM detection)
- [ ] **SD Card Logging:** Log all events to microSD for offline analysis
- [ ] **OLED Display:** Show current temp, battery, trigger count in real-time
- [ ] **Adjustable Sensitivity:** Rotary encoder or buttons to change thresholds without reprogramming
- [ ] **Multi-Color Modes:** Customizable LED color schemes for different investigation types
- [ ] **Sound Recording Trigger:** Activate recording device via relay when REM event occurs
- [ ] **Mesh Network:** ESP-NOW protocol for peer-to-peer REM-Pod communication without WiFi

---

## Credits & Licensing

**Hardware Platform:** Espressif ESP32 Dev Module  
**Sensor Libraries:** Adafruit Industries (BMP280 drivers)  
**JSON Handling:** ArduinoJson by Benoit Blanchon  
**Inspired By:** REM-Pod v3 by Digital Dowsing LLC

**License:** Open source for personal/educational use. Commercial deployment requires separate licensing for REM-Pod trademark compliance.

---

## Support

For issues, questions, or contributions:

- **Repository:** APXCreativeCo/OracleBox
- **Documentation:** See `PROJECT_STRUCTURE.md` and `ORGANIZATION_GUIDE.md` in repo root
- **Architecture:** See `CHATGPT_ARCHITECTURE_ANSWERS.txt` for system design Q&A

**Hardware Questions:** Verify wiring against pinout diagram in this README  
**Software Issues:** Check Serial Monitor output during Phase 1 (before calibration)  
**Detection Problems:** Review Troubleshooting section above

---

**Ready to hunt ghosts with science.** 👻⚡
