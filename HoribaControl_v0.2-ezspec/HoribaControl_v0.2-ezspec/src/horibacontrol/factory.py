from __future__ import annotations

from horibacontrol.application import HoribaControlApplication
from horibacontrol.config import AppConfig
from horibacontrol.hardware.ezspec import EzSpecBackend
from horibacontrol.hardware.simulation import SimulationBackend
from horibacontrol.logging_setup import configure_logging


def create_application(config: AppConfig, force_mode: str | None = None) -> HoribaControlApplication:
    logger = configure_logging(config.log_directory)
    mode = force_mode or str(config.raw["application"].get("mode", "simulation"))
    if mode == "hardware":
        backend = EzSpecBackend(
            config=config.raw.get("ezspec", {}),
            instrument_config=config.raw.get("instrument", {}),
            logger=logger,
        )
    elif mode == "simulation":
        backend = SimulationBackend(config.simulation)
    else:
        raise ValueError(f"Mode inconnu : {mode}")
    return HoribaControlApplication(backend, logger, config.output_directory)
