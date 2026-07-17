from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from .models import ScanResult, Spectrum


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def save_spectrum(spectrum: Spectrum, base_path: str | Path) -> list[Path]:
    base = Path(base_path)
    base.parent.mkdir(parents=True, exist_ok=True)
    csv_path = base.with_suffix(".csv")
    npz_path = base.with_suffix(".npz")
    json_path = base.with_suffix(".json")

    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, delimiter=";")
        writer.writerow(["x", "intensity"])
        writer.writerows(zip(spectrum.x, spectrum.y))

    np.savez_compressed(
        npz_path,
        x=spectrum.x,
        y=spectrum.y,
        center_wavelength_nm=spectrum.center_wavelength_nm,
        exposure_time=spectrum.exposure_time,
    )

    metadata = {
        "center_wavelength_nm": spectrum.center_wavelength_nm,
        "exposure_time": spectrum.exposure_time,
        "timestamp_utc": spectrum.timestamp_utc,
        "metadata": spectrum.metadata,
    }
    json_path.write_text(json.dumps(_jsonable(metadata), indent=2, ensure_ascii=False), encoding="utf-8")
    return [csv_path, npz_path, json_path]


def save_scan(result: ScanResult, base_path: str | Path) -> list[Path]:
    base = Path(base_path)
    base.parent.mkdir(parents=True, exist_ok=True)
    csv_path = base.with_suffix(".csv")
    npz_path = base.with_suffix(".npz")
    json_path = base.with_suffix(".json")

    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, delimiter=";")
        writer.writerow(["requested_nm", "measured_nm", "integrated_intensity", "peak_intensity"])
        writer.writerows(
            zip(
                result.requested_wavelength_nm,
                result.measured_wavelength_nm,
                result.integrated_intensity,
                result.peak_intensity,
            )
        )

    np.savez_compressed(
        npz_path,
        requested_wavelength_nm=result.requested_wavelength_nm,
        measured_wavelength_nm=result.measured_wavelength_nm,
        integrated_intensity=result.integrated_intensity,
        peak_intensity=result.peak_intensity,
    )

    json_path.write_text(
        json.dumps(_jsonable({"metadata": result.metadata, "frame_count": len(result.frames)}), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return [csv_path, npz_path, json_path]
