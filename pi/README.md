# Raspberry Pi Hub

Python daemon and deployment scripts for the OracleBox hub.

## Contents

- `oraclebox.py` - Main daemon with Bluetooth server, FM sweep, LED control, and WiFi satellite hub
- `tea5767_debug_scan.py` - FM tuner testing and debugging utility
- `deploy_to_pi.ps1` - PowerShell script to deploy code to Pi over SSH
- `pi_instructions_wifi_and_startup.txt` - Setup guide for WiFi hotspot and systemd service

## Architecture

The Pi acts as the central hub:
- **Bluetooth SPP Server** - Receives commands from Android app
- **WiFi Access Point** - Creates isolated hotspot for ESP32 satellites
- **WiFi Socket Server** - Receives sensor data from satellites (port 8888)
- **TEA5767 FM Control** - I2C communication for Spirit Box sweep
- **Audio Processing** - USB audio interface with real-time FX pipeline
- **LED Animations** - GPIO control for Sweep and Box LEDs
- **Voice Synthesis** - espeak-ng with vintage radio effects
- **Event Logging** - Unified log of all device activity

## Setup

See `pi_instructions_wifi_and_startup.txt` for complete setup guide.

Quick start:
```bash
# Install dependencies
sudo apt install python3-smbus python3-gpiozero espeak-ng sox

# Create directories
mkdir -p /home/dylan/oraclebox/{announcements,sounds,logs}

# Copy files
cp oraclebox.py /home/dylan/oraclebox/
chmod +x /home/dylan/oraclebox/oraclebox.py

# Setup systemd service
sudo cp oraclebox.service /etc/systemd/system/
sudo systemctl enable oraclebox
sudo systemctl start oraclebox
```

## WiFi Hotspot Configuration

The Pi creates `OracleBox-Network` hotspot:
- IP: 192.168.4.1
- DHCP range: 192.168.4.2-192.168.4.20
- No internet routing (isolated network)
- WPA2 password protected

ESP32 satellites connect to this network and communicate via socket on port 8888.

## Deployment

Use PowerShell script from Windows:
```powershell
.\deploy_to_pi.ps1
```

Or manually via SSH:
```bash
scp oraclebox.py dylan@raspberrypi.local:/home/dylan/oraclebox/
ssh dylan@raspberrypi.local 'sudo systemctl restart oraclebox'
```
