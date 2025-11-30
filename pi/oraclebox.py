#!/usr/bin/env python3
"""
OracleBox Merged Controller
Version: 2.3.0
Last Updated: November 26, 2025
Changes: 
  - Added BT_AUDIO DISCOVER command to scan for nearby unpaired devices
  - Added BT_AUDIO PAIR command to pair with new Bluetooth devices
  - Enhanced device discovery with paired/connected status
  - Automatic device trust after successful pairing
"""

import os
import signal
import time
import json
import threading
import subprocess

# Optional Bluetooth library
try:
    import bluetooth
except ImportError:
    bluetooth = None

# FM low-level I2C support
try:
    import fcntl
    _fcntl_available = True
except ImportError:
    _fcntl_available = False

from gpiozero import LED, PWMLED

# ==================== DEBUG / LOGGING CONFIGURATION ====================
# Control what gets logged to the console - set to False to reduce noise
# ========================================================================

class DebugConfig:
    """Master debug configuration - toggle logging categories on/off"""
    
    # === BLUETOOTH COMMUNICATION ===
    BLUETOOTH_RAW_COMMANDS = True      # Log all raw bluetooth commands received
    BLUETOOTH_RESPONSES = True         # Log all responses sent back to phone
    
    # === SWEEP / FM RADIO ===
    SWEEP_CYCLES = True                # Log sweep start/end messages
    SWEEP_FREQUENCY_CHANGES = False    # Log every frequency step (very verbose!)
    FM_TUNER_OPERATIONS = True         # Log FM tuner I2C communication
    
    # === AUDIO / FX ===
    FX_STATE_CHANGES = True            # Log FX enable/disable/restart events
    FX_PARAMETER_CHANGES = True        # Log FX parameter adjustments
    AUDIO_PASSTHROUGH = True           # Log audio passthrough start/stop
    MIXER_OPERATIONS = True            # Log ALSA mixer changes
    BT_AUDIO_OPERATIONS = True         # Log Bluetooth audio connection/disconnect
    AUDIO_DEVICE_CHANGES = True        # Log audio output device switching
    
    # === LED OPERATIONS ===
    LED_MODE_CHANGES = True            # Log LED mode changes
    LED_CONFIG_CHANGES = True          # Log LED brightness/speed adjustments
    
    # === SOUND FILES ===
    SOUND_PLAYBACK = True              # Log sound file playback events
    SOUND_UPLOADS = True               # Log sound file upload progress
    
    # === COMMANDS (by category) ===
    CMD_SPEED = True                   # Log SPEED, FASTER, SLOWER commands
    CMD_DIRECTION = True               # Log DIR command
    CMD_START_STOP = True              # Log START, STOP commands
    CMD_LED = True                     # Log LED commands
    CMD_SWEEP_CFG = True               # Log SWEEP_CFG commands
    CMD_BOX_CFG = True                 # Log BOX_CFG commands
    CMD_SOUND = True                   # Log SOUND commands
    CMD_FX = True                      # Log FX commands
    CMD_MIXER = True                   # Log MIXER commands
    CMD_MUTE = True                    # Log MUTE commands
    CMD_BT_AUDIO = True                # Log BT_AUDIO commands
    CMD_STATUS_PING = False            # Log STATUS and PING commands (can be spammy)
    
    # === SYSTEM / INITIALIZATION ===
    SYSTEM_STARTUP = True              # Log system initialization messages
    CONFIG_LOAD_SAVE = True            # Log config file operations
    ERROR_MESSAGES = True              # Always show errors (recommended: True)

debug = DebugConfig()

# ========================================================================
# ==================== END DEBUG CONFIGURATION ===========================
# ========================================================================

# -------------------- PATHS / CONFIG --------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
SOUNDS_DIR = os.path.join(BASE_DIR, "sounds")
ANNOUNCEMENTS_DIR = os.path.join(SOUNDS_DIR, "Announcements")
STARTUP_SOUNDS_DIR = os.path.join(SOUNDS_DIR, "Startup")
REMPOD_SOUNDS_DIR = os.path.join(SOUNDS_DIR, "RemPod")
MUSICBOX_SOUNDS_DIR = os.path.join(SOUNDS_DIR, "MusicBox")
LED_CONFIG_PATH = os.path.join(BASE_DIR, "oraclebox_led_config.json")
FX_CONFIG_PATH = os.path.join(BASE_DIR, "oraclebox_fx_config.json")

SUPPORTED_SOUND_EXTENSIONS = (".wav", ".mp3")
STARTUP_SOUND_TIMEOUT = 30.0  # seconds

# Sweep speeds in ms
SWEEP_SPEEDS_MS = [50, 100, 150, 200, 250, 300, 350]

# GPIO pins
SWEEP_LED_PIN = 17  # sweep indicator LED
BOX_LED_PIN = 27    # ambient box LED (PWM)

# Shared RGB LED pins (4-leg: Red + Green + Blue + Common Anode)
# Used by both REM Pod and Music Box
RGB_LED_RED = 22
RGB_LED_GREEN = 23
RGB_LED_BLUE = 24

# Bluetooth settings
BT_SERVICE_NAME = "OracleBox"
BT_UUID = "00001101-0000-1000-8000-00805F9B34FB"  # standard SPP UUID

# -------------------- STATE CLASSES --------------------

class OracleBoxState:
    def __init__(self):
        # defaults; will be overridden by config.json if present
        self.speed_index = 2          # 150 ms
        self.direction = 1            # 1 = up, -1 = down
        self.running = False          # Don't auto-start sweep; wait for START command

        # LED defaults
        self.sweep_led_mode = "on"        # classic sweep flashes
        self.box_led_mode = "flicker"     # ambient flicker

        # Empty string means "no startup sound configured"
        self.startup_sound = ""

    def to_dict(self):
        return {
            "speed_ms": SWEEP_SPEEDS_MS[self.speed_index],
            "direction": "up" if self.direction == 1 else "down",
            "running": self.running,  # Include for STATUS command, but not saved to file
            "sweep_led_mode": self.sweep_led_mode,
            "box_led_mode": self.box_led_mode,
            "startup_sound": self.startup_sound,
        }
    
    def to_config_dict(self):
        """Return dict for saving to config file (excludes running state)."""
        return {
            "speed_ms": SWEEP_SPEEDS_MS[self.speed_index],
            "direction": "up" if self.direction == 1 else "down",
            # Never save running state - always start stopped
            "sweep_led_mode": self.sweep_led_mode,
            "box_led_mode": self.box_led_mode,
            "startup_sound": self.startup_sound,
        }

    def load_from_config(self):
        if not os.path.exists(CONFIG_PATH):
            return
        try:
            with open(CONFIG_PATH, "r") as f:
                data = json.load(f)

            ms = int(data.get("speed_ms", 150))
            self.speed_index = closest_speed_index(ms)

            direction_str = data.get("direction", "up")
            self.direction = 1 if direction_str == "up" else -1

            # CRITICAL: Never load running state from config - always start stopped
            # This prevents FM passthrough from auto-playing on boot
            self.running = False
            self.sweep_led_mode = data.get("sweep_led_mode", "on")
            self.box_led_mode = data.get("box_led_mode", "flicker")
            self.startup_sound = data.get("startup_sound", "")
        except Exception as e:
            if debug.ERROR_MESSAGES:
                print("Error loading config:", e)

    def save_to_config(self):
        try:
            with open(CONFIG_PATH, "w") as f:
                json.dump(self.to_config_dict(), f, indent=2)
        except Exception as e:
            if debug.ERROR_MESSAGES:
                print("Error saving config:", e)


class RemPodState:
    """REM Pod simulation state"""
    def __init__(self):
        self.armed = False
        self.sensitivity = 3  # 1-5, default level 3
        self.alert_sound = "default.wav"  # Sound to play on trigger
        self.temp_alerts = True  # Enable temperature deviation alerts
        self.simulating = False  # True when auto-triggering simulation
        self.simulation_interval = 5.0  # seconds between auto triggers
        
    def to_dict(self):
        return {
            "armed": self.armed,
            "sensitivity": self.sensitivity,
            "alert_sound": self.alert_sound,
            "temp_alerts": self.temp_alerts,
            "simulating": self.simulating,
            "simulation_interval": self.simulation_interval,
        }


class MusicBoxState:
    """Music Box simulation state (ultrasonic motion detection)"""
    def __init__(self):
        self.active = False  # Active and monitoring
        self.calibrated = False  # Has completed initial calibration
        self.trigger_sound = "default.wav"  # Music to play on trigger
        self.detection_range = 5.0  # meters (16 ft max)
        self.simulating = False  # True when auto-triggering simulation
        self.simulation_interval = 10.0  # seconds between auto triggers
        self.last_trigger_time = 0  # timestamp of last trigger
        
    def to_dict(self):
        return {
            "active": self.active,
            "calibrated": self.calibrated,
            "trigger_sound": self.trigger_sound,
            "detection_range": self.detection_range,
            "simulating": self.simulating,
            "simulation_interval": self.simulation_interval,
        }


class LedConfig:
    """Persistent configuration for LED brightness and animation speed."""

    def __init__(self):
        # Defaults (0-255 brightness, arbitrary speed scale 1-10)
        self.sweep_min_brightness = 0
        self.sweep_max_brightness = 255
        self.sweep_speed = 3

        self.box_min_brightness = 0
        self.box_max_brightness = 255
        self.box_speed = 3

    def to_dict(self):
        return {
            "sweep_min_brightness": self.sweep_min_brightness,
            "sweep_max_brightness": self.sweep_max_brightness,
            "sweep_speed": self.sweep_speed,
            "box_min_brightness": self.box_min_brightness,
            "box_max_brightness": self.box_max_brightness,
            "box_speed": self.box_speed,
        }

    def load(self):
        if not os.path.exists(LED_CONFIG_PATH):
            return
        try:
            with open(LED_CONFIG_PATH, "r") as f:
                data = json.load(f)
            self.sweep_min_brightness = int(data.get("sweep_min_brightness", self.sweep_min_brightness))
            self.sweep_max_brightness = int(data.get("sweep_max_brightness", self.sweep_max_brightness))
            self.sweep_speed = int(data.get("sweep_speed", self.sweep_speed))
            self.box_min_brightness = int(data.get("box_min_brightness", self.box_min_brightness))
            self.box_max_brightness = int(data.get("box_max_brightness", self.box_max_brightness))
            self.box_speed = int(data.get("box_speed", self.box_speed))
        except Exception as e:
            if debug.ERROR_MESSAGES:
                print("Error loading LED config:", e)

    def save(self):
        try:
            with open(LED_CONFIG_PATH, "w") as f:
                json.dump(self.to_dict(), f, indent=2)
        except Exception as e:
            if debug.ERROR_MESSAGES:
                print("Error saving LED config:", e)


class AudioConfig:
    """Audio output device configuration."""
    
    def __init__(self):
        # Default audio device (USB card 3)
        self.default_device = "plughw:3,0"
        
        # Bluetooth audio device (MAC address or ALSA device name)
        self.bt_device = None
        self.bt_connected = False
        
        # Current active output device
        self.current_device = self.default_device
    
    def to_dict(self):
        return {
            "default_device": self.default_device,
            "bt_device": self.bt_device,
            "bt_connected": self.bt_connected,
            "current_device": self.current_device,
        }


class FxConfig:
    """Audio FX configuration for SoX effects chain."""
    
    def __init__(self):
        # Master bypass
        self.enabled = False

        # Band-pass range in Hz (FM_RAW_PORTAL defaults - Ghost Portal style)
        self.bp_low = 500
        self.bp_high = 2600

        # Reverb settings (FM_RAW_PORTAL defaults - subtle, clean)
        self.reverb_room = 30
        self.reverb_damping = 45
        self.reverb_wet = 85
        self.reverb_dry = 65

        # Extra clarity / bite (FM_RAW_PORTAL defaults - minimal for clarity)
        self.contrast_amount = 18

        # Gains in dB (FM_RAW_PORTAL defaults)
        self.pre_gain_db = -6
        self.post_gain_db = 8
        
        # Current preset name (or "CUSTOM" if manually adjusted)
        # Default to FM_RAW_PORTAL since built-in FM tuner is the default mode
        self.preset = "FM_RAW_PORTAL"

    def to_dict(self):
        return {
            "enabled": self.enabled,
            "preset": self.preset,
            "bp_low": self.bp_low,
            "bp_high": self.bp_high,
            "reverb_room": self.reverb_room,
            "reverb_damping": self.reverb_damping,
            "reverb_wet": self.reverb_wet,
            "reverb_dry": self.reverb_dry,
            "contrast_amount": self.contrast_amount,
            "pre_gain_db": self.pre_gain_db,
            "post_gain_db": self.post_gain_db,
        }

    @classmethod
    def from_dict(cls, data):
        fx = cls()
        fx.enabled = bool(data.get("enabled", fx.enabled))
        fx.preset = str(data.get("preset", fx.preset))
        fx.bp_low = int(data.get("bp_low", fx.bp_low))
        fx.bp_high = int(data.get("bp_high", fx.bp_high))
        fx.reverb_room = int(data.get("reverb_room", fx.reverb_room))
        fx.reverb_damping = int(data.get("reverb_damping", fx.reverb_damping))
        fx.reverb_wet = int(data.get("reverb_wet", fx.reverb_wet))
        fx.reverb_dry = int(data.get("reverb_dry", fx.reverb_dry))
        fx.contrast_amount = int(data.get("contrast_amount", fx.contrast_amount))
        fx.pre_gain_db = int(data.get("pre_gain_db", fx.pre_gain_db))
        fx.post_gain_db = int(data.get("post_gain_db", fx.post_gain_db))
        return fx

    def load(self):
        """Load FX config from file."""
        if not os.path.exists(FX_CONFIG_PATH):
            return
        try:
            with open(FX_CONFIG_PATH, "r") as f:
                data = json.load(f)
            loaded = self.from_dict(data)
            # Don't load enabled state - always start disabled
            # self.enabled = loaded.enabled
            self.preset = loaded.preset
            self.bp_low = loaded.bp_low
            self.bp_high = loaded.bp_high
            self.reverb_room = loaded.reverb_room
            self.reverb_damping = loaded.reverb_damping
            self.reverb_wet = loaded.reverb_wet
            self.reverb_dry = loaded.reverb_dry
            self.contrast_amount = loaded.contrast_amount
            self.pre_gain_db = loaded.pre_gain_db
            self.post_gain_db = loaded.post_gain_db
        except Exception as e:
            if debug.ERROR_MESSAGES:
                print("Error loading FX config:", e)

    def save(self):
        """Save FX config to file."""
        try:
            with open(FX_CONFIG_PATH, "w") as f:
                json.dump(self.to_dict(), f, indent=2)
        except Exception as e:
            if debug.ERROR_MESSAGES:
                print("Error saving FX config:", e)
    
    def apply_preset(self, preset_name):
        """Apply a named preset to this FxConfig instance."""
        preset_name = preset_name.upper()
        if preset_name not in FX_PRESETS:
            return False
        
        preset = FX_PRESETS[preset_name]
        self.bp_low = preset["bp_low"]
        self.bp_high = preset["bp_high"]
        self.reverb_room = preset["reverb_room"]
        self.reverb_damping = preset["reverb_damping"]
        self.reverb_wet = preset["reverb_wet"]
        self.reverb_dry = preset["reverb_dry"]
        self.contrast_amount = preset["contrast_amount"]
        self.pre_gain_db = preset["pre_gain_db"]
        self.post_gain_db = preset["post_gain_db"]
        self.preset = preset_name
        return True


