"""Per-user application paths for macOS, Windows, and Linux."""

from __future__ import annotations

import os
import sys
from pathlib import Path


APP_DIR_NAME = "Technocore Easy Setup"


def app_data_dir() -> Path:
    """Return a per-user local application data directory."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / APP_DIR_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "technocore-easy-setup"


def identity_path() -> Path:
    """Return the one canonical identity path used by the GUI."""
    return app_data_dir() / "identity.pem"
