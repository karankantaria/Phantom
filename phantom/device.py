"""Phantom device layer (Phase 1).

A clean, synchronous-facing wrapper around pymobiledevice3 that:
  - finds the connected iPhone and reads its info / iOS version,
  - establishes the developer connection (iOS 17+ via tunneld RSD, ≤16 via usbmux lockdown),
  - mounts the DeveloperDiskImage,
  - sets/clears the simulated GPS location, and
  - runs the MANDATORY keep-alive loop that re-sends the current fix every ~1.5 s with
    idle jitter, so the location never decays/freezes (BUILD_PLAN §2, §4.2).

pymobiledevice3's API is async; we run a single event loop in a background thread (the
"bridge") and expose blocking methods so the rest of the app (and the future FastAPI
layer) can call this without caring about asyncio.

Windows notes baked in from Phase 0 (see Progress.md):
  - Use `remote tunneld` (NOT `start-tunnel --userspace`, which hangs on Windows).
  - tunneld must run elevated; `start_tunneld()` spawns it via UAC and launches python.exe
    with a real console (avoids the blessed/`sys.__stdout__ is None` import crash).
"""
from __future__ import annotations

import asyncio
import logging
import sys
import threading
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

import requests
from packaging.version import Version

from pymobiledevice3.exceptions import AlreadyMountedError
from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation
from pymobiledevice3.services.mobile_image_mounter import auto_mount
from pymobiledevice3.services.simulate_location import DtSimulateLocation
from pymobiledevice3.tunneld.api import TUNNELD_DEFAULT_ADDRESS, get_tunneld_device_by_udid

from phantom.geo import jitter_coord

logger = logging.getLogger("phantom.device")

KEEPALIVE_INTERVAL = 1.5  # seconds between re-sends (matches every working reference impl)
IDLE_JITTER_M = (1.0, 5.0)  # metres of drift applied on each keep-alive re-send


class DeviceError(RuntimeError):
    """Raised for device-layer problems with a user-actionable message."""


@dataclass
class DeviceInfo:
    udid: str
    name: str
    product_type: str
    ios_version: str

    @property
    def is_ios17_plus(self) -> bool:
        return Version(self.ios_version) >= Version("17.0")


class _AsyncBridge:
    """Owns one asyncio event loop running in a daemon thread."""

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, name="phantom-loop", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    def run(self, coro: Awaitable, timeout: Optional[float] = None):
        """Run a coroutine on the loop from another thread and block for the result."""
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result(timeout)

    def stop(self) -> None:
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)


# ─────────────────────────── tunneld helpers (module-level) ───────────────────────────

def is_tunneld_running(address: tuple[str, int] = TUNNELD_DEFAULT_ADDRESS) -> bool:
    try:
        requests.get(f"http://{address[0]}:{address[1]}", timeout=2)
        return True
    except requests.exceptions.RequestException:
        return False


def start_tunneld(wait: float = 30.0) -> None:
    """Start `pymobiledevice3 remote tunneld` elevated, then wait until its API responds.

    On Windows this raises a UAC prompt and launches python.exe with its own console
    (so the pymobiledevice3 CLI's blessed import does not crash on a missing stdout).
    On macOS/Linux it shells out with sudo (interactive terminal required), though the
    userspace path is usually preferable there.
    """
    if is_tunneld_running():
        return

    if sys.platform == "win32":
        import ctypes

        # ShellExecuteW 'runas' → UAC elevation. SW_SHOWMINNOACTIVE(7): real console, unobtrusive.
        rc = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, "-m pymobiledevice3 remote tunneld", None, 7
        )
        if rc <= 32:
            raise DeviceError(f"Failed to launch elevated tunneld (ShellExecute code {rc}). Approve the UAC prompt.")
    else:
        import shlex
        import subprocess

        subprocess.Popen(shlex.split(f"sudo {sys.executable} -m pymobiledevice3 remote tunneld"))

    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        if is_tunneld_running():
            return
        time.sleep(1.0)
    raise DeviceError("tunneld did not come up in time. Did you approve the UAC/sudo prompt?")


# ───────────────────────────────── the device layer ─────────────────────────────────

