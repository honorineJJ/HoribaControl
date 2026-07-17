from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Iterable

import numpy as np

from .backend import InstrumentBackend
from .models import CameraSettings, Spectrum


class HoribaBackend(InstrumentBackend):
    """Backend réel utilisant le package officiel horiba-sdk."""

    def __init__(self, config: dict[str, Any], logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.manager: Any = None
        self.mono: Any = None
        self.ccd: Any = None
        self.connected = False
        self._abort_event = asyncio.Event()

    async def connect(self) -> dict:
        try:
            from horiba_sdk.devices import DeviceManager
        except ImportError as exc:
            raise RuntimeError(
                "Le package horiba-sdk n'est pas installé. Exécutez : pip install horiba-sdk"
            ) from exc

        connection = self.config.get("connection", {})
        self.manager = DeviceManager(
            start_icl=bool(connection.get("start_icl", True)),
            icl_ip=str(connection.get("icl_ip", "127.0.0.1")),
            icl_port=str(connection.get("icl_port", "25010")),
            enable_binary_messages=bool(connection.get("enable_binary_messages", True)),
            enable_logging=bool(connection.get("enable_sdk_logging", False)),
        )
        self.logger.info("Démarrage du DeviceManager HORIBA et découverte des périphériques")
        await self.manager.start()

        mono_index = int(self.config.get("instrument", {}).get("monochromator_index", 0))
        camera_index = int(self.config.get("instrument", {}).get("camera_index", 0))
        monos = list(self.manager.monochromators)
        cameras = list(self.manager.charge_coupled_devices)

        if not monos:
            await self.manager.stop()
            raise RuntimeError("Aucun monochromateur détecté par ICL.")
        if not cameras:
            await self.manager.stop()
            raise RuntimeError("Aucune caméra CCD détectée par ICL.")
        if mono_index >= len(monos) or camera_index >= len(cameras):
            await self.manager.stop()
            raise IndexError(
                f"Index périphérique invalide. Monochromateurs={len(monos)}, CCD={len(cameras)}."
            )

        self.mono = monos[mono_index]
        self.ccd = cameras[camera_index]
        await self.mono.open()
        await self.ccd.open()
        self.connected = True
        self._abort_event.clear()

        if self.config.get("motion", {}).get("initialize_on_connect", False):
            await self.initialize()

        return await self.status()

    async def disconnect(self) -> None:
        errors: list[str] = []
        if self.ccd is not None:
            try:
                if await self.ccd.is_open():
                    await self.ccd.close()
            except Exception as exc:  # matériel : nettoyage best-effort
                errors.append(f"CCD: {exc}")
        if self.mono is not None:
            try:
                if await self.mono.is_open():
                    await self.mono.close()
            except Exception as exc:
                errors.append(f"Monochromateur: {exc}")
        if self.manager is not None:
            try:
                await self.manager.stop()
            except Exception as exc:
                errors.append(f"DeviceManager: {exc}")
        self.connected = False
        if errors:
            self.logger.warning("Erreurs à la fermeture : %s", "; ".join(errors))

    async def initialize(self, progress: Callable[[str], None] | None = None) -> None:
        self._require_connected()
        if progress:
            progress("Initialisation mécanique du MicroHR…")
        await self.mono.initialize()
        await self._wait_until(
            predicate=self.mono.is_busy,
            expected=False,
            timeout=float(self.config.get("motion", {}).get("timeout_s", 180.0)),
            interval=float(self.config.get("motion", {}).get("poll_interval_s", 0.1)),
            label="initialisation du monochromateur",
        )
        if not await self.mono.is_initialized():
            raise RuntimeError("Le MicroHR n'indique pas un état initialisé après le homing.")
        if progress:
            progress("MicroHR initialisé.")

    async def status(self) -> dict:
        self._require_connected()
        camera_temperature = None
        try:
            camera_temperature = await self.ccd.get_chip_temperature()
        except Exception:
            self.logger.debug("Température CCD non disponible", exc_info=True)

        return {
            "connected": True,
            "monochromator_open": await self.mono.is_open(),
            "camera_open": await self.ccd.is_open(),
            "initialized": await self.mono.is_initialized(),
            "wavelength_nm": await self.mono.get_current_wavelength(),
            "grating": (await self.mono.get_turret_grating()).value + 1,
            "camera_temperature_c": camera_temperature,
            "monochromator_configuration": await self.mono.configuration(),
            "camera_configuration": await self.ccd.get_configuration(),
        }

    async def move_to(self, wavelength_nm: float) -> float:
        self._require_connected()
        self._abort_event.clear()
        await self.mono.move_to_target_wavelength(float(wavelength_nm))
        await self._wait_until(
            predicate=self.mono.is_busy,
            expected=False,
            timeout=float(self.config.get("motion", {}).get("timeout_s", 180.0)),
            interval=float(self.config.get("motion", {}).get("poll_interval_s", 0.1)),
            label=f"déplacement vers {wavelength_nm:.3f} nm",
        )
        return float(await self.mono.get_current_wavelength())

    async def select_grating(self, grating_number: int) -> None:
        self._require_connected()
        if grating_number not in (1, 2, 3):
            raise ValueError("Le numéro de réseau doit être 1, 2 ou 3.")
        enum_value = self.mono.Grating(grating_number - 1)
        await self.mono.set_turret_grating(enum_value)
        await self._wait_until(
            predicate=self.mono.is_busy,
            expected=False,
            timeout=float(self.config.get("motion", {}).get("timeout_s", 180.0)),
            interval=float(self.config.get("motion", {}).get("poll_interval_s", 0.1)),
            label=f"sélection du réseau {grating_number}",
        )

    async def acquire(self, settings: CameraSettings) -> Spectrum:
        self._require_connected()
        self._abort_event.clear()
        center = float(await self.mono.get_current_wavelength())

        await self.ccd.set_exposure_time(int(settings.exposure_time))
        await self.ccd.set_acquisition_count(int(settings.acquisition_count))

        chip_size = await self.ccd.get_chip_size()
        width = int(getattr(chip_size, "width", getattr(chip_size, "x", settings.x_size)))
        height = int(getattr(chip_size, "height", getattr(chip_size, "y", settings.y_size)))
        x_size = min(settings.x_size, width - settings.x_origin)
        y_size = min(settings.y_size, height - settings.y_origin)
        if x_size <= 0 or y_size <= 0:
            raise ValueError(f"ROI hors capteur : capteur={width}×{height}")

        await self._configure_acquisition_format()
        await self.ccd.set_region_of_interest(
            roi_index=1,
            x_origin=settings.x_origin,
            y_origin=settings.y_origin,
            x_size=x_size,
            y_size=y_size,
            x_bin=settings.x_bin,
            y_bin=min(settings.y_bin, y_size),
        )
        await self._configure_x_axis(settings.x_axis_conversion, center)

        await self._wait_until(
            predicate=self.ccd.get_acquisition_ready,
            expected=True,
            timeout=settings.timeout_s,
            interval=settings.poll_interval_s,
            label="préparation de la caméra",
        )
        await self.ccd.acquisition_start(bool(settings.open_shutter))
        await self._wait_until(
            predicate=self.ccd.get_acquisition_busy,
            expected=False,
            timeout=settings.timeout_s,
            interval=settings.poll_interval_s,
            label="acquisition CCD",
        )
        raw = await self.ccd.get_acquisition_data()
        x, y = self._extract_xy(raw)
        return Spectrum(
            x=x,
            y=y,
            center_wavelength_nm=center,
            exposure_time=settings.exposure_time,
            metadata={
                "backend": "HORIBA EzSpec",
                "raw_keys": list(raw.keys()) if isinstance(raw, dict) else [],
                "roi": {
                    "x_origin": settings.x_origin,
                    "y_origin": settings.y_origin,
                    "x_size": x_size,
                    "y_size": y_size,
                    "x_bin": settings.x_bin,
                    "y_bin": min(settings.y_bin, y_size),
                },
            },
        )

    async def abort(self) -> None:
        self._abort_event.set()
        if self.ccd is not None:
            try:
                if await self.ccd.get_acquisition_busy():
                    await self.ccd.acquisition_abort()
            except Exception:
                self.logger.debug("Impossible d'interrompre la CCD", exc_info=True)

    async def _configure_acquisition_format(self) -> None:
        try:
            from horiba_sdk.core.acquisition_format import AcquisitionFormat
            candidates = ("SPECTRA", "SPECTRUM", "STANDARD", "FULL_VERTICAL_BINNING", "IMAGE")
            selected = next((getattr(AcquisitionFormat, n) for n in candidates if hasattr(AcquisitionFormat, n)), None)
            if selected is not None:
                await self.ccd.set_acquisition_format(1, selected)
        except (ImportError, AttributeError):
            self.logger.debug("Format d'acquisition laissé à la configuration ICL.")
        except Exception:
            self.logger.warning("Le format d'acquisition existant est conservé.", exc_info=True)

    async def _configure_x_axis(self, name: str, center: float) -> None:
        try:
            from horiba_sdk.core.x_axis_conversion_type import XAxisConversionType
            conversion = getattr(XAxisConversionType, name)
            if name == "FROM_ICL_SETTINGS_INI":
                mono_index = float(self.config.get("instrument", {}).get("monochromator_index", 0))
                await self.ccd.set_center_wavelength(mono_index, center)
            await self.ccd.set_x_axis_conversion_type(conversion)
        except Exception:
            self.logger.warning(
                "Conversion X '%s' indisponible ; utilisation de l'axe retourné par ICL.", name, exc_info=True
            )

    async def _wait_until(
        self,
        predicate: Callable[[], Any],
        expected: bool,
        timeout: float,
        interval: float,
        label: str,
    ) -> None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while True:
            if self._abort_event.is_set():
                raise asyncio.CancelledError(f"Opération interrompue : {label}")
            value = bool(await predicate())
            if value is expected:
                return
            if loop.time() >= deadline:
                raise TimeoutError(f"Délai dépassé pendant {label} ({timeout:.1f} s).")
            await asyncio.sleep(interval)

    def _extract_xy(self, raw: Any) -> tuple[np.ndarray, np.ndarray]:
        arrays = list(self._numeric_arrays(raw))
        if not arrays:
            raise RuntimeError(f"Aucune donnée numérique exploitable dans la réponse CCD : {type(raw).__name__}")

        named_x = self._find_named_array(raw, ("x", "xdata", "wavelength", "wavelengths", "axis"))
        named_y = self._find_named_array(raw, ("y", "ydata", "intensity", "intensities", "data", "values"))

        if named_y is None:
            named_y = max(arrays, key=lambda item: item.size)
        y = np.asarray(named_y, dtype=float).reshape(-1)

        if named_x is not None and np.asarray(named_x).size == y.size:
            x = np.asarray(named_x, dtype=float).reshape(-1)
        else:
            x = np.arange(y.size, dtype=float)
        return x, y

    def _numeric_arrays(self, value: Any) -> Iterable[np.ndarray]:
        if isinstance(value, dict):
            for child in value.values():
                yield from self._numeric_arrays(child)
        elif isinstance(value, (list, tuple)):
            try:
                array = np.asarray(value, dtype=float)
                if array.ndim >= 1 and array.size > 1:
                    yield array
                    return
            except (TypeError, ValueError):
                pass
            for child in value:
                yield from self._numeric_arrays(child)
        elif isinstance(value, np.ndarray) and np.issubdtype(value.dtype, np.number):
            yield value

    def _find_named_array(self, value: Any, names: tuple[str, ...]) -> np.ndarray | None:
        if isinstance(value, dict):
            for key, child in value.items():
                normalized = str(key).lower().replace("_", "")
                if any(name in normalized for name in names):
                    try:
                        array = np.asarray(child, dtype=float)
                        if array.ndim >= 1 and array.size > 1:
                            return array
                    except (TypeError, ValueError):
                        pass
            for child in value.values():
                found = self._find_named_array(child, names)
                if found is not None:
                    return found
        elif isinstance(value, (list, tuple)):
            for child in value:
                found = self._find_named_array(child, names)
                if found is not None:
                    return found
        return None

    def _require_connected(self) -> None:
        if not self.connected or self.mono is None or self.ccd is None:
            raise RuntimeError("Le système HORIBA n'est pas connecté.")
