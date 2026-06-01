"""Helpers for locating embedded resources.

When bundled with PyInstaller, files added via --add-data are unpacked under
sys._MEIPASS.
"""

from __future__ import annotations

import sys
from pathlib import Path


def bundled_data_root() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(__file__).resolve().parents[2]


def resource_path(relative_path: str) -> Path:
    return bundled_data_root() / relative_path
