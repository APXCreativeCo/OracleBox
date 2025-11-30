# ESP32 REM-Pod Satellite

Wireless EM field detector that connects to OracleBox hub via WiFi.

## Hardware Components

- **ESP32 Dev Board** (WiFi enabled)
- **SparkFun AT42QT1011 Capacitive Touch Sensor** - Real REM-Pod field detection
- **Telescopic Antenna** - Connected to AT42QT1011 for sensitivity
- **BMP280 Sensor** - Temperature and barometric pressure monitoring
- **Active Buzzer** - Audible alerts on EM field triggers
- **LEDs** - Visual indicators (idle/trigger/alert states)
- **Battery Pack** - Portable power (18650 or similar)

## Pin Configuration

```
AT42QT1011 OUT → GPIO 34 (input, detects field trigger)
BMP280 SDA     → GPIO 21
BMP280 SCL     → GPIO 22
Active Buzzer  → GPIO 25
LED Status     → GPIO 2 (built-in)
LED Trigger    → GPIO 26
```

## Features

- Connects to OracleBox WiFi hotspot automatically
- Sends EM field trigger events with strength level (0-10 scale)
- Monitors temperature deviations (alerts on rapid changes)
- Barometric pressure logging
- Local buzzer/LED feedback
- Low battery warnings transmitted to hub
- Auto-reconnect on connection loss
- Configurable sensitivity thresholds

## Protocol

Sends JSON messages to OracleBox hub over WiFi:

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
  "timestamp": 1701234567
}
```

## Setup

1. Install Arduino IDE or PlatformIO
2. Install ESP32 board support
3. Install required libraries:
   - WiFi (built-in)
   - Adafruit_BMP280
   - ArduinoJson
4. Configure WiFi credentials for OracleBox hotspot
5. Set device ID and location name
6. Upload firmware

## Configuration

Edit `config.h`:
```cpp
#define WIFI_SSID "OracleBox-Network"
#define WIFI_PASSWORD "yourpassword"
#define DEVICE_ID "rempod_01"
#define LOCATION "hallway"
#define HUB_IP "192.168.4.1"
#define HUB_PORT 8888
```

## Power Consumption

- Idle: ~80mA
- Active (WiFi + sensors): ~120mA
- Trigger (buzzer + LEDs): ~180mA
- Expected battery life: 8-12 hours on 2500mAh 18650
