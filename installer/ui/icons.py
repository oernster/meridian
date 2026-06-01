"""Qt icon helpers for installer UI."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from PySide6.QtGui import QIcon


def build_installer_window_icon(*, project_root: Path) -> QIcon:
    from PySide6.QtGui import QIcon

    brand_path = _find_brand_icon_path(project_root=project_root)
    if brand_path is not None:
        return QIcon(str(brand_path))
    return QIcon()


def _find_brand_icon_path(*, project_root: Path) -> Path | None:
    filenames = ["meridian.png", "meridian.ico"]

    roots: list[Path] = []

    try:
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            roots.append(Path(meipass))
    except Exception:
        pass

    roots.append(project_root)

    try:
        roots.append(Path(sys.executable).resolve().parent)
    except Exception:
        pass

    try:
        roots.append(Path.cwd())
    except Exception:
        pass

    for root in roots:
        for name in filenames:
            p = root / name
            try:
                if p.exists() and p.is_file():
                    return p
            except Exception:
                continue

    return None


def set_windows_app_user_model_id(app_id: str) -> None:
    if os.name != "nt":
        return

    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        return
