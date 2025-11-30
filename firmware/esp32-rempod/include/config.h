#ifndef CONFIG_H
#define CONFIG_H

// WiFi Configuration - OracleBox Hub Hotspot
#define WIFI_SSID "OracleBox-Network"
#define WIFI_PASSWORD "yourpassword"

// Device Configuration
#define DEVICE_ID "rempod_01"
#define LOCATION "hallway"

// OracleBox Hub Configuration
#define HUB_IP "192.168.4.1"
#define HUB_PORT 8888

// AT42QT1011 Sensitivity Configuration
#define TRIGGER_THRESHOLD 3      // Consecutive triggers to register as event
#define TRIGGER_COOLDOWN 2000    // ms before re-trigger allowed

// Temperature Deviation Alert
#define TEMP_DEVIATION_THRESHOLD 2.0  // Degrees F for rapid change alert
#define TEMP_CHECK_INTERVAL 5000      // Check temp every 5 seconds

// Battery Monitoring
#define BATTERY_CHECK_INTERVAL 60000  // Check battery every 60 seconds
#define BATTERY_LOW_THRESHOLD 20      // Low battery warning at 20%

// Buzzer Feedback
#define BUZZER_DURATION 100      // ms for trigger beep
#define BUZZER_FREQ 2000         // Hz for trigger tone

#endif
