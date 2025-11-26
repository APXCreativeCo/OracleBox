import os
import time
import json
import threading

import subprocess

try:
    import bluetooth
except ImportError:
    bluetooth = None

# -------------------- BLUETOOTH SETTINGS --------------------

BT_SERVICE_NAME = "OracleBox"
BT_UUID = "00001101-0000-1000-8000-00805F9B34FB"  # Classic SPP UUID (kept for future use)

# Placeholder for SOUNDS_DIR and SUPPORTED_SOUND_EXTENSIONS
SOUNDS_DIR = "sounds"  # Adjust as needed
SUPPORTED_SOUND_EXTENSIONS = [".wav", ".mp3"]

# Placeholder for apply_led_modes
def apply_led_modes():
    pass

# Placeholder for OracleBoxState
class OracleBoxState:
    def __init__(self):
        self.muted = False
        self.speed_index = 0
        self.direction = 1
        self.running = False
        self.sweep_led_mode = "off"
        self.box_led_mode = "off"
        self.startup_sound = ""
    def save_to_config(self):
        pass
    def load_from_config(self):
        pass
    def to_dict(self):
        return {
            "muted": self.muted,
            "speed_index": self.speed_index,
            "direction": self.direction,
            "running": self.running,
            "sweep_led_mode": self.sweep_led_mode,
            "box_led_mode": self.box_led_mode,
            "startup_sound": self.startup_sound,
        }

# -------------------- FX CONFIG --------------------

