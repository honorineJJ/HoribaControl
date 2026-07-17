from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

from .models import CameraSettings, Spectrum


class InstrumentBackend(ABC):
    @abstractmethod
    async def connect(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def disconnect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def initialize(self, progress: Callable[[str], None] | None = None) -> None:
        raise NotImplementedError

    @abstractmethod
    async def status(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def move_to(self, wavelength_nm: float) -> float:
        raise NotImplementedError

    @abstractmethod
    async def select_grating(self, grating_number: int) -> None:
        raise NotImplementedError

    @abstractmethod
    async def acquire(self, settings: CameraSettings) -> Spectrum:
        raise NotImplementedError

    @abstractmethod
    async def abort(self) -> None:
        raise NotImplementedError
