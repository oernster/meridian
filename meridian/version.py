"""Application identity and version.

The repository-root ``VERSION`` file is the single source of truth for the
version string. This module reads it and every other consumer imports
``__version__`` from here, so the number is written in exactly one place.

The file is looked for beside the package (a source tree, an editable install, a
PyInstaller bundle root) and then inside the package, so a layout that ships it
alongside the modules still resolves. When neither is present the fallback below
is used rather than raising, so importing this module can never break a build.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

APP_NAME: str = "Meridian"
APP_AUTHOR: str = "Oliver Ernster"
APP_COPYRIGHT: str = "© Oliver Ernster"
APP_APPUSERMODELID: str = "com.oliverernster.meridian"

FALLBACK_VERSION: str = "0.0.0-dev"

_PACKAGE_DIR = Path(__file__).resolve().parent

VERSION_FILE_CANDIDATES: tuple[Path, ...] = (
    _PACKAGE_DIR.parent / "VERSION",
    _PACKAGE_DIR / "VERSION",
)


def read_version(candidates: Iterable[Path]) -> str:
    """Return the first non-empty VERSION file's contents, else the fallback."""
    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if text:
            return text
    return FALLBACK_VERSION


__version__: str = read_version(VERSION_FILE_CANDIDATES)
