"""Install / upgrade / reinstall operations."""

from __future__ import annotations

import logging
import os
import shutil
import sys
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from installer.constants import InstallerIdentity
from installer.ops.errors import AppRunningError, InstallerOperationError
from installer.ops.payload import payload_zip_path
from installer.ops.running_app import is_app_running
from installer.ops.shortcuts import create_shortcut, get_shortcut_paths
from installer.state.registry import write_uninstall_entry
from meridian.version import APP_AUTHOR, APP_NAME, __version__

logger = logging.getLogger("installer.install")

ProgressCb = Callable[[str], None]


def _progress(progress, *, pct: int | None, message: str) -> None:  # noqa: ANN001
    if not progress:
        return
    if pct is None:
        progress(message)
    else:
        progress({"pct": int(pct), "message": message})


@dataclass(frozen=True, slots=True)
class InstallOptions:
    target_dir: Path
    create_desktop_shortcut: bool
    create_start_menu_shortcut: bool


def _installer_staging_root() -> Path:
    local = os.getenv("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(local) / "MeridianInstaller" / "staging"


def _extract_payload_to(
    staging_dir: Path, *, progress=None, cancel_event=None
) -> None:  # noqa: ANN001
    staging_dir.mkdir(parents=True, exist_ok=True)
    _check_cancel(cancel_event)
    _progress(progress, pct=10, message="Extracting payload...")
    logger.info("Extracting payload to %s", staging_dir)
    with zipfile.ZipFile(payload_zip_path(), "r") as zf:
        zf.extractall(staging_dir)

    _check_cancel(cancel_event)

    exe = staging_dir / "Meridian.exe"
    internal = staging_dir / "_internal"
    if not exe.exists() or not internal.exists():
        raise InstallerOperationError("Payload is missing Meridian.exe or _internal/")


def _swap_in_bundle(staging_dir: Path, target_dir: Path) -> None:
    target_dir = target_dir.resolve()
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Swapping bundle into %s (staging=%s)", target_dir, staging_dir)

    backup_dir: Path | None = None
    if target_dir.exists():
        backup_dir = target_dir.with_name(
            target_dir.name + f".old.{uuid.uuid4().hex[:8]}"
        )
        try:
            target_dir.rename(backup_dir)
        except Exception as exc:
            raise InstallerOperationError(
                f"Unable to replace existing install at {target_dir}"
            ) from exc

    try:
        try:
            staging_dir.rename(target_dir)
        except OSError:
            shutil.copytree(staging_dir, target_dir, dirs_exist_ok=False)
            shutil.rmtree(staging_dir, ignore_errors=True)
    except Exception:
        if backup_dir and backup_dir.exists() and not target_dir.exists():
            try:
                backup_dir.rename(target_dir)
            except Exception:
                pass
        raise
    finally:
        if backup_dir and backup_dir.exists():
            shutil.rmtree(backup_dir, ignore_errors=True)


def _check_cancel(cancel_event) -> None:  # noqa: ANN001
    if cancel_event is not None and getattr(cancel_event, "is_set", lambda: False)():
        raise InstallerOperationError("Cancelled")


def _copy_self_to_install(identity: InstallerIdentity, install_dir: Path) -> Path:
    install_dir = install_dir.resolve()
    dst = identity.installer_exe_path(install_dir)
    dst.parent.mkdir(parents=True, exist_ok=True)

    src = Path(sys.executable).resolve()
    logger.info("Copying installer from %s to %s", src, dst)
    shutil.copy2(src, dst)
    return dst


def _register_uninstall(
    identity: InstallerIdentity,
    *,
    install_dir: Path,
    installer_copy: Path,
    shortcut_desktop: bool,
    shortcut_start_menu: bool,
) -> None:
    exe = install_dir / "Meridian.exe"
    uninstall_cmd = f'"{installer_copy}" --uninstall'

    display_icon = str(exe)
    for ico_name in ["meridian.ico"]:
        ico_path = install_dir / ico_name
        if ico_path.exists():
            display_icon = str(ico_path)
            break

    write_uninstall_entry(
        identity.uninstall_key,
        display_name=APP_NAME,
        display_version=__version__,
        install_location=install_dir,
        uninstall_string=uninstall_cmd,
        display_icon=display_icon,
        publisher=APP_AUTHOR,
        shortcut_desktop=shortcut_desktop,
        shortcut_start_menu=shortcut_start_menu,
        installer_path=str(installer_copy),
    )


def _deploy_runtime_icon_assets(*, install_dir: Path) -> None:
    """Deploy icon assets next to Meridian.exe."""

    project_root = Path(__file__).resolve().parents[2]

    for name in [
        "meridian.png",
        "meridian.ico",
        "meridian_16.png",
        "meridian_32.png",
        "meridian_48.png",
        "meridian_64.png",
        "meridian_128.png",
        "meridian_256.png",
        "meridian_512.png",
    ]:
        src = project_root / name
        if not src.exists():
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                src = Path(meipass) / name
        if not src.exists():
            continue
        try:
            shutil.copy2(src, install_dir / name)
        except Exception:
            pass


def install_new(
    identity: InstallerIdentity,
    opts: InstallOptions,
    *,
    progress=None,
    cancel_event=None,
) -> None:  # noqa: ANN001
    target_dir = opts.target_dir.resolve()

    staging_dir = target_dir.parent / f".meridian_staging.install.{uuid.uuid4().hex}"
    if staging_dir.exists():
        shutil.rmtree(staging_dir, ignore_errors=True)

    try:
        _extract_payload_to(staging_dir, progress=progress, cancel_event=cancel_event)
        _progress(progress, pct=45, message="Installing...")

        _check_cancel(cancel_event)
        _swap_in_bundle(staging_dir, target_dir)

        _deploy_runtime_icon_assets(install_dir=target_dir)

        _progress(progress, pct=75, message="Registering uninstall entry...")
        _check_cancel(cancel_event)
        logger.info("Registering uninstall entry for %s", target_dir)
        installer_copy = _copy_self_to_install(identity, target_dir)
        _register_uninstall(
            identity,
            install_dir=target_dir,
            installer_copy=installer_copy,
            shortcut_desktop=opts.create_desktop_shortcut,
            shortcut_start_menu=opts.create_start_menu_shortcut,
        )

        _progress(progress, pct=90, message="Creating shortcuts...")
        _check_cancel(cancel_event)
        logger.info("Applying shortcuts")
        _apply_shortcuts(identity, target_dir, opts)
        _progress(progress, pct=100, message="Completed")
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)


