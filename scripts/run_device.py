"""Phase 1 manual test harness.

Connects to the iPhone, sets a simulated location, and runs the keep-alive loop until
you press Ctrl+C. While it runs, the fix is re-sent every ~1.5 s with jitter — this is
what makes Pokémon Go hold the location instead of throwing "Failed to detect location".

Usage (from repo root, with the venv python):
    .venv\\Scripts\\python -m scripts.run_device                 # defaults to San Francisco
    .venv\\Scripts\\python -m scripts.run_device 40.6892 -74.0445  # Statue of Liberty

Requires: iPhone plugged in + trusted, Developer Mode on. On iOS 17+ it will auto-start
tunneld elevated (approve the UAC prompt) if it isn't already running.
"""
from __future__ import annotations

import logging
import sys
import time

from phantom import DeviceLayer

# San Francisco (Ferry Building-ish) — same coord we proved in Phase 0.
DEFAULT_LAT, DEFAULT_LON = 37.7749, -122.4194


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    lat, lon = DEFAULT_LAT, DEFAULT_LON
    if len(sys.argv) == 3:
        lat, lon = float(sys.argv[1]), float(sys.argv[2])

    dev = DeviceLayer()
    dev.start()
    print("Connecting to device (this mounts the DDI and may take a minute the first time)…")
    info = dev.connect()
    print(f"Connected: {info.name} — {info.product_type}, iOS {info.ios_version}")

    dev.set_location(lat, lon)
    print(f"Location set to {lat}, {lon}. Keep-alive running (re-send every ~1.5 s with jitter).")
    print("Open Maps / Pokémon Go now — the fix will hold. Press Ctrl+C to stop and restore real GPS.")

    try:
        while True:
            time.sleep(5)
            tgt = dev.current_target
            print(f"  …holding {tgt[0]:.5f}, {tgt[1]:.5f}" if tgt else "  …no target")
    except KeyboardInterrupt:
        print("\nStopping — clearing location and tearing down…")
    finally:
        dev.close()
    print("Done. Real GPS restored.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
