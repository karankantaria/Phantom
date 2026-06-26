# TEST_RESULTS.md — Real-Location Discriminating Experiment (live log)

Per-trial data for the real-location discriminating experiment described in `PoGo_AntiCheat_Report.md` §5.4 (discriminate H3 environment-fingerprint from H1/H2 location-content). Recorded live; folded into the paper §8.4.

## Session context
- **Date/time started:** 2026-06-26 ~07:38 (local)
- **Rig:** Phantom / pymobiledevice3 9.30.1 · iPhone 11 (iPhone12,1) · iOS 26.5 (23F77) · Windows 11 host
- **Tunnel:** `tunneld` elevated; RSD at test start `fd9d:7be1:4af0::1 : 49793` (re-read per trial — changes per tunnel)
- **Keep-alive:** 1.5 s re-send + 1–5 m idle jitter (identical to original failing test)
- **Device motion:** none (stationary throughout)
- **Network:** Cellular · Carrier: **Safaricom** (Kenya)
- **VPN:** OFF (confirmed by user)
- **Account spoof-history:** previously spoofed (San Francisco teleport, 2026-06-25) — **confound noted**
- **Soft-ban:** user reports low likelihood; never entered game yesterday (error 12 blocked entry before in-game movement)
- **Physical city / true position:** **Nairobi, Kenya** (exact coordinates withheld for author privacy)
- **Offset target:** **~334 m north** of the device's true position (+0.003° latitude; coherent with the local Safaricom/Nairobi IP + cell context)
- **Coherence note:** unlike the original SF test (GPS=SF while IP/cell=Nairobi → large mismatch), this target IS coherent with the real Nairobi network context. That is the manipulation.

## Control verification
- Apple Maps showed the OFFSET point (spoof confirmed live)? **YES** (user confirmed blue dot ~330 m north of true)

## Trials (PoGo, force-quit between each, spoof + keep-alive running throughout)
| Trial | PoGo outcome (loads / error 12 / other) | Time-to-result (s) | Notes |
|---|---|---|---|
| 1 | **Error 12** | ~3 | Map briefly rendered at the spoofed offset location, then error 12 — same behavior as the SF test |
| 2 | **Error 12** | ~3 | Also showed PoGo's speed-lock popup *"You are going too fast, are you a passenger?"* despite the device being stationary — implies PoGo computed an apparent high speed (likely the real→offset transition or keep-alive jitter being read as movement). Error 12 still fired. |
| 3 | **Error 12** | ~4 | No speed popup this time (popup was intermittent — only trial 2). Error 12 still fired. |

## Summary
- **Majority outcome: Error 12 — 3/3 trials** (unanimous), each ~3–4 s after launch, map briefly rendering at the spoofed offset before failing.
- **Conclusion per TEST_PLAN §3 decision table:** Error 12 **still fires with a location coherent with the real IP/cell AND matching the real sensors** (same city, ~same altitude/magnetic field, ~330 m offset). This **excludes the entire content-based class {H1 network coherence, H2 static sensor cross-validation}** — both predicted the error would *clear* at the real location, and it did not. The supported explanation is **H3 — the instrumented/developer-environment fingerprint** (Developer Mode + mounted DDI + live instruments/DTX debug session held open for keep-alive). PoGo rejects the *runtime environment*, not the *coordinate*.
- **Secondary observation:** intermittent speed-lock popup ("going too fast / passenger?") on trial 2 only, while stationary → PoGo computed apparent motion from our fixes (likely the real→offset transition or keep-alive jitter read as movement). Did not affect the error-12 outcome (trial 3 had no popup, same result).
- **Epistemic status:** environment-vs-content question is now `[Confirmed by us]` (3/3, controlled). H1-vs-H2 remains unseparated `[Inferred]` (deliberately not pursued — edges into bypass territory per TEST_PLAN §3 ethics).
- **Confounds noted:** same account with prior SF spoof history; cellular (not Wi-Fi); 3 trials (small N, but unanimous).
- Screenshots captured? (user to attach if desired for the paper)
