#include <Arduino.h>
#include <WiFi.h>
#include <ArduinoJson.h>
#include "config.h"
#include "melodies.h"

// Pin Definitions
const int PIR_PIN = 35;           // AM312 PIR motion sensor
const int BUZZER_PIN = 27;        // Passive buzzer (PWM)
const int LED_STATUS = 2;         // Built-in LED (status)
const int LED_TRIGGER = 26;       // External LED (trigger indicator)

// State Variables
WiFiClient client;
unsigned long lastTrigger = 0;
unsigned long lastBatteryCheck = 0;
bool motionDetected = false;
int batteryPercent = 100;

// Function Declarations
void connectWiFi();
void checkMotion();
void playMelody();
void sendEventToHub(const char* event, const char* melody, int duration);
void blinkLED(int pin, int times, int delayMs);
int readBattery();

void setup() {
  Serial.begin(115200);
  Serial.println("\n>>> Music Box Satellite Starting...");
  
  // Pin Setup
  pinMode(PIR_PIN, INPUT);
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
  
  // Connect to OracleBox WiFi
  connectWiFi();
  
  Serial.println("[OK] Music Box ready");
  Serial.print("Device ID: ");
  Serial.println(DEVICE_ID);
  Serial.print("Location: ");
  Serial.println(LOCATION);
  Serial.print("Melody: ");
  Serial.println(MELODY);
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
  
  // Check for motion
  checkMotion();
  
  // Battery monitoring
  if (millis() - lastBatteryCheck > BATTERY_CHECK_INTERVAL) {
    batteryPercent = readBattery();
    lastBatteryCheck = millis();
    
    if (batteryPercent < BATTERY_LOW_THRESHOLD) {
      Serial.print("[WARN] Low battery: ");
      Serial.print(batteryPercent);
      Serial.println("%");
      sendEventToHub("low_battery", MELODY, 0);
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

void checkMotion() {
  int pirState = digitalRead(PIR_PIN);
  
  // Motion detected and holdtime elapsed
  if (pirState == HIGH && (millis() - lastTrigger > PIR_HOLDTIME)) {
    motionDetected = true;
    lastTrigger = millis();
    
    Serial.println("[!] MOTION DETECTED");
    
    // Visual feedback
    digitalWrite(LED_TRIGGER, HIGH);
    
    // Play melody
    unsigned long startTime = millis();
    playMelody();
    unsigned long duration = millis() - startTime;
    
    // Send event to hub
    sendEventToHub("motion_detected", MELODY, duration);
    
    // Turn off trigger LED
    digitalWrite(LED_TRIGGER, LOW);
    
    motionDetected = false;
  }
}

void playMelody() {
  const int* notes;
  const int* durations;
  int length;
  
  // Select melody based on config
  if (strcmp(MELODY, "lullaby") == 0) {
    notes = melody_lullaby;
    durations = durations_lullaby;
    length = melody_lullaby_length;
  } else if (strcmp(MELODY, "carousel") == 0) {
    notes = melody_carousel;
    durations = durations_carousel;
    length = melody_carousel_length;
  } else {
    // Default: twinkle_star
    notes = melody_twinkle_star;
    durations = durations_twinkle_star;
    length = melody_twinkle_length;
  }
  
  Serial.print("[*] Playing melody: ");
  Serial.println(MELODY);
  
  // Play each note
  for (int i = 0; i < length; i++) {
    tone(BUZZER_PIN, notes[i], durations[i]);
    delay(durations[i] * 1.1); // Small gap between notes
    noTone(BUZZER_PIN);
  }
}

void sendEventToHub(const char* event, const char* melody, int duration) {
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
  doc["device"] = "musicbox";
  doc["id"] = DEVICE_ID;
  doc["location"] = LOCATION;
  doc["event"] = event;
  doc["melody"] = melody;
  doc["duration"] = duration;
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
