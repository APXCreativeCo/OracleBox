"""Custom TEA5767 debug scan for user-specified frequencies."""

def _calc_bytes(freq_mhz: float):

import time
import fcntl

TEA5767_ADDR = 0x60
BUS_NUM = 1
FREQS = [100.1]  # Test a known FM broadcast frequency
SETTLE_S = 0.3

def _calc_bytes(freq_mhz, mute=True):
    pll = int(4 * ((freq_mhz * 1_000_000) + 225_000) / 32_768)
    data0 = (pll >> 8) & 0x3F
    data1 = pll & 0xFF
    data2 = 0xB0 if mute else 0x30  # Bit 7: MUTE (1=mute, 0=unmute)
    data3 = 0x10
    data4 = 0x00
    return [data0, data1, data2, data3, data4]

def write_tea5767_raw(bus_num, addr, data):
    with open(f'/dev/i2c-{bus_num}', 'r+b', buffering=0) as f:
        fcntl.ioctl(f, 0x0703, addr)
        f.write(bytearray(data))

def read_tea5767_raw(bus_num, addr, num_bytes):
    with open(f'/dev/i2c-{bus_num}', 'r+b', buffering=0) as f:
        fcntl.ioctl(f, 0x0703, addr)
        return list(f.read(num_bytes))



def main():
    print(f"Testing frequencies: {FREQS}")
    for freq in FREQS:
        try:
            print(f"Tuning to {freq} MHz (mute on)...")
            write_tea5767_raw(BUS_NUM, TEA5767_ADDR, _calc_bytes(freq, mute=True))
            time.sleep(SETTLE_S)
            print(f"Unmuting...")
            write_tea5767_raw(BUS_NUM, TEA5767_ADDR, _calc_bytes(freq, mute=False))
            time.sleep(SETTLE_S)
            try:
                status = read_tea5767_raw(BUS_NUM, TEA5767_ADDR, 5)
                status_hex = " ".join(f"{b:02X}" for b in status)
                print(f"{freq:8.3f} MHz -> OK, status bytes: {status_hex}")
            except Exception as exc:
                print(f"{freq:8.3f} MHz -> wrote OK, status read failed: {exc}")
        except Exception as exc:
            print(f"{freq:8.3f} MHz -> WRITE ERROR: {exc}")

if __name__ == "__main__":
    main()
