/*
 * ESP32 Music Box Satellite
 * Hardware: ESP32 Dev Module
 * 
 * PINOUT:
 *   GPIO27 -> Passive Buzzer
 *   GPIO14 -> RGB LED Red
 *   GPIO26 -> RGB LED Green
 *   GPIO25 -> RGB LED Blue
 *   GPIO4  -> PIR Sensor (AM312 OUT)
 *   3V3    -> PIR VCC
 *   GND    -> PIR GND + RGB LED common cathode + Buzzer GND
 *   VIN    -> AA Battery Pack +
 * 
 * LIBRARIES REQUIRED:
 *   - WiFi (built-in)
 *   - ArduinoJson (install from Library Manager: "ArduinoJson" by Benoit Blanchon)
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
#include <math.h>

// ==================== CONFIGURATION ====================
// WiFi Settings (OracleBox Hub - optional, device works standalone)
#define WIFI_SSID "OracleBox-Network"
#define WIFI_PASSWORD "yourpassword"

// Device Identity
#define DEVICE_ID "musicbox_01"
#define LOCATION "bedroom"

// Hub Settings (optional - only used if WiFi available)
#define HUB_IP "192.168.4.1"
#define HUB_PORT 8888

// Melody Selection: "twinkle_star", "lullaby", "carousel", "creepy_doll", "weasel", "tiptoe", "rosie"
#define MELODY "twinkle_star"

// PIR Sensor Settings
#define PIR_HOLDTIME 5000  // milliseconds before re-trigger allowed

// Battery Monitoring
#define BATTERY_CHECK_INTERVAL 60000  // Check battery every 60 seconds
#define BATTERY_LOW_THRESHOLD 20      // Low battery warning at 20%

// ==================== PIN DEFINITIONS ====================
const int PIR_PIN = 4;            // AM312 PIR motion sensor OUTPUT
const int BUZZER_PIN = 27;        // Passive buzzer (tone output)
const int RGB_LED_RED = 14;       // RGB LED - RED pin
const int RGB_LED_GREEN = 26;     // RGB LED - GREEN pin
const int RGB_LED_BLUE = 25;      // RGB LED - BLUE pin

// ==================== MELODIES ====================
// Note definitions (frequencies in Hz)
#define NOTE_C4  262
#define NOTE_D4  294
#define NOTE_E4  330
#define NOTE_F4  349
#define NOTE_G4  392
#define NOTE_A4  440
#define NOTE_B4  494
#define NOTE_C5  523
#define NOTE_D5  587
#define NOTE_E5  659
#define NOTE_F5  698
#define NOTE_G5  784
#define NOTE_A5  880
#define NOTE_B5  988
#define NOTE_C6  1047

// Duration definitions (in milliseconds)
#define WHOLE_NOTE 1600
#define HALF_NOTE 800
#define QUARTER_NOTE 400
#define EIGHTH_NOTE 200

// Twinkle Twinkle Little Star
const int melody_twinkle_star[] = {
  NOTE_C5, NOTE_C5, NOTE_G5, NOTE_G5, NOTE_A5, NOTE_A5, NOTE_G5,
  NOTE_F5, NOTE_F5, NOTE_E5, NOTE_E5, NOTE_D5, NOTE_D5, NOTE_C5
};
const int durations_twinkle_star[] = {
  QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, 
  QUARTER_NOTE, QUARTER_NOTE, HALF_NOTE,
  QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, 
  QUARTER_NOTE, QUARTER_NOTE, HALF_NOTE
};
const int melody_twinkle_length = 14;

// Brahms Lullaby (creepy version - slower)
const int melody_lullaby[] = {
  NOTE_G4, NOTE_G4, NOTE_A4, NOTE_G4, NOTE_C5, NOTE_B4,
  NOTE_G4, NOTE_G4, NOTE_A4, NOTE_G4, NOTE_D5, NOTE_C5
};
const int durations_lullaby[] = {
  QUARTER_NOTE, QUARTER_NOTE, HALF_NOTE, HALF_NOTE, HALF_NOTE, WHOLE_NOTE,
  QUARTER_NOTE, QUARTER_NOTE, HALF_NOTE, HALF_NOTE, HALF_NOTE, WHOLE_NOTE
};
const int melody_lullaby_length = 12;

// Carousel/Music Box (repetitive creepy tune) - balanced volume
const int melody_carousel[] = {
  NOTE_C5, NOTE_E5, NOTE_G5, NOTE_E5, NOTE_C5, NOTE_G4,
  NOTE_C5, NOTE_E5, NOTE_G5, NOTE_E5, NOTE_C5, NOTE_G4,
  NOTE_D5, NOTE_F5, NOTE_A5, NOTE_F5, NOTE_D5, NOTE_A4
};
const int durations_carousel[] = {
  QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE,
  QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE,
  QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE
};
const int melody_carousel_length = 18;

// Creepy Doll (descending melody box style)
const int melody_creepy_doll[] = {
  NOTE_G5, NOTE_E5, NOTE_C5, NOTE_G4, 
  NOTE_G5, NOTE_E5, NOTE_C5, NOTE_G4,
  NOTE_F5, NOTE_D5, NOTE_B4, NOTE_G4,
  NOTE_E5, NOTE_C5, NOTE_A4, NOTE_G4
};
const int durations_creepy_doll[] = {
  QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, HALF_NOTE,
  QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, HALF_NOTE,
  QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, HALF_NOTE,
  QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, HALF_NOTE
};
const int melody_creepy_doll_length = 16;

// Pop Goes the Weasel (classic creepy music box)
const int melody_weasel[] = {
  NOTE_G4, NOTE_C5, NOTE_C5, NOTE_C5, NOTE_D5, NOTE_E5,
  NOTE_E5, NOTE_D5, NOTE_C5, NOTE_D5, NOTE_E5, NOTE_C5,
  NOTE_G4, NOTE_C5, NOTE_C5, NOTE_C5, NOTE_D5, NOTE_E5,
  NOTE_E5, NOTE_E5, NOTE_D5, NOTE_D5, NOTE_C5
};
const int durations_weasel[] = {
  EIGHTH_NOTE, EIGHTH_NOTE, EIGHTH_NOTE, EIGHTH_NOTE, EIGHTH_NOTE, QUARTER_NOTE,
  EIGHTH_NOTE, EIGHTH_NOTE, EIGHTH_NOTE, EIGHTH_NOTE, QUARTER_NOTE, QUARTER_NOTE,
  EIGHTH_NOTE, EIGHTH_NOTE, EIGHTH_NOTE, EIGHTH_NOTE, EIGHTH_NOTE, QUARTER_NOTE,
  EIGHTH_NOTE, EIGHTH_NOTE, EIGHTH_NOTE, EIGHTH_NOTE, HALF_NOTE
};
const int melody_weasel_length = 23;

// Tiptoe Through the Tulips (creepy slow version)
const int melody_tiptoe[] = {
  NOTE_G4, NOTE_C5, NOTE_E5, NOTE_G5, NOTE_E5, NOTE_C5,
  NOTE_G4, NOTE_C5, NOTE_E5, NOTE_G5, NOTE_E5, NOTE_C5,
  NOTE_A4, NOTE_D5, NOTE_F5, NOTE_A5, NOTE_F5, NOTE_D5,
  NOTE_G4, NOTE_E5, NOTE_G5, NOTE_C5
};
const int durations_tiptoe[] = {
  QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE,
  QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE,
  QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE,
  QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, HALF_NOTE
};
const int melody_tiptoe_length = 22;

// Ring Around the Rosie (actual melody - creepy slow)
const int melody_rosie[] = {
  NOTE_C5, NOTE_C5, NOTE_D5, NOTE_E5,
  NOTE_E5, NOTE_D5, NOTE_E5, NOTE_F5, NOTE_E5,
  NOTE_D5, NOTE_D5, NOTE_E5, NOTE_D5, NOTE_C5,
  NOTE_G4, NOTE_C5, NOTE_C5
};
const int durations_rosie[] = {
  QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, HALF_NOTE,
  QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, HALF_NOTE,
  QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, HALF_NOTE,
  QUARTER_NOTE, HALF_NOTE, WHOLE_NOTE
};
const int melody_rosie_length = 17;

// ==================== STATE VARIABLES ====================
WiFiClient client;
unsigned long lastTrigger = 0;
unsigned long lastBatteryCheck = 0;
bool motionDetected = false;
int batteryPercent = 100;

// Proximity / intensity level: 1 = weak, 2 = strong, 3 = extra-strong
int strengthLevel = 1;

// Melody playback state (for motion-reactive pause/resume)
int currentNoteIndex = 0;
unsigned long noteStartTime = 0;
unsigned long elapsedInCurrentNote = 0;
bool melodyPlaying = false;
bool melodyPaused = false;

// ==================== FUNCTION DECLARATIONS ====================
bool connectWiFi();
void displayBatteryLevel(int percent);
void checkMotion();
void playMelody();
void playMelodyStep();
void updateMelodyRGB();
void resetMelodyState();
void sendEventToHub(const char* event, const char* melody, int duration);
int readBattery();

// ==================== SETUP ====================
void setup() {
  Serial.begin(115200);
  Serial.println("\n>>> Music Box Satellite Starting...");
  Serial.println("=== SYSTEM STARTUP SEQUENCE ===\n");
  
  // Pin Setup
  pinMode(PIR_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(RGB_LED_RED, OUTPUT);
  pinMode(RGB_LED_GREEN, OUTPUT);
  pinMode(RGB_LED_BLUE, OUTPUT);

  // ---------------- SYSTEM SELF-TEST ----------------
  Serial.println("[SELF-TEST] Checking hardware...");

  // PIR quick read (just logs state)
  int pirInitial = digitalRead(PIR_PIN);
  Serial.print("      PIR initial state: ");
  Serial.println(pirInitial);

  // RGB LED test: Red -> Green -> Blue
  digitalWrite(RGB_LED_RED, HIGH);
  delay(150);
  digitalWrite(RGB_LED_RED, LOW);

  digitalWrite(RGB_LED_GREEN, HIGH);
  delay(150);
  digitalWrite(RGB_LED_GREEN, LOW);

  digitalWrite(RGB_LED_BLUE, HIGH);
  delay(150);
  digitalWrite(RGB_LED_BLUE, LOW);

  // Buzzer chirp
  tone(BUZZER_PIN, NOTE_C5, 120);
  delay(150);
  tone(BUZZER_PIN, NOTE_E5, 120);
  delay(150);
  noTone(BUZZER_PIN);

  Serial.println("[SELF-TEST] Hardware OK");

  // Set to idle red after test
  digitalWrite(RGB_LED_RED, HIGH);
  digitalWrite(RGB_LED_GREEN, LOW);
  digitalWrite(RGB_LED_BLUE, LOW);
  
  // === STARTUP SEQUENCE ===
  
  // 1. System Check - Cyan pulse (extra little flair after self-test)
  Serial.println("[1/3] Hardware Check...");
  for (int i = 0; i < 2; i++) {
    digitalWrite(RGB_LED_GREEN, HIGH);
    digitalWrite(RGB_LED_BLUE, HIGH);
    tone(BUZZER_PIN, NOTE_C5, 100);
    delay(150);
    digitalWrite(RGB_LED_GREEN, LOW);
    digitalWrite(RGB_LED_BLUE, LOW);
    delay(100);
  }
  Serial.println("      [OK] Hardware initialized\n");
  delay(300);
  
  // 2. WiFi/Hub Connection Check
  Serial.println("[2/3] Hub Connection Check...");
  bool hubConnected = connectWiFi();
  
  if (hubConnected) {
    // Solid GREEN = Hub connected
    digitalWrite(RGB_LED_GREEN, HIGH);
    tone(BUZZER_PIN, NOTE_G5, 200);
    delay(200);
    noTone(BUZZER_PIN);
    tone(BUZZER_PIN, NOTE_C6, 300);
    delay(300);
    noTone(BUZZER_PIN);
    Serial.println("      [OK] Hub connection: ONLINE\n");
    delay(500);
    digitalWrite(RGB_LED_GREEN, LOW);
  } else {
    // Red FLASHES = No hub connection
    for (int i = 0; i < 3; i++) {
      digitalWrite(RGB_LED_RED, HIGH);
      tone(BUZZER_PIN, NOTE_C4, 150);
      delay(150);
      digitalWrite(RGB_LED_RED, LOW);
      noTone(BUZZER_PIN);
      delay(100);
    }
    Serial.println("      [WARN] Hub connection: OFFLINE (standalone mode)\n");
    delay(300);
  }
  
  // 3. Battery Level Check
  Serial.println("[3/3] Battery Level Check...");
  batteryPercent = readBattery();
  displayBatteryLevel(batteryPercent);
  delay(500);
  
  // All checks complete - ready tone
  Serial.println("\n=== STARTUP COMPLETE ===");
  Serial.println("[OK] Music Box ready");
  Serial.print("Device ID: ");
  Serial.println(DEVICE_ID);
  Serial.print("Location: ");
  Serial.println(LOCATION);
  Serial.print("Melody: ");
  Serial.println(MELODY);
  Serial.print("Battery: ");
  Serial.print(batteryPercent);
  Serial.println("%");
  Serial.println("\n[TIP] Wave hand over PIR sensor to trigger melody!");
  
  // Final ready tone - ascending notes
  tone(BUZZER_PIN, NOTE_C5, 100);
  delay(120);
  tone(BUZZER_PIN, NOTE_E5, 100);
  delay(120);
  tone(BUZZER_PIN, NOTE_G5, 200);
  delay(220);
  noTone(BUZZER_PIN);
  
  // Ensure idle red at end of startup
  digitalWrite(RGB_LED_RED, HIGH);
  digitalWrite(RGB_LED_GREEN, LOW);
  digitalWrite(RGB_LED_BLUE, LOW);
}

// ==================== MAIN LOOP ====================
void loop() {
  // ---------------- IDLE RED WATCHDOG ----------------
  static unsigned long lastIdleCheck = 0;
  if (millis() - lastIdleCheck > 250) {   // check every 250ms
    lastIdleCheck = millis();
    if (!motionDetected && !melodyPlaying) {
      // Force LED to solid red (idle state)
      digitalWrite(RGB_LED_RED, HIGH);
      digitalWrite(RGB_LED_GREEN, LOW);
      digitalWrite(RGB_LED_BLUE, LOW);
    }
  }

  // Check for motion
  checkMotion();
  
  // Continue playing melody if active
  if (melodyPlaying) {
    playMelodyStep();
  }
  
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

// ==================== BATTERY LEVEL DISPLAY ====================
void displayBatteryLevel(int percent) {
  Serial.print("      Battery: ");
  Serial.print(percent);
  Serial.print("% - ");
  
  if (percent > 75) {
    // HIGH (>75%) - Solid GREEN + ascending tone
    Serial.println("FULL");
    digitalWrite(RGB_LED_GREEN, HIGH);
    tone(BUZZER_PIN, NOTE_G5, 150);
    delay(150);
    tone(BUZZER_PIN, NOTE_C6, 150);
    delay(150);
    noTone(BUZZER_PIN);
    delay(300);
    digitalWrite(RGB_LED_GREEN, LOW);
    
  } else if (percent > 50) {
    // GOOD (50-75%) - Solid CYAN (green+blue) + mid tone
    Serial.println("GOOD");
    digitalWrite(RGB_LED_GREEN, HIGH);
    digitalWrite(RGB_LED_BLUE, HIGH);
    tone(BUZZER_PIN, NOTE_G5, 300);
    delay(300);
    noTone(BUZZER_PIN);
    delay(300);
    digitalWrite(RGB_LED_GREEN, LOW);
    digitalWrite(RGB_LED_BLUE, LOW);
    
  } else if (percent > 25) {
    // LOW (25-50%) - Solid YELLOW (red+green) + warning tone
    Serial.println("LOW");
    digitalWrite(RGB_LED_RED, HIGH);
    digitalWrite(RGB_LED_GREEN, HIGH);
    tone(BUZZER_PIN, NOTE_E5, 200);
    delay(200);
    tone(BUZZER_PIN, NOTE_D5, 200);
    delay(200);
    noTone(BUZZER_PIN);
    delay(300);
    digitalWrite(RGB_LED_RED, LOW);
    digitalWrite(RGB_LED_GREEN, LOW);
    
  } else {
    // CRITICAL (<25%) - Flashing RED + descending alarm
    Serial.println("CRITICAL");
    for (int i = 0; i < 3; i++) {
      digitalWrite(RGB_LED_RED, HIGH);
      tone(BUZZER_PIN, NOTE_E5, 100);
      delay(100);
      digitalWrite(RGB_LED_RED, LOW);
      tone(BUZZER_PIN, NOTE_C5, 100);
      delay(100);
      noTone(BUZZER_PIN);
      delay(50);
    }
  }
}

// ==================== MOTION DETECTION ====================
void checkMotion() {
  int pirState = digitalRead(PIR_PIN);
  
  if (pirState == HIGH) {
    // Motion detected
    if (!motionDetected) {
      // First detection
      motionDetected = true;
      lastTrigger = millis();
      Serial.println("[!] MOTION DETECTED");
      Serial.print("    Current strength level: ");
      Serial.println(strengthLevel);
      sendEventToHub("motion_detected", MELODY, 0);
    }
    
    // Start or resume melody
    if (!melodyPlaying) {
      Serial.println("[*] Starting melody playback");
      melodyPlaying = true;
      melodyPaused = false;
    } else if (melodyPaused) {
      Serial.println("[*] Resuming melody from pause");
      melodyPaused = false;
      noteStartTime = millis() - elapsedInCurrentNote; // Resume from paused position
    }
    
  } else {
    // No motion detected
    if (motionDetected) {
      // Motion just stopped
      Serial.println("[!] MOTION STOPPED - pausing melody");
      motionDetected = false;
      
      if (melodyPlaying && !melodyPaused) {
        // Pause the melody
        melodyPaused = true;
        elapsedInCurrentNote = millis() - noteStartTime;
        noTone(BUZZER_PIN);
        
        // Set LED to dim red during pause
        analogWrite(RGB_LED_RED, 50);
        analogWrite(RGB_LED_GREEN, 0);
        analogWrite(RGB_LED_BLUE, 0);
      }
      
      // Check if paused for too long (5 seconds) - reset completely
      static unsigned long pauseStartTime = 0;
      if (melodyPaused) {
        if (pauseStartTime == 0) pauseStartTime = millis();
        if (millis() - pauseStartTime > 5000) {
          Serial.println("[OK] Pause timeout - resetting melody");
          resetMelodyState();
          pauseStartTime = 0;
        }
      } else {
        pauseStartTime = 0;
      }
    }
  }
}

// ==================== MELODY PLAYBACK (motion-reactive, strength-based RGB) ====================
void playMelody() {
  // Legacy function - now handled by playMelodyStep() in loop
  // Kept for compatibility but not used
}

void playMelodyStep() {
  if (melodyPaused) {
    return; // Don't play while paused
  }
  
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
  } else if (strcmp(MELODY, "creepy_doll") == 0) {
    notes = melody_creepy_doll;
    durations = durations_creepy_doll;
    length = melody_creepy_doll_length;
  } else if (strcmp(MELODY, "weasel") == 0) {
    notes = melody_weasel;
    durations = durations_weasel;
    length = melody_weasel_length;
  } else if (strcmp(MELODY, "tiptoe") == 0) {
    notes = melody_tiptoe;
    durations = durations_tiptoe;
    length = melody_tiptoe_length;
  } else if (strcmp(MELODY, "rosie") == 0) {
    notes = melody_rosie;
    durations = durations_rosie;
    length = melody_rosie_length;
  } else {
    // Default: twinkle_star
    notes = melody_twinkle_star;
    durations = durations_twinkle_star;
    length = melody_twinkle_length;
  }
  
  // Initialize note if starting fresh
  if (noteStartTime == 0) {
    noteStartTime = millis();
    tone(BUZZER_PIN, notes[currentNoteIndex]);
    Serial.print("[*] Playing note ");
    Serial.print(currentNoteIndex + 1);
    Serial.print("/");
    Serial.print(length);
    Serial.print(" | strength level = ");
    Serial.println(strengthLevel);
  }
  
  // Check if current note duration completed
  unsigned long elapsed = millis() - noteStartTime;
  int noteDuration = durations[currentNoteIndex];
  
  if (elapsed < noteDuration) {
    // Still playing current note - update RGB
    updateMelodyRGB();
  } else {
    // Note finished - move to next
    noTone(BUZZER_PIN);
    
    // Small gap between notes
    if (strengthLevel == 3 && elapsed < noteDuration + 30) {
      // White strobe for extra-strong
      digitalWrite(RGB_LED_RED, HIGH);
      digitalWrite(RGB_LED_GREEN, HIGH);
      digitalWrite(RGB_LED_BLUE, HIGH);
      return;
    }
    
    if (elapsed < noteDuration + 50) {
      return; // Gap between notes
    }
    
    // Advance to next note
    currentNoteIndex++;
    
    if (currentNoteIndex >= length) {
      // Melody complete - check if should loop
      if (digitalRead(PIR_PIN) == HIGH) {
        // Motion still present - loop melody and increase strength
        Serial.println("[*] Melody complete - looping");
        currentNoteIndex = 0;
        if (strengthLevel < 3) {
          strengthLevel++;
          Serial.print("[!] Strength increased to level ");
          Serial.println(strengthLevel);
        }
      } else {
        // Motion ended during melody - stop
        Serial.println("[OK] Melody complete - stopping");
        resetMelodyState();
        return;
      }
    }
    
    // Start next note
    noteStartTime = millis();
    tone(BUZZER_PIN, notes[currentNoteIndex]);
  }
}

void updateMelodyRGB() {
  unsigned long elapsed = millis() - noteStartTime;
  float phase = (elapsed % 3000) / 3000.0f; // base phase 0–1 over 3s
  
  int r = 0, g = 0, b = 0;
  
  // ===== STRENGTH-BASED RGB BEHAVIOR =====
  if (strengthLevel == 1) {
    // WEAK: soft blue / purple, low intensity, smooth
    b = 60 + (int)(sin(phase * 6.283f) * 40.0f);  // around 20–100
    r = 40;                                       // subtle red tint
    g = 0;
    
  } else if (strengthLevel == 2) {
    // STRONG: rainbow base + red pulses
    r = (int)((sin(phase * 6.283f) * 127.0f) + 128.0f);
    g = (int)((sin((phase + 0.33f) * 6.283f) * 127.0f) + 128.0f);
    b = (int)((sin((phase + 0.67f) * 6.283f) * 127.0f) + 128.0f);
    
    // Periodic red pulse
    if ((int)(phase * 100) % 10 == 0) {
      r = 255;
    }
    
  } else { 
    // EXTRA STRONG: red-dominant + unstable color, feels aggressive
    r = 255;
    g = 40 + (int)(sin((phase + 0.5f) * 6.283f) * 60.0f);
    b = 40 + (int)(sin((phase + 0.8f) * 6.283f) * 60.0f);
  }
  
  // Apply RGB
  analogWrite(RGB_LED_RED,   constrain(r, 0, 255));
  analogWrite(RGB_LED_GREEN, constrain(g, 0, 255));
  analogWrite(RGB_LED_BLUE,  constrain(b, 0, 255));
}

void resetMelodyState() {
  melodyPlaying = false;
  melodyPaused = false;
  currentNoteIndex = 0;
  noteStartTime = 0;
  elapsedInCurrentNote = 0;
  strengthLevel = 1;
  noTone(BUZZER_PIN);
  
  // Return to solid red idle
  digitalWrite(RGB_LED_RED, HIGH);
  digitalWrite(RGB_LED_GREEN, LOW);
  digitalWrite(RGB_LED_BLUE, LOW);
}

// ==================== HUB COMMUNICATION ====================
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
