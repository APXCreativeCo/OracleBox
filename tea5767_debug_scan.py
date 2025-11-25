"""Minimal TEA5767 tuner exerciser for hardware diagnostics."""

import argparse
import time

import smbus

TEA5767_ADDR = 0x60


def _calc_bytes(freq_mhz: float):
    pll = int(4 * ((freq_mhz * 1_000_000) + 225_000) / 32_768)
    data0 = (pll >> 8) & 0x3F
    data1 = pll & 0xFF
    data2 = 0b10110000
    data3 = 0b00010000
    data4 = 0x00
    return [data0, data1, data2, data3, data4]


def scan_frequencies(bus, freqs, settle_s: float):
    print(f"Scanning {len(freqs)} frequencies (settle {settle_s:.2f}s)...")
    for freq in freqs:
        try:
            bus.write_i2c_block_data(TEA5767_ADDR, 0, _calc_bytes(freq))
        except Exception as exc:
            print(f"{freq:6.1f} MHz -> WRITE ERROR: {exc}")
            continue

        time.sleep(settle_s)

        try:
            status = bus.read_i2c_block_data(TEA5767_ADDR, 0, 5)
            status_hex = " ".join(f"{b:02X}" for b in status)
            print(f"{freq:6.1f} MHz -> OK, status bytes: {status_hex}")
        except Exception as exc:
            print(f"{freq:6.1f} MHz -> wrote OK, status read failed: {exc}")


def _parse_args():
    parser = argparse.ArgumentParser(description="Simple TEA5767 channel scan helper")
    parser.add_argument(
        "--freqs",
        nargs="*",
        type=float,
        default=None,
        help="Explicit list of MHz frequencies to test",
    )
    parser.add_argument(
        "--start",
        type=float,
        help="Start MHz for generated sweep (requires --end)",
    )
    parser.add_argument(
        "--end",
        type=float,
        help="End MHz for generated sweep (requires --start)",
    )
    parser.add_argument(
        "--step",
        type=float,
        default=0.2,
        help="Step size in MHz when using --start/--end (default 0.2)",
    )
    parser.add_argument(
        "--settle",
        type=float,
        default=0.15,
        help="Delay after tuning before reading status (seconds)",
    )
    parser.add_argument(
        "--bus",
        type=int,
        default=1,
        help="I2C bus number (default 1)",
    )
    return parser.parse_args()


def _build_frequency_list(args):
    if args.freqs:
        return args.freqs
    if args.start is not None and args.end is not None:
        if args.step <= 0:
            raise ValueError("--step must be positive")
        start = min(args.start, args.end)
        end = max(args.start, args.end)
        count = int(((end - start) / args.step) + 1)
        return [round(start + i * args.step, 3) for i in range(max(1, count))]
    # Default sample stations across the FM band
    return [88.1, 92.3, 96.7, 100.1, 104.5, 107.9]


def main():
    args = _parse_args()
    try:
        bus = smbus.SMBus(args.bus)
    except Exception as exc:
        print(f"Failed to open I2C bus {args.bus}: {exc}")
        return

    try:
        freqs = _build_frequency_list(args)
    except ValueError as exc:
        print(exc)
        return

    scan_frequencies(bus, freqs, args.settle)


if __name__ == "__main__":
    main()
