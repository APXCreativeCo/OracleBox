# ESP32 Music Box Satellite

Wireless motion detector with creepy chime melodies that connects to OracleBox hub via WiFi.

## Hardware Components

- **ESP32 Dev Board** (WiFi enabled)
- **AM312 PIR Motion Sensor** - Passive infrared motion detection
- **Passive Buzzer** - Plays chime melodies on trigger
- **LEDs** - Visual indicators (idle/triggered states)
- **Battery Pack** - Portable power (18650 or similar)

## Pin Configuration

```
AM312 OUT      → GPIO 35 (input, motion detection)
Passive Buzzer → GPIO 27 (PWM for tones)
LED Status     → GPIO 2 (built-in)
LED Trigger    → GPIO 26
```

## Features

- Connects to OracleBox WiFi hotspot automatically
- Detects motion with PIR sensor
- Plays eerie music box melody on trigger (local + alerts hub)
- Configurable melody patterns (creepy children's songs)
- Adjustable PIR sensitivity and hold time
- Low battery warnings transmitted to hub
- Auto-reconnect on connection loss
- Multiple melody options

## Melodies

Pre-programmed chime patterns:
- **Twinkle Star** - Classic creepy music box tune
- **Lullaby** - Slow, haunting melody
- **Carousel** - Circus-style creepy tune
- **Custom** - Define your own note sequences

## Protocol

Sends JSON messages to OracleBox hub over WiFi:

```json
{
  "device": "musicbox",
  "id": "musicbox_01",
  "location": "bedroom",
  "event": "motion_detected",
  "melody": "twinkle_star",
  "duration": 5000,
  "battery": 72,
  "timestamp": 1701234567
}
```

## Setup

1. Install Arduino IDE or PlatformIO
2. Install ESP32 board support
3. Install required libraries:
   - WiFi (built-in)
   - ArduinoJson
4. Configure WiFi credentials for OracleBox hotspot
5. Set device ID and location name
6. Upload firmware

## Configuration

Edit `config.h`:
```cpp
#define WIFI_SSID "OracleBox-Network"
#define WIFI_PASSWORD "yourpassword"
#define DEVICE_ID "musicbox_01"
#define LOCATION "bedroom"
#define HUB_IP "192.168.4.1"
#define HUB_PORT 8888
#define MELODY "twinkle_star"
#define PIR_HOLDTIME 5000  // ms before re-trigger
```

## Power Consumption

- Idle: ~70mA
- Active (WiFi + sensors): ~110mA
- Playing melody: ~140mA
- Expected battery life: 10-14 hours on 2500mAh 18650

## Melody Format

Define custom melodies in `melodies.h`:
```cpp
const int melody[] = {NOTE_C5, NOTE_E5, NOTE_G5, NOTE_C6};
const int durations[] = {4, 4, 4, 2};  // 4 = quarter, 2 = half
```
