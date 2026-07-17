from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Callable

import numpy as np

from .backend import InstrumentBackend
from .data_io import save_scan, save_spectrum
from .models import CameraSettings, ScanResult, ScanSettings, Spectrum


class MicroHRController:
    def __init__(
        self,
        backend: InstrumentBackend,
        logger: logging.Logger,
        output_directory: str | Path = "data",
    ):
        self.backend = backend
        self.logger = logger
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(parents=True, exist_ok=True)
        self.connected = False
        self.last_spectrum: Spectrum | None = None
        self.last_scan: ScanResult | None = None
        self._operation_lock = asyncio.Lock()
        self._abort_requested = False

    async def connect(self) -> dict:
        async with self._operation_lock:
            status = await self.backend.connect()
            self.connected = True
            self.logger.info("Connexion établie")
            return status

    async def disconnect(self) -> None:
        self._abort_requested = True
        await self.backend.abort()
        await self.backend.disconnect()
        self.connected = False
        self.logger.info("Connexion fermée")

    async def initialize(self, progress: Callable[[str], None] | None = None) -> None:
        async with self._operation_lock:
            await self.backend.initialize(progress)

    async def status(self) -> dict:
        return await self.backend.status()

    async def move_to(self, wavelength_nm: float) -> float:
        async with self._operation_lock:
            self._abort_requested = False
            measured = await self.backend.move_to(wavelength_nm)
            self.logger.info("Position atteinte : %.4f nm", measured)
            return measured

    async def select_grating(self, number: int) -> None:
        async with self._operation_lock:
            self._abort_requested = False
            await self.backend.select_grating(number)
            self.logger.info("Réseau %d sélectionné", number)

    async def acquire(self, settings: CameraSettings, output: str | Path | None = None) -> Spectrum:
        async with self._operation_lock:
            self._abort_requested = False
            spectrum = await self.backend.acquire(settings)
            self.last_spectrum = spectrum
            if output is not None:
                save_spectrum(spectrum, output)
            return spectrum

    async def scan(
        self,
        scan: ScanSettings,
        camera: CameraSettings,
        progress: Callable[[int, int, float, Spectrum], None] | None = None,
        output: str | Path | None = None,
    ) -> ScanResult:
        scan.validate()
        async with self._operation_lock:
            self._abort_requested = False
            requested = self._wavelength_axis(scan)
            measured: list[float] = []
            integrated: list[float] = []
            peaks: list[float] = []
            frames: list[Spectrum] = []

            for index, target in enumerate(requested, start=1):
                if self._abort_requested:
                    raise asyncio.CancelledError("Scan interrompu par l'utilisateur.")
                actual = await self.backend.move_to(float(target))
                if scan.settle_time_s > 0:
                    await asyncio.sleep(scan.settle_time_s)
                frame = await self.backend.acquire(camera)
                measured.append(actual)
                integrated.append(float(np.trapezoid(frame.y, frame.x)))
                peaks.append(float(np.max(frame.y)))
                frames.append(frame)
                self.last_spectrum = frame

                if scan.save_each_frame and output is not None:
                    frame_base = Path(output).with_name(f"{Path(output).name}_{index:04d}_{actual:.3f}nm")
                    save_spectrum(frame, frame_base)
                if progress:
                    progress(index, len(requested), actual, frame)

            result = ScanResult(
                requested_wavelength_nm=requested,
                measured_wavelength_nm=np.asarray(measured),
                integrated_intensity=np.asarray(integrated),
                peak_intensity=np.asarray(peaks),
                frames=frames,
                metadata={
                    "start_nm": scan.start_nm,
                    "stop_nm": scan.stop_nm,
                    "step_nm": scan.step_nm,
                    "exposure_time": camera.exposure_time,
                },
            )
            self.last_scan = result
            if output is not None:
                save_scan(result, output)
            return result

    async def abort(self) -> None:
        self._abort_requested = True
        await self.backend.abort()
        self.logger.warning("Demande d'arrêt envoyée")

    @staticmethod
    def _wavelength_axis(scan: ScanSettings) -> np.ndarray:
        epsilon = abs(scan.step_nm) * 1e-9
        stop = scan.stop_nm + (epsilon if scan.step_nm > 0 else -epsilon)
        values = np.arange(scan.start_nm, stop, scan.step_nm, dtype=float)
        if values.size == 0:
            raise ValueError("Le scan ne contient aucun point.")
        return values
