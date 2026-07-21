from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import numpy as np


class InstrumentState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    INITIALIZING = "initializing"
    READY = "ready"
    MOVING = "moving"
    ACQUIRING = "acquiring"
    ERROR = "error"
    STOPPING = "stopping"


@dataclass(frozen=True, slots=True)
class AcquisitionSettings:
    exposure_ms: int = 100
    detector_pixels: int = 1024
    acquisition_count: int = 1
    open_shutter: bool = True
    x_origin: int = 0
    y_origin: int = 0
    x_size: int = 1024
    y_size: int = 256
    x_bin: int = 1
    y_bin: int = 256

    def validate(self) -> None:
        if self.exposure_ms <= 0:
            raise ValueError("Le temps d’exposition doit être strictement positif.")
        if self.detector_pixels < 16:
            raise ValueError("Le nombre de pixels doit être supérieur ou égal à 16.")
        if self.acquisition_count <= 0:
            raise ValueError("Le nombre d’acquisitions doit être strictement positif.")
        for name, value in (
            ("x_size", self.x_size),
            ("y_size", self.y_size),
            ("x_bin", self.x_bin),
            ("y_bin", self.y_bin),
        ):
            if value <= 0:
                raise ValueError(f"{name} doit être strictement positif.")


@dataclass(slots=True)
class Spectrum:
    x: np.ndarray
    intensity: np.ndarray
    center_wavelength_nm: float
    exposure_ms: int
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    @property
    def integrated_intensity(self) -> float:
        return float(np.trapezoid(self.intensity, self.x))

    @property
    def peak_intensity(self) -> float:
        return float(np.max(self.intensity))
