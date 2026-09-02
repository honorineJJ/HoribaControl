from __future__ import annotations

import logging
from pathlib import Path

from horibacontrol.core.command_queue import CommandQueue
from horibacontrol.core.event_bus import EventBus
from horibacontrol.core.state_machine import StateMachine
from horibacontrol.domain.commands import (
    acquire_command,
    connect_command,
    disconnect_command,
    initialize_command,
    move_command,
)
from horibacontrol.domain.models import AcquisitionSettings, Spectrum
from horibacontrol.hardware.backend import InstrumentBackend
from horibacontrol.services.spectrum_io import save_spectrum


class HoribaControlApplication:
    def __init__(
        self,
        backend: InstrumentBackend,
        logger: logging.Logger,
        output_directory: str | Path = "data",
    ) -> None:
        self.backend = backend
        self.logger = logger
        self.output_directory = Path(output_directory)
        self.events = EventBus()
        self.state = StateMachine()
        self.commands = CommandQueue(backend, self.state, self.events, logger)

    async def start(self) -> None:
        await self.commands.start()

    async def stop(self) -> None:
        if self.state.state.value != "disconnected":
            await self.commands.submit(disconnect_command())
        await self.commands.stop()

    async def run_demo(
        self,
        wavelength_nm: float = 532.0,
        exposure_ms: int = 100,
        detector_pixels: int = 1024,
    ) -> Spectrum:
        await self.commands.submit(connect_command())
        await self.commands.submit(initialize_command())
        await self.commands.submit(move_command(wavelength_nm))
        spectrum = await self.commands.submit(
            acquire_command(AcquisitionSettings(exposure_ms, detector_pixels))
        )
        save_spectrum(spectrum, self.output_directory / "demo_spectrum")
        return spectrum
