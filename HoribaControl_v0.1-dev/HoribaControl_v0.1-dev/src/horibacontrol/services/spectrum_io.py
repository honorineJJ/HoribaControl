from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from horibacontrol.domain.models import Spectrum


def _json_value(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value


def save_spectrum(spectrum: Spectrum, base_path: str | Path) -> tuple[Path, Path]:
    base = Path(base_path)
    base.parent.mkdir(parents=True, exist_ok=True)
    csv_path = base.with_suffix(".csv")
    json_path = base.with_suffix(".json")

    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, delimiter=";")
        writer.writerow(["x", "intensity"])
        writer.writerows(zip(spectrum.x, spectrum.intensity))

    metadata = {
        "center_wavelength_nm": spectrum.center_wavelength_nm,
        "exposure_ms": spectrum.exposure_ms,
        "timestamp_utc": spectrum.timestamp_utc,
        "integrated_intensity": spectrum.integrated_intensity,
        "peak_intensity": spectrum.peak_intensity,
        "metadata": _json_value(spectrum.metadata),
    }
    json_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return csv_path, json_path
