#ifndef CONFIG_H
#define CONFIG_H

// ==================== MUSIC BOX PINOUT ====================
// LEFT SIDE PINS:
//   GPIO25 → RGB LED - BLUE
//   GPIO26 → RGB LED - GREEN
//   GPIO27 → Passive Buzzer (tone output)
//   GPIO14 → RGB LED - RED
//   GND (Pin 27) → Battery - (AA pack)
//   VIN (Pin 29) → Battery + (AA pack)
//
// RIGHT SIDE PINS:
//   GPIO04 → PIR Sensor OUTPUT
//   3V3 (Pin 30) → PIR Sensor VCC
//   GND (Pin 28) → PIR Sensor GND + LED - + Buzzer - (shared)
//
// NOTES:
//   - RGB LED is 4-pin common-cathode (3 color pins + shared GND)
//   - Buzzer is passive, uses tone() for melodies
//   - PIR is AM312 3-pin module
//   - GPIO01/03 left free for serial debugging
// ==========================================================

// WiFi Configuration - OracleBox Hub Hotspot
#define WIFI_SSID "OracleBox-Network"
#define WIFI_PASSWORD "yourpassword"

// Device Configuration
#define DEVICE_ID "musicbox_01"
#define LOCATION "bedroom"

// OracleBox Hub Configuration
#define HUB_IP "192.168.4.1"
#define HUB_PORT 8888

// Melody Selection
// Options: "twinkle_star", "lullaby", "carousel"
#define MELODY "twinkle_star"

// PIR Sensor Configuration
#define PIR_HOLDTIME 5000  // milliseconds before re-trigger allowed

// Battery Monitoring
#define BATTERY_CHECK_INTERVAL 60000  // Check battery every 60 seconds
#define BATTERY_LOW_THRESHOLD 20      // Low battery warning at 20%

#endif
