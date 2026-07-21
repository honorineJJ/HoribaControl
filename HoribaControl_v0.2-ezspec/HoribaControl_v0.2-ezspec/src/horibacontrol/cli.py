from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from horibacontrol.config import load_config
from horibacontrol.domain.commands import (
    acquire_command,
    connect_command,
    disconnect_command,
    initialize_command,
    move_command,
    select_grating_command,
    status_command,
)
from horibacontrol.domain.models import AcquisitionSettings
from horibacontrol.factory import create_application
from horibacontrol.services.spectrum_io import save_spectrum


def _settings(config) -> AcquisitionSettings:
    acquisition = config.raw["acquisition"]
    roi = acquisition.get("roi", {})
    return AcquisitionSettings(
        exposure_ms=int(acquisition.get("exposure_ms", 100)),
        detector_pixels=int(config.simulation.get("detector_pixels", 1024)),
        acquisition_count=int(acquisition.get("acquisition_count", 1)),
        open_shutter=bool(acquisition.get("open_shutter", True)),
        x_origin=int(roi.get("x_origin", 0)),
        y_origin=int(roi.get("y_origin", 0)),
        x_size=int(roi.get("x_size", 1024)),
        y_size=int(roi.get("y_size", 256)),
        x_bin=int(roi.get("x_bin", 1)),
        y_bin=int(roi.get("y_bin", 256)),
    )


async def _run(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    mode = "simulation" if args.command == "demo" else "hardware"
    app = create_application(config, force_mode=mode)
    await app.start()
    try:
        if args.command == "demo":
            spectrum = await app.run_demo(
                wavelength_nm=float(config.raw["acquisition"].get("center_wavelength_nm", 532.0)),
                exposure_ms=int(config.raw["acquisition"].get("exposure_ms", 100)),
                detector_pixels=int(config.simulation.get("detector_pixels", 1024)),
            )
            print(f"Spectre simulé : {spectrum.intensity.size} points")
            print(f"Maximum : {spectrum.peak_intensity:.2f}")
            print(f"Intégrale : {spectrum.integrated_intensity:.2f}")

        elif args.command == "diagnose":
            await app.commands.submit(connect_command())
            status = await app.commands.submit(status_command())
            print(json.dumps(status, indent=2, ensure_ascii=False, default=str))

        elif args.command == "hardware-smoke":
            await app.commands.submit(connect_command())
            await app.commands.submit(initialize_command())
            if args.grating is not None:
                await app.commands.submit(select_grating_command(args.grating))
            measured = await app.commands.submit(move_command(args.wavelength))
            spectrum = await app.commands.submit(acquire_command(_settings(config)))
            output = Path(args.output)
            csv_path, json_path = save_spectrum(spectrum, output)
            print(f"Position mesurée : {measured:.6f} nm")
            print(f"Spectre : {spectrum.intensity.size} points")
            print(f"CSV : {csv_path}")
            print(f"JSON : {json_path}")
    finally:
        try:
            if app.state.state.value != "disconnected":
                await app.commands.submit(disconnect_command())
        finally:
            await app.commands.stop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HoribaControl")
    parser.add_argument("--config", default="config/default.yaml")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("demo", help="Scénario complet en simulation")
    sub.add_parser("diagnose", help="Connexion EzSpec et affichage de la configuration matérielle")

    smoke = sub.add_parser("hardware-smoke", help="Initialiser, déplacer et acquérir sur le matériel")
    smoke.add_argument("--wavelength", type=float, default=532.0)
    smoke.add_argument("--grating", type=int, choices=[1, 2, 3])
    smoke.add_argument("--output", default="data/hardware_smoke")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    asyncio.run(_run(args))
