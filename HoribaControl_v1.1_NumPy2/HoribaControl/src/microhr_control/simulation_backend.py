from __future__ import annotations

import asyncio
import math
from typing import Callable

import numpy as np

from .backend import InstrumentBackend
from .models import CameraSettings, Spectrum


class SimulationBackend(InstrumentBackend):
    def __init__(self):
        self.connected = False
        self.wavelength_nm = 532.0
        self.grating = 1
        self.initialized = False
        self._abort = False

    async def connect(self) -> dict:
        await asyncio.sleep(0.25)
        self.connected = True
        return await self.status()

    async def disconnect(self) -> None:
        self.connected = False

    async def initialize(self, progress: Callable[[str], None] | None = None) -> None:
        self._require()
        if progress:
            progress("Simulation du homing…")
        await asyncio.sleep(0.5)
        self.initialized = True
        if progress:
            progress("MicroHR simulé initialisé.")

    async def status(self) -> dict:
        self._require()
        return {
            "connected": True,
            "monochromator_open": True,
            "camera_open": True,
            "initialized": self.initialized,
            "wavelength_nm": self.wavelength_nm,
            "grating": self.grating,
            "camera_temperature_c": -70.0,
            "monochromator_configuration": {"model": "MicroHR simulation"},
            "camera_configuration": {"model": "Syncerity simulation", "chip": [1024, 256]},
        }

    async def move_to(self, wavelength_nm: float) -> float:
        self._require()
        self._abort = False
        distance = abs(float(wavelength_nm) - self.wavelength_nm)
        for _ in range(max(1, min(20, int(distance / 5) + 1))):
            if self._abort:
                raise asyncio.CancelledError("Déplacement simulé interrompu.")
            await asyncio.sleep(0.02)
        self.wavelength_nm = float(wavelength_nm)
        return self.wavelength_nm

    async def select_grating(self, grating_number: int) -> None:
        self._require()
        if grating_number not in (1, 2, 3):
            raise ValueError("Le réseau doit être 1, 2 ou 3.")
        await asyncio.sleep(0.25)
        self.grating = grating_number

    async def acquire(self, settings: CameraSettings) -> Spectrum:
        self._require()
        self._abort = False
        await asyncio.sleep(min(1.0, max(0.02, settings.exposure_time / 1000.0)))
        if self._abort:
            raise asyncio.CancelledError("Acquisition simulée interrompue.")

        pixels = max(32, settings.x_size // max(1, settings.x_bin))
        span = 35.0 / self.grating
        x = np.linspace(self.wavelength_nm - span / 2, self.wavelength_nm + span / 2, pixels)
        peak1 = np.exp(-0.5 * ((x - 532.0) / 0.55) ** 2) * 42000
        peak2 = np.exp(-0.5 * ((x - 546.1) / 0.8) ** 2) * 25000
        broad = np.exp(-0.5 * ((x - 575.0) / 5.0) ** 2) * 8000
        rng = np.random.default_rng(int(self.wavelength_nm * 1000) % (2**32 - 1))
        noise = rng.normal(500, 180, pixels)
        scale = max(0.01, settings.exposure_time / 100.0)
        y = np.clip((peak1 + peak2 + broad) * scale + noise, 0, None)
        return Spectrum(
            x=x,
            y=y,
            center_wavelength_nm=self.wavelength_nm,
            exposure_time=settings.exposure_time,
            metadata={"backend": "simulation", "grating": self.grating},
        )

    async def abort(self) -> None:
        self._abort = True

    def _require(self) -> None:
        if not self.connected:
            raise RuntimeError("Simulation non connectée.")