class DeviceLayer:
    """Blocking facade over the iPhone's location-simulation service + keep-alive loop.

    Typical use:
        dev = DeviceLayer()
        dev.start()
        dev.connect()              # auto-starts tunneld if needed (UAC on Windows)
        dev.set_location(37.7749, -122.4194)
        ...                        # keep-alive holds & jitters the fix
        dev.clear_location()
        dev.close()
    """

    def __init__(
        self,
        keepalive_interval: float = KEEPALIVE_INTERVAL,
        idle_jitter_m: tuple[float, float] = IDLE_JITTER_M,
        auto_start_tunnel: bool = True,
    ) -> None:
        self._bridge = _AsyncBridge()
        self._interval = keepalive_interval
        self._idle_jitter_m = idle_jitter_m
        self._auto_start_tunnel = auto_start_tunnel

        self.info: Optional[DeviceInfo] = None
        self._sim = None  # object exposing async set(lat,lon)/clear()
        self._closers: list[Callable[[], Awaitable]] = []  # async teardown, run in reverse
        self._sim_lock: Optional[asyncio.Lock] = None  # serialises DVT access (created on loop)
        self._keepalive_task: Optional[asyncio.Task] = None

        self._target_lock = threading.Lock()
        self._target: Optional[tuple[float, float]] = None
        self._connected = False

    # ---- lifecycle ----

    def start(self) -> None:
        self._bridge.start()

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def current_target(self) -> Optional[tuple[float, float]]:
        with self._target_lock:
            return self._target

    def connect(self, udid: Optional[str] = None, timeout: float = 180.0) -> DeviceInfo:
        """Detect the device, establish the dev connection, mount the DDI, start keep-alive."""
        return self._bridge.run(self._connect(udid), timeout=timeout)

    def set_location(self, lat: float, lon: float) -> None:
        """Set the simulated location now; the keep-alive loop holds & jitters it thereafter."""
        if not self._connected:
            raise DeviceError("Not connected. Call connect() first.")
        with self._target_lock:
            self._target = (lat, lon)
        self._bridge.run(self._emit(lat, lon))

    def clear_location(self) -> None:
        """Stop simulating and restore the device's real GPS."""
        if not self._connected:
            return
        with self._target_lock:
            self._target = None
        self._bridge.run(self._clear())

    def close(self) -> None:
        """Tear everything down cleanly."""
        if self._bridge.loop.is_closed():
            return
        try:
            self._bridge.run(self._teardown(), timeout=15)
        except Exception as exc:  # best-effort
            logger.warning("teardown error: %s", exc)
        self._bridge.stop()

    # ---- async internals (run on the bridge loop) ----

    async def _connect(self, udid: Optional[str]) -> DeviceInfo:
        lockdown = await create_using_usbmux(serial=udid)
        info = DeviceInfo(
            udid=lockdown.udid,
            name=lockdown.short_info.get("DeviceName", "iPhone") if hasattr(lockdown, "short_info") else "iPhone",
            product_type=lockdown.product_type,
            ios_version=lockdown.product_version,
        )
        self.info = info
        self._sim_lock = asyncio.Lock()
        logger.info("Device: %s (%s) iOS %s", info.name, info.product_type, info.ios_version)

        if info.is_ios17_plus:
            await self._connect_ios17(lockdown, info)
        else:
            await self._connect_legacy(lockdown)

        self._keepalive_task = self._bridge.loop.create_task(self._keepalive())
        self._connected = True
        return info

    async def _connect_ios17(self, lockdown, info: DeviceInfo) -> None:
        if not is_tunneld_running():
            if not self._auto_start_tunnel:
                raise DeviceError(
                    "tunneld is not running. Start it elevated:  python -m pymobiledevice3 remote tunneld"
                )
            logger.info("tunneld not running — starting it elevated (approve the UAC prompt)…")
            await asyncio.to_thread(start_tunneld)

        rsd = await get_tunneld_device_by_udid(info.udid)
        if rsd is None:
            raise DeviceError("tunneld is up but has no tunnel for this device yet. Re-plug the iPhone and retry.")

        try:
            await auto_mount(rsd)
            logger.info("DeveloperDiskImage mounted.")
        except AlreadyMountedError:
            logger.info("DeveloperDiskImage already mounted.")

        provider = DvtProvider(rsd)
        dvt = await provider.__aenter__()
        sim = LocationSimulation(dvt)
        await sim.__aenter__()
        self._sim = sim
        # Teardown in reverse: stop sim → close DVT → close RSD → close lockdown.
        self._closers = [
            lambda: sim.__aexit__(None, None, None),
            lambda: provider.__aexit__(None, None, None),
            lambda: _maybe_close(rsd),
            lambda: _maybe_close(lockdown),
        ]

    async def _connect_legacy(self, lockdown) -> None:
        # iOS ≤16 path: old DeveloperDiskImage over usbmux, DtSimulateLocation service.
        # NOTE: structured per BUILD_PLAN but UNTESTED (no ≤16 device available).
        try:
            await auto_mount(lockdown)
        except AlreadyMountedError:
            pass
        self._sim = DtSimulateLocation(lockdown)
        self._closers = [lambda: _maybe_close(lockdown)]

    async def _emit(self, lat: float, lon: float) -> None:
        async with self._sim_lock:
            await self._sim.set(lat, lon)

    async def _clear(self) -> None:
        async with self._sim_lock:
            await self._sim.clear()

    async def _keepalive(self) -> None:
        """Re-send the current fix every interval with idle jitter, until cancelled."""
        try:
            while True:
                await asyncio.sleep(self._interval)
                with self._target_lock:
                    target = self._target
                if target is None:
                    continue
                jlat, jlon = jitter_coord(*target, *self._idle_jitter_m)
                try:
                    await self._emit(jlat, jlon)
                except Exception as exc:  # don't let one bad re-send kill the loop
                    logger.warning("keep-alive re-send failed: %s", exc)
        except asyncio.CancelledError:
            pass

    async def _teardown(self) -> None:
        self._connected = False
        if self._keepalive_task is not None:
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass
            self._keepalive_task = None
        # Best-effort: clear the fix before closing so the phone returns to real GPS.
        if self._sim is not None:
            try:
                await self._clear()
            except Exception:
                pass
        for closer in self._closers:
            try:
                await closer()
            except Exception as exc:
                logger.debug("closer error: %s", exc)
        self._closers = []
        self._sim = None


async def _maybe_close(obj) -> None:
    """Close a pymobiledevice3 object whether its close is sync or async (or absent)."""
    for attr in ("aclose", "close"):
        fn = getattr(obj, attr, None)
        if fn is None:
            continue
        result = fn()
        if asyncio.iscoroutine(result):
            await result
        return
