from __future__ import annotations

from .config import load_config
from .controller import MicroHRController
from .horiba_backend import HoribaBackend
from .logging_utils import configure_logging
from .simulation_backend import SimulationBackend


def create_controller(config_path: str = "config.yaml"):
    config = load_config(config_path)
    app_cfg = config.get("application", {})
    logger = configure_logging(app_cfg.get("log_directory", "logs"))
    if bool(app_cfg.get("simulation", False)):
        backend = SimulationBackend()
        logger.warning("MODE SIMULATION actif")
    else:
        backend = HoribaBackend(config, logger)
    controller = MicroHRController(
        backend=backend,
        logger=logger,
        output_directory=app_cfg.get("output_directory", "data"),
    )
    return controller, config
