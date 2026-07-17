from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(directory: str | Path) -> logging.Logger:
    log_dir = Path(directory)
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("microhr_control")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(threadName)s | %(name)s | %(message)s"
    )

    file_handler = logging.FileHandler(log_dir / "microhr_control.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger
