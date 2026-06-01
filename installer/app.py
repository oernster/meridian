"""Meridian installer GUI entrypoint."""

from __future__ import annotations

import logging
import os
import sys
import traceback
from pathlib import Path

from PySide6.QtWidgets import QApplication

from installer.cli import parse_args, wants_remove_user_data
from installer.shared.logging_setup import setup_installer_logging
from installer.ui.icons import (
    build_installer_window_icon,
    set_windows_app_user_model_id,
)
from installer.ui.main_window import InstallerMainWindow
from meridian.version import APP_NAME, __version__


def main(argv: list[str] | None = None) -> int:
    if os.name != "nt":
        print("Meridian installer is Windows-only")
        return 2

    log_path = setup_installer_logging()

    def _excepthook(exc_type, exc, tb):  # noqa: ANN001
        with log_path.open("a", encoding="utf-8") as f:
            f.write("\n=== Unhandled exception ===\n")
            traceback.print_exception(exc_type, exc, tb, file=f)
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _excepthook

    args = parse_args(list(argv) if argv is not None else sys.argv[1:])
    _ = wants_remove_user_data(args)

    app = QApplication([f"{APP_NAME} Setup"])
    app.setApplicationName(f"{APP_NAME} Setup")
    app.setApplicationVersion(__version__)

    set_windows_app_user_model_id("com.oliverernster.meridian.installer")

    logger = logging.getLogger("installer.icon")
    try:
        from PySide6.QtGui import QIcon

        icon = build_installer_window_icon(
            project_root=Path(__file__).resolve().parents[1]
        )
        if not icon.isNull():
            app.setWindowIcon(icon)
            logger.info("Installer window icon applied (QApplication).")
    except Exception:
        logger.exception("Failed to set QApplication window icon")

    win = InstallerMainWindow(cli_args=args)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
