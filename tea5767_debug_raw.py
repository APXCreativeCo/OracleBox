"""
TEA5767 FM Tuner Raw I2C Debug Script
Uses raw I2C block write (no register address) as recommended for TEA5767.
"""

import time
import fcntl

I2C_SLAVE = 0x0703
TEA5767_ADDR = 0x60
BUS_NUM = 1
SETTLE_S = 0.3


def calc_bytes(freq_mhz, mute=True):
    pll = int(4 * ((freq_mhz * 1_000_000) + 225_000) / 32_768)
    data0 = (pll >> 8) & 0x3F
    data1 = pll & 0xFF
    data2 = 0xB0 if mute else 0x30  # Bit 7: MUTE (1=mute, 0=unmute)
    data3 = 0x10  # XTAL=32.768kHz
    data4 = 0x00
    return [data0, data1, data2, data3, data4]


def write_tea5767_raw(bus_num, addr, data):
    with open(f'/dev/i2c-{bus_num}', 'r+b', buffering=0) as f:
        fcntl.ioctl(f, I2C_SLAVE, addr)
        f.write(bytearray(data))


def read_tea5767_raw(bus_num, addr, num_bytes):
    with open(f'/dev/i2c-{bus_num}', 'r+b', buffering=0) as f:
        fcntl.ioctl(f, I2C_SLAVE, addr)
        return list(f.read(num_bytes))


def main():
    freq = 100.1  # MHz, change as needed
    print(f"Tuning to {freq} MHz (mute on)...")
    write_tea5767_raw(BUS_NUM, TEA5767_ADDR, calc_bytes(freq, mute=True))
    time.sleep(SETTLE_S)
    print(f"Unmuting...")
    write_tea5767_raw(BUS_NUM, TEA5767_ADDR, calc_bytes(freq, mute=False))
    time.sleep(SETTLE_S)
    try:
        status = read_tea5767_raw(BUS_NUM, TEA5767_ADDR, 5)
        status_hex = " ".join(f"{b:02X}" for b in status)
        print(f"Status bytes: {status_hex}")
    except Exception as exc:
        print(f"Status read failed: {exc}")


if __name__ == "__main__":
    main()
