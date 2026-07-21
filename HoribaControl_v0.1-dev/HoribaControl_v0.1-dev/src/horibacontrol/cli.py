from __future__ import annotations

import argparse
import asyncio

from horibacontrol.application import HoribaControlApplication
from horibacontrol.config import load_config
from horibacontrol.hardware.simulation import SimulationBackend
from horibacontrol.logging_setup import configure_logging


async def _demo(config_path: str) -> None:
    config = load_config(config_path)
    logger = configure_logging(config.log_directory)
    backend = SimulationBackend(config.simulation)
    app = HoribaControlApplication(backend, logger, config.output_directory)

    await app.start()
    try:
        acquisition = config.raw["acquisition"]
        spectrum = await app.run_demo(
            wavelength_nm=float(acquisition.get("center_wavelength_nm", 532.0)),
            exposure_ms=int(acquisition.get("exposure_ms", 100)),
            detector_pixels=int(config.simulation.get("detector_pixels", 1024)),
        )
        print(f"Spectre acquis : {spectrum.intensity.size} points")
        print(f"Maximum : {spectrum.peak_intensity:.2f}")
        print(f"Intégrale : {spectrum.integrated_intensity:.2f}")
        print(f"Fichier : {config.output_directory / 'demo_spectrum.csv'}")
    finally:
        await app.stop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HoribaControl")
    parser.add_argument("--config", default="config/default.yaml")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("demo", help="Exécuter le scénario complet en simulation")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "demo":
        asyncio.run(_demo(args.config))