# -------------------- FX PRESETS --------------------

FX_PRESETS = {
    # SB7-oriented modes (external SB7 spirit box)
    # Focus: Crystal clear voices, minimal static/noise, subtle reverb
    "SB7_CLASSIC": {
        "category": "SB7",
        "description": "Balanced portal mode - the baseline that works great",
        "bp_low": 500,
        "bp_high": 2600,
        "reverb_room": 35,
        "reverb_damping": 40,
        "reverb_wet": 100,
        "reverb_dry": 55,
        "contrast_amount": 20,
        "pre_gain_db": -6,
        "post_gain_db": 8,
    },
    "SB7_CRYSTAL_CLEAR": {
        "category": "SB7",
        "description": "Maximum voice clarity - tight vocal range, minimal noise",
        "bp_low": 550,
        "bp_high": 2400,
        "reverb_room": 32,
        "reverb_damping": 42,
        "reverb_wet": 95,
        "reverb_dry": 60,
        "contrast_amount": 17,
        "pre_gain_db": -7,
        "post_gain_db": 7,
    },
    "SB7_DEEP_VOICE": {
        "category": "SB7",
        "description": "Enhanced low frequencies for deeper male voices",
        "bp_low": 400,
        "bp_high": 2200,
        "reverb_room": 33,
        "reverb_damping": 38,
        "reverb_wet": 98,
        "reverb_dry": 57,
        "contrast_amount": 19,
        "pre_gain_db": -6,
        "post_gain_db": 9,
    },
    "SB7_HIGH_VOICE": {
        "category": "SB7",
        "description": "Enhanced high frequencies for lighter female/child voices",
        "bp_low": 600,
        "bp_high": 2800,
        "reverb_room": 34,
        "reverb_damping": 41,
        "reverb_wet": 97,
        "reverb_dry": 58,
        "contrast_amount": 18,
        "pre_gain_db": -6,
        "post_gain_db": 8,
    },
    "SB7_DYNAMIC_GATE": {
        "category": "SB7",
        "description": "Advanced multi-stage processing with dynamic compression gate",
        "bp_low": 450,
        "bp_high": 2400,
        "reverb_room": 20,
        "reverb_damping": 35,
        "reverb_wet": 45,
        "reverb_dry": 40,
        "contrast_amount": 12,
        "pre_gain_db": -6,
        "post_gain_db": 8,
    },
    "SB7_CLARITY_MAX": {
        "category": "SB7",
        "description": "Minimal static, maximal intelligibility - EVP-safe sweet spot",
        "bp_low": 420,
        "bp_high": 2850,
        "reverb_room": 22,
        "reverb_damping": 38,
        "reverb_wet": 65,
        "reverb_dry": 55,
        "contrast_amount": 17,
        "pre_gain_db": -5,
        "post_gain_db": 10,
    },
    "SB7_STATIC_KILLER": {
        "category": "SB7",
        "description": "Aggressive static reduction with enhanced voice punch",
        "bp_low": 480,
        "bp_high": 2700,
        "reverb_room": 22,
        "reverb_damping": 38,
        "reverb_wet": 70,
        "reverb_dry": 50,
        "contrast_amount": 19,
        "pre_gain_db": -5,
        "post_gain_db": 10,
    },
    
    # Built-in FM tuner modes (TEA5767 sweep)
    # Focus: Crystal clear voices, minimal static/noise, subtle reverb (Ghost Portal style)
    "FM_RAW_PORTAL": {
        "category": "FM",
        "description": "Clean voice isolation - default Ghost Portal style preset",
        "bp_low": 500,
        "bp_high": 2600,
        "reverb_room": 30,
        "reverb_damping": 45,
        "reverb_wet": 85,
        "reverb_dry": 65,
        "contrast_amount": 18,
        "pre_gain_db": -6,
        "post_gain_db": 8,
    },
    "FM_CRYSTAL_CLEAR": {
        "category": "FM",
        "description": "Maximum voice clarity - tight vocal range, minimal noise",
        "bp_low": 550,
        "bp_high": 2400,
        "reverb_room": 28,
        "reverb_damping": 48,
        "reverb_wet": 80,
        "reverb_dry": 70,
        "contrast_amount": 15,
        "pre_gain_db": -7,
        "post_gain_db": 7,
    },
    "FM_DEEP_VOICE": {
        "category": "FM",
        "description": "Enhanced low frequencies for deeper male voices",
        "bp_low": 400,
        "bp_high": 2200,
        "reverb_room": 32,
        "reverb_damping": 42,
        "reverb_wet": 90,
        "reverb_dry": 60,
        "contrast_amount": 16,
        "pre_gain_db": -6,
        "post_gain_db": 9,
    },
    "FM_HIGH_VOICE": {
        "category": "FM",
        "description": "Enhanced high frequencies for lighter female/child voices",
        "bp_low": 600,
        "bp_high": 2800,
        "reverb_room": 30,
        "reverb_damping": 46,
        "reverb_wet": 85,
        "reverb_dry": 65,
        "contrast_amount": 17,
        "pre_gain_db": -6,
        "post_gain_db": 8,
    },
    "FM_DYNAMIC_GATE": {
        "category": "FM",
        "description": "Advanced multi-stage processing with dynamic compression gate",
        "bp_low": 450,
        "bp_high": 2400,
        "reverb_room": 20,
        "reverb_damping": 35,
        "reverb_wet": 45,
        "reverb_dry": 40,
        "contrast_amount": 12,
        "pre_gain_db": -6,
        "post_gain_db": 8,
    },
    "FM_CLARITY_MAX": {
        "category": "FM",
        "description": "Definitive high-clarity FM filter - balanced intelligibility",
        "bp_low": 460,
        "bp_high": 2750,
        "reverb_room": 26,
        "reverb_damping": 40,
        "reverb_wet": 58,
        "reverb_dry": 52,
        "contrast_amount": 15,
        "pre_gain_db": -6,
        "post_gain_db": 11,
    },
    "FM_CLARITY_VOICE_ONLY": {
        "category": "FM",
        "description": "Super clean, maximum noise reduction - loud voices, minimal static",
        "bp_low": 520,
        "bp_high": 2550,
        "reverb_room": 18,
        "reverb_damping": 40,
        "reverb_wet": 48,
        "reverb_dry": 55,
        "contrast_amount": 14,
        "pre_gain_db": -7,
        "post_gain_db": 12,
    },
    "FM_EXTREME_VOICE_ONLY": {
        "category": "FM",
        "description": "Nuclear static removal - 80-85% noise cut, maximum voice boost",
        "bp_low": 600,
        "bp_high": 2400,
        "reverb_room": 10,
        "reverb_damping": 45,
        "reverb_wet": 35,
        "reverb_dry": 65,
        "contrast_amount": 20,
        "pre_gain_db": -9,
        "post_gain_db": 12,
    },
}


led_config = LedConfig()
led_config.load()

audio_config = AudioConfig()

# LEDs (real gpiozero)
sweep_led = LED(SWEEP_LED_PIN)
box_led = PWMLED(BOX_LED_PIN)

# Shared RGB LED (4-leg common anode - active_high=False inverts logic)
# Used by both REM Pod and Music Box with different color patterns
rgb_led_red = PWMLED(RGB_LED_RED, active_high=False)
rgb_led_green = PWMLED(RGB_LED_GREEN, active_high=False)
rgb_led_blue = PWMLED(RGB_LED_BLUE, active_high=False)

# REM Pod state
rempod_state = RemPodState()
rempod_lock = threading.Lock()

# Music Box state
musicbox_state = MusicBoxState()
musicbox_lock = threading.Lock()

# Lock to protect shared state between threads
state_lock = threading.Lock()
audio_lock = threading.Lock()

# -------------------- FM RADIO (TEA5767 via /dev/i2c) --------------------

TEA5767_ADDR = 0x60
I2C_BUS = 1
fm_radio_available = _fcntl_available

if _fcntl_available:
    if debug.FM_TUNER_OPERATIONS:
        print(f"[FM] I2C support available, will attempt to use TEA5767 at 0x{TEA5767_ADDR:02X}")
else:
    if debug.FM_TUNER_OPERATIONS:
        print("[FM] fcntl module not available, FM radio disabled")


def tea5767_write(freq_mhz, mono=False):
    """Write frequency to TEA5767 using raw I2C (/dev/i2c-X + fcntl).
    
    Args:
        freq_mhz: Frequency in MHz (76.0 - 108.0)
        mono: True for forced mono (clearer voices), False for stereo (more air)
    
    Uses corrected control bytes:
    - XTAL = 1 (32.768 kHz crystal)
    - PLLREF = 0
    - No search mode
    - SMUTE/HCC/SNC = 1 (noise reduction ON)
    - MS bit for mono/stereo control
    """
    if not fm_radio_available:
        return False

    try:
        # Calculate PLL value (high-side injection)
        pll = int(4 * ((freq_mhz * 1_000_000) + 225_000) / 32_768)

        # Build 5-byte control sequence
        byte1 = (pll >> 8) & 0x3F   # PLL13..8, mute/search = 0
        byte2 = pll & 0xFF          # PLL7..0
        
        # Byte 3: high-side injection, mono/stereo control
        if mono:
            byte3 = 0x18            # High-side, forced mono
        else:
            byte3 = 0x10            # High-side, stereo
        
        byte4 = 0x1E                # XTAL=32.768kHz, SMUTE/HCC/SNC=1 (noise reduction)
        byte5 = 0x00                # PLLREF=0, no test bits
        
        data = [byte1, byte2, byte3, byte4, byte5]

        # Write using raw I2C
        with open(f"/dev/i2c-{I2C_BUS}", "r+b", buffering=0) as f:
            fcntl.ioctl(f, 0x0703, TEA5767_ADDR)  # I2C_SLAVE
            f.write(bytearray(data))
        return True
    except Exception as e:
        if debug.ERROR_MESSAGES:
            print(f"[FM] Error writing to TEA5767: {e}")
        return False


def check_tea5767():
    """Check if TEA5767 is present on I2C bus."""
    global fm_radio_available
    if not fm_radio_available:
        if debug.FM_TUNER_OPERATIONS:
            print("[FM] I2C support not available")
        return False

    try:
        with open(f"/dev/i2c-{I2C_BUS}", "r+b", buffering=0) as f:
            fcntl.ioctl(f, 0x0703, TEA5767_ADDR)  # I2C_SLAVE
            data = f.read(5)
            print(f"[FM] TEA5767 found at 0x{TEA5767_ADDR:02X}, status bytes: {[hex(b) for b in data]}")
            return True
    except FileNotFoundError:
        print(f"[FM] I2C bus /dev/i2c-{I2C_BUS} not found - is I2C enabled?")
        fm_radio_available = False
        return False
    except OSError as e:
        print(f"[FM] TEA5767 not responding at 0x{TEA5767_ADDR:02X}: {e}")
        return False
    except Exception as e:
        print(f"[FM] Error checking TEA5767: {e}")
        return False


def set_freq(freq_mhz):
    """Set FM radio frequency via TEA5767."""
    if not fm_radio_available:
        return False

    success = tea5767_write(freq_mhz)
    if success and debug.SWEEP_FREQUENCY_CHANGES:
        print(f"[FM] Tuned to {freq_mhz:.1f} MHz")
    return success


# -------------------- HELPERS --------------------

def closest_speed_index(ms):
    closest = 0
    best_diff = 999999
    for i, preset in enumerate(SWEEP_SPEEDS_MS):
        diff = abs(ms - preset)
        if diff < best_diff:
            best_diff = diff
            closest = i
    return closest


def current_delay_seconds():
    with state_lock:
        return SWEEP_SPEEDS_MS[state.speed_index] / 1000.0


