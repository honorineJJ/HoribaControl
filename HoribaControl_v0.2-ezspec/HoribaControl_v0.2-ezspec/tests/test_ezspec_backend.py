from __future__ import annotations

from enum import Enum

import numpy as np

from horibacontrol.domain.models import AcquisitionSettings
from horibacontrol.hardware.ezspec import EzSpecBackend


class FakeGrating(Enum):
    ONE = 0
    TWO = 1
    THREE = 2


class FakeMono:
    Grating = FakeGrating

    def __init__(self):
        self.opened = False
        self.initialized = False
        self.busy_reads = 0
        self.wavelength = 500.0
        self.grating = FakeGrating.ONE

    async def open(self): self.opened = True
    async def close(self): self.opened = False
    async def is_open(self): return self.opened
    async def initialize(self):
        self.initialized = True
        self.busy_reads = 1
    async def is_busy(self):
        if self.busy_reads:
            self.busy_reads -= 1
            return True
        return False
    async def is_initialized(self): return self.initialized
    async def configuration(self): return {"model": "MicroHR fake"}
    async def get_current_wavelength(self): return self.wavelength
    async def move_to_target_wavelength(self, wavelength):
        self.wavelength = wavelength
        self.busy_reads = 1
    async def get_turret_grating(self): return self.grating
    async def set_turret_grating(self, value):
        self.grating = value
        self.busy_reads = 1


class Chip:
    width = 8
    height = 4


class FakeCamera:
    def __init__(self):
        self.opened = False
        self.busy_reads = 0
    async def open(self): self.opened = True
    async def close(self): self.opened = False
    async def is_open(self): return self.opened
    async def get_chip_temperature(self): return -68.5
    async def get_configuration(self): return {"model": "Syncerity fake"}
    async def get_chip_size(self): return Chip()
    async def set_exposure_time(self, value): self.exposure = value
    async def set_acquisition_count(self, value): self.count = value
    async def set_acquisition_format(self, *args): pass
    async def set_region_of_interest(self, **kwargs): self.roi = kwargs
    async def set_center_wavelength(self, *args): pass
    async def set_x_axis_conversion_type(self, *args): pass
    async def get_acquisition_ready(self): return True
    async def acquisition_start(self, value): self.busy_reads = 1
    async def get_acquisition_busy(self):
        if self.busy_reads:
            self.busy_reads -= 1
            return True
        return False
    async def get_acquisition_data(self):
        return {"xAxis": [500, 501, 502, 503], "intensity": [1, 5, 3, 1]}
    async def acquisition_abort(self): self.busy_reads = 0


class FakeManager:
    def __init__(self, **kwargs):
        self.monochromators = [FakeMono()]
        self.charge_coupled_devices = [FakeCamera()]
        self.started = False
    async def start(self): self.started = True
    async def stop(self): self.started = False


class Logger:
    def debug(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass


async def test_ezspec_complete_sequence():
    backend = EzSpecBackend(
        {"poll_interval_s": 0, "discovery_timeout_s": 1, "motion_timeout_s": 1, "acquisition_timeout_s": 1},
        {"monochromator_index": 0, "camera_index": 0},
        Logger(),
        manager_factory=FakeManager,
    )
    status = await backend.connect()
    assert status["detected_monochromators"] == 1
    await backend.initialize()
    assert await backend.move_to(532.0) == 532.0
    await backend.select_grating(2)
    spectrum = await backend.acquire(
        AcquisitionSettings(
            exposure_ms=10,
            detector_pixels=16,
            x_size=8,
            y_size=4,
            y_bin=4,
        )
    )
    assert np.array_equal(spectrum.x, np.array([500, 501, 502, 503], dtype=float))
    assert spectrum.peak_intensity == 5
    await backend.disconnect()
    assert not backend.connected


def test_extract_xy_nested_response():
    raw = {"acquisitions": [{"roi": {"wavelengths": [1, 2, 3], "data": [4, 5, 6]}}]}
    x, y = EzSpecBackend._extract_xy(raw)
    assert x.tolist() == [1, 2, 3]
    assert y.tolist() == [4, 5, 6]
