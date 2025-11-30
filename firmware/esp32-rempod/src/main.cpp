#include <Arduino.h>
#include <WiFi.h>
#include <Wire.h>
#include <Adafruit_BMP280.h>
#include <ArduinoJson.h>
#include "config.h"

// Pin Definitions
const int AT42QT1011_PIN = 34;    // AT42QT1011 OUT pin (capacitive sensor)
const int BUZZER_PIN = 25;        // Active buzzer
const int LED_STATUS = 2;         // Built-in LED (status)
const int LED_TRIGGER = 26;       // External LED (trigger indicator)
const int BMP280_SDA = 21;        // I2C SDA
const int BMP280_SCL = 22;        // I2C SCL

// Sensors
Adafruit_BMP280 bmp;
WiFiClient client;

// State Variables
unsigned long lastTrigger = 0;
unsigned long lastTempCheck = 0;
unsigned long lastBatteryCheck = 0;
int triggerCount = 0;
float lastTemp = 0;
float currentTemp = 0;
float currentPressure = 0;
int batteryPercent = 100;

// Function Declarations
void connectWiFi();
void checkEMField();
void checkTemperature();
void sendEventToHub(const char* event, int strength, float temp, float pressure);
void triggerAlert(int strength);
void blinkLED(int pin, int times, int delayMs);
int readBattery();

void setup() {
  Serial.begin(115200);
  Serial.println("\n>>> REM-Pod Satellite Starting...");
  
  // Pin Setup
  pinMode(AT42QT1011_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_STATUS, OUTPUT);
  pinMode(LED_TRIGGER, OUTPUT);
  
  // Initial LED pattern - startup
  for(int i = 0; i < 3; i++) {
    digitalWrite(LED_STATUS, HIGH);
    delay(100);
    digitalWrite(LED_STATUS, LOW);
    delay(100);
  }
  
  // Initialize I2C for BMP280
  Wire.begin(BMP280_SDA, BMP280_SCL);
  
  // Initialize BMP280
  if (!bmp.begin(0x76)) {  // Try 0x76, if fails try 0x77
    Serial.println("[ERROR] BMP280 sensor not found!");
    blinkLED(LED_STATUS, 10, 100);
  } else {
    Serial.println("[OK] BMP280 initialized");
    bmp.setSampling(Adafruit_BMP280::MODE_NORMAL,
                    Adafruit_BMP280::SAMPLING_X2,
                    Adafruit_BMP280::SAMPLING_X16,
                    Adafruit_BMP280::FILTER_X16,
                    Adafruit_BMP280::STANDBY_MS_500);
    
    // Get baseline temperature
    lastTemp = bmp.readTemperature() * 9.0 / 5.0 + 32.0; // Convert to Fahrenheit
  }
  
  // Connect to OracleBox WiFi
  connectWiFi();
  
  Serial.println("[OK] REM-Pod ready");
  Serial.print("Device ID: ");
  Serial.println(DEVICE_ID);
  Serial.print("Location: ");
  Serial.println(LOCATION);
}

void loop() {
  // Check WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    digitalWrite(LED_STATUS, LOW);
    Serial.println("[WARN] WiFi disconnected, reconnecting...");
    connectWiFi();
    return;
  }
  
  // Status LED heartbeat
  static unsigned long lastHeartbeat = 0;
  if (millis() - lastHeartbeat > 2000) {
    digitalWrite(LED_STATUS, HIGH);
    delay(50);
    digitalWrite(LED_STATUS, LOW);
    lastHeartbeat = millis();
  }
  
  // Check EM field sensor
  checkEMField();
  
  // Check temperature deviations
  checkTemperature();
  
  // Battery monitoring
  if (millis() - lastBatteryCheck > BATTERY_CHECK_INTERVAL) {
    batteryPercent = readBattery();
    lastBatteryCheck = millis();
    
    if (batteryPercent < BATTERY_LOW_THRESHOLD) {
      Serial.print("[WARN] Low battery: ");
      Serial.print(batteryPercent);
      Serial.println("%");
      sendEventToHub("low_battery", 0, currentTemp, currentPressure);
    }
  }
  
  delay(50);
}

void connectWiFi() {
  Serial.print("[*] Connecting to WiFi: ");
  Serial.println(WIFI_SSID);
  
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[OK] WiFi connected");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
    digitalWrite(LED_STATUS, HIGH);
    delay(1000);
    digitalWrite(LED_STATUS, LOW);
  } else {
    Serial.println("\n[ERROR] WiFi connection failed");
    blinkLED(LED_STATUS, 5, 200);
  }
}