def _apply_mode_to_led(mode, led, is_pwm=True):
    """Apply a single LED mode to a gpiozero LED/PWMLED."""
    import random
    import math

    # Stop any existing animations
    if is_pwm:
        led.source = None
    
    # Basic on/off
    if mode == "on":
        if is_pwm:
            led.value = 1.0
        else:
            led.on()
        return

    if mode == "off":
        if is_pwm:
            led.value = 0.0
        else:
            led.off()
        return

    # Breathing modes (PWM only) - use source pattern
    if mode == "breath" and is_pwm:
        speed_scale = max(1, min(10, led_config.box_speed))
        factor = 11 - speed_scale
        period = 1.0 * factor / 3.0  # Breathing period in seconds
        
        def breath_pattern():
            step = 0
            while True:
                # Sine wave for smooth breathing
                val = (math.sin(step) + 1) / 2  # 0 to 1
                span = max(0, led_config.box_max_brightness - led_config.box_min_brightness)
                brightness = led_config.box_min_brightness + val * span
                yield max(0.0, min(1.0, brightness / 255.0))
                step += 0.1
        
        led.source_delay = 0.05
        led.source = breath_pattern()
        return

    if mode == "breath_fast" and is_pwm:
        speed_scale = max(1, min(10, led_config.box_speed))
        factor = 11 - speed_scale
        
        def breath_fast_pattern():
            step = 0
            while True:
                val = (math.sin(step * 3) + 1) / 2  # Faster sine wave
                span = max(0, led_config.box_max_brightness - led_config.box_min_brightness)
                brightness = led_config.box_min_brightness + val * span
                yield max(0.0, min(1.0, brightness / 255.0))
                step += 0.1
        
        led.source_delay = 0.03
        led.source = breath_fast_pattern()
        return

    # Heartbeat pattern - double pulse then pause
    if mode == "heartbeat":
        speed_scale = max(1, min(10, led_config.sweep_speed if not is_pwm else led_config.box_speed))
        
        def heartbeat_pattern():
            while True:
                yield 1.0  # First beat
                yield 1.0
                yield 0.0
                yield 1.0  # Second beat
                yield 1.0
                yield 0.0
                yield 0.0  # Pause
                yield 0.0
                yield 0.0
        
        delay = 0.08 * (11 - speed_scale) / 6.0
        if is_pwm:
            led.source_delay = delay
            led.source = heartbeat_pattern()
        else:
            # For regular LED, use values generator
            led.source = heartbeat_pattern()
            led.source_delay = delay
        return

    # Strobe pattern - rapid on/off
    if mode == "strobe":
        speed_scale = max(1, min(10, led_config.sweep_speed if not is_pwm else led_config.box_speed))
        
        def strobe_pattern():
            while True:
                yield 1.0
                yield 0.0
        
        delay = 0.05 * (11 - speed_scale) / 6.0
        if is_pwm:
            led.source_delay = delay
            led.source = strobe_pattern()
        else:
            led.source = strobe_pattern()
            led.source_delay = delay
        return

    # Flicker / random_burst (PWM only)
    if mode == "flicker" and is_pwm:
        def flicker_pattern():
            while True:
                raw = random.uniform(0.2, 1.0)
                span = max(0, led_config.box_max_brightness - led_config.box_min_brightness)
                val = led_config.box_min_brightness + raw * span
                yield max(0.0, min(1.0, val / 255.0))

        speed_scale = max(1, min(10, led_config.box_speed))
        led.source_delay = 0.08 * (11 - speed_scale) / 6.0
        led.source = flicker_pattern()
        return

    if mode == "random_burst" and is_pwm:
        def burst_pattern():
            while True:
                if random.random() < 0.1:
                    val = led_config.box_max_brightness
                    yield max(0.0, min(1.0, val / 255.0))
                else:
                    raw = random.uniform(0.0, 0.3)
                    span = max(0, led_config.box_max_brightness - led_config.box_min_brightness)
                    val = led_config.box_min_brightness + raw * span
                    yield max(0.0, min(1.0, val / 255.0))

        speed_scale = max(1, min(10, led_config.box_speed))
        led.source_delay = 0.15 * (11 - speed_scale) / 6.0
        led.source = burst_pattern()
        return

    # "sweep" mode is driven explicitly from sweep_thread; keep LED idle here
    if mode == "sweep":
        if is_pwm:
            led.value = 0.0
        else:
            led.off()
        return

    # Unknown mode: treat as off
    if is_pwm:
        led.value = 0.0
    else:
        led.off()


def apply_led_modes():
    """Apply current LED animation modes to the physical LEDs."""
    with state_lock:
        sweep_mode = state.sweep_led_mode
        box_mode = state.box_led_mode

    _apply_mode_to_led(sweep_mode, sweep_led, is_pwm=False)
    _apply_mode_to_led(box_mode, box_led, is_pwm=True)


def _player_command_for(path):
    """Resolve the correct playback command for a sound file."""
    _, ext = os.path.splitext(path.lower())
    if ext == ".mp3":
        return ["mpg123", "-q", path], "mpg123"
    if ext == ".wav":
        return ["aplay", "-q", path], "aplay"
    return None, None


def _blocking_playback(cmd, player, timeout_s=None):
    """Run a playback command synchronously and surface stdout/stderr."""
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_s,
            check=False,
        )
        if result.stdout:
            print(f"[{player}] stdout: {result.stdout.decode(errors='ignore').strip()}")
        if result.stderr:
            print(f"[{player}] stderr: {result.stderr.decode(errors='ignore').strip()}")
        return result.returncode
    except subprocess.TimeoutExpired as exc:
        print(f"{player} timed out after {timeout_s}s; stopping playback")
        try:
            exc.process.kill()
        except Exception:
            pass
        return -1


def play_sound(name=None):
    """Play a sound file (WAV via aplay, MP3 via mpg123).
    Temporarily stops FX to avoid audio device conflicts."""
    if name is None:
        with state_lock:
            name = state.startup_sound

    if not name:
        print("No sound configured")
        return

    # Check in order: Announcements, Startup, RemPod, MusicBox, sounds root
    path = os.path.join(ANNOUNCEMENTS_DIR, name)
    if not os.path.exists(path):
        path = os.path.join(STARTUP_SOUNDS_DIR, name)
        if not os.path.exists(path):
            path = os.path.join(REMPOD_SOUNDS_DIR, name)
            if not os.path.exists(path):
                path = os.path.join(MUSICBOX_SOUNDS_DIR, name)
                if not os.path.exists(path):
                    path = os.path.join(SOUNDS_DIR, name)
                    if not os.path.exists(path):
                        print("Sound file not found:", name)
                        return

    cmd, player = _player_command_for(path)
    if not cmd:
        print("Unsupported sound format:", path)
        return

    # Pause FX to free audio device
    global _fx_proc, _fx_needs_restart
    fx_was_running = (_fx_proc is not None)
    if fx_was_running:
        if debug.SOUND_PLAYBACK:
            print("[SOUND] Pausing FX for announcement playback")
        _stop_fx_proc()

    try:
        # Play and wait for completion
        proc = subprocess.Popen(cmd)
        print(f"Playing sound via {player}: {name}")
        proc.wait()  # Wait for sound to finish
        if debug.SOUND_PLAYBACK:
            print(f"[SOUND] Playback complete: {name}")
    except FileNotFoundError:
        print(f"{player} not installed. Install it or convert files to WAV.")
    except Exception as e:
        print("Error playing sound:", e)
    finally:
        # Resume FX if it was running
        if fx_was_running:
            if debug.SOUND_PLAYBACK:
                print("[SOUND] Resuming FX")
            _fx_needs_restart = True


def list_sounds(folder=None):
    """List sound files, optionally from a specific subfolder.
    Args:
        folder: None for all sounds, or 'startup', 'rempod', 'musicbox', 'announcements'
    """
    if folder:
        folder_map = {
            'startup': STARTUP_SOUNDS_DIR,
            'rempod': REMPOD_SOUNDS_DIR,
            'musicbox': MUSICBOX_SOUNDS_DIR,
            'announcements': ANNOUNCEMENTS_DIR
        }
        target_dir = folder_map.get(folder.lower())
        if not target_dir or not os.path.exists(target_dir):
            return []
        return sorted(
            [
                f
                for f in os.listdir(target_dir)
                if os.path.splitext(f.lower())[1] in SUPPORTED_SOUND_EXTENSIONS
            ]
        )
    
    # Return all sounds from all folders
    if not os.path.exists(SOUNDS_DIR):
        return []
    
    all_sounds = []
    # Root sounds directory
    if os.path.exists(SOUNDS_DIR):
        all_sounds.extend([
            f for f in os.listdir(SOUNDS_DIR)
            if os.path.isfile(os.path.join(SOUNDS_DIR, f)) and
            os.path.splitext(f.lower())[1] in SUPPORTED_SOUND_EXTENSIONS
        ])
    
    # All subdirectories
    for subdir in [ANNOUNCEMENTS_DIR, STARTUP_SOUNDS_DIR, REMPOD_SOUNDS_DIR, MUSICBOX_SOUNDS_DIR]:
        if os.path.exists(subdir):
            all_sounds.extend([
                f for f in os.listdir(subdir)
                if os.path.splitext(f.lower())[1] in SUPPORTED_SOUND_EXTENSIONS
            ])
    
    return sorted(list(set(all_sounds)))  # Remove duplicates


# -------------------- REM POD SIMULATION HELPERS --------------------

def _rgb_led_off():
    """Turn off RGB LED"""
    rgb_led_red.off()
    rgb_led_green.off()
    rgb_led_blue.off()


def _rempod_leds_off():
    """Turn off all REM Pod LEDs (uses shared RGB)"""
    _rgb_led_off()


def _rempod_set_sensitivity_leds(level):
    """Display sensitivity level with LED pattern (1-5)
    Level 1 = Purple (R+B)
    Level 2 = Purple + Red flash
    Level 3 = Purple + Red + Blue flash
    Level 4 = Purple + Red + Blue + Yellow (R+G)
    Level 5 = All colors cycle
    """
    _rempod_leds_off()
    time.sleep(0.1)
    
    # Purple (R+B) - always on for any level
    if level >= 1:
        rgb_led_red.value = 0.5
        rgb_led_blue.value = 0.5
        time.sleep(0.3)
    
    # Add Red flash
    if level >= 2:
        rgb_led_red.value = 1.0
        time.sleep(0.3)
        rgb_led_red.value = 0.5
    
    # Add Blue flash
    if level >= 3:
        rgb_led_blue.value = 1.0
        time.sleep(0.3)
        rgb_led_blue.value = 0.5
    
    # Add Yellow (R+G) flash
    if level >= 4:
        rgb_led_red.value = 1.0
        rgb_led_green.value = 1.0
        time.sleep(0.3)
        rgb_led_red.value = 0.5
        rgb_led_green.value = 0.0
    
    # Add Green flash
    if level >= 5:
        rgb_led_green.value = 1.0
        time.sleep(0.3)
    
    # Return to dim purple indicator
    _rempod_leds_off()
    rgb_led_red.value = 0.2
    rgb_led_blue.value = 0.2


def _rempod_trigger(trigger_type="EMF"):
    """Trigger REM Pod alert with LED and sound
    
    Args:
        trigger_type: "EMF", "TEMP_HOT", "TEMP_COLD", or sensitivity level 1-5
    """
    with rempod_lock:
        if not rempod_state.armed:
            return
        
        sound = rempod_state.alert_sound
    
    # LED patterns based on trigger type
    if trigger_type == "TEMP_HOT":
        # Red LED with ascending tone pattern
        for i in range(3):
            rgb_led_red.value = 1.0
            time.sleep(0.15)
            rgb_led_red.value = 0.0
            time.sleep(0.1)
    
    elif trigger_type == "TEMP_COLD":
        # Blue LED with descending tone pattern
        for i in range(3):
            rgb_led_blue.value = 1.0
            time.sleep(0.15)
            rgb_led_blue.value = 0.0
            time.sleep(0.1)
    
    else:
        # EMF trigger - cycle through colors
        colors = [
            (1.0, 0.0, 0.0),  # Red
            (0.0, 1.0, 0.0),  # Green
            (0.0, 0.0, 1.0),  # Blue
            (1.0, 1.0, 0.0),  # Yellow
        ]
        
        for r, g, b in colors:
            rgb_led_red.value = r
            rgb_led_green.value = g
            rgb_led_blue.value = b
            time.sleep(0.1)
    
    _rempod_leds_off()
    
    # Play alert sound from RemPod folder
    if sound:
        try:
            path = os.path.join(REMPOD_SOUNDS_DIR, sound)
            if not os.path.exists(path):
                path = os.path.join(SOUNDS_DIR, sound)
            
            if os.path.exists(path):
                threading.Thread(target=play_sound, args=(sound,), daemon=True).start()
        except Exception as e:
            if debug.ERROR_MESSAGES:
                print(f"[REMPOD] Error playing sound: {e}")


def rempod_simulation_thread():
    """Background thread for auto-triggering REM Pod alerts during simulation"""
    import random
    
    if debug.SYSTEM_STARTUP:
        print("[REMPOD] Simulation thread started")
    
    while True:
        with rempod_lock:
            simulating = rempod_state.simulating
            armed = rempod_state.armed
            interval = rempod_state.simulation_interval
            temp_enabled = rempod_state.temp_alerts
        
        if simulating and armed:
            # Random trigger type
            trigger_types = ["EMF"]
            if temp_enabled:
                trigger_types.extend(["TEMP_HOT", "TEMP_COLD"])
            
            trigger = random.choice(trigger_types)
            _rempod_trigger(trigger)
            
            if debug.SYSTEM_STARTUP:
                print(f"[REMPOD] Auto-triggered: {trigger}")
            
            time.sleep(interval)
        else:
            time.sleep(1.0)


# -------------------- MUSIC BOX SIMULATION HELPERS --------------------

def _musicbox_calibrate():
    """Calibrate Music Box - flash LED and play calibration tune"""
    if debug.SYSTEM_STARTUP:
        print("[MUSICBOX] Calibrating...")
    
    # Flash cyan (G+B) LED during calibration
    for i in range(3):
        rgb_led_green.value = 1.0
        rgb_led_blue.value = 1.0
        time.sleep(0.3)
        _rgb_led_off()
        time.sleep(0.2)
    
    with musicbox_lock:
        musicbox_state.calibrated = True
    
    if debug.SYSTEM_STARTUP:
        print("[MUSICBOX] Calibration complete")


