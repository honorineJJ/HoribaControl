from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True, slots=True)
class AppConfig:
    raw: dict[str, Any]

    @property
    def output_directory(self) -> Path:
        return Path(self.raw["application"]["output_directory"])

    @property
    def log_directory(self) -> Path:
        return Path(self.raw["application"]["log_directory"])

    @property
    def simulation(self) -> dict[str, Any]:
        return dict(self.raw.get("simulation", {}))


def load_config(path: str | Path = "config/default.yaml") -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration introuvable : {config_path.resolve()}")
    with config_path.open("r", encoding="utf-8") as stream:
        raw = yaml.safe_load(stream) or {}
    required = ("instrument", "application", "simulation", "acquisition")
    missing = [name for name in required if name not in raw]
    if missing:
        raise ValueError(f"Sections de configuration absentes : {', '.join(missing)}")
    return AppConfig(raw=raw)