void checkEMField() {
  int sensorState = digitalRead(AT42QT1011_PIN);
  
  // AT42QT1011 goes HIGH when field detected
  if (sensorState == HIGH) {
    triggerCount++;
    
    // Require multiple consecutive triggers to avoid false positives
    if (triggerCount >= TRIGGER_THRESHOLD && (millis() - lastTrigger > TRIGGER_COOLDOWN)) {
      
      // Calculate strength (0-10 scale) based on trigger persistence
      int strength = map(triggerCount, TRIGGER_THRESHOLD, TRIGGER_THRESHOLD * 3, 3, 10);
      strength = constrain(strength, 3, 10);
      
      Serial.print("[!] EM FIELD DETECTED - Strength: ");
      Serial.println(strength);
      
      // Trigger alert
      triggerAlert(strength);
      
      // Send event to hub
      sendEventToHub("em_trigger", strength, currentTemp, currentPressure);
      
      lastTrigger = millis();
      triggerCount = 0;
    }
  } else {
    // Reset trigger count if sensor goes low
    if (triggerCount > 0) {
      triggerCount--;
    }
  }
}

void checkTemperature() {
  if (millis() - lastTempCheck > TEMP_CHECK_INTERVAL) {
    currentTemp = bmp.readTemperature() * 9.0 / 5.0 + 32.0; // Fahrenheit
    currentPressure = bmp.readPressure() / 100.0; // hPa
    
    float tempChange = abs(currentTemp - lastTemp);
    
    if (tempChange > TEMP_DEVIATION_THRESHOLD) {
      Serial.print("[!] TEMP DEVIATION: ");
      Serial.print(tempChange, 1);
      Serial.println("F");
      
      // Quick LED blink for temp alert
      blinkLED(LED_TRIGGER, 2, 50);
      
      // Send temp alert to hub
      sendEventToHub("temp_deviation", 0, currentTemp, currentPressure);
    }
    
    lastTemp = currentTemp;
    lastTempCheck = millis();
    
    // Debug output
    Serial.print("Temp: ");
    Serial.print(currentTemp, 1);
    Serial.print("F  Pressure: ");
    Serial.print(currentPressure, 1);
    Serial.println(" hPa");
  }
}

void triggerAlert(int strength) {
  // LED feedback - blink faster for stronger signals
  int blinkCount = map(strength, 3, 10, 3, 10);
  
  digitalWrite(LED_TRIGGER, HIGH);
  
  // Buzzer feedback
  tone(BUZZER_PIN, BUZZER_FREQ, BUZZER_DURATION * strength / 5);
  
  // Blink LED during trigger
  for (int i = 0; i < blinkCount; i++) {
    digitalWrite(LED_TRIGGER, LOW);
    delay(30);
    digitalWrite(LED_TRIGGER, HIGH);
    delay(30);
  }
  
  digitalWrite(LED_TRIGGER, LOW);
}

void sendEventToHub(const char* event, int strength, float temp, float pressure) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WARN] Cannot send event - no WiFi");
    return;
  }
  
  Serial.print("[*] Sending event to hub: ");
  Serial.println(event);
  
  if (!client.connect(HUB_IP, HUB_PORT)) {
    Serial.println("[ERROR] Connection to hub failed");
    blinkLED(LED_STATUS, 3, 100);
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
  
  Serial.print("[OK] Event sent: ");
  Serial.println(jsonString);
}

void blinkLED(int pin, int times, int delayMs) {
  for (int i = 0; i < times; i++) {
    digitalWrite(pin, HIGH);
    delay(delayMs);
    digitalWrite(pin, LOW);
    delay(delayMs);
  }
}

int readBattery() {
  // Read analog pin for battery voltage
  // Assuming voltage divider on GPIO34 (ADC1_CH6)
  // Adjust based on your actual battery monitoring circuit
  
  // For now, simulate battery drain (remove this in production)
  static int simBattery = 100;
  simBattery -= random(0, 2);
  if (simBattery < 0) simBattery = 0;
  return simBattery;
  
  // Real implementation example:
  // int rawValue = analogRead(34);
  // float voltage = (rawValue / 4095.0) * 3.3 * 2; // *2 if using voltage divider
  // int percent = map(voltage * 100, 320, 420, 0, 100); // 3.2V-4.2V range for Li-ion
  // return constrain(percent, 0, 100);
}