def _musicbox_trigger():
    """Trigger Music Box - light LED and play creepy music"""
    with musicbox_lock:
        if not musicbox_state.active or not musicbox_state.calibrated:
            return
        
        sound = musicbox_state.trigger_sound
        musicbox_state.last_trigger_time = time.time()
    
    if debug.SYSTEM_STARTUP:
        print("[MUSICBOX] Motion detected! Playing music...")
    
    # Turn on green LED (different from REM Pod colors)
    rgb_led_green.value = 1.0
    
    # Play creepy music from MusicBox folder
    if sound:
        try:
            path = os.path.join(MUSICBOX_SOUNDS_DIR, sound)
            if not os.path.exists(path):
                path = os.path.join(SOUNDS_DIR, sound)
            
            if os.path.exists(path):
                threading.Thread(target=play_sound, args=(sound,), daemon=True).start()
        except Exception as e:
            if debug.ERROR_MESSAGES:
                print(f"[MUSICBOX] Error playing sound: {e}")
    
    # Keep LED on for duration of music (simulate)
    time.sleep(3.0)
    _rgb_led_off()


def musicbox_simulation_thread():
    """Background thread for auto-triggering Music Box during simulation"""
    import random
    
    if debug.SYSTEM_STARTUP:
        print("[MUSICBOX] Simulation thread started")
    
    while True:
        with musicbox_lock:
            simulating = musicbox_state.simulating
            active = musicbox_state.active
            interval = musicbox_state.simulation_interval
        
        if simulating and active:
            # Random delay within interval (simulate random motion)
            delay = interval * random.uniform(0.5, 1.5)
            time.sleep(delay)
            
            _musicbox_trigger()
            
            if debug.SYSTEM_STARTUP:
                print(f"[MUSICBOX] Auto-triggered (next in ~{interval}s)")
        else:
            time.sleep(1.0)


# -------------------- BLUETOOTH AUDIO HELPERS --------------------

