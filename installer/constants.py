"""Installer constants."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from meridian.version import APP_AUTHOR, APP_NAME

UNINSTALL_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Meridian"


@dataclass(frozen=True, slots=True)
class InstallerIdentity:
    app_name: str = APP_NAME
    publisher: str = APP_AUTHOR

    uninstall_key: str = UNINSTALL_REG_KEY
    uninstall_key_name: str = "Meridian"

    installer_subdir: str = "_installer"
    installer_exe_name: str = "MeridianSetup.exe"

    start_menu_folder: str = "Meridian"
    shortcut_name: str = "Meridian"

    def installer_exe_path(self, install_root: Path) -> Path:
        return install_root / self.installer_subdir / self.installer_exe_name
