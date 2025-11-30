#ifndef CONFIG_H
#define CONFIG_H

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
