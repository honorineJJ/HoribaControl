from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import numpy as np

from horibacontrol.domain.models import AcquisitionSettings, Spectrum
from horibacontrol.hardware.backend import InstrumentBackend


class EzSpecBackend(InstrumentBackend):
    """Backend matériel pour horiba-sdk 1.0.3 et ICL.exe."""

    def __init__(
        self,
        config: dict[str, Any],
        instrument_config: dict[str, Any],
        logger: logging.Logger,
        manager_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.config = config
        self.instrument_config = instrument_config
        self.logger = logger
        self._manager_factory = manager_factory
        self.manager: Any = None
        self.monochromator: Any = None
        self.camera: Any = None
        self.connected = False
        self._abort_event = asyncio.Event()

    async def connect(self) -> dict:
        if self.connected:
            return await self.status()

        factory = self._manager_factory
        if factory is None:
            try:
                from horiba_sdk.devices import DeviceManager
            except ImportError as exc:
                raise RuntimeError(
                    "horiba-sdk 1.0.3 n’est pas installé. "
                    "Exécutez : pip install -e .[hardware]"
                ) from exc
            factory = DeviceManager

        self.manager = factory(
            start_icl=bool(self.config.get("start_icl", True)),
            icl_ip=str(self.config.get("icl_ip", "127.0.0.1")),
            icl_port=str(self.config.get("icl_port", "25010")),
            enable_binary_messages=bool(self.config.get("enable_binary_messages", True)),
            enable_logging=bool(self.config.get("enable_sdk_logging", False)),
        )

        try:
            await asyncio.wait_for(
                self.manager.start(),
                timeout=float(self.config.get("discovery_timeout_s", 30.0)),
            )
            monochromators = list(self.manager.monochromators)
            cameras = list(self.manager.charge_coupled_devices)
            mono_index = int(self.instrument_config.get("monochromator_index", 0))
            camera_index = int(self.instrument_config.get("camera_index", 0))

            if not monochromators:
                raise RuntimeError("Aucun monochromateur découvert par ICL.")
            if not cameras:
                raise RuntimeError("Aucune caméra CCD découverte par ICL.")
            if mono_index >= len(monochromators):
                raise IndexError(
                    f"Index monochromateur {mono_index} invalide ; "
                    f"{len(monochromators)} détecté(s)."
                )
            if camera_index >= len(cameras):
                raise IndexError(
                    f"Index caméra {camera_index} invalide ; {len(cameras)} détectée(s)."
                )

            self.monochromator = monochromators[mono_index]
            self.camera = cameras[camera_index]
            await self.monochromator.open()
            await self.camera.open()
            self.connected = True
            self._abort_event.clear()
            return await self.status()
        except BaseException:
            await self._safe_manager_stop()
            self.monochromator = None
            self.camera = None
            self.connected = False
            raise

    async def disconnect(self) -> None:
        errors: list[str] = []
        for label, device in (("caméra", self.camera), ("monochromateur", self.monochromator)):
            if device is None:
                continue
            try:
                if await device.is_open():
                    await device.close()
            except Exception as exc:
                errors.append(f"{label}: {exc}")
        try:
            await self._safe_manager_stop()
        except Exception as exc:
            errors.append(f"DeviceManager: {exc}")
        self.camera = None
        self.monochromator = None
        self.manager = None
        self.connected = False
        if errors:
            self.logger.warning("Fermeture partielle : %s", "; ".join(errors))

    async def initialize(self) -> None:
        self._require_connected()
        self._abort_event.clear()
        await self.monochromator.initialize()
        await self._wait_for(
            self.monochromator.is_busy,
            expected=False,
            timeout=float(self.config.get("motion_timeout_s", 180.0)),
            label="initialisation du MicroHR",
        )
        if not await self.monochromator.is_initialized():
            raise RuntimeError("Le MicroHR ne confirme pas son initialisation.")

    async def status(self) -> dict:
        self._require_connected()
        temperature = None
        try:
            temperature = float(await self.camera.get_chip_temperature())
        except Exception:
            self.logger.debug("Température CCD indisponible", exc_info=True)

        grating = await self.monochromator.get_turret_grating()
        grating_value = int(getattr(grating, "value", grating)) + 1
        return {
            "backend": "ezspec",
            "connected": True,
            "initialized": bool(await self.monochromator.is_initialized()),
            "wavelength_nm": float(await self.monochromator.get_current_wavelength()),
            "grating": grating_value,
            "camera_temperature_c": temperature,
            "monochromator_configuration": await self.monochromator.configuration(),
            "camera_configuration": await self.camera.get_configuration(),
            "detected_monochromators": len(self.manager.monochromators),
            "detected_cameras": len(self.manager.charge_coupled_devices),
        }

    async def move_to(self, wavelength_nm: float) -> float:
        self._require_connected()
        self._abort_event.clear()
        await self.monochromator.move_to_target_wavelength(float(wavelength_nm))
        await self._wait_for(
            self.monochromator.is_busy,
            expected=False,
            timeout=float(self.config.get("motion_timeout_s", 180.0)),
            label=f"déplacement vers {wavelength_nm:.4f} nm",
        )
        return float(await self.monochromator.get_current_wavelength())

    async def select_grating(self, grating_number: int) -> None:
        self._require_connected()
        if grating_number not in (1, 2, 3):
            raise ValueError("Le réseau doit être 1, 2 ou 3.")
        grating_enum = self.monochromator.Grating(grating_number - 1)
        await self.monochromator.set_turret_grating(grating_enum)
        await self._wait_for(
            self.monochromator.is_busy,
            expected=False,
            timeout=float(self.config.get("motion_timeout_s", 180.0)),
            label=f"sélection du réseau {grating_number}",
        )

    async def acquire(self, settings: AcquisitionSettings) -> Spectrum:
        self._require_connected()
        settings.validate()
        self._abort_event.clear()
        center = float(await self.monochromator.get_current_wavelength())

        chip = await self.camera.get_chip_size()
        width, height = int(chip.width), int(chip.height)
        x_size = min(settings.x_size, width - settings.x_origin)
        y_size = min(settings.y_size, height - settings.y_origin)
        if x_size <= 0 or y_size <= 0:
            raise ValueError(f"ROI hors du capteur {width} × {height}.")

        await self.camera.set_exposure_time(int(settings.exposure_ms))
        await self.camera.set_acquisition_count(int(settings.acquisition_count))
        await self._configure_acquisition_format()
        await self.camera.set_region_of_interest(
            roi_index=1,
            x_origin=settings.x_origin,
            y_origin=settings.y_origin,
            x_size=x_size,
            y_size=y_size,
            x_bin=min(settings.x_bin, x_size),
            y_bin=min(settings.y_bin, y_size),
        )
        await self._configure_wavelength_axis(center)

        await self._wait_for(
            self.camera.get_acquisition_ready,
            expected=True,
            timeout=float(self.config.get("acquisition_timeout_s", 180.0)),
            label="préparation de la caméra",
        )
        await self.camera.acquisition_start(bool(settings.open_shutter))
        await self._wait_for(
            self.camera.get_acquisition_busy,
            expected=False,
            timeout=float(self.config.get("acquisition_timeout_s", 180.0)),
            label="acquisition CCD",
        )
        raw = await self.camera.get_acquisition_data()
        x, intensity = self._extract_xy(raw)
        return Spectrum(
            x=x,
            intensity=intensity,
            center_wavelength_nm=center,
            exposure_ms=settings.exposure_ms,
            metadata={
                "backend": "ezspec",
                "roi": {
                    "x_origin": settings.x_origin,
                    "y_origin": settings.y_origin,
                    "x_size": x_size,
                    "y_size": y_size,
                    "x_bin": min(settings.x_bin, x_size),
                    "y_bin": min(settings.y_bin, y_size),
                },
                "raw_data_type": type(raw).__name__,
            },
        )

    async def abort(self) -> None:
        self._abort_event.set()
        if self.camera is not None:
            try:
                if await self.camera.get_acquisition_busy():
                    await self.camera.acquisition_abort()
            except Exception:
                self.logger.debug("Arrêt CCD impossible", exc_info=True)

    async def _configure_acquisition_format(self) -> None:
        try:
            from horiba_sdk.core.acquisition_format import AcquisitionFormat
            candidates = ("SPECTRA", "SPECTRUM", "STANDARD", "FULL_VERTICAL_BINNING", "IMAGE")
            value = next(
                (getattr(AcquisitionFormat, name) for name in candidates if hasattr(AcquisitionFormat, name)),
                None,
            )
            if value is not None:
                await self.camera.set_acquisition_format(1, value)
        except Exception:
            self.logger.debug("Format d’acquisition ICL conservé", exc_info=True)

    async def _configure_wavelength_axis(self, center: float) -> None:
        try:
            from horiba_sdk.core.x_axis_conversion_type import XAxisConversionType
            conversion = XAxisConversionType.FROM_ICL_SETTINGS_INI
            mono_index = float(self.instrument_config.get("monochromator_index", 0))
            await self.camera.set_center_wavelength(mono_index, center)
            await self.camera.set_x_axis_conversion_type(conversion)
        except Exception:
            self.logger.warning(
                "Axe spectral calibré indisponible ; l’axe retourné par ICL sera utilisé.",
                exc_info=True,
            )

    async def _wait_for(
        self,
        predicate: Callable[[], Awaitable[bool]],
        expected: bool,
        timeout: float,
        label: str,
    ) -> None:
        deadline = asyncio.get_running_loop().time() + timeout
        interval = float(self.config.get("poll_interval_s", 0.1))
        while True:
            if self._abort_event.is_set():
                raise asyncio.CancelledError(f"Opération interrompue : {label}")
            if bool(await predicate()) is expected:
                return
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError(f"Délai dépassé pendant {label} ({timeout:.1f} s).")
            await asyncio.sleep(interval)

    async def _safe_manager_stop(self) -> None:
        if self.manager is not None:
            await self.manager.stop()

    def _require_connected(self) -> None:
        if not self.connected or self.monochromator is None or self.camera is None:
            raise RuntimeError("Le système EzSpec n’est pas connecté.")

    @classmethod
    def _extract_xy(cls, raw: Any) -> tuple[np.ndarray, np.ndarray]:
        named_x = cls._find_array(raw, ("xaxis", "xdata", "wavelength", "wavelengths"))
        named_y = cls._find_array(raw, ("ydata", "intensity", "intensities", "data", "values"))
        arrays = list(cls._all_arrays(raw))
        if named_y is None:
            if not arrays:
                raise RuntimeError("Aucune donnée numérique reçue de la caméra.")
            named_y = max(arrays, key=lambda item: item.size)
        y = np.asarray(named_y, dtype=float).reshape(-1)
        if named_x is not None and np.asarray(named_x).size == y.size:
            x = np.asarray(named_x, dtype=float).reshape(-1)
        else:
            x = np.arange(y.size, dtype=float)
        return x, y

    @classmethod
    def _find_array(cls, value: Any, names: tuple[str, ...]) -> np.ndarray | None:
        if isinstance(value, dict):
            for key, child in value.items():
                normalized = str(key).lower().replace("_", "")
                if any(name in normalized for name in names):
                    try:
                        array = np.asarray(child, dtype=float)
                        if array.size > 1:
                            return array
                    except (TypeError, ValueError):
                        pass
            for child in value.values():
                found = cls._find_array(child, names)
                if found is not None:
                    return found
        elif isinstance(value, (list, tuple)):
            for child in value:
                found = cls._find_array(child, names)
                if found is not None:
                    return found
        return None

    @classmethod
    def _all_arrays(cls, value: Any):
        if isinstance(value, dict):
            for child in value.values():
                yield from cls._all_arrays(child)
        elif isinstance(value, (list, tuple)):
            try:
                array = np.asarray(value, dtype=float)
                if array.size > 1:
                    yield array
                    return
            except (TypeError, ValueError):
                pass
            for child in value:
                yield from cls._all_arrays(child)
        elif isinstance(value, np.ndarray) and np.issubdtype(value.dtype, np.number):
            yield value
