import asyncio

import numpy as np

from microhr_control.controller import MicroHRController
from microhr_control.models import CameraSettings, ScanSettings
from microhr_control.simulation_backend import SimulationBackend


class DummyLogger:
    def info(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass


def test_simulated_acquisition(tmp_path):
    async def scenario():
        controller = MicroHRController(SimulationBackend(), DummyLogger(), tmp_path)
        await controller.connect()
        await controller.move_to(532.0)
        spectrum = await controller.acquire(CameraSettings(x_size=256))
        assert spectrum.x.size == spectrum.y.size == 256
        assert np.max(spectrum.y) > 1000
        await controller.disconnect()
    asyncio.run(scenario())


def test_simulated_scan(tmp_path):
    async def scenario():
        controller = MicroHRController(SimulationBackend(), DummyLogger(), tmp_path)
        await controller.connect()
        result = await controller.scan(
            ScanSettings(530.0, 534.0, 1.0, settle_time_s=0),
            CameraSettings(x_size=128),
        )
        assert len(result.frames) == 5
        assert result.integrated_intensity.size == 5
        await controller.disconnect()
    asyncio.run(scenario())