def upgrade_or_reinstall(
    identity: InstallerIdentity,
    *,
    current_install_dir: Path,
    opts: InstallOptions,
    progress=None,
    cancel_event=None,
) -> None:
    current_install_dir = current_install_dir.resolve()
    target_dir = opts.target_dir.resolve()

    exe = current_install_dir / "Meridian.exe"
    if exe.exists() and is_app_running(exe):
        raise AppRunningError("Meridian is currently running")

    logger.info(
        "Upgrade/reinstall: current=%s target=%s", current_install_dir, target_dir
    )

    staging_dir = target_dir.parent / f".meridian_staging.upgrade.{uuid.uuid4().hex}"
    if staging_dir.exists():
        shutil.rmtree(staging_dir, ignore_errors=True)

    try:
        _extract_payload_to(staging_dir, progress=progress, cancel_event=cancel_event)

        _progress(progress, pct=45, message="Replacing application files...")
        _check_cancel(cancel_event)

        if target_dir == current_install_dir:
            _swap_in_bundle(staging_dir, target_dir)
        else:
            _swap_in_bundle(staging_dir, target_dir)
            try:
                shutil.rmtree(current_install_dir, ignore_errors=True)
            except Exception:
                pass

        _deploy_runtime_icon_assets(install_dir=target_dir)

        _progress(progress, pct=75, message="Registering uninstall entry...")
        _check_cancel(cancel_event)
        logger.info("Registering uninstall entry for %s", target_dir)
        installer_copy = _copy_self_to_install(identity, target_dir)
        _register_uninstall(
            identity,
            install_dir=target_dir,
            installer_copy=installer_copy,
            shortcut_desktop=opts.create_desktop_shortcut,
            shortcut_start_menu=opts.create_start_menu_shortcut,
        )

        _progress(progress, pct=90, message="Updating shortcuts...")
        _check_cancel(cancel_event)
        logger.info("Applying shortcuts")
        _apply_shortcuts(identity, target_dir, opts)
        _progress(progress, pct=100, message="Completed")
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)


def _apply_shortcuts(
    identity: InstallerIdentity, install_dir: Path, opts: InstallOptions
) -> None:
    exe = install_dir / "Meridian.exe"
    sp = get_shortcut_paths(identity)

    if opts.create_desktop_shortcut:
        create_shortcut(exe, sp.desktop_lnk, working_dir=install_dir)
    else:
        try:
            sp.desktop_lnk.unlink(missing_ok=True)
        except Exception:
            pass

    if opts.create_start_menu_shortcut:
        create_shortcut(exe, sp.start_menu_lnk, working_dir=install_dir)
    else:
        try:
            sp.start_menu_lnk.unlink(missing_ok=True)
        except Exception:
            pass