class FxConfig:
    def __init__(self):
        # Master bypass
        self.enabled = False

        # Band-pass range in Hz
        self.bp_low = 500
        self.bp_high = 2600

        # Reverb settings
        self.reverb_room = 35
        self.reverb_damping = 40
        self.reverb_wet = 100
        self.reverb_dry = 55

        # Extra clarity / bite
        self.contrast_amount = 20

        # Gains in dB
        self.pre_gain_db = -6
        self.post_gain_db = 8

    def to_dict(self):
        return {
            "enabled": self.enabled,
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

# Placeholder or actual imports/definitions for missing symbols
try:
    from .config import led_config, SWEEP_SPEEDS_MS, closest_speed_index
except ImportError:
    # Fallbacks if not in a module
    led_config = None  # Replace with actual config object
    SWEEP_SPEEDS_MS = [50, 100, 150, 200, 250, 300, 350]
    def closest_speed_index(ms):
        return min(range(len(SWEEP_SPEEDS_MS)), key=lambda i: abs(SWEEP_SPEEDS_MS[i] - ms))

# Global lock for thread safety
state_lock = threading.Lock()
def handle_command(command):
    command = command.strip()
    if not command:
        return "ERR Empty command"

    parts = command.split()
    cmd = parts[0].upper()
    args = parts[1:]

    global state, _fx_needs_restart

    if cmd == "MUTE":
        if not args:
            return "ERR MUTE needs ON/OFF"
        sub = args[0].upper()
        with state_lock:
            if sub == "ON":
                state.muted = True
            elif sub == "OFF":
                state.muted = False
            else:
                return "ERR MUTE bad value"
            state.save_to_config()
        return f"OK MUTE {'ON' if state.muted else 'OFF'}"

    if cmd == "STATUS":
        with state_lock:
            data = state.to_dict()
            data.update(led_config.to_dict())
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

        if target == "ALL" and mode == "OFF":
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
            sounds = list_sounds()
            return "OK SOUND LIST " + json.dumps(sounds)

        if sub == "PLAY":
            name = args[1] if len(args) > 1 else None
            play_sound(name)
            return "OK SOUND PLAY"

        if sub == "SET":
            if len(args) != 2:
                return "ERR SOUND SET needs filename"
            name = args[1]
            if name not in list_sounds():
                return "ERR SOUND SET not found"
            with state_lock:
                state.startup_sound = name
                state.save_to_config()
            return "OK SOUND SET " + name

        if sub == "CLEAR":
            with state_lock:
                state.startup_sound = ""
                state.save_to_config()
            return "OK SOUND CLEAR"

        return "ERR SOUND unknown"

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
                _fx_needs_restart = True
            return "OK FX ENABLED"

        if sub == "DISABLE":
            with fx_lock:
                fx_config.enabled = False
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

            with fx_lock:
                changed = False
                if param == "BP_LOW":
                    fx_config.bp_low = value
                    changed = True
                elif param == "BP_HIGH":
                    fx_config.bp_high = value
                    changed = True
                elif param == "REVERB":
                    fx_config.reverb_room = value
                    changed = True
                elif param == "REVERB_DAMP":
                    fx_config.reverb_damping = value
                    changed = True
                elif param == "REVERB_WET":
                    fx_config.reverb_wet = value
                    changed = True
                elif param == "REVERB_DRY":
                    fx_config.reverb_dry = value
                    changed = True
                elif param == "CONTRAST":
                    fx_config.contrast_amount = value
                    changed = True
                elif param == "PRE_GAIN":
                    fx_config.pre_gain_db = value
                    changed = True
                elif param == "POST_GAIN":
                    fx_config.post_gain_db = value
                    changed = True
                else:
                    return "ERR FX SET unknown param"

                if changed:
                    _fx_needs_restart = True

            return "OK FX SET " + param + " " + str(value)

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

    return "ERR Unknown command"

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

# -------------------- AUDIO PLAYBACK HELPERS --------------------

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
    """Play a sound file (WAV via aplay, MP3 via mpg123)."""
    if name is None:
        with state_lock:
            name = state.startup_sound

    if not name:
        print("No sound configured")
        return

    path = os.path.join(SOUNDS_DIR, name)
    if not os.path.exists(path):
        print("Sound file not found:", path)
        return

    cmd, player = _player_command_for(path)
    if not cmd:
        print("Unsupported sound format:", path)
        return

    try:
        subprocess.Popen(cmd)
        print(f"Playing sound via {player}: {name}")
    except FileNotFoundError:
        print(f"{player} not installed. Install it or convert files to WAV.")
    except Exception as e:
        print("Error playing sound:", e)

def list_sounds():
    if not os.path.exists(SOUNDS_DIR):
        return []
    return sorted(
        [
            f
            for f in os.listdir(SOUNDS_DIR)
            if os.path.splitext(f.lower())[1] in SUPPORTED_SOUND_EXTENSIONS
        ]
    )


state = OracleBoxState()
state.load_from_config()

fx_config = FxConfig()
fx_lock = threading.Lock()

_fx_proc = None  # type: subprocess.Popen | None
_fx_needs_restart = False

def build_sox_cmd_from_fx():
    """Build the SoX command line based on current fx_config for USB card 3."""
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

    cmd = [
        "sox",
        "-t", "alsa", "plughw:3,0",
        "-t", "alsa", "plughw:3,0",
        "gain", str(pre_gain),
        "sinc", f"{bp_low}-{bp_high}",
    ]

    if contrast_amount > 0:
        cmd += ["contrast", str(contrast_amount)]

    cmd += [
        "reverb", str(room), str(damp), str(wet), str(dry),
        "gain", str(post_gain),
    ]

    return cmd


def _stop_fx_proc():
    global _fx_proc
    if _fx_proc is not None:
        try:
            _fx_proc.terminate()
            _fx_proc.wait(timeout=2.0)
        except Exception:
            try:
                _fx_proc.kill()
            except Exception:
                pass
        _fx_proc = None


def fx_thread():
    """Background thread that keeps the SoX portal chain running."""
    global _fx_proc, _fx_needs_restart

    print("[FX] thread started")

    while True:
        with fx_lock:
            enabled = fx_config.enabled
            needs_restart = _fx_needs_restart
            _fx_needs_restart = False

        if not enabled:
            if _fx_proc is not None:
                print("[FX] disabling effects, stopping sox")
                _stop_fx_proc()
            time.sleep(0.2)
            continue

        if _fx_proc is None or needs_restart:
            if _fx_proc is not None:
                print("[FX] restarting sox with new parameters")
                _stop_fx_proc()

            cmd = build_sox_cmd_from_fx()
            if cmd is None:
                time.sleep(0.2)
                continue

            print("[FX] launching sox:", " ".join(cmd))
            try:
                _fx_proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.STDOUT,
                )
            except Exception as e:
                print("[FX] ERROR starting sox:", e)
                _fx_proc = None
                time.sleep(1.0)
                continue

        time.sleep(0.2)

# -------------------- SWEEP THREAD --------------------

def sweep_thread():
    apply_led_modes()
    print("Sweep thread started")

    while True:
        with state_lock:
            running = state.running
            direction = state.direction

        if not running:
            time.sleep(0.1)
            continue

        if direction == 1:
            steps = range(880, 1080, 2)
        else:
            steps = range(1080, 880, -2)

        for step in steps:
            with state_lock:
                running = state.running
                direction_now = state.direction
                sweep_mode = state.sweep_led_mode
                box_mode = state.box_led_mode
            if not running:
                break

            freq_mhz = step / 10.0
            set_freq(freq_mhz)

            # Only force per-step flashes when dial mode is plain "on"
            # (classic sweep indicator) or when the box LED mode is
            # explicitly set to "sweep". Other modes are driven by
            # apply_led_modes() and should not be overridden here.
            if sweep_mode == "on" or box_mode == "sweep":
                # Pulse duration and brightness derived from sweep config
                speed_scale = max(1, min(10, led_config.sweep_speed))
                pulse_ms = 10 + (11 - speed_scale) * 3  # ~13ms..40ms
                pulse_sec = pulse_ms / 1000.0

                if sweep_mode == "on":
                    sweep_led.on()
                if box_mode == "sweep":
                    # Use box brightness range scaled by sweep config
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

