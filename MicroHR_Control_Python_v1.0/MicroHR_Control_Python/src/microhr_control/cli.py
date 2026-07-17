from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from .factory import create_controller
from .models import CameraSettings, ScanSettings


async def _run(args: argparse.Namespace) -> None:
    controller, config = create_controller(args.config)
    camera_cfg = config.get("camera", {})
    roi = camera_cfg.get("roi", {})
    camera = CameraSettings(
        exposure_time=int(getattr(args, "exposure", None) or camera_cfg.get("exposure_time", 100)),
        acquisition_count=int(camera_cfg.get("acquisition_count", 1)),
        open_shutter=bool(camera_cfg.get("open_shutter", True)),
        timeout_s=float(camera_cfg.get("timeout_s", 120)),
        poll_interval_s=float(camera_cfg.get("poll_interval_s", 0.1)),
        x_origin=int(roi.get("x_origin", 0)),
        y_origin=int(roi.get("y_origin", 0)),
        x_size=int(roi.get("x_size", 1024)),
        y_size=int(roi.get("y_size", 256)),
        x_bin=int(roi.get("x_bin", 1)),
        y_bin=int(roi.get("y_bin", 256)),
        x_axis_conversion=str(camera_cfg.get("x_axis_conversion", "FROM_ICL_SETTINGS_INI")),
    )
    try:
        await controller.connect()
        if args.command == "status":
            print(json.dumps(await controller.status(), indent=2, ensure_ascii=False, default=str))
        elif args.command == "initialize":
            await controller.initialize(print)
        elif args.command == "move":
            print(f"{await controller.move_to(args.wavelength):.6f} nm")
        elif args.command == "grating":
            await controller.select_grating(args.number)
        elif args.command == "acquire":
            spectrum = await controller.acquire(camera, args.output)
            print(f"{spectrum.y.size} points, maximum={spectrum.y.max():.3f}")
        elif args.command == "scan":
            scan = ScanSettings(args.start, args.stop, args.step, args.settle, args.save_each_frame)
            result = await controller.scan(
                scan,
                camera,
                lambda i, n, w, _: print(f"{i}/{n} : {w:.4f} nm"),
                args.output,
            )
            print(f"Scan terminé : {len(result.frames)} points")
    finally:
        await controller.disconnect()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pilotage HORIBA MicroHR + Syncerity")
    parser.add_argument("--config", default="config.yaml")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status")
    sub.add_parser("initialize")

    move = sub.add_parser("move")
    move.add_argument("wavelength", type=float)

    grating = sub.add_parser("grating")
    grating.add_argument("number", type=int, choices=[1, 2, 3])

    acquire = sub.add_parser("acquire")
    acquire.add_argument("--exposure", type=int)
    acquire.add_argument("--output")

    scan = sub.add_parser("scan")
    scan.add_argument("--start", type=float, required=True)
    scan.add_argument("--stop", type=float, required=True)
    scan.add_argument("--step", type=float, required=True)
    scan.add_argument("--settle", type=float, default=0.2)
    scan.add_argument("--exposure", type=int)
    scan.add_argument("--output")
    scan.add_argument("--save-each-frame", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    asyncio.run(_run(args))
