import os
import time
import json
import threading

import subprocess

try:
    import bluetooth
except ImportError:
    bluetooth = None

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

    global state

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

    return "ERR Unknown command"
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

# -------------------- COMMAND API --------------------

def handle_command(command):

    command = command.strip()
    if not command:
        return "ERR Empty command"

    parts = command.split()
    cmd = parts[0].upper()
    args = parts[1:]

    global state

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

    return "ERR Unknown command"

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

    bluetooth_server()
