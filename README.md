# Phantom — host-side iOS GPS spoofing, and where modern anti-cheat stops it

**Phantom** is a non-jailbreak, host-side iOS GPS spoofer built on Apple's own
developer location-simulation service (via [`pymobiledevice3`](https://github.com/doronz88/pymobiledevice3)),
runnable from a Windows host. It is the working artifact behind a research paper that
asks a sharper question: **why does a system-wide simulated GPS fix that Apple Maps and
Snapchat accept get specifically rejected by Pokémon GO?**

> **Result in one line:** the spoof works system-wide (Maps, Snapchat honor it) but
> Pokémon GO rejects it with *"Failed to detect location (12)"* — a deliberate
> anti-cheat block that the software/developer-mode method cannot overcome. The paper
> traces the detection boundary and shows the "obvious" explanation
> (`isSimulatedBySoftware`) is a red herring.

This is a **defensive / educational negative-result analysis.** It characterizes a
detection boundary; it does **not** provide an anti-cheat bypass. All testing used the
author's own device and account. See [Ethics](#ethics).

## The paper

📄 **`PoGo_AntiCheat_Report.md`** (and `PoGo_AntiCheat_Report.pdf`) — *"Maps Says Yes,
the Game Says No: Why Non-Jailbreak iOS GPS Spoofing Can't Beat Modern Anti-Cheat."*

> **Paper DOI:** [10.5281/zenodo.20917374](https://doi.org/10.5281/zenodo.20917374) · **Code DOI:** [10.5281/zenodo.20916696](https://doi.org/10.5281/zenodo.20916696)

Key findings:
- A working host-side spoofer on the iOS 17+ RemoteXPC / DVT `LocationSimulation` path
  (with the mandatory keep-alive loop and GPS jitter).
- A controlled differential test isolating the rejection to Niantic's anti-cheat, not
  the implementation.
- The iOS 15+ `CLLocationSourceInformation.isSimulatedBySoftware` flag does **not** fire
  for the developer/DVT channel — so an app relying on it would miss the spoof (§9.1).
- A "real-location" experiment showing error 12 persists even at a *coherent* coordinate,
  so coordinate content is not the discriminating variable (§8.4), with the remaining
  hypotheses and confounds laid out candidly.

## Repository layout

| Path | What |
|---|---|
| `PoGo_AntiCheat_Report.md` / `.pdf` | The research paper |
| `phantom/` | Host-side device layer: connect, mount DDI, set location, keep-alive loop |
| `scripts/run_device.py` | Manual test harness — set a location and hold it until Ctrl+C |
| `sourceinfo-probe/` | A minimal iOS app to measure the `isSimulatedBySoftware` flag (see its README) |
| `TEST_RESULTS.md` | Per-trial data for the §8.4 real-location experiment |
| `requirements.txt` | Python dependencies |

## Requirements & install

- Windows host with Apple Mobile Device Service (from the iTunes bundle) for `usbmuxd`.
- Python 3.12–3.14. (On 3.13/3.14 a couple of dependencies compile from source and need
  the Microsoft C++ Build Tools — see paper §7.1.)
- A non-jailbroken iPhone, paired/trusted, with **Developer Mode** enabled.

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

## Usage

```bash
# Default target is San Francisco; or pass lat lon
.venv\Scripts\python -m scripts.run_device
.venv\Scripts\python -m scripts.run_device 40.6892 -74.0445
```

This connects, mounts the DeveloperDiskImage, sets the location, and runs the keep-alive
loop (re-send every ~1.5 s with 1–5 m jitter) until you press Ctrl+C, then restores real
GPS. The fix propagates to ordinary apps system-wide. Anti-cheat-hardened apps
(Pokémon GO) will reject it — that rejection is the subject of the paper.

## Ethics

Spoofing location in Pokémon GO violates Niantic's Terms of Service and carries an
escalating ban risk. This project does **not** advocate or instruct circumventing that
anti-cheat — its central finding is that the software method studied *cannot* beat it. No
IMU-spoofing, debug-signal hiding, MFi-key extraction, or modified clients are provided.
The reusable artifact is positioned for **legitimate location testing** (navigation /
geofence / fitness QA, location-gated feature testing) on apps without anti-cheat — the
use case the OS mechanism is intended for. No vulnerability in Apple or Niantic systems
was discovered or exploited; only Apple's documented developer tooling is used.

## License

- **Code** (`phantom/`, `scripts/`, `sourceinfo-probe/`): MIT — see [`LICENSE`](LICENSE).
- **Paper & documentation**: CC BY 4.0.

## Citation

If you reference this work, please cite the paper:

> Kantaria, K. (2026). *Maps Says Yes, the Game Says No: Why Non-Jailbreak iOS GPS
> Spoofing Can't Beat Modern Anti-Cheat.* Zenodo. https://doi.org/10.5281/zenodo.20917374

The accompanying software artifact is archived separately at
https://doi.org/10.5281/zenodo.20916696.
