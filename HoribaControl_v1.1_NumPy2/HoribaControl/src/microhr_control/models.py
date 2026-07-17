from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np


@dataclass(slots=True)
class CameraSettings:
    exposure_time: int = 100
    acquisition_count: int = 1
    open_shutter: bool = True
    timeout_s: float = 120.0
    poll_interval_s: float = 0.1
    x_origin: int = 0
    y_origin: int = 0
    x_size: int = 1024
    y_size: int = 256
    x_bin: int = 1
    y_bin: int = 256
    x_axis_conversion: str = "FROM_ICL_SETTINGS_INI"


@dataclass(slots=True)
class ScanSettings:
    start_nm: float
    stop_nm: float
    step_nm: float
    settle_time_s: float = 0.2
    save_each_frame: bool = False

    def validate(self) -> None:
        if self.step_nm == 0:
            raise ValueError("Le pas du scan ne peut pas être nul.")
        if self.stop_nm > self.start_nm and self.step_nm < 0:
            raise ValueError("Le pas doit être positif pour un scan croissant.")
        if self.stop_nm < self.start_nm and self.step_nm > 0:
            raise ValueError("Le pas doit être négatif pour un scan décroissant.")


@dataclass(slots=True)
class Spectrum:
    x: np.ndarray
    y: np.ndarray
    center_wavelength_nm: float
    exposure_time: int
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )


@dataclass(slots=True)
class ScanResult:
    requested_wavelength_nm: np.ndarray
    measured_wavelength_nm: np.ndarray
    integrated_intensity: np.ndarray
    peak_intensity: np.ndarray
    frames: list[Spectrum]
    metadata: dict[str, Any] = field(default_factory=dict)
