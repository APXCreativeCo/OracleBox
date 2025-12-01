/*
 * ESP32 REM-Pod Satellite (REM-Pod v3 Style)
 * Hardware: ESP32 Dev Module
 * 
 * PINOUT (38-pin ESP32 Dev Module):
 * 
 * === LEFT SIDE (odd pins) ===
 *   Pin 1  - EN           : UNUSED
 *   Pin 3  - GPIO36       : UNUSED (input-only)
 *   Pin 5  - GPIO39       : UNUSED (input-only)
 *   Pin 7  - GPIO35       : UNUSED (input-only)
 *   Pin 9  - GPIO34       : UNUSED (input-only)
 *   Pin 11 - GPIO32       : LED1 RED (front-left)
 *   Pin 13 - GPIO33       : LED1 GREEN (front-left)
 *   Pin 15 - GPIO25       : LED1 BLUE (front-left)
 *   Pin 17 - GPIO26       : LED2 RED (back-left)
 *   Pin 19 - GPIO27       : Active Buzzer +
 *   Pin 21 - GPIO14       : LED2 GREEN (back-left)
 *   Pin 23 - GPIO12       : AT42QT1011 LED output
 *   Pin 25 - GPIO13       : LED2 BLUE (back-left)
 *   Pin 27 - GND          : Battery -, LEDs -, Buzzer -, Sensors GND
 *   Pin 29 - VIN          : Battery + (AA pack)
 * 
 * === RIGHT SIDE (even pins) ===
 *   Pin 2  - GPIO23       : LED3 RED (front-right)
 *   Pin 4  - GPIO22       : BMP280 SCL (I2C)
 *   Pin 6  - GPIO01 (TX0) : LED5 BLUE (center) - only after Serial.end()
 *   Pin 8  - GPIO03 (RX0) : UNUSED (leave free)
 *   Pin 10 - GPIO21       : BMP280 SDA (I2C)
 *   Pin 12 - GPIO19       : LED3 GREEN (front-right)
 *   Pin 14 - GPIO18       : LED3 BLUE (front-right)
 *   Pin 16 - GPIO05       : LED4 RED (back-right)
 *   Pin 18 - GPIO17       : LED4 GREEN (back-right)
 *   Pin 20 - GPIO16       : LED4 BLUE (back-right)
 *   Pin 22 - GPIO04       : AT42QT1011 OUTPUT (main REM detect)
 *   Pin 24 - GPIO02       : LED5 RED (center "main dome")
 *   Pin 26 - GPIO15       : LED5 GREEN (center)
 *   Pin 28 - GND          : Shared ground rail
 *   Pin 30 - 3V3          : AT42 VDD + BMP280 VCC
 * 
 * SENSOR WIRING:
 *   AT42QT1011 (SparkFun Capacitive Touch):
 *     VDD -> 3V3 (Pin 30)
 *     OUT -> GPIO4 (Pin 22)
 *     LED -> GPIO12 (Pin 23)
 *     GND -> GND (Pin 28)
 *     PAD -> telescopic antenna (external)
 * 
 *   GY-BMP280 (Temp + Pressure):
 *     VCC -> 3V3 (Pin 30)
 *     GND -> GND (Pin 28)
 *     SCL -> GPIO22 (Pin 4)
 *     SDA -> GPIO21 (Pin 10)
 * 
 * LIBRARIES REQUIRED:
 *   - WiFi (built-in)
 *   - ArduinoJson (install from Library Manager)
 *   - Adafruit BMP280 Library
 *   - Adafruit Unified Sensor
 * 
 * BOARD SETTINGS:
 *   Board: "ESP32 Dev Module"
 *   Upload Speed: 115200
 *   CPU Frequency: 240MHz
 *   Flash Size: 4MB
 *   Partition Scheme: Default
 *   Port: COM3 (or your CP2102 port)
 */

#include <WiFi.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_BMP280.h>
#include <Adafruit_Sensor.h>

// ==================== CONFIGURATION ====================
// WiFi Settings (OracleBox Hub - optional, device works standalone)
#define WIFI_SSID "OracleBox-Network"
#define WIFI_PASSWORD "yourpassword"

// Device Identity
#define DEVICE_ID "rempod_01"
#define LOCATION "hallway"

// Hub Settings (optional - only used if WiFi available)
#define HUB_IP "192.168.4.1"
#define HUB_PORT 8888

