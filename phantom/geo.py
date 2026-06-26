"""Geo helpers for the movement/keep-alive engine.

Only the small bits needed by the device layer live here for now (jitter). Haversine
distance/bearing and interpolation arrive in Phase 2 (movement engine).
"""
from __future__ import annotations

import math
import random

# Meters per degree of latitude (constant enough for our scale).
_METERS_PER_DEG = 111_320.0


def jitter_coord(lat: float, lon: float, min_m: float = 1.0, max_m: float = 5.0) -> tuple[float, float]:
    """Offset a coordinate by a small random vector (default 1–5 m) in a random direction.

    Real GPS drifts a few meters constantly; emitting a perfectly static coordinate is a
    known spoofing-detection signal (BUILD_PLAN §3.2, §4.2). Used on every keep-alive
    re-send so the fix is never frozen.
    """
    dist = random.uniform(min_m, max_m)
    angle = random.uniform(0, 2 * math.pi)
    dlat = (dist / _METERS_PER_DEG) * math.cos(angle)
    # Longitude degrees shrink with latitude; clamp cos() so we never blow up near the poles.
    dlon = (dist / (_METERS_PER_DEG * max(math.cos(math.radians(lat)), 0.01))) * math.sin(angle)
    return lat + dlat, lon + dlon
