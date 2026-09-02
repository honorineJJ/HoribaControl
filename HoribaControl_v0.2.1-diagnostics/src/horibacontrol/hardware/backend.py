from __future__ import annotations

from abc import ABC, abstractmethod

from horibacontrol.domain.models import AcquisitionSettings, Spectrum


class InstrumentBackend(ABC):
    @abstractmethod
    async def connect(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def disconnect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def initialize(self) -> None:
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
    async def acquire(self, settings: AcquisitionSettings) -> Spectrum:
        raise NotImplementedError

    @abstractmethod
    async def abort(self) -> None:
        raise NotImplementedError