def list_bt_audio_devices():
    """List available Bluetooth audio devices (paired and connected)."""
    if debug.BT_AUDIO_OPERATIONS:
        print("[BT AUDIO] Scanning for paired devices...")
    try:
        # Get paired devices
        result = subprocess.run(
            ["bluetoothctl", "devices"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5
        )
        
        if result.returncode != 0:
            if debug.BT_AUDIO_OPERATIONS:
                print("[BT AUDIO] bluetoothctl not available")
            return {"error": "bluetoothctl not available"}
        
        devices = []
        for line in result.stdout.strip().split('\n'):
            if line.startswith("Device "):
                parts = line.split(maxsplit=2)
                if len(parts) >= 3:
                    mac = parts[1]
                    name = parts[2]
                    
                    # Check if connected
                    info_result = subprocess.run(
                        ["bluetoothctl", "info", mac],
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=3
                    )
                    
                    connected = "Connected: yes" in info_result.stdout
                    
                    devices.append({
                        "mac": mac,
                        "name": name,
                        "connected": connected
                    })
                    
                    if debug.BT_AUDIO_OPERATIONS:
                        status = "connected" if connected else "paired"
                        print(f"[BT AUDIO] Found {name} ({mac}) - {status}")
        
        if debug.BT_AUDIO_OPERATIONS:
            print(f"[BT AUDIO] Scan complete: {len(devices)} device(s) found")
        return {"devices": devices}
    
    except Exception as e:
        if debug.ERROR_MESSAGES:
            print(f"[BT AUDIO] list_bt_audio_devices error: {e}")
        return {"error": str(e)}


def discover_bt_devices():
    """List paired Bluetooth devices."""
    # Just return already paired devices - user will pair manually via bluetoothctl
    return list_bt_audio_devices()


def pair_bt_device(mac_address):
    """Pair with a Bluetooth device."""
    if debug.BT_AUDIO_OPERATIONS:
        print(f"[BT AUDIO] Pairing with {mac_address}...")
    try:
        # Pair device
        result = subprocess.run(
            ["bluetoothctl", "pair", mac_address],
            capture_output=True,
            text=True,
            check=False,
            timeout=30
        )
        
        if result.returncode != 0 or "Failed" in result.stdout:
            if debug.BT_AUDIO_OPERATIONS:
                print(f"[BT AUDIO] Pairing failed: {result.stdout.strip()}")
            return False
        
        # Trust the device so it auto-connects in future
        subprocess.run(
            ["bluetoothctl", "trust", mac_address],
            capture_output=True,
            text=True,
            check=False,
            timeout=5
        )
        
        if debug.BT_AUDIO_OPERATIONS:
            print(f"[BT AUDIO] Successfully paired with {mac_address}")
        return True
    
    except Exception as e:
        if debug.ERROR_MESSAGES:
            print(f"[BT AUDIO] pair error: {e}")
        return False


def connect_bt_device(mac_address):
    """Connect to a Bluetooth device by MAC address."""
    if debug.BT_AUDIO_OPERATIONS:
        print(f"[BT AUDIO] Connecting to {mac_address}...")
    try:
        # Connect device
        result = subprocess.run(
            ["bluetoothctl", "connect", mac_address],
            capture_output=True,
            text=True,
            check=False,
            timeout=10
        )
        
        if result.returncode != 0 or "Failed" in result.stdout:
            if debug.BT_AUDIO_OPERATIONS:
                print(f"[BT AUDIO] Connection failed: {result.stdout.strip()}")
            return False
        
        # Wait a moment for audio profile to connect
        if debug.BT_AUDIO_OPERATIONS:
            print(f"[BT AUDIO] Device connected, waiting for audio profile...")
        time.sleep(2)
        
        if debug.BT_AUDIO_OPERATIONS:
            print(f"[BT AUDIO] Successfully connected to {mac_address}")
        return True
    
    except Exception as e:
        if debug.ERROR_MESSAGES:
            print(f"[BT AUDIO] connect error: {e}")
        return False


def disconnect_bt_device(mac_address):
    """Disconnect a Bluetooth device."""
    if debug.BT_AUDIO_OPERATIONS:
        print(f"[BT AUDIO] Disconnecting {mac_address}...")
    try:
        result = subprocess.run(
            ["bluetoothctl", "disconnect", mac_address],
            capture_output=True,
            text=True,
            check=False,
            timeout=5
        )
        
        if result.returncode == 0:
            if debug.BT_AUDIO_OPERATIONS:
                print(f"[BT AUDIO] Successfully disconnected {mac_address}")
        else:
            if debug.BT_AUDIO_OPERATIONS:
                print(f"[BT AUDIO] Disconnect failed: {result.stdout.strip()}")
        return result.returncode == 0
    
    except Exception as e:
        if debug.ERROR_MESSAGES:
            print(f"[BT AUDIO] disconnect error: {e}")
        return False


def get_bt_audio_sink():
    """Get the PulseAudio/ALSA sink name for Bluetooth audio output."""
    if debug.BT_AUDIO_OPERATIONS:
        print("[BT AUDIO] Looking for Bluetooth audio sink...")
    try:
        # Try to find bluez sink in pactl
        result = subprocess.run(
            ["pactl", "list", "short", "sinks"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5
        )
        
        if result.returncode == 0:
            if debug.BT_AUDIO_OPERATIONS:
                print(f"[BT AUDIO] Available sinks:\n{result.stdout.strip()}")
            for line in result.stdout.strip().split('\n'):
                if "bluez" in line.lower():
                    sink_name = line.split()[1]
                    if debug.BT_AUDIO_OPERATIONS:
                        print(f"[BT AUDIO] Found Bluetooth sink: {sink_name}")
                    return sink_name
        
        if debug.BT_AUDIO_OPERATIONS:
            print("[BT AUDIO] No Bluetooth audio sink found")
        return None
    
    except Exception as e:
        if debug.ERROR_MESSAGES:
            print(f"[BT AUDIO] get_bt_audio_sink error: {e}")
        return None


def set_audio_output_device(device):
    """Set the current audio output device and restart audio processes."""
    global _fx_needs_restart, _passthrough_proc
    
    if debug.AUDIO_DEVICE_CHANGES:
        print(f"[AUDIO] Switching output device to: {device}")
    
    with audio_lock:
        audio_config.current_device = device
    
    # Restart FX process to use new device
    _fx_needs_restart = True
    if debug.AUDIO_DEVICE_CHANGES:
        print("[AUDIO] FX restart flagged for device change")
    
    # Stop and restart passthrough if it was running
    was_running = _passthrough_proc is not None
    if was_running:
        if debug.AUDIO_DEVICE_CHANGES:
            print("[AUDIO] Restarting passthrough with new device...")
        _stop_passthrough()
        time.sleep(0.3)  # Give audio system time to stabilize
        _start_passthrough()
    
    if debug.AUDIO_DEVICE_CHANGES:
        print(f"[AUDIO] Output device switched successfully")


# -------------------- ALSA MIXER HELPERS --------------------

def get_mixer_status():
    """Get current ALSA mixer state for USB card 3."""
    try:
        result = subprocess.run(
            ["amixer", "-c", "3", "contents"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5
        )
        if result.returncode != 0:
            return {"error": "amixer command failed"}
        
        output = result.stdout
        state = {
            "speaker_volume": 0,
            "speaker_switch": False,
            "mic_playback_volume": 0,
            "mic_playback_switch": False,
            "mic_capture_volume": 0,
            "mic_capture_switch": False,
            "auto_gain": False
        }
        
        lines = output.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # numid=3: Mic Playback Switch
            if "numid=3" in line and i + 1 < len(lines):
                val_line = lines[i + 1]
                state["mic_playback_switch"] = "values=on" in val_line
            
            # numid=4: Mic Playback Volume
            elif "numid=4" in line and i + 1 < len(lines):
                val_line = lines[i + 1]
                try:
                    if "values=" in val_line:
                        val = val_line.split("values=")[1].split(",")[0].strip()
                        state["mic_playback_volume"] = int(val)
                except (IndexError, ValueError):
                    pass
            
            # numid=5: Speaker Playback Switch
            elif "numid=5" in line and i + 1 < len(lines):
                val_line = lines[i + 1]
                state["speaker_switch"] = "values=on" in val_line
            
            # numid=6: Speaker Playback Volume
            elif "numid=6" in line and i + 1 < len(lines):
                val_line = lines[i + 1]
                try:
                    if "values=" in val_line:
                        val = val_line.split("values=")[1].split(",")[0].strip()
                        state["speaker_volume"] = int(val)
                except (IndexError, ValueError):
                    pass
            
            # numid=7: Mic Capture Switch
            elif "numid=7" in line and i + 1 < len(lines):
                val_line = lines[i + 1]
                state["mic_capture_switch"] = "values=on" in val_line
            
            # numid=8: Mic Capture Volume
            elif "numid=8" in line and i + 1 < len(lines):
                val_line = lines[i + 1]
                try:
                    if "values=" in val_line:
                        val = val_line.split("values=")[1].split(",")[0].strip()
                        state["mic_capture_volume"] = int(val)
                except (IndexError, ValueError):
                    pass
            
            # numid=9: Auto Gain Control
            elif "numid=9" in line and i + 1 < len(lines):
                val_line = lines[i + 1]
                state["auto_gain"] = "values=on" in val_line
            
            i += 1
        
        return state
    
    except Exception as e:
        print(f"[MIXER] get_mixer_status error: {e}")
        return {"error": str(e)}


def set_speaker_volume(level):
    """Set speaker playback volume for USB card 3 (0-37)."""
    try:
        level = max(0, min(37, int(level)))
        
        # Set volume
        result = subprocess.run(
            ["amixer", "-c", "3", "cset", "numid=6", str(level)],
            capture_output=True,
            check=False,
            timeout=5
        )
        if result.returncode != 0:
            print(f"[MIXER] set_speaker_volume failed: {result.stderr.decode()}")
            return False
        
        # Ensure speaker switch is ON
        subprocess.run(
            ["amixer", "-c", "3", "cset", "numid=5", "on"],
            capture_output=True,
            check=False,
            timeout=5
        )
        
        return True
    
    except Exception as e:
        print(f"[MIXER] set_speaker_volume error: {e}")
        return False


def set_mic_volume(level):
    """Set mic capture volume for USB card 3 (0-35)."""
    try:
        level = max(0, min(35, int(level)))
        
        result = subprocess.run(
            ["amixer", "-c", "3", "cset", "numid=8", str(level)],
            capture_output=True,
            check=False,
            timeout=5
        )
        if result.returncode != 0:
            print(f"[MIXER] set_mic_volume failed: {result.stderr.decode()}")
            return False
        
        return True
    
    except Exception as e:
        print(f"[MIXER] set_mic_volume error: {e}")
        return False


def set_auto_gain(enabled):
    """Set auto gain control for USB card 3."""
    try:
        val = "on" if enabled else "off"
        
        result = subprocess.run(
            ["amixer", "-c", "3", "cset", "numid=9", val],
            capture_output=True,
            check=False,
            timeout=5
        )
        if result.returncode != 0:
            print(f"[MIXER] set_auto_gain failed: {result.stderr.decode()}")
            return False
        
        return True
    
    except Exception as e:
        print(f"[MIXER] set_auto_gain error: {e}")
        return False


def set_speaker_mute(muted):
    """Set speaker mute state for USB card 3 (numid=5 Speaker Playback Switch)."""
    try:
        val = "off" if muted else "on"
        
        result = subprocess.run(
            ["amixer", "-c", "3", "cset", "numid=5", val],
            capture_output=True,
            check=False,
            timeout=5
        )
        if result.returncode != 0:
            print(f"[MIXER] set_speaker_mute failed: {result.stderr.decode()}")
            return False
        
        print(f"[MIXER] Speaker mute set to: {muted}")
        return True
    
    except Exception as e:
        print(f"[MIXER] set_speaker_mute error: {e}")
        return False


# -------------------- GLOBAL STATE --------------------

state = OracleBoxState()
state.load_from_config()

fx_config = FxConfig()
fx_config.load()
fx_lock = threading.Lock()

_fx_proc = None  # type: subprocess.Popen | None
_fx_needs_restart = False

# FM audio passthrough (raw FM → speaker when FX is off)
_passthrough_proc = None


# -------------------- SOX FX HELPERS --------------------

def build_sox_cmd_from_fx():
    """Build pure ALSA FX pipeline using arecord | sox | aplay (matches manual test base)."""
    with fx_lock:
        fx = fx_config

        if not fx.enabled:
            return None

        # Clamp values to safe ranges
        bp_low = max(100, min(2000, fx.bp_low))
        bp_high = max(bp_low + 200, min(5000, fx.bp_high))
        contrast_amount = max(0, min(40, fx.contrast_amount))
        pre_gain = max(-24, min(0, fx.pre_gain_db))
        post_gain = max(0, min(18, fx.post_gain_db))
        room = max(0, min(100, fx.reverb_room))
        damp = max(0, min(100, fx.reverb_damping))
        wet = max(0, min(100, fx.reverb_wet))
        dry = max(0, min(100, fx.reverb_dry))
    
    with audio_lock:
        output_device = audio_config.current_device

    # Pure ALSA pipeline - same base as manual test, then add user FX on top
    # This bypasses PulseAudio to get the same clean, dynamic audio
    
    # Build the sox effects chain
    effects = [
        "highpass", "250",
        "lowpass", "4800",
        "compand", "0.08,0.2", "-28,-18", "6",
        "gain", str(pre_gain),
        "sinc", f"{bp_low}-{bp_high}",
    ]
    
    if contrast_amount > 0:
        effects += ["contrast", str(contrast_amount)]
    
    effects += [
        "reverb", str(room), str(damp), str(wet), str(dry),
        "gain", str(post_gain),
        "remix", "1,2", "1,2",  # Convert mono FM to stereo by mixing both input channels to both output channels
    ]
    
    # Join effects with spaces for shell command
    sox_effects = " ".join(effects)

    # Use shell pipeline: arecord | sox | aplay (pure ALSA, no PulseAudio)
    cmd = [
        "sh", "-c",
        f"arecord -D plughw:3,0 -f S16_LE -r 48000 -c 2 | "
        f"sox -t wav - -t wav - {sox_effects} | "
        f"aplay -D {output_device}"
    ]

    return cmd


def _stop_fx_proc():
    global _fx_proc
    if _fx_proc is not None:
        try:
            # Kill entire process group (shell + arecord + sox + aplay)
            try:
                os.killpg(os.getpgid(_fx_proc.pid), signal.SIGTERM)
                time.sleep(0.3)
                # Force kill if still running
                try:
                    os.killpg(os.getpgid(_fx_proc.pid), signal.SIGKILL)
                except Exception:
                    pass
            except Exception:
                # Fallback to regular terminate
                _fx_proc.terminate()
                _fx_proc.wait(timeout=2.0)
        except Exception:
            try:
                _fx_proc.kill()
            except Exception:
                pass
        _fx_proc = None
        # Extra time for ALSA to fully release the audio devices
        time.sleep(0.5)


def _start_passthrough():
    """Start pure ALSA FM audio passthrough - matches manual test exactly."""
    global _passthrough_proc
    if _passthrough_proc is not None:
        return
    
    with audio_lock:
        output_device = audio_config.current_device
    
    # Pure ALSA pipeline - EXACT match to manual test for perfect audio quality
    # This bypasses PulseAudio completely to get raw, clean, dynamic audio
    # Convert mono FM to stereo output by duplicating to both speakers
    cmd = [
        "sh", "-c",
        f"arecord -D plughw:3,0 -f S16_LE -r 48000 -c 2 | "
        f"sox -t wav - -t wav - highpass 250 lowpass 4800 compand 0.08,0.2 -28,-18 6 gain -3 remix 1,2 1,2 | "
        f"aplay -D {output_device}"
    ]
    
    if debug.AUDIO_PASSTHROUGH:
        print(f"[AUDIO] Pure ALSA passthrough command: {cmd[2]}")
    
    try:
        # Start with new process group so we can kill entire pipeline
        _passthrough_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid,  # Create new process group
        )
        if debug.AUDIO_PASSTHROUGH:
            print(f"[AUDIO] Pure ALSA passthrough started (no PulseAudio) to {output_device}")
    except Exception as e:
        if debug.ERROR_MESSAGES:
            print(f"[AUDIO] ERROR starting passthrough: {e}")
        _passthrough_proc = None


def _stop_passthrough():
    """Stop FM audio passthrough and ensure devices are fully released."""
    global _passthrough_proc
    if _passthrough_proc:
        try:
            # Kill entire process group (shell + arecord + sox + aplay)
            try:
                os.killpg(os.getpgid(_passthrough_proc.pid), signal.SIGTERM)
                time.sleep(0.3)
                # Force kill if still running
                try:
                    os.killpg(os.getpgid(_passthrough_proc.pid), signal.SIGKILL)
                except Exception:
                    pass
            except Exception:
                # Fallback to regular terminate
                _passthrough_proc.terminate()
                try:
                    _passthrough_proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    _passthrough_proc.kill()
                    _passthrough_proc.wait()
        except Exception:
            pass
        _passthrough_proc = None
        if debug.AUDIO_PASSTHROUGH:
            print("[AUDIO] FM passthrough stopped (process group killed)")
        # Extra time for ALSA to fully release the audio devices
        time.sleep(0.5)


# -------------------- COMMAND API --------------------

def handle_command(command):
    command = command.strip()
    if not command:
        return "ERR Empty command"

    parts = command.split()
    cmd = parts[0].upper()
    args = parts[1:]

    global state, _fx_needs_restart

    if cmd == "STATUS":
        with state_lock:
            data = state.to_dict()
            data.update(led_config.to_dict())
        # Add muted state from mixer
        mixer_info = get_mixer_status()
        data["muted"] = not mixer_info.get("speaker_switch", False)
        return "OK " + json.dumps(data)

    if cmd == "PING":
        with state_lock:
            payload = {
                "ok": True,
                "speed_ms": SWEEP_SPEEDS_MS[state.speed_index],
                "direction": "up" if state.direction == 1 else "down",
                "running": state.running,
                "sweep_led_mode": state.sweep_led_mode,
                "box_led_mode": state.box_led_mode,
                "startup_sound": state.startup_sound or "",
            }
        return "OK " + json.dumps(payload)

    if cmd == "RESTART":
        # Restart the OracleBox system using oboxrestart command
        try:
            subprocess.Popen(["oboxrestart"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return "OK RESTART"
        except Exception as e:
            if debug.ERROR_MESSAGES:
                print(f"[CMD] ERROR executing restart: {e}")
            return "ERR RESTART failed"

    if cmd == "SHUTDOWN":
        # Shutdown the OracleBox system using oboxstop command
        try:
            subprocess.Popen(["oboxstop"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return "OK SHUTDOWN"
        except Exception as e:
            if debug.ERROR_MESSAGES:
                print(f"[CMD] ERROR executing shutdown: {e}")
            return "ERR SHUTDOWN failed"

    if cmd == "SPEED":
        if len(args) != 1:
            return "ERR SPEED needs ms"
        try:
            ms = int(args[0])
        except ValueError:
            return "ERR SPEED bad value"
        with state_lock:
            state.speed_index = closest_speed_index(ms)
            state.save_to_config()
            ms_actual = SWEEP_SPEEDS_MS[state.speed_index]
        return "OK SPEED " + str(ms_actual)

    if cmd == "FASTER":
        with state_lock:
            if state.speed_index > 0:
                state.speed_index -= 1
                state.save_to_config()
            ms = SWEEP_SPEEDS_MS[state.speed_index]
        return "OK SPEED " + str(ms)

    if cmd == "SLOWER":
        with state_lock:
            if state.speed_index < len(SWEEP_SPEEDS_MS) - 1:
                state.speed_index += 1
                state.save_to_config()
            ms = SWEEP_SPEEDS_MS[state.speed_index]
        return "OK SPEED " + str(ms)

    if cmd == "DIR":
        if not args:
            return "ERR DIR needs UP/DOWN/TOGGLE"
        sub = args[0].upper()
        with state_lock:
            if sub == "UP":
                state.direction = 1
            elif sub == "DOWN":
                state.direction = -1
            elif sub == "TOGGLE":
                state.direction *= -1
            else:
                return "ERR DIR bad value"
            state.save_to_config()
            d = "UP" if state.direction == 1 else "DOWN"
        return "OK DIR " + d

    if cmd == "START":
        with state_lock:
            state.running = True
            state.save_to_config()
        return "OK START"

    if cmd == "STOP":
        with state_lock:
            state.running = False
            state.save_to_config()
        return "OK STOP"

    if cmd == "SWEEP_CFG":
        if len(args) != 2:
            return "ERR SWEEP_CFG needs field and value"
        field = args[0].upper()
        try:
            value = int(args[1])
        except ValueError:
            return "ERR invalid value"

        # Validate and apply
        if field == "MIN":
            if not 0 <= value <= 255:
                return "ERR invalid value"
            if value > led_config.sweep_max_brightness:
                return "ERR min > max"
            old = led_config.sweep_min_brightness
            led_config.sweep_min_brightness = value
            try:
                led_config.save()
            except Exception:
                led_config.sweep_min_brightness = old
                return "ERR could not save config"
            if debug.CMD_SWEEP_CFG:
                print(f"SWEEP_CFG MIN: {old} -> {value}")
            return "OK"

        if field == "MAX":
            if not 0 <= value <= 255:
                return "ERR invalid value"
            if value < led_config.sweep_min_brightness:
                return "ERR min > max"
            old = led_config.sweep_max_brightness
            led_config.sweep_max_brightness = value
            try:
                led_config.save()
            except Exception:
                led_config.sweep_max_brightness = old
                return "ERR could not save config"
            if debug.CMD_SWEEP_CFG:
                print(f"SWEEP_CFG MAX: {old} -> {value}")
            return "OK"

        if field == "SPEED":
            if not 1 <= value <= 10:
                return "ERR invalid value"
            old = led_config.sweep_speed
            led_config.sweep_speed = value
            try:
                led_config.save()
            except Exception:
                led_config.sweep_speed = old
                return "ERR could not save config"
            if debug.CMD_SWEEP_CFG:
                print(f"SWEEP_CFG SPEED: {old} -> {value}")
            return "OK"

        return "ERR unknown field"

    if cmd == "BOX_CFG":
        if len(args) != 2:
            return "ERR BOX_CFG needs field and value"
        field = args[0].upper()
        try:
            value = int(args[1])
        except ValueError:
            return "ERR invalid value"

        if field == "MIN":
            if not 0 <= value <= 255:
                return "ERR invalid value"
            if value > led_config.box_max_brightness:
                return "ERR min > max"
            old = led_config.box_min_brightness
            led_config.box_min_brightness = value
            try:
                led_config.save()
            except Exception:
                led_config.box_min_brightness = old
                return "ERR could not save config"
            if debug.CMD_BOX_CFG:
                print(f"BOX_CFG MIN: {old} -> {value}")
            return "OK"

        if field == "MAX":
            if not 0 <= value <= 255:
                return "ERR invalid value"
            if value < led_config.box_min_brightness:
                return "ERR min > max"
            old = led_config.box_max_brightness
            led_config.box_max_brightness = value
            try:
                led_config.save()
            except Exception:
                led_config.box_max_brightness = old
                return "ERR could not save config"
            if debug.CMD_BOX_CFG:
                print(f"BOX_CFG MAX: {old} -> {value}")
            return "OK"

        if field == "SPEED":
            if not 1 <= value <= 10:
                return "ERR invalid value"
            old = led_config.box_speed
            led_config.box_speed = value
            try:
                led_config.save()
            except Exception:
                led_config.box_speed = old
                return "ERR could not save config"
            if debug.CMD_BOX_CFG:
                print(f"BOX_CFG SPEED: {old} -> {value}")
            return "OK"

        return "ERR unknown field"

    if cmd == "LED":
        if len(args) < 2:
            return "ERR LED needs target and mode"
        target = args[0].upper()
        mode = args[1].lower()

        valid_modes = (
            "on",
            "off",
            "breath",
            "breath_fast",
            "heartbeat",
            "strobe",
            "flicker",
            "random_burst",
            "sweep",
        )

        if mode not in valid_modes:
            return "ERR LED mode"

        if target == "SWEEP":
            with state_lock:
                state.sweep_led_mode = mode
                state.save_to_config()
            apply_led_modes()
            return "OK LED SWEEP " + mode

        if target == "BOX":
            with state_lock:
                state.box_led_mode = mode
                state.save_to_config()
            apply_led_modes()
            return "OK LED BOX " + mode

        if target == "ALL" and mode.lower() == "off":
            with state_lock:
                state.sweep_led_mode = "off"
                state.box_led_mode = "off"
                state.save_to_config()
            apply_led_modes()
            return "OK LED ALL OFF"

        return "ERR LED unknown target"

    if cmd == "SOUND":
        if not args:
            return "ERR SOUND needs subcommand"
        sub = args[0].upper()

        if sub == "STATUS":
            with state_lock:
                current = state.startup_sound or ""
            exists = bool(current) and os.path.exists(os.path.join(SOUNDS_DIR, current))
            payload = {"startup_sound": current, "startup_exists": exists}
            return "OK SOUND STATUS " + json.dumps(payload)

        if sub == "LIST":
            folder = args[1] if len(args) > 1 else None
            sounds = list_sounds(folder)
            return "OK SOUND LIST " + json.dumps(sounds)

        if sub == "PLAY":
            name = args[1] if len(args) > 1 else None
            play_sound(name)
            return "OK SOUND PLAY"

        if sub == "SET":
            if len(args) < 2:
                return "ERR SOUND SET needs filename"
            # Join all remaining args to support filenames with spaces
            name = " ".join(args[1:])
            # Check if file actually exists (more reliable than list_sounds cache)
            path = os.path.join(SOUNDS_DIR, name)
            if not os.path.exists(path):
                if debug.ERROR_MESSAGES:
                    print(f"[SOUND SET] File not found: {path}")
                return "ERR SOUND SET not found"
            if debug.CMD_SOUND:
                print(f"[SOUND SET] Setting startup sound to: {name}")
            with state_lock:
                state.startup_sound = name
                state.save_to_config()
            if debug.CMD_SOUND:
                print(f"[SOUND SET] Config saved successfully")
            return "OK SOUND SET " + name

        if sub == "CLEAR":
            with state_lock:
                state.startup_sound = ""
                state.save_to_config()
            return "OK SOUND CLEAR"

        if debug.ERROR_MESSAGES:
            print(f"[SOUND] Unknown subcommand: {sub}")
        return "ERR SOUND unknown subcommand"

    if cmd == "FX":
        if not args:
            return "ERR FX needs subcommand"

        sub = args[0].upper()

        if sub == "STATUS":
            with fx_lock:
                data = fx_config.to_dict()
            return "OK FX STATUS " + json.dumps(data)

        if sub == "ENABLE":
            with fx_lock:
                fx_config.enabled = True
                fx_config.save()
            _fx_needs_restart = True
            return "OK FX ENABLED"

        if sub == "DISABLE":
            with fx_lock:
                fx_config.enabled = False
                fx_config.save()
            _fx_needs_restart = True
            return "OK FX DISABLED"

        if sub == "SET":
            if len(args) != 3:
                return "ERR FX SET needs param and value"
            param = args[1].upper()
            val_str = args[2]
            try:
                value = int(val_str)
            except ValueError:
                return "ERR FX SET bad value"

            # Validate value ranges and enforce constraints
            with fx_lock:
                changed = False
                
                if param == "BP_LOW":
                    # Band-pass low: 100-2000 Hz
                    if not 100 <= value <= 2000:
                        return "ERR BP_LOW range 100-2000"
                    # Ensure minimum 200 Hz gap with bp_high
                    if value + 200 > fx_config.bp_high:
                        # Auto-adjust bp_high to maintain 200 Hz gap
                        fx_config.bp_high = min(5000, value + 200)
                    fx_config.bp_low = value
                    changed = True
                    
                elif param == "BP_HIGH":
                    # Band-pass high: 300-5000 Hz
                    if not 300 <= value <= 5000:
                        return "ERR BP_HIGH range 300-5000"
                    # Ensure minimum 200 Hz gap with bp_low
                    if value - 200 < fx_config.bp_low:
                        # Auto-adjust bp_low to maintain 200 Hz gap
                        fx_config.bp_low = max(100, value - 200)
                    fx_config.bp_high = value
                    changed = True
                    
                elif param == "REVERB":
                    # Reverb room size: 0-100
                    if not 0 <= value <= 100:
                        return "ERR REVERB range 0-100"
                    fx_config.reverb_room = value
                    changed = True
                    
                elif param == "REVERB_DAMP":
                    # Reverb damping: 0-100
                    if not 0 <= value <= 100:
                        return "ERR REVERB_DAMP range 0-100"
                    fx_config.reverb_damping = value
                    changed = True
                    
                elif param == "REVERB_WET":
                    # Reverb wet mix: 0-100
                    if not 0 <= value <= 100:
                        return "ERR REVERB_WET range 0-100"
                    fx_config.reverb_wet = value
                    changed = True
                    
                elif param == "REVERB_DRY":
                    # Reverb dry mix: 0-100
                    if not 0 <= value <= 100:
                        return "ERR REVERB_DRY range 0-100"
                    fx_config.reverb_dry = value
                    changed = True
                    
                elif param == "CONTRAST":
                    # Contrast enhancement: 0-40
                    if not 0 <= value <= 40:
                        return "ERR CONTRAST range 0-40"
                    fx_config.contrast_amount = value
                    changed = True
                    
                elif param == "PRE_GAIN":
                    # Pre-gain in dB: -24 to 0
                    if not -24 <= value <= 0:
                        return "ERR PRE_GAIN range -24 to 0"
                    fx_config.pre_gain_db = value
                    changed = True
                    
                elif param == "POST_GAIN":
                    # Post-gain in dB: 0 to 18
                    if not 0 <= value <= 18:
                        return "ERR POST_GAIN range 0-18"
                    fx_config.post_gain_db = value
                    changed = True
                    
                else:
                    return "ERR FX SET unknown param"

                if changed:
                    # Manual adjustment: mark as CUSTOM
                    fx_config.preset = "CUSTOM"
                    fx_config.save()
            
            if changed:
                _fx_needs_restart = True

            return "OK FX SET " + param + " " + str(value)

        if sub == "PRESET":
            if len(args) < 2:
                return "ERR FX PRESET needs subcommand"
            
            preset_sub = args[1].upper()
            
            if preset_sub == "LIST":
                # Return list of presets with categories and descriptions
                preset_list = []
                for name, info in FX_PRESETS.items():
                    preset_list.append({
                        "name": name,
                        "category": info["category"],
                        "description": info["description"]
                    })
                return "OK FX PRESET LIST " + json.dumps(preset_list)
            
            if preset_sub == "INFO":
                # FX PRESET INFO <preset_name>
                if len(args) != 3:
                    return "ERR FX PRESET INFO needs preset name"
                
                preset_name = args[2].upper()
                
                if preset_name not in FX_PRESETS:
                    return "ERR FX PRESET unknown"
                
                preset_info = FX_PRESETS[preset_name].copy()
                return "OK FX PRESET INFO " + json.dumps(preset_info)
            
            if preset_sub == "STATUS":
                # Return current preset name and full parameters
                with fx_lock:
                    data = fx_config.to_dict()
                return "OK FX PRESET STATUS " + json.dumps(data)
            
            if preset_sub == "SET":
                if len(args) != 3:
                    return "ERR FX PRESET SET needs preset name"
                
                preset_name = args[2].upper()
                
                with fx_lock:
                    success = fx_config.apply_preset(preset_name)
                    if not success:
                        available = ", ".join(FX_PRESETS.keys())
                        return f"ERR FX PRESET unknown (available: {available})"
                    fx_config.save()
                
                _fx_needs_restart = True
                    
                return "OK FX PRESET SET " + preset_name
            
            if preset_sub == "SAVE":
                # FX PRESET SAVE <name> <category> <bp_low> <bp_high> <contrast> <reverb> <gain>
                if len(args) < 8:
                    return "ERR FX PRESET SAVE needs: name category bp_low bp_high contrast reverb gain"
                
                try:
                    preset_name = args[2].upper()
                    category = args[3].upper()
                    bp_low = int(args[4])
                    bp_high = int(args[5])
                    contrast = int(args[6])
                    reverb = int(args[7])
                    post_gain = int(args[8])
                    
                    # Create new preset entry
                    new_preset = {
                        "category": category,
                        "description": f"Custom {category} preset",
                        "bp_low": bp_low,
                        "bp_high": bp_high,
                        "reverb_room": reverb,
                        "reverb_damping": 40,  # default
                        "reverb_wet": 100,     # default
                        "reverb_dry": 55,      # default
                        "contrast_amount": contrast,
                        "pre_gain_db": -6,     # default
                        "post_gain_db": post_gain,
                    }
                    
                    # Add to global presets dictionary
                    FX_PRESETS[preset_name] = new_preset
                    
                    # Apply it immediately and save
                    with fx_lock:
                        fx_config.apply_preset(preset_name)
                        fx_config.save()
                    
                    _fx_needs_restart = True
                    
                    return "OK FX PRESET SAVED " + preset_name
                    
                except (ValueError, IndexError) as e:
                    return f"ERR FX PRESET SAVE invalid parameters: {e}"
            
            return "ERR FX PRESET unknown subcommand"

        return "ERR FX unknown subcommand"

    if cmd == "MIXER":
        if not args:
            return "ERR MIXER needs subcommand"
        sub = args[0].upper()

        if sub == "STATUS":
            info = get_mixer_status()
            return "OK MIXER STATUS " + json.dumps(info)

        if sub == "SET":
            if len(args) != 3:
                return "ERR MIXER SET needs field and value"
            field = args[1].upper()
            value = args[2]

            if field == "SPEAKER_VOL":
                try:
                    level = int(value)
                except ValueError:
                    return "ERR invalid volume"
                if not 0 <= level <= 37:
                    return "ERR volume range 0-37"
                ok = set_speaker_volume(level)
                return "OK MIXER SET SPEAKER_VOL" if ok else "ERR mixer set failed"

            if field == "MIC_VOL":
                try:
                    level = int(value)
                except ValueError:
                    return "ERR invalid volume"
                if not 0 <= level <= 35:
                    return "ERR volume range 0-35"
                ok = set_mic_volume(level)
                return "OK MIXER SET MIC_VOL" if ok else "ERR mixer set failed"

            if field == "AUTO_GAIN":
                v = value.upper()
                if v not in ("ON", "OFF"):
                    return "ERR AUTO_GAIN needs ON/OFF"
                enabled = (v == "ON")
                ok = set_auto_gain(enabled)
                return "OK MIXER SET AUTO_GAIN" if ok else "ERR mixer set failed"

            return "ERR MIXER unknown field"

        return "ERR MIXER unknown subcommand"

    if cmd == "MUTE":
        if not args:
            return "ERR MUTE needs ON/OFF"
        v = args[0].upper()
        if v not in ("ON", "OFF"):
            return "ERR MUTE needs ON/OFF"
        muted = (v == "ON")
        ok = set_speaker_mute(muted)
        return "OK MUTE " + v if ok else "ERR mute set failed"

    if cmd == "BT_AUDIO":
        if not args:
            return "ERR BT_AUDIO needs subcommand"
        sub = args[0].upper()
        
        if debug.CMD_BT_AUDIO:
            print(f"[CMD] BT_AUDIO {sub}")

        if sub == "LIST":
            # List available Bluetooth audio devices (paired only)
            result = list_bt_audio_devices()
            return "OK BT_AUDIO LIST " + json.dumps(result)

        if sub == "DISCOVER":
            # Scan for nearby Bluetooth devices (paired and unpaired)
            result = discover_bt_devices()
            return "OK BT_AUDIO DISCOVER " + json.dumps(result)

        if sub == "PAIR":
            # BT_AUDIO PAIR <MAC_ADDRESS>
            if len(args) < 2:
                return "ERR BT_AUDIO PAIR needs MAC address"
            
            mac = args[1].upper()
            success = pair_bt_device(mac)
            if success:
                return "OK BT_AUDIO PAIRED " + mac
            else:
                return "ERR BT_AUDIO pairing failed"

        if sub == "STATUS":
            # Return current audio config
            with audio_lock:
                data = audio_config.to_dict()
            return "OK BT_AUDIO STATUS " + json.dumps(data)

        if sub == "CONNECT":
            # BT_AUDIO CONNECT <MAC_ADDRESS>
            if len(args) < 2:
                return "ERR BT_AUDIO CONNECT needs MAC address"
            
            mac = args[1].upper()
            
            # Connect to Bluetooth device
            success = connect_bt_device(mac)
            if not success:
                return "ERR BT_AUDIO connection failed"
            
            # Get the audio sink for this device
            sink = get_bt_audio_sink()
            if not sink:
                # Fallback: try default bluez device name
                sink = "bluez_sink"
            
            # Update audio config
            with audio_lock:
                audio_config.bt_device = mac
                audio_config.bt_connected = True
                audio_config.current_device = sink
            
            # Restart audio processes with new device
            set_audio_output_device(sink)
            
            return "OK BT_AUDIO CONNECTED " + mac

        if sub == "STREAM_PHONE":
            # BT_AUDIO STREAM_PHONE - route audio to the connected phone
            # This will attempt to connect the phone's audio profile
            
            if debug.BT_AUDIO_OPERATIONS:
                print("[BT AUDIO] Attempting to stream to phone...")
            
            # First, try to get list of paired devices to find phone
            devices_result = list_bt_audio_devices()
            if "error" in devices_result:
                return "ERR BT_AUDIO bluetooth not available"
            
            # Get any connected device (should be the phone)
            connected_device = None
            for dev in devices_result.get("devices", []):
                if dev.get("connected"):
                    connected_device = dev
                    break
            
            if not connected_device:
                # No device connected, try to find paired devices
                if debug.BT_AUDIO_OPERATIONS:
                    print("[BT AUDIO] No connected device, attempting to connect first paired device...")
                
                if devices_result.get("devices"):
                    # Try the first paired device (likely the phone)
                    first_device = devices_result["devices"][0]
                    if connect_bt_device(first_device["mac"]):
                        connected_device = first_device
            
            if not connected_device:
                return "ERR BT_AUDIO no phone paired or connection failed"
            
            # Disconnect and reconnect to force A2DP profile activation
            mac = connected_device["mac"]
            if debug.BT_AUDIO_OPERATIONS:
                print(f"[BT AUDIO] Reconnecting {mac} to activate A2DP profile...")
            try:
                # Disconnect first
                subprocess.run(["bluetoothctl", "disconnect", mac], 
                             capture_output=True, timeout=5, check=False)
                time.sleep(1)
                # Reconnect - this should activate A2DP
                result = subprocess.run(["bluetoothctl", "connect", mac],
                                      capture_output=True, text=True, timeout=10, check=False)
                if debug.BT_AUDIO_OPERATIONS:
                    print(f"[BT AUDIO] Reconnect result: {result.stdout.strip()}")
                time.sleep(2)  # Give A2DP time to initialize
            except Exception as e:
                if debug.ERROR_MESSAGES:
                    print(f"[BT AUDIO] Reconnect error: {e}")
            
            # Ensure PulseAudio Bluetooth modules are loaded
            if debug.BT_AUDIO_OPERATIONS:
                print("[BT AUDIO] Ensuring PulseAudio Bluetooth modules are loaded...")
            try:
                # Unload and reload modules to force refresh
                subprocess.run(["pactl", "unload-module", "module-bluetooth-discover"], 
                             capture_output=True, timeout=5, check=False)
                subprocess.run(["pactl", "unload-module", "module-bluetooth-policy"],
                             capture_output=True, timeout=5, check=False)
                time.sleep(0.5)
                subprocess.run(["pactl", "load-module", "module-bluetooth-discover"], 
                             capture_output=True, timeout=5, check=False)
                subprocess.run(["pactl", "load-module", "module-bluetooth-policy"],
                             capture_output=True, timeout=5, check=False)
                time.sleep(2)  # Give PulseAudio more time to detect new sink
            except Exception as e:
                if debug.ERROR_MESSAGES:
                    print(f"[BT AUDIO] Module reload error: {e}")
            
            # Now get the audio sink, with multiple retry attempts
            sink = None
            for attempt in range(5):
                sink = get_bt_audio_sink()
                if sink:
                    break
                if debug.BT_AUDIO_OPERATIONS:
                    print(f"[BT AUDIO] Audio sink not found, retrying ({attempt + 1}/5)...")
                time.sleep(1)
                
            if not sink:
                if debug.BT_AUDIO_OPERATIONS:
                    print("[BT AUDIO] Failed: No phone audio sink available after 5 attempts")
                return "ERR BT_AUDIO phone connected but no audio profile available"
            
            # Update audio config to use phone
            with audio_lock:
                audio_config.bt_device = connected_device["mac"]
                audio_config.bt_connected = True
                audio_config.current_device = sink
            
            # Restart audio processes with phone sink
            set_audio_output_device(sink)
            
            if debug.BT_AUDIO_OPERATIONS:
                print(f"[BT AUDIO] Now streaming to {connected_device['name']} via {sink}")
            return "OK BT_AUDIO STREAMING TO PHONE"

        if sub == "DISCONNECT":
            # Disconnect current Bluetooth device and revert to speaker
            with audio_lock:
                mac = audio_config.bt_device
                if not mac:
                    return "ERR BT_AUDIO no device connected"
            
            # Only disconnect external devices (not phone SPP connection)
            if mac != "PHONE":
                disconnect_bt_device(mac)
            
            # Revert to default speaker
            with audio_lock:
                audio_config.bt_device = None
                audio_config.bt_connected = False
                audio_config.current_device = audio_config.default_device
            
            # Restart audio with speaker
            set_audio_output_device(audio_config.default_device)
            
            return "OK BT_AUDIO DISCONNECTED"

        return "ERR BT_AUDIO unknown subcommand"

    if cmd == "REMPOD":
        if not args:
            return "ERR REMPOD needs subcommand"
        
        sub = args[0].upper()
        
        if sub == "STATUS":
            with rempod_lock:
                data = rempod_state.to_dict()
            return "OK REMPOD STATUS " + json.dumps(data)
        
        if sub == "ARM":
            with rempod_lock:
                rempod_state.armed = True
            _rempod_set_sensitivity_leds(rempod_state.sensitivity)
            return "OK REMPOD ARMED"
        
        if sub == "DISARM":
            with rempod_lock:
                rempod_state.armed = False
            _rempod_leds_off()
            return "OK REMPOD DISARMED"
        
        if sub == "SENSITIVITY":
            if len(args) < 2:
                return "ERR REMPOD SENSITIVITY needs 1-5"
            try:
                level = int(args[1])
                if not 1 <= level <= 5:
                    return "ERR REMPOD SENSITIVITY range 1-5"
            except ValueError:
                return "ERR REMPOD SENSITIVITY bad value"
            
            with rempod_lock:
                rempod_state.sensitivity = level
            _rempod_set_sensitivity_leds(level)
            return f"OK REMPOD SENSITIVITY {level}"
        
        if sub == "TRIGGER":
            # Manual trigger for testing
            if len(args) >= 2:
                trigger_type = args[1].upper()
            else:
                trigger_type = "EMF"
            
            _rempod_trigger(trigger_type)
            return f"OK REMPOD TRIGGER {trigger_type}"
        
        if sub == "SOUND":
            if len(args) < 2:
                return "ERR REMPOD SOUND needs filename"
            sound_name = " ".join(args[1:])
            with rempod_lock:
                rempod_state.alert_sound = sound_name
            return "OK REMPOD SOUND " + sound_name
        
        if sub == "TEMP":
            if len(args) < 2:
                return "ERR REMPOD TEMP needs ON/OFF"
            toggle = args[1].upper()
            if toggle == "ON":
                with rempod_lock:
                    rempod_state.temp_alerts = True
                return "OK REMPOD TEMP ON"
            elif toggle == "OFF":
                with rempod_lock:
                    rempod_state.temp_alerts = False
                return "OK REMPOD TEMP OFF"
            else:
                return "ERR REMPOD TEMP needs ON/OFF"
        
        if sub == "SIMULATE":
            if len(args) < 2:
                return "ERR REMPOD SIMULATE needs START/STOP"
            action = args[1].upper()
            if action == "START":
                with rempod_lock:
                    rempod_state.simulating = True
                    if len(args) >= 3:
                        try:
                            rempod_state.simulation_interval = float(args[2])
                        except ValueError:
                            pass
                return "OK REMPOD SIMULATE STARTED"
            elif action == "STOP":
                with rempod_lock:
                    rempod_state.simulating = False
                return "OK REMPOD SIMULATE STOPPED"
            else:
                return "ERR REMPOD SIMULATE needs START/STOP"
        
        if sub == "SOUNDS":
            # List actual sound files from RemPod folder
            try:
                sound_files = []
                if os.path.exists(REMPOD_SOUNDS_DIR):
                    for fname in os.listdir(REMPOD_SOUNDS_DIR):
                        fpath = os.path.join(REMPOD_SOUNDS_DIR, fname)
                        if os.path.isfile(fpath) and fname.lower().endswith(('.wav', '.mp3', '.ogg', '.flac')):
                            sound_files.append(fname)
                sound_files.sort()
                return "OK REMPOD SOUNDS " + json.dumps(sound_files)
            except Exception as e:
                if debug.ERROR_MESSAGES:
                    print(f"[REMPOD] ERROR listing sounds: {e}")
                return "OK REMPOD SOUNDS []"
        
        return "ERR REMPOD unknown subcommand"

    if cmd == "MUSICBOX":
        if not args:
            return "ERR MUSICBOX needs subcommand"
        
        sub = args[0].upper()
        
        if sub == "STATUS":
            with musicbox_lock:
                data = musicbox_state.to_dict()
            return "OK MUSICBOX STATUS " + json.dumps(data)
        
        if sub == "START":
            with musicbox_lock:
                musicbox_state.active = True
                musicbox_state.calibrated = False
            
            # Calibrate in background thread
            threading.Thread(target=_musicbox_calibrate, daemon=True).start()
            
            return "OK MUSICBOX STARTED"
        
        if sub == "STOP":
            with musicbox_lock:
                musicbox_state.active = False
                musicbox_state.calibrated = False
            _rgb_led_off()
            return "OK MUSICBOX STOPPED"
        
        if sub == "TRIGGER":
            # Manual trigger for testing
            _musicbox_trigger()
            return "OK MUSICBOX TRIGGER"
        
        if sub == "SOUND":
            if len(args) < 2:
                return "ERR MUSICBOX SOUND needs filename"
            sound_name = " ".join(args[1:])
            with musicbox_lock:
                musicbox_state.trigger_sound = sound_name
            return "OK MUSICBOX SOUND " + sound_name
        
        if sub == "RANGE":
            if len(args) < 2:
                return "ERR MUSICBOX RANGE needs meters (1-5)"
            try:
                range_m = float(args[1])
                if not 1.0 <= range_m <= 5.0:
                    return "ERR MUSICBOX RANGE 1-5 meters"
            except ValueError:
                return "ERR MUSICBOX RANGE bad value"
            
            with musicbox_lock:
                musicbox_state.detection_range = range_m
            return f"OK MUSICBOX RANGE {range_m}"
        
        if sub == "SIMULATE":
            if len(args) < 2:
                return "ERR MUSICBOX SIMULATE needs START/STOP"
            action = args[1].upper()
            if action == "START":
                with musicbox_lock:
                    musicbox_state.simulating = True
                    if len(args) >= 3:
                        try:
                            musicbox_state.simulation_interval = float(args[2])
                        except ValueError:
                            pass
                return "OK MUSICBOX SIMULATE STARTED"
            elif action == "STOP":
                with musicbox_lock:
                    musicbox_state.simulating = False
                return "OK MUSICBOX SIMULATE STOPPED"
            else:
                return "ERR MUSICBOX SIMULATE needs START/STOP"
        
        if sub == "PLAY":
            # Alias for manual trigger
            _musicbox_trigger()
            return "OK MUSICBOX PLAY"
        
        if sub == "SOUNDS":
            # List actual sound files from MusicBox folder
            try:
                sound_files = []
                if os.path.exists(MUSICBOX_SOUNDS_DIR):
                    for fname in os.listdir(MUSICBOX_SOUNDS_DIR):
                        fpath = os.path.join(MUSICBOX_SOUNDS_DIR, fname)
                        if os.path.isfile(fpath) and fname.lower().endswith(('.wav', '.mp3', '.ogg', '.flac')):
                            sound_files.append(fname)
                sound_files.sort()
                return "OK MUSICBOX SOUNDS " + json.dumps(sound_files)
            except Exception as e:
                if debug.ERROR_MESSAGES:
                    print(f"[MUSICBOX] ERROR listing sounds: {e}")
                return "OK MUSICBOX SOUNDS []"
        
        return "ERR MUSICBOX unknown subcommand"

    if cmd == "FM":
        if not args:
            return "ERR FM needs subcommand"
        
        sub = args[0].upper()
        
        if sub == "TEST":
            if len(args) < 2:
                return "ERR FM TEST needs frequency (MHz)"
            try:
                freq = float(args[1])
                if not 76.0 <= freq <= 108.0:
                    return "ERR FM TEST frequency range 76.0-108.0 MHz"
            except ValueError:
                return "ERR FM TEST bad frequency"
            
            # Tune to frequency
            if tea5767_write(freq):
                # Start passthrough for 10 seconds to hear it
                _start_passthrough()
                threading.Timer(10.0, _stop_passthrough).start()
                return f"OK FM TEST {freq} (playing for 10s)"
            else:
                return "ERR FM TEST tuner not available"
        
        if sub == "TUNE":
            if len(args) < 2:
                return "ERR FM TUNE needs frequency (MHz)"
            try:
                freq = float(args[1])
                if not 76.0 <= freq <= 108.0:
                    return "ERR FM TUNE frequency range 76.0-108.0 MHz"
            except ValueError:
                return "ERR FM TUNE bad frequency"
            
            # Just tune, don't start playback
            if tea5767_write(freq):
                return f"OK FM TUNE {freq}"
            else:
                return "ERR FM TUNE tuner not available"
        
        return "ERR FM unknown subcommand"

    if cmd == "MIC":
        if not args:
            return "ERR MIC needs subcommand"
        
        sub = args[0].upper()
        
        if sub == "GAIN":
            # FM capture level is locked at 15 for optimal audio quality
            return "ERR MIC GAIN locked at 15 (use MIC STATUS to verify)"
        
        if sub == "STATUS":
            # Get current mic gain
            try:
                result = subprocess.run(
                    ["amixer", "-c", "3", "get", "Mic"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=3
                )
                # Parse output for percentage
                import re
                match = re.search(r'\[(\d+)%\]', result.stdout)
                if match:
                    gain = match.group(1)
                    return f"OK MIC STATUS {gain}"
                else:
                    return "OK MIC STATUS unknown"
            except Exception as e:
                return f"ERR MIC STATUS failed: {e}"
        
        return "ERR MIC unknown subcommand"

    return "ERR Unknown command"


# -------------------- FX THREAD --------------------

def fx_thread():
    """Background thread that keeps the SoX portal chain running."""
    global _fx_proc, _fx_needs_restart

    if debug.SYSTEM_STARTUP:
        print("[FX] thread started")

    while True:
        with fx_lock:
            enabled = fx_config.enabled
            needs_restart = _fx_needs_restart
            _fx_needs_restart = False
        
        with state_lock:
            sweep_running = state.running

        # Only process audio (FX or passthrough) when Spirit Box sweep is running
        if not sweep_running:
            # Stop both FX and passthrough when not in Spirit Box mode
            if _fx_proc is not None:
                if debug.FX_STATE_CHANGES:
                    print("[FX] stopping effects (Spirit Box not active)")
                _stop_fx_proc()
            if _passthrough_proc is not None:
                if debug.AUDIO_PASSTHROUGH:
                    print("[AUDIO] stopping passthrough (Spirit Box not active)")
                _stop_passthrough()
            
            time.sleep(0.2)
            continue

        # Spirit Box is running - apply FX if enabled, otherwise use passthrough
        if not enabled:
            if _fx_proc is not None:
                if debug.FX_STATE_CHANGES:
                    print("[FX] disabling effects, stopping sox")
                _stop_fx_proc()
            
            # Start raw audio passthrough when FX disabled but Spirit Box running
            if _passthrough_proc is None:
                _start_passthrough()
            
            time.sleep(0.2)
            continue
        
        # FX is enabled, so stop passthrough if running
        if debug.FX_STATE_CHANGES and enabled:
            print(f"[FX] FX enabled, sweep running, _fx_proc={_fx_proc is not None}, needs_restart={needs_restart}")
        
        if _passthrough_proc is not None:
            _stop_passthrough()
            # Give audio devices time to fully release (CRITICAL for ALSA device switching)
            time.sleep(1.0)

        # Always restart if FX process is not running or needs restart
        if _fx_proc is None or needs_restart:
            if _fx_proc is not None:
                if debug.FX_STATE_CHANGES:
                    print("[FX] restarting sox with new parameters")
                _stop_fx_proc()

            cmd = build_sox_cmd_from_fx()
            if cmd is None:
                time.sleep(0.2)
                continue

            if debug.FX_STATE_CHANGES:
                print("[FX] Pure ALSA FX pipeline:", cmd[2] if len(cmd) > 2 else cmd)
            try:
                # Start with new process group so we can kill entire pipeline
                _fx_proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setsid,  # Create new process group
                )
                if debug.FX_STATE_CHANGES:
                    print("[FX] Pure ALSA FX started (no PulseAudio)")
                    # Give it a moment to see if it crashes immediately
                    time.sleep(0.1)
                    poll = _fx_proc.poll()
                    if poll is not None:
                        stdout, stderr = _fx_proc.communicate()
                        print(f"[FX] ERROR: Process exited immediately with code {poll}")
                        if stderr:
                            print(f"[FX] STDERR: {stderr.decode('utf-8', errors='ignore')}")
                        _fx_proc = None
                        time.sleep(1.0)
                        continue
            except Exception as e:
                if debug.ERROR_MESSAGES:
                    print("[FX] ERROR starting FX pipeline:", e)
                _fx_proc = None
                time.sleep(1.0)
                continue

        time.sleep(0.2)


# -------------------- SWEEP THREAD --------------------

def sweep_thread():
    apply_led_modes()
    if debug.SYSTEM_STARTUP:
        print("[SWEEP] Thread started")

    while True:
        with state_lock:
            running = state.running
            direction = state.direction

        if not running:
            time.sleep(0.1)
            continue

        if direction == 1:
            steps = range(880, 1080, 2)
            if debug.SWEEP_CYCLES:
                print("[SWEEP] Starting UP sweep 88.0 -> 108.0 MHz")
        else:
            steps = range(1080, 880, -2)
            if debug.SWEEP_CYCLES:
                print("[SWEEP] Starting DOWN sweep 108.0 -> 88.0 MHz")

        step_count = 0
        for step in steps:
            with state_lock:
                running = state.running
                direction_now = state.direction
                sweep_mode = state.sweep_led_mode
                box_mode = state.box_led_mode

            if not running:
                if debug.SWEEP_CYCLES:
                    print(f"[SWEEP] Stopped by user after {step_count} steps")
                break

            freq_mhz = step / 10.0
            set_freq(freq_mhz)
            step_count += 1

            # Per-step flash behaviour
            if sweep_mode == "on" or box_mode == "sweep":
                speed_scale = max(1, min(10, led_config.sweep_speed))
                pulse_ms = 10 + (11 - speed_scale) * 3  # ~13ms..40ms
                pulse_sec = pulse_ms / 1000.0

                if sweep_mode == "on":
                    sweep_led.on()
                if box_mode == "sweep":
                    span = max(0, led_config.box_max_brightness - led_config.box_min_brightness)
                    val = led_config.box_max_brightness
                    level = max(0.0, min(1.0, val / 255.0)) if span > 0 else 1.0
                    box_led.value = level

                time.sleep(pulse_sec)

                if sweep_mode == "on":
                    sweep_led.off()
                if box_mode == "sweep":
                    box_led.value = 0.0

            time.sleep(current_delay_seconds())

        if running:
            if debug.SWEEP_CYCLES:
                print(f"[SWEEP] Completed sweep cycle ({step_count} steps), restarting...")


# -------------------- BLUETOOTH SERVER --------------------

def bluetooth_server():
    if bluetooth is None:
        print("python3-bluez not installed; Bluetooth disabled")
        return

    server_sock = None
    try:
        server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        server_sock.bind(("", 1))
        server_sock.listen(1)

        print("OracleBox Bluetooth server running on RFCOMM channel 1")
        print("Service name:", BT_SERVICE_NAME)

        while True:
            print("Waiting for Bluetooth connection...")
            client_sock, client_info = server_sock.accept()
            print("Bluetooth connection from", client_info)

            try:
                buffer = ""
                while True:
                    data = client_sock.recv(1024)
                    if not data:
                        break
                    buffer += data.decode("utf-8", errors="ignore")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue

                        if debug.BLUETOOTH_RAW_COMMANDS:
                            print("RX RAW:", repr(line))

                        if line.startswith("CMD: "):
                            line = line[5:]

                        if line.startswith("UPLOAD_SOUND"):
                            if debug.SOUND_UPLOADS:
                                print("[UPLOAD_SOUND] header:", line)
                            parts = line.split()
                            if len(parts) < 3:
                                err = "ERR invalid upload header\n".encode("utf-8")
                                client_sock.send(err)
                                if debug.ERROR_MESSAGES:
                                    print("[UPLOAD_SOUND] invalid header parts:", parts)
                                continue

                            _, name_str, size_str = parts[0], parts[1], parts[2]
                            try:
                                size = int(size_str)
                            except ValueError:
                                err = "ERR invalid size\n".encode("utf-8")
                                client_sock.send(err)
                                if debug.ERROR_MESSAGES:
                                    print("[UPLOAD_SOUND] invalid size:", size_str)
                                continue

                            if debug.SOUND_UPLOADS:
                                print(f"[UPLOAD_SOUND] name={name_str} size={size}")
                            client_sock.send(b"OK READY\n")
                            if debug.SOUND_UPLOADS:
                                print("[UPLOAD_SOUND] sent OK READY")

                            remaining = size
                            chunks = []
                            while remaining > 0:
                                chunk = client_sock.recv(remaining)
                                if not chunk:
                                    print("[UPLOAD_SOUND] connection closed early")
                                    client_sock.send(b"ERR incomplete upload\n")
                                    break
                                chunks.append(chunk)
                                remaining -= len(chunk)
                                if debug.SOUND_UPLOADS:
                                    print(f"[UPLOAD_SOUND] received {size - remaining}/{size} bytes")

                            if remaining > 0:
                                continue

                            data_bytes = b"".join(chunks)

                            try:
                                os.makedirs(SOUNDS_DIR, exist_ok=True)
                                path = os.path.join(SOUNDS_DIR, name_str)
                                with open(path, "wb") as f:
                                    f.write(data_bytes)
                                if debug.SOUND_UPLOADS:
                                    print(f"[UPLOAD_SOUND] saved {len(data_bytes)} bytes to {path}")
                                client_sock.send(b"OK SAVED\n")
                            except Exception as e:
                                if debug.ERROR_MESSAGES:
                                    print("[UPLOAD_SOUND] error saving file:", e)
                                client_sock.send(b"ERR save failed\n")

                            buffer = ""
                            continue

                        if debug.BLUETOOTH_RAW_COMMANDS:
                            print("CMD:", line)
                        response = handle_command(line)
                        if debug.BLUETOOTH_RESPONSES:
                            print("RESPONSE:", response)
                        client_sock.send((response + "\n").encode("utf-8"))
            except OSError:
                pass
            finally:
                client_sock.close()
                print("Bluetooth client disconnected")

    finally:
        if server_sock is not None:
            try:
                server_sock.close()
            except Exception:
                pass


# -------------------- MAIN --------------------

if __name__ == "__main__":
    os.makedirs(SOUNDS_DIR, exist_ok=True)
    os.makedirs(ANNOUNCEMENTS_DIR, exist_ok=True)
    os.makedirs(STARTUP_SOUNDS_DIR, exist_ok=True)
    os.makedirs(REMPOD_SOUNDS_DIR, exist_ok=True)
    os.makedirs(MUSICBOX_SOUNDS_DIR, exist_ok=True)

    if debug.SYSTEM_STARTUP:
        print("=" * 60)
        print("OracleBox Paranormal Investigation System")
        print("Version: 2.1.0 (November 26, 2025)")
        print("=" * 60)
        print("Updates:")
        print("  - Voice-guided navigation support")
        print("  - Manual start mode (sweep on demand)")
        print("  - Enhanced FX audio pipeline")
        print("=" * 60)
        print("Speeds:", SWEEP_SPEEDS_MS, "ms")
        print("Config:", state.to_dict())
        print()

    # Check for TEA5767 FM tuner
    if debug.SYSTEM_STARTUP:
        print("[INIT] Checking for TEA5767 FM tuner...")
    tea5767_present = check_tea5767()
    if debug.SYSTEM_STARTUP:
        if tea5767_present:
            print("[INIT] [OK] TEA5767 FM tuner detected and ready")
        else:
            print("[INIT] [FAIL] TEA5767 FM tuner not found (sweeps will run without FM)")
        print()

    # Set speaker volume to 75% (level 28) at startup
    if debug.SYSTEM_STARTUP:
        print("[INIT] Setting speaker volume to 75%...")
    set_speaker_volume(28)

    # Lock FM capture (mic gain) at 15 for optimal audio quality
    if debug.SYSTEM_STARTUP:
        print("[INIT] Setting FM capture level to 15 (locked)...")
    try:
        subprocess.run(
            ["amixer", "-c", "3", "set", "Capture", "15"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3
        )
    except Exception as e:
        if debug.ERROR_MESSAGES:
            print(f"[INIT] WARNING: Could not set FM capture level: {e}")

    # Determine if a valid startup sound is configured
    with state_lock:
        startup_name = state.startup_sound

    if startup_name:
        # Check all folders for startup sound (same order as play_sound)
        startup_path = os.path.join(STARTUP_SOUNDS_DIR, startup_name)
        if not os.path.exists(startup_path):
            startup_path = os.path.join(ANNOUNCEMENTS_DIR, startup_name)
            if not os.path.exists(startup_path):
                startup_path = os.path.join(SOUNDS_DIR, startup_name)
    else:
        startup_path = ""

    if startup_path and os.path.exists(startup_path):
        if debug.SOUND_PLAYBACK:
            print(f"[SOUND] Startup sound selected: {startup_name}")
        try:
            size = os.path.getsize(startup_path)
        except OSError:
            size = -1
        if size >= 0 and debug.SOUND_PLAYBACK:
            print(f"[SOUND] File size: {size} bytes")
        cmd, player = _player_command_for(startup_path)
        if not cmd:
            if debug.ERROR_MESSAGES:
                print(f"[SOUND] ERROR: Unsupported format: {startup_path}")
        else:
            if debug.SOUND_PLAYBACK:
                print(f"[SOUND] Using {player} for playback")
                print(f"[SOUND] Command: {' '.join(cmd)}")
                try:
                    print(f"[SOUND] Working dir: {os.getcwd()}")
                except Exception:
                    pass

            _apply_mode_to_led("strobe", sweep_led, is_pwm=False)
            _apply_mode_to_led("flicker", box_led, is_pwm=True)

            if debug.SOUND_PLAYBACK:
                print("[SOUND] Playing startup sound...")
            try:
                ret = _blocking_playback(cmd, player, timeout_s=STARTUP_SOUND_TIMEOUT)
                if ret not in (0, None) and debug.ERROR_MESSAGES:
                    print(f"[SOUND] WARNING: Player exited with code {ret}")
            except FileNotFoundError:
                if debug.ERROR_MESSAGES:
                    print(f"[SOUND] ERROR: {player} not installed")
            except Exception as e:
                if debug.ERROR_MESSAGES:
                    print(f"[SOUND] ERROR: {e}")
            finally:
                _apply_mode_to_led("off", sweep_led, is_pwm=False)
                _apply_mode_to_led("off", box_led, is_pwm=True)

        if debug.SOUND_PLAYBACK:
            print("[SOUND] Waiting 1 second before starting sweep...")
        time.sleep(1.0)
        apply_led_modes()
        
        # Now that startup sound is complete, start FX thread
        if debug.SYSTEM_STARTUP:
            print("[INIT] Starting FX thread (after startup sound)...")
        fx_t = threading.Thread(target=fx_thread, daemon=True)
        fx_t.start()
    else:
        if debug.SYSTEM_STARTUP:
            print("[SOUND] No startup sound configured")

    if debug.SYSTEM_STARTUP:
        print()
        print("[INIT] Starting sweep thread...")
    t = threading.Thread(target=sweep_thread, daemon=True)
    t.start()

    # Only start FX thread if no startup sound was played
    # (FX thread is started after sound playback to avoid effects on startup sound)
    if not (startup_path and os.path.exists(startup_path)):
        if debug.SYSTEM_STARTUP:
            print("[INIT] Starting FX thread...")
        fx_t = threading.Thread(target=fx_thread, daemon=True)
        fx_t.start()

    if debug.SYSTEM_STARTUP:
        print("[INIT] Starting REM Pod simulation thread...")
    rempod_t = threading.Thread(target=rempod_simulation_thread, daemon=True)
    rempod_t.start()

    if debug.SYSTEM_STARTUP:
        print("[INIT] Starting Music Box simulation thread...")
    musicbox_t = threading.Thread(target=musicbox_simulation_thread, daemon=True)
    musicbox_t.start()

    if debug.SYSTEM_STARTUP:
        print("[INIT] Making Bluetooth discoverable...")
    try:
        # Use DisplayYesNo agent for automatic confirmation
        agent_proc = subprocess.Popen(
            ["bluetoothctl"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        commands = "agent DisplayYesNo\ndefault-agent\ndiscoverable on\npairable on\nquit\n"
        agent_proc.communicate(input=commands.encode(), timeout=5)
        
        if debug.SYSTEM_STARTUP:
            print("[INIT] Bluetooth set to discoverable and pairable")
    except Exception as e:
        if debug.ERROR_MESSAGES:
            print(f"[INIT] Failed to set discoverable: {e}")
    
    if debug.SYSTEM_STARTUP:
        print("[INIT] Starting Bluetooth server...")
        print("=" * 60)
        print()
    bluetooth_server()