# -------------------- BLUETOOTH SERVER --------------------

def bluetooth_server():
    if bluetooth is None:
        print("python3-bluez not installed; Bluetooth disabled")
        return

    server_sock = None
    try:
        # Listen on a fixed RFCOMM channel 1; no SDP/advertise_service
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

                        # Debug: log raw line
                        print("RX RAW:", repr(line))

                        # Optional CMD: prefix from Android side
                        if line.startswith("CMD: "):
                            line = line[5:]

                        # Special handling for UPLOAD_SOUND, which streams bytes
                        if line.startswith("UPLOAD_SOUND"):
                            print("[UPLOAD_SOUND] header:", line)
                            parts = line.split()
                            if len(parts) < 3:
                                err = "ERR invalid upload header\n".encode("utf-8")
                                client_sock.send(err)
                                print("[UPLOAD_SOUND] invalid header parts:", parts)
                                continue

                            _, name_str, size_str = parts[0], parts[1], parts[2]
                            try:
                                size = int(size_str)
                            except ValueError:
                                err = "ERR invalid size\n".encode("utf-8")
                                client_sock.send(err)
                                print("[UPLOAD_SOUND] invalid size:", size_str)
                                continue

                            print(f"[UPLOAD_SOUND] name={name_str} size={size}")

                            # Handshake so Android can start sending bytes
                            client_sock.send(b"OK READY\n")
                            print("[UPLOAD_SOUND] sent OK READY")

                            # Read exactly <size> bytes from the socket
                            remaining = size
                            chunks = []
                            while remaining > 0:
                                chunk = client_sock.recv(remaining)
                                if not chunk:
                                    print("[UPLOAD_SOUND] connection closed before receiving all bytes")
                                    client_sock.send(b"ERR incomplete upload\n")
                                    break
                                chunks.append(chunk)
                                remaining -= len(chunk)
                                print(f"[UPLOAD_SOUND] received {size - remaining}/{size} bytes")

                            if remaining > 0:
                                # Incomplete upload already reported
                                continue

                            data_bytes = b"".join(chunks)

                            # Save to sounds directory
                            try:
                                os.makedirs(SOUNDS_DIR, exist_ok=True)
                                path = os.path.join(SOUNDS_DIR, name_str)
                                with open(path, "wb") as f:
                                    f.write(data_bytes)
                                print(f"[UPLOAD_SOUND] saved {len(data_bytes)} bytes to {path}")
                                client_sock.send(b"OK SAVED\n")
                            except Exception as e:
                                print("[UPLOAD_SOUND] error saving file:", e)
                                client_sock.send(b"ERR save failed\n")

                            # After raw bytes, there might already be extra text in the socket
                            # so we reset the line buffer for the next commands.
                            buffer = ""
                            continue

                        # Normal text command path
                        print("CMD:", line)
                        response = handle_command(line)
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

    print("OracleBox starting...")
    print("Speeds:", SWEEP_SPEEDS_MS, "ms")
    print("Config:", state.to_dict())

    # Determine if a valid startup sound is configured
    with state_lock:
        startup_name = state.startup_sound

    if startup_name:
        startup_path = os.path.join(SOUNDS_DIR, startup_name)
    else:
        startup_path = ""

    if startup_path and os.path.exists(startup_path):
        print(f"Startup sound selected, playing before sweep: {startup_name}")
        try:
            size = os.path.getsize(startup_path)
        except OSError:
            size = -1
        if size >= 0:
            print(f"Startup sound size: {size} bytes")
        cmd, player = _player_command_for(startup_path)
        if not cmd:
            print("Unsupported startup sound format:", startup_path)
        else:
            print(f"Using {player} for startup playback")
            print("Startup command:", " ".join(cmd))
            try:
                print("Working dir:", os.getcwd())
            except Exception:
                pass

            # Temporarily override LEDs without disturbing stored modes.
            _apply_mode_to_led("strobe", sweep_led, is_pwm=False)
            _apply_mode_to_led("flicker", box_led, is_pwm=True)

            try:
                ret = _blocking_playback(cmd, player, timeout_s=STARTUP_SOUND_TIMEOUT)
                if ret not in (0, None):
                    print(f"Startup player exited with code {ret}; check audio output or format")
            except FileNotFoundError:
                print(f"{player} not installed. Install it or convert files to WAV.")
            except Exception as e:
                print("Error playing startup sound:", e)
            finally:
                _apply_mode_to_led("off", sweep_led, is_pwm=False)
                _apply_mode_to_led("off", box_led, is_pwm=True)

        # Grace period after startup sound to keep sweep/FM quiet
        time.sleep(1.0)
        apply_led_modes()
    else:
        print("No valid startup sound configured; starting sweep immediately")

    t = threading.Thread(target=sweep_thread, daemon=True)
    t.start()

    fx_t = threading.Thread(target=fx_thread, daemon=True)
    fx_t.start()

    bluetooth_server()
