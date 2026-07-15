# config.py

```python
"""
Configuration globale du logiciel MicroHR Control
"""

from pathlib import Path

# ------------------------------------------------------------------
# Informations générales
# ------------------------------------------------------------------

APPLICATION_NAME = "MicroHR Control"

APPLICATION_VERSION = "1.0.0"

# ------------------------------------------------------------------
# SDK HORIBA
# ------------------------------------------------------------------

START_ICL = True

ICL_IP = "127.0.0.1"

ICL_PORT = 25010

ENABLE_BINARY_MESSAGES = True

ENABLE_LOGGING = True

# ------------------------------------------------------------------
# Répertoires
# ------------------------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent

DATA_DIR = PROJECT_DIR / "data"

LOG_DIR = PROJECT_DIR / "logs"

EXPORT_DIR = PROJECT_DIR / "exports"

CONFIG_DIR = PROJECT_DIR / "config"

for directory in (
    DATA_DIR,
    LOG_DIR,
    EXPORT_DIR,
    CONFIG_DIR,
):
    directory.mkdir(exist_ok=True)

# ------------------------------------------------------------------
# Spectromètre
# ------------------------------------------------------------------

DEFAULT_WAVELENGTH = 532.0

DEFAULT_GRATING = 0

DEFAULT_SLIT = 100

# ------------------------------------------------------------------
# Caméra Syncerity
# ------------------------------------------------------------------

DEFAULT_EXPOSURE_MS = 100.0

DEFAULT_GAIN = 1

DEFAULT_BINNING = 1

CCD_TARGET_TEMPERATURE = -70

# ------------------------------------------------------------------
# Acquisition
# ------------------------------------------------------------------

AVERAGES = 1

ACCUMULATIONS = 1

SAVE_FORMAT = "csv"

AUTO_SAVE = False
```