// REM Detection Settings
#define AT42_POLL_INTERVAL 30       // milliseconds between AT42 checks
#define TRIGGER_THRESHOLD 3         // triggerCount needed to fire event
#define MAX_TRIGGER_COUNT 10        // max strength level
#define COOLDOWN_TIME 2000          // ms between REM events

// Temperature Settings
#define TEMP_CHECK_INTERVAL 5000    // Check temp every 5 seconds
#define TEMP_DEVIATION_THRESHOLD 2.0  // °F deviation to trigger event

// Battery Monitoring
#define BATTERY_CHECK_INTERVAL 60000  // Check battery every 60 seconds
#define BATTERY_LOW_THRESHOLD 20      // Low battery warning at 20%

// Calibration Settings
#define CALIBRATION_TIME 8000       // 8 seconds calibration window

// ==================== PIN DEFINITIONS ====================
// AT42QT1011 Capacitive Touch Sensor
const int AT42_OUT_PIN = 4;         // Main REM field detect
const int AT42_LED_PIN = 12;        // Mirror of AT42 onboard LED

// BMP280 Temperature/Pressure (I2C)
const int BMP280_SDA = 21;
const int BMP280_SCL = 22;

// Active Buzzer
const int BUZZER_PIN = 27;

// RGB LED 1 (Front-Left)
const int LED1_RED = 32;
const int LED1_GREEN = 33;
const int LED1_BLUE = 25;

// RGB LED 2 (Back-Left)
const int LED2_RED = 26;
const int LED2_GREEN = 14;
const int LED2_BLUE = 13;

// RGB LED 3 (Front-Right)
const int LED3_RED = 23;
const int LED3_GREEN = 19;
const int LED3_BLUE = 18;

// RGB LED 4 (Back-Right)
const int LED4_RED = 5;
const int LED4_GREEN = 17;
const int LED4_BLUE = 16;

// RGB LED 5 (Center "Main Dome")
const int LED5_RED = 2;
const int LED5_GREEN = 15;
const int LED5_BLUE = 1;  // TX0 - only use after Serial.end()

// ==================== STATE VARIABLES ====================
WiFiClient client;
Adafruit_BMP280 bmp;

// REM detection
int triggerCount = 0;
unsigned long lastTrigger = 0;
unsigned long lastAT42Check = 0;
bool remEventActive = false;

// Temperature monitoring
float baselineTemp = 0.0;
float baselinePressure = 0.0;
unsigned long lastTempCheck = 0;
bool tempDeviation = false;

// Battery
int batteryPercent = 100;
unsigned long lastBatteryCheck = 0;

// System state
bool calibrationComplete = false;
bool serialActive = true;

// ==================== FUNCTION DECLARATIONS ====================
bool connectWiFi();
void runCalibration();
void checkREMField();
void checkTemperature();
void setLED(int ledNum, int r, int g, int b);
void setAllLEDs(int r, int g, int b);
void displayREMEvent(int strength);
void displayTempDeviation(float tempDelta, bool isCooling);
void armedState();
void calibrationAnimation();
void startupHardwareTest();
void sendEventToHub(const char* event, int strength, float temp, float pressure);
int readBattery();

// ==================== SETUP ====================
void setup() {
  // ============ PHASE 1: BOOT + DEBUG (Serial ON) ============
  Serial.begin(115200);
  delay(100);
  Serial.println("\n");
  Serial.println("========================================");
  Serial.println("   ESP32 REM-Pod Satellite v3");
  Serial.println("========================================");
  Serial.println();
  Serial.print("[INFO] Device ID: ");
  Serial.println(DEVICE_ID);
  Serial.print("[INFO] Location: ");
  Serial.println(LOCATION);
  Serial.println();
  
  // Pin Setup - LEDs
  pinMode(LED1_RED, OUTPUT);
  pinMode(LED1_GREEN, OUTPUT);
  pinMode(LED1_BLUE, OUTPUT);
  pinMode(LED2_RED, OUTPUT);
  pinMode(LED2_GREEN, OUTPUT);
  pinMode(LED2_BLUE, OUTPUT);
  pinMode(LED3_RED, OUTPUT);
  pinMode(LED3_GREEN, OUTPUT);
  pinMode(LED3_BLUE, OUTPUT);
  pinMode(LED4_RED, OUTPUT);
  pinMode(LED4_GREEN, OUTPUT);
  pinMode(LED4_BLUE, OUTPUT);
  pinMode(LED5_RED, OUTPUT);
  pinMode(LED5_GREEN, OUTPUT);
  // LED5_BLUE (TX0) will be set after Serial.end()
  
  // Pin Setup - Sensors & Buzzer
  pinMode(AT42_OUT_PIN, INPUT);
  pinMode(AT42_LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
  
  // Initialize I2C
  Wire.begin(BMP280_SDA, BMP280_SCL);
  
  Serial.println("[1/4] Hardware Initialization...");
  
  // Hardware self-test
  startupHardwareTest();
  
  Serial.println("[OK] Hardware test complete");
  Serial.println();
  
  // Initialize BMP280
  Serial.println("[2/4] Initializing BMP280...");
  if (!bmp.begin(0x76)) {
    Serial.println("[ERROR] BMP280 not found! Check wiring.");
    Serial.println("        Continuing without temp monitoring...");
  } else {
    Serial.println("[OK] BMP280 initialized");
    bmp.setSampling(Adafruit_BMP280::MODE_NORMAL,
                    Adafruit_BMP280::SAMPLING_X2,
                    Adafruit_BMP280::SAMPLING_X16,
                    Adafruit_BMP280::FILTER_X16,
                    Adafruit_BMP280::STANDBY_MS_500);
  }
  Serial.println();
  
  // AT42 status check
  Serial.println("[3/4] Checking AT42QT1011...");
  int at42State = digitalRead(AT42_OUT_PIN);
  Serial.print("      AT42 OUT initial state: ");
  Serial.println(at42State == HIGH ? "HIGH" : "LOW");
  Serial.println("[OK] AT42 ready");
  Serial.println();
  
  // WiFi connection attempt
  Serial.println("[4/4] WiFi Connection...");
  bool hubConnected = connectWiFi();
  if (hubConnected) {
    Serial.println("[OK] Hub connected");
    // Brief green flash on all LEDs
    setAllLEDs(0, 255, 0);
    digitalWrite(BUZZER_PIN, HIGH);
    delay(100);
    digitalWrite(BUZZER_PIN, LOW);
    setAllLEDs(0, 0, 0);
  } else {
    Serial.println("[WARN] Hub offline - standalone mode");
    // Brief red flash on all LEDs
    setAllLEDs(255, 0, 0);
    digitalWrite(BUZZER_PIN, HIGH);
    delay(100);
    digitalWrite(BUZZER_PIN, LOW);
    delay(100);
    digitalWrite(BUZZER_PIN, HIGH);
    delay(100);
    digitalWrite(BUZZER_PIN, LOW);
    setAllLEDs(0, 0, 0);
  }
  Serial.println();
  
  // Battery check
  batteryPercent = readBattery();
  Serial.print("[INFO] Battery: ");
  Serial.print(batteryPercent);
  Serial.println("%");
  Serial.println();
  
  // ============ PHASE 2: CALIBRATION (Serial OFF after this) ============
  Serial.println("========================================");
  Serial.println("   STARTING CALIBRATION PHASE");
  Serial.println("========================================");
  Serial.println("[INFO] Establishing environmental baseline...");
  Serial.println("[INFO] Keep area clear for 8 seconds...");
  Serial.println();
  delay(500);
  
  // Disable Serial to free TX0 (GPIO1) for LED5_BLUE
  Serial.println("[OK] Calibration starting, disabling Serial output...");
  delay(200);  // Allow Serial buffer to flush
  Serial.end();
  serialActive = false;
  
  // Now we can use LED5_BLUE (TX0)
  pinMode(LED5_BLUE, OUTPUT);
  
  // Run calibration with LED animations
  runCalibration();
  
  // ============ PHASE 3: READY / IDLE ============
  calibrationComplete = true;
  
  // Transition to armed state
  armedState();
  
  // Ready beep
  digitalWrite(BUZZER_PIN, HIGH);
  delay(50);
  digitalWrite(BUZZER_PIN, LOW);
  delay(100);
  digitalWrite(BUZZER_PIN, HIGH);
  delay(50);
  digitalWrite(BUZZER_PIN, LOW);
}

// ==================== MAIN LOOP ====================
void loop() {
  // Check REM field continuously
  if (millis() - lastAT42Check >= AT42_POLL_INTERVAL) {
    lastAT42Check = millis();
    checkREMField();
  }
  
  // Check temperature periodically
  if (millis() - lastTempCheck >= TEMP_CHECK_INTERVAL) {
    lastTempCheck = millis();
    checkTemperature();
  }
  
  // Battery monitoring
  if (millis() - lastBatteryCheck >= BATTERY_CHECK_INTERVAL) {
    batteryPercent = readBattery();
    lastBatteryCheck = millis();
    
    if (batteryPercent < BATTERY_LOW_THRESHOLD) {
      sendEventToHub("low_battery", 0, 0, 0);
      // Low battery visual: dim yellow pulse on center LED
      setLED(5, 50, 50, 0);
      delay(200);
      armedState();
    }
  }
  
  // If no events active, maintain armed state
  if (!remEventActive && !tempDeviation) {
    // Subtle heartbeat on center LED every 2 seconds
    static unsigned long lastHeartbeat = 0;
    if (millis() - lastHeartbeat > 2000) {
      lastHeartbeat = millis();
      setLED(5, 30, 0, 0);  // Dim red pulse
      delay(100);
      setLED(5, 10, 0, 10);  // Back to dim purple
    }
  }
  
  delay(10);
}

// ==================== HARDWARE TEST ====================
void startupHardwareTest() {
  Serial.println("      Testing RGB LEDs...");
  
  // Quick rainbow sweep across all 5 LEDs
  int colors[][3] = {
    {255, 0, 0},    // Red
    {255, 127, 0},  // Orange
    {255, 255, 0},  // Yellow
    {0, 255, 0},    // Green
    {0, 0, 255},    // Blue
    {75, 0, 130},   // Indigo
    {148, 0, 211}   // Violet
  };
  
  for (int c = 0; c < 7; c++) {
    for (int led = 1; led <= 5; led++) {
      setLED(led, colors[c][0], colors[c][1], colors[c][2]);
      delay(30);
    }
  }
  
  setAllLEDs(0, 0, 0);
  delay(200);
  
  // White flash all
  setAllLEDs(255, 255, 255);
  delay(100);
  setAllLEDs(0, 0, 0);
  
  Serial.println("      Testing buzzer...");
  digitalWrite(BUZZER_PIN, HIGH);
  delay(100);
  digitalWrite(BUZZER_PIN, LOW);
  delay(50);
  digitalWrite(BUZZER_PIN, HIGH);
  delay(100);
  digitalWrite(BUZZER_PIN, LOW);
}

// ==================== CALIBRATION ====================
void runCalibration() {
  unsigned long startTime = millis();
  float tempSum = 0;
  float pressureSum = 0;
  int samples = 0;
  
  int at42Low = 0;
  int at42High = 0;
  
  // Run calibration animation + sampling for CALIBRATION_TIME ms
  while (millis() - startTime < CALIBRATION_TIME) {
    calibrationAnimation();
    
    // Sample BMP280
    if (bmp.begin(0x76)) {
      tempSum += bmp.readTemperature() * 9.0 / 5.0 + 32.0;  // Convert to °F
      pressureSum += bmp.readPressure() / 100.0;  // hPa
      samples++;
    }
    
    // Sample AT42 noise
    if (digitalRead(AT42_OUT_PIN) == HIGH) {
      at42High++;
    } else {
      at42Low++;
    }
    
    delay(50);
  }
  
  // Calculate baselines
  if (samples > 0) {
    baselineTemp = tempSum / samples;
    baselinePressure = pressureSum / samples;
  }
  
  // Turn off animation LEDs
  setAllLEDs(0, 0, 0);
  
  // Brief confirmation: all LEDs green pulse
  setAllLEDs(0, 150, 0);
  delay(300);
  setAllLEDs(0, 0, 0);
}

void calibrationAnimation() {
  static unsigned long lastUpdate = 0;
  static int phase = 0;
  
  if (millis() - lastUpdate < 100) return;
  lastUpdate = millis();
  
  // Outer LEDs: breathing teal/purple wave
  int brightness = 50 + (int)(50 * sin(phase * 0.1));
  setLED(1, 0, brightness, brightness);  // Front-left
  setLED(2, 0, brightness, brightness);  // Back-left
  setLED(3, 0, brightness, brightness);  // Front-right
  setLED(4, 0, brightness, brightness);  // Back-right
  
  // Center LED: rotating hue scan
  int hue = (phase * 5) % 360;
  int r, g, b;
  if (hue < 120) {
    r = 255 - (hue * 2);
    g = hue * 2;
    b = 0;
  } else if (hue < 240) {
    r = 0;
    g = 255 - ((hue - 120) * 2);
    b = (hue - 120) * 2;
  } else {
    r = (hue - 240) * 2;
    g = 0;
    b = 255 - ((hue - 240) * 2);
  }
  setLED(5, r / 4, g / 4, b / 4);
  
  phase++;
}

// ==================== REM FIELD DETECTION ====================
void checkREMField() {
  int at42State = digitalRead(AT42_OUT_PIN);
  
  // Mirror AT42 onboard LED
  digitalWrite(AT42_LED_PIN, at42State);
  
  // Adjust triggerCount based on AT42 state
  if (at42State == HIGH) {
    if (triggerCount < MAX_TRIGGER_COUNT) {
      triggerCount++;
    }
  } else {
    if (triggerCount > 0) {
      triggerCount--;
    }
  }
  
  // Check if we've exceeded threshold and cooldown elapsed
  if (triggerCount >= TRIGGER_THRESHOLD && !remEventActive) {
    if (millis() - lastTrigger >= COOLDOWN_TIME) {
      // REM EVENT TRIGGERED
      remEventActive = true;
      lastTrigger = millis();
      
      int strength = map(triggerCount, TRIGGER_THRESHOLD, MAX_TRIGGER_COUNT, 1, 10);
      strength = constrain(strength, 1, 10);
      
      // Display LED + buzzer based on strength
      displayREMEvent(strength);
      
      // Send to hub
      float currentTemp = bmp.begin(0x76) ? (bmp.readTemperature() * 9.0 / 5.0 + 32.0) : baselineTemp;
      float currentPressure = bmp.begin(0x76) ? (bmp.readPressure() / 100.0) : baselinePressure;
      sendEventToHub("em_trigger", strength, currentTemp, currentPressure);
      
      remEventActive = false;
    }
  }
  
  // If triggerCount drops to 0, ensure we're back in armed state
  if (triggerCount == 0 && !remEventActive) {
    armedState();
  }
}

void displayREMEvent(int strength) {
  // Strength 1-10 drives LED pattern + buzzer duration
  
  int duration = map(strength, 1, 10, 100, 800);  // 100ms - 800ms
  int brightness = map(strength, 1, 10, 50, 255);
  
  // LED pattern based on strength
  if (strength <= 3) {
    // Low: Center + front-left flicker
    for (int i = 0; i < 5; i++) {
      setLED(5, brightness, 0, brightness);  // Purple center
      setLED(1, brightness / 2, 0, brightness / 2);
      delay(50);
      setAllLEDs(0, 0, 0);
      delay(50);
    }
  } else if (strength <= 6) {
    // Mid: Center + outer LEDs 1-2 active
    for (int i = 0; i < 8; i++) {
      setLED(5, brightness, 0, brightness);
      setLED(1, brightness, 0, 0);
      setLED(2, brightness, 0, 0);
      delay(40);
      setAllLEDs(0, 0, 0);
      delay(40);
    }
  } else {
    // High: All 5 LEDs, bright, fast flicker
    for (int i = 0; i < 12; i++) {
      setAllLEDs(brightness, 0, brightness);
      delay(30);
      setAllLEDs(0, 0, 0);
      delay(30);
    }
  }
  
  // Buzzer
  digitalWrite(BUZZER_PIN, HIGH);
  delay(duration);
  digitalWrite(BUZZER_PIN, LOW);
  
  // Return to armed
  delay(200);
  armedState();
}

// ==================== TEMPERATURE MONITORING ====================
void checkTemperature() {
  if (!bmp.begin(0x76)) return;
  
  float currentTemp = bmp.readTemperature() * 9.0 / 5.0 + 32.0;  // °F
  float currentPressure = bmp.readPressure() / 100.0;  // hPa
  
  float tempDelta = currentTemp - baselineTemp;
  
  if (abs(tempDelta) >= TEMP_DEVIATION_THRESHOLD) {
    // Temperature deviation detected
    tempDeviation = true;
    
    bool isCooling = tempDelta < 0;
    
    // Display visual alert (no buzzer)
    displayTempDeviation(tempDelta, isCooling);
    
    // Send to hub
    sendEventToHub("temp_deviation", (int)(abs(tempDelta) * 10), currentTemp, currentPressure);
    
    tempDeviation = false;
    armedState();
  }
}

void displayTempDeviation(float tempDelta, bool isCooling) {
  // Visual-only alert for temperature changes
  
  if (isCooling) {
    // Temp drop: blue/cyan flashes on outer LEDs, blue pulse on center
    for (int i = 0; i < 6; i++) {
      setLED(1, 0, 100, 255);
      setLED(2, 0, 100, 255);
      setLED(3, 0, 100, 255);
      setLED(4, 0, 100, 255);
      setLED(5, 0, 150, 255);
      delay(150);
      setAllLEDs(0, 0, 0);
      delay(150);
    }
  } else {
    // Temp rise: orange/red flashes
    for (int i = 0; i < 6; i++) {
      setLED(1, 255, 100, 0);
      setLED(2, 255, 100, 0);
      setLED(3, 255, 100, 0);
      setLED(4, 255, 100, 0);
      setLED(5, 255, 50, 0);
      delay(150);
      setAllLEDs(0, 0, 0);
      delay(150);
    }
  }
  
  delay(500);
}

// ==================== LED CONTROL ====================
void setLED(int ledNum, int r, int g, int b) {
  // Set individual RGB LED (1-5)
  r = constrain(r, 0, 255);
  g = constrain(g, 0, 255);
  b = constrain(b, 0, 255);
  
  switch(ledNum) {
    case 1:  // Front-left
      analogWrite(LED1_RED, r);
      analogWrite(LED1_GREEN, g);
      analogWrite(LED1_BLUE, b);
      break;
    case 2:  // Back-left
      analogWrite(LED2_RED, r);
      analogWrite(LED2_GREEN, g);
      analogWrite(LED2_BLUE, b);
      break;
    case 3:  // Front-right
      analogWrite(LED3_RED, r);
      analogWrite(LED3_GREEN, g);
      analogWrite(LED3_BLUE, b);
      break;
    case 4:  // Back-right
      analogWrite(LED4_RED, r);
      analogWrite(LED4_GREEN, g);
      analogWrite(LED4_BLUE, b);
      break;
    case 5:  // Center
      analogWrite(LED5_RED, r);
      analogWrite(LED5_GREEN, g);
      analogWrite(LED5_BLUE, b);
      break;
  }
}

void setAllLEDs(int r, int g, int b) {
  for (int i = 1; i <= 5; i++) {
    setLED(i, r, g, b);
  }
}

void armedState() {
  // Armed/idle state: center LED dim purple, outer LEDs off
  setLED(1, 0, 0, 0);
  setLED(2, 0, 0, 0);
  setLED(3, 0, 0, 0);
  setLED(4, 0, 0, 0);
  setLED(5, 10, 0, 10);  // Dim purple
}

// ==================== WIFI CONNECTION ====================
bool connectWiFi() {
  Serial.print("      Connecting to WiFi: ");
  Serial.println(WIFI_SSID);
  
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 10) {
    delay(300);
    Serial.print(".");
    attempts++;
  }
  Serial.println();
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("      IP: ");
    Serial.println(WiFi.localIP());
    return true;
  } else {
    return false;
  }
}

