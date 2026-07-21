from pathlib import Path

from horibacontrol.application import HoribaControlApplication
from horibacontrol.hardware.simulation import SimulationBackend


class SilentLogger:
    def info(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass


async def test_complete_demo_scenario(tmp_path: Path):
    backend = SimulationBackend(
        {
            "initial_wavelength_nm": 500.0,
            "move_speed_nm_per_second": 1000.0,
            "detector_pixels": 128,
            "random_seed": 7,
        }
    )
    app = HoribaControlApplication(backend, SilentLogger(), tmp_path)

    await app.start()
    try:
        spectrum = await app.run_demo(532.0, 10, 128)
        assert spectrum.intensity.size == 128
        assert spectrum.center_wavelength_nm == 532.0
        assert spectrum.integrated_intensity > 0
        assert (tmp_path / "demo_spectrum.csv").exists()
        assert (tmp_path / "demo_spectrum.json").exists()
    finally:
        await app.stop()
