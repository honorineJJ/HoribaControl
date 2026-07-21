from __future__ import annotations

import asyncio
from typing import Any

import numpy as np

from horibacontrol.domain.models import AcquisitionSettings, Spectrum
from horibacontrol.hardware.backend import InstrumentBackend


class SimulationBackend(InstrumentBackend):
    def __init__(self, config: dict[str, Any]) -> None:
        self.connected = False
        self.initialized = False
        self.wavelength_nm = float(config.get("initial_wavelength_nm", 532.0))
        self.move_speed = float(config.get("move_speed_nm_per_second", 100.0))
        self.default_pixels = int(config.get("detector_pixels", 1024))
        self._rng = np.random.default_rng(int(config.get("random_seed", 1)))
        self._abort_event = asyncio.Event()
        self.grating = 1

    async def connect(self) -> dict:
        await asyncio.sleep(0.05)
        self.connected = True
        self._abort_event.clear()
        return {
            "monochromator": "MicroHR simulation",
            "camera": "Syncerity simulation",
            "serial_number": "0340-0913-MHRA",
        }

    async def disconnect(self) -> None:
        self._abort_event.set()
        await asyncio.sleep(0.01)
        self.connected = False
        self.initialized = False

    async def initialize(self) -> None:
        self._require_connected()
        self._abort_event.clear()
        await self._sleep_interruptible(0.1)
        self.initialized = True

    async def status(self) -> dict:
        self._require_connected()
        return {
            "backend": "simulation",
            "connected": self.connected,
            "initialized": self.initialized,
            "wavelength_nm": self.wavelength_nm,
            "grating": self.grating,
            "camera_temperature_c": -70.0,
            "monochromator_configuration": {"model": "MicroHR simulation"},
            "camera_configuration": {"model": "Syncerity simulation"},
        }

    async def move_to(self, wavelength_nm: float) -> float:
        self._require_ready()
        self._abort_event.clear()
        distance = abs(float(wavelength_nm) - self.wavelength_nm)
        duration = min(0.5, distance / max(self.move_speed, 1e-6))
        await self._sleep_interruptible(duration)
        self.wavelength_nm = float(wavelength_nm)
        return self.wavelength_nm

    async def select_grating(self, grating_number: int) -> None:
        self._require_ready()
        if grating_number not in (1, 2, 3):
            raise ValueError("Le réseau doit être 1, 2 ou 3.")
        await self._sleep_interruptible(0.05)
        self.grating = grating_number

    async def acquire(self, settings: AcquisitionSettings) -> Spectrum:
        self._require_ready()
        settings.validate()
        self._abort_event.clear()
        await self._sleep_interruptible(min(0.5, settings.exposure_ms / 1000.0))

        pixels = settings.detector_pixels or self.default_pixels
        span_nm = 30.0
        x = np.linspace(
            self.wavelength_nm - span_nm / 2,
            self.wavelength_nm + span_nm / 2,
            pixels,
        )

        signal = (
            self._gaussian(x, 532.0, 0.30, 52000.0)
            + self._gaussian(x, 546.1, 0.55, 24000.0)
            + self._gaussian(x, 577.0, 0.90, 14000.0)
        )
        scale = settings.exposure_ms / 100.0
        noise = self._rng.normal(300.0, 80.0, pixels)
        intensity = np.clip(signal * scale + noise, 0.0, None)

        return Spectrum(
            x=x,
            intensity=intensity,
            center_wavelength_nm=self.wavelength_nm,
            exposure_ms=settings.exposure_ms,
            metadata={"backend": "simulation", "pixels": pixels},
        )

    async def abort(self) -> None:
        self._abort_event.set()

    async def _sleep_interruptible(self, duration: float) -> None:
        remaining = max(0.0, duration)
        while remaining > 0:
            if self._abort_event.is_set():
                raise asyncio.CancelledError("Opération interrompue.")
            step = min(0.02, remaining)
            await asyncio.sleep(step)
            remaining -= step

    @staticmethod
    def _gaussian(x: np.ndarray, center: float, sigma: float, amplitude: float) -> np.ndarray:
        return amplitude * np.exp(-0.5 * ((x - center) / sigma) ** 2)

    def _require_connected(self) -> None:
        if not self.connected:
            raise RuntimeError("Le backend n’est pas connecté.")

    def _require_ready(self) -> None:
        self._require_connected()
        if not self.initialized:
            raise RuntimeError("Le backend n’est pas initialisé.")