// ==================== HUB COMMUNICATION ====================
void sendEventToHub(const char* event, int strength, float temp, float pressure) {
  if (WiFi.status() != WL_CONNECTED) {
    // Hub offline - event logged locally only (no Serial available)
    return;
  }
  
  if (!client.connect(HUB_IP, HUB_PORT)) {
    // Hub unreachable
    return;
  }
  
  // Create JSON message
  JsonDocument doc;
  doc["device"] = "rempod";
  doc["id"] = DEVICE_ID;
  doc["location"] = LOCATION;
  doc["event"] = event;
  doc["strength"] = strength;
  doc["temperature"] = temp;
  doc["pressure"] = pressure;
  doc["battery"] = batteryPercent;
  doc["timestamp"] = millis() / 1000;
  
  // Serialize and send
  String jsonString;
  serializeJson(doc, jsonString);
  client.println(jsonString);
  client.flush();
  client.stop();
}

// ==================== BATTERY MONITORING ====================
int readBattery() {
  // For now, simulate battery drain (replace with real voltage monitoring)
  static int simBattery = 100;
  simBattery -= random(0, 2);
  if (simBattery < 0) simBattery = 0;
  return simBattery;
  
  // Real implementation example (add voltage divider on GPIO34):
  // int rawValue = analogRead(34);
  // float voltage = (rawValue / 4095.0) * 3.3 * 2; // *2 if using voltage divider
  // int percent = map(voltage * 100, 320, 420, 0, 100); // 3.2V-4.2V for Li-ion
  // return constrain(percent, 0, 100);
}
