# sourceinfo-probe

A minimal SwiftUI iOS app that reads its own Core Location fix and displays the
iOS 15+ provenance flags `CLLocationSourceInformation.isSimulatedBySoftware`
and `.isProducedByAccessory`.

**Why it exists.** The paper (§9.1) argues that `isSimulatedBySoftware` is a *red
herring*: per an Apple DTS statement, that flag is set only for Core Location's own
(Xcode GPX) simulation path and **not** for a third-party/developer-channel provider
like the DVT `simulate-location` path this project uses — so an anti-cheat relying on
it would miss the spoof. This app measures that directly. Running it while a DVT
keep-alive injects a fix should show `isSimulatedBySoftware = false`, which would
upgrade the paper's claim from *[Reported — Apple DTS]* to *[Confirmed]*.

This is a **defensive/educational measurement of a public Apple API**. It never
touches Pokémon GO or any game — it only reads the device's own location.

## Files
- `SourceInfoProbeApp.swift` — app entry point
- `ContentView.swift` — `LocationReader` (CLLocationManager delegate) + the UI

## Requirements
- **macOS + Xcode 16+** (to match an iOS 26 device SDK). Building/signing a native iOS
  app is macOS-only; it cannot be produced from the Windows host this project runs on.
- A **free Apple ID** is sufficient for signing — Xcode's "Personal Team" gives a
  7-day provisioning profile, ample for a few-minute test. No paid Developer Program needed.
- An iOS 15+ device with Developer Mode enabled (iOS 16+).

## Build
1. Xcode → New → Project → iOS → App. Interface **SwiftUI**, Language **Swift**.
2. Replace the generated `App.swift` and `ContentView.swift` with the two files here.
3. Add the location usage string (the app crashes on launch without it): target → Info →
   `Privacy - Location When In Use Usage Description` =
   `Reads the device location to display its CoreLocation provenance flags.`
4. Signing & Capabilities → Team = your Apple ID; set a unique bundle id.
5. Plug in the device, Run (⌘R). First run: trust the developer cert on-device under
   Settings → General → VPN & Device Management, then re-run.

## Run protocol
Grant **While Using** + **Precise Location ON** (identical to how the paper tested
Pokémon GO). Force-quit and relaunch between conditions so each reading is fresh; wait
for `updates ≥ 5` before recording.

| Condition | Setup | Expected |
|---|---|---|
| **A — real GPS (baseline)** | No spoof running | flags `false` (or `sourceInformation` nil on early fixes) |
| **B — DVT spoof live** (the headline read) | Bring up the host-side spoofer + keep-alive; first confirm `lat`/`lon` track the spoofed target (proves the channel is live) | `isSimulatedBySoftware = false`, `isProducedByAccessory = false` |
| **C — Xcode GPX (positive control)** | In Xcode, Debug → Simulate Location → pick a city/GPX | `isSimulatedBySoftware = true` |

Condition C proves the app reads the flag correctly (so a `false` in B is a real
negative) **and** demonstrates the Apple DTS distinction — GPX path `true`, DVT path
`false` — on one device.

## Interpreting the result
- **B shows `false`** → confirms §9.1: the developer/DVT channel does not trip the flag.
- **B shows `true`** → contradicts the Apple DTS guidance for this path; a notable
  finding that would invert §9.1. Report it rather than discarding it.
- **`sourceInformation` always nil** → provenance is not populated on this path; still a
  valid finding (an app cannot read provenance here at all).

If you run this, a result (with a screenshot of Condition B/C) is directly useful to the
`pymobiledevice3` community and to the paper — contributions welcome.
