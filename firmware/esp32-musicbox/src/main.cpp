#include <Arduino.h>
#include <WiFi.h>
#include <ArduinoJson.h>
#include "config.h"
#include "melodies.h"

// Pin Definitions (Music Box - Finalized Hardware)
const int PIR_PIN = 4;            // AM312 PIR motion sensor OUTPUT
const int BUZZER_PIN = 27;        // Passive buzzer (tone output)
const int RGB_LED_RED = 14;       // RGB LED - RED pin
const int RGB_LED_GREEN = 26;     // RGB LED - GREEN pin
const int RGB_LED_BLUE = 25;      // RGB LED - BLUE pin

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
int readBattery();

void setup() {
  Serial.begin(115200);
  Serial.println("\n>>> Music Box Satellite Starting...");
  
  // Pin Setup
  pinMode(PIR_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(RGB_LED_RED, OUTPUT);
  pinMode(RGB_LED_GREEN, OUTPUT);
  pinMode(RGB_LED_BLUE, OUTPUT);
  
  // Initial LED pattern - startup (cyan pulse: green + blue)
  for(int i = 0; i < 3; i++) {
    digitalWrite(RGB_LED_GREEN, HIGH);
    digitalWrite(RGB_LED_BLUE, HIGH);
    delay(100);
    digitalWrite(RGB_LED_GREEN, LOW);
    digitalWrite(RGB_LED_BLUE, LOW);
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
  // Status LED heartbeat (dim green pulse - always active)
  static unsigned long lastHeartbeat = 0;
  if (millis() - lastHeartbeat > 2000) {
    digitalWrite(RGB_LED_GREEN, HIGH);
    delay(50);
    digitalWrite(RGB_LED_GREEN, LOW);
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
  while (WiFi.status() != WL_CONNECTED && attempts < 10) {
    delay(300);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[OK] WiFi connected");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
    digitalWrite(RGB_LED_GREEN, HIGH);
    delay(500);
    digitalWrite(RGB_LED_GREEN, LOW);
  } else {
    Serial.println("\n[WARN] WiFi unavailable - operating standalone");
    // Brief yellow flash (red+green) to indicate standalone mode
    digitalWrite(RGB_LED_RED, HIGH);
    digitalWrite(RGB_LED_GREEN, HIGH);
    delay(300);
    digitalWrite(RGB_LED_RED, LOW);
    digitalWrite(RGB_LED_GREEN, LOW);
  }
}

void checkMotion() {
  int pirState = digitalRead(PIR_PIN);
  
  // Motion detected and holdtime elapsed
  if (pirState == HIGH && (millis() - lastTrigger > PIR_HOLDTIME)) {
    motionDetected = true;
    lastTrigger = millis();
    
    Serial.println("[!] MOTION DETECTED");
    
    // Play melody with RGB cycling
    unsigned long startTime = millis();
    playMelody();
    unsigned long duration = millis() - startTime;
    
    // Send event to hub
    sendEventToHub("motion_detected", MELODY, duration);
    
    // Turn off all LEDs after melody
    digitalWrite(RGB_LED_RED, LOW);
    digitalWrite(RGB_LED_GREEN, LOW);
    digitalWrite(RGB_LED_BLUE, LOW);
    
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
  
  // Start RGB fade thread while playing melody
  unsigned long fadeStartTime = millis();
  
  // Play each note
  for (int i = 0; i < length; i++) {
    // Play note
    tone(BUZZER_PIN, notes[i], durations[i]);
    
    // Smooth RGB fade during note duration
    int steps = durations[i] / 20; // 20ms per step for smooth transition
    for (int step = 0; step < steps; step++) {
      // Calculate RGB values for smooth rainbow cycle
      unsigned long elapsed = millis() - fadeStartTime;
      float phase = (elapsed % 3000) / 3000.0; // 3 second full cycle
      
      int r = (sin(phase * 6.283) * 127) + 128;
      int g = (sin((phase + 0.33) * 6.283) * 127) + 128;
      int b = (sin((phase + 0.67) * 6.283) * 127) + 128;
      
      analogWrite(RGB_LED_RED, r);
      analogWrite(RGB_LED_GREEN, g);
      analogWrite(RGB_LED_BLUE, b);
      
      delay(20);
    }
    
    noTone(BUZZER_PIN);
    delay(durations[i] * 0.1); // Small gap between notes
  }
}

void sendEventToHub(const char* event, const char* melody, int duration) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[INFO] Hub offline - event logged locally only");
    return;
  }
  
  Serial.print("[*] Sending event to hub: ");
  Serial.println(event);
  
  if (!client.connect(HUB_IP, HUB_PORT)) {
    Serial.println("[INFO] Hub unreachable - event logged locally only");
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
