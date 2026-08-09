"""Create/remove per-user shortcuts."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from installer.constants import InstallerIdentity
from installer.ops.errors import InstallerOperationError
from meridian.version import APP_APPUSERMODELID


def _default_icon_location_for(target_exe: Path) -> str:
    # Resolving touches the filesystem and can fail on an unreachable path.
    # The executable carries its own icon resource, so falling back to it
    # yields a correct shortcut with a slightly lower-resolution icon.
    try:
        ico = target_exe.resolve().parent / "meridian.ico"
        if ico.exists() and ico.is_file():
            return str(ico.resolve()).replace("\\", "/")
    except Exception:
        pass
    return str(target_exe)


@dataclass(frozen=True, slots=True)
class ShortcutPaths:
    desktop_lnk: Path
    start_menu_lnk: Path


def _require_windows() -> None:
    if os.name != "nt":
        raise RuntimeError("Shortcuts are supported on Windows only")


def get_shortcut_paths(identity: InstallerIdentity) -> ShortcutPaths:
    _require_windows()

    desktop_dir = Path(os.path.join(os.path.expanduser("~"), "Desktop"))

    appdata = os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    programs_dir = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    start_menu_folder = programs_dir / identity.start_menu_folder

    return ShortcutPaths(
        desktop_lnk=desktop_dir / f"{identity.shortcut_name}.lnk",
        start_menu_lnk=start_menu_folder / f"{identity.shortcut_name}.lnk",
    )


def create_shortcut(  # pragma: no cover
    target_exe: Path, shortcut_path: Path, *, working_dir: Path | None = None
) -> None:
    """Write a `.lnk` through the Windows shell.

    Excluded from coverage deliberately, and recorded in TESTING.md. Exercising
    it means creating a real shortcut in the running user's own Desktop and
    Start Menu through COM, which is a side effect on the developer's machine
    rather than a test. Every caller is covered, and each is asserted to invoke
    this with the executable, destination and working directory it should.
    """
    _require_windows()
    shortcut_path.parent.mkdir(parents=True, exist_ok=True)

    pythoncom = None
    com_initialized = False
    try:
        import pythoncom as _pythoncom  # type: ignore
        from win32com.propsys import propsys  # type: ignore
        from win32com.shell import shell  # type: ignore

        pythoncom = _pythoncom
        pythoncom.CoInitialize()
        com_initialized = True

        link = pythoncom.CoCreateInstance(
            shell.CLSID_ShellLink,
            None,
            pythoncom.CLSCTX_INPROC_SERVER,
            shell.IID_IShellLink,
        )

        link.SetPath(str(target_exe))
        if working_dir is not None:
            link.SetWorkingDirectory(str(working_dir))

        icon_path = _default_icon_location_for(target_exe)
        link.SetIconLocation(icon_path, 0)

        if not APP_APPUSERMODELID:
            raise InstallerOperationError("APP_APPUSERMODELID is empty")

        store = link.QueryInterface(propsys.IID_IPropertyStore)
        key = propsys.PSGetPropertyKeyFromName("System.AppUserModel.ID")
        pv = propsys.PROPVARIANTType(APP_APPUSERMODELID)
        store.SetValue(key, pv)
        store.Commit()

        persist = link.QueryInterface(pythoncom.IID_IPersistFile)
        persist.Save(str(shortcut_path), 0)
    except InstallerOperationError:
        raise
    except Exception as exc:
        # Not swallowed: COM reports a dozen unrelated failure types across
        # the import, the instance creation and the save. They mean one thing
        # to the caller, so they are translated into the installer's own error
        # with the original attached rather than surfaced raw.
        raise InstallerOperationError(
            f"Failed to create shortcut '{shortcut_path}' -> '{target_exe}': {exc!r}"
        ) from exc
    finally:
        # Balancing CoInitialize. A failure here leaks one COM apartment for
        # the few seconds the installer has left to live, which must not mask
        # the real error being raised above.
        try:
            if pythoncom is not None and com_initialized:
                pythoncom.CoUninitialize()
        except Exception:
            pass


def remove_shortcut(shortcut_path: Path) -> None:
    # A shortcut the user has locked, moved or already deleted is not worth
    # failing an uninstall over: the application itself is still removed. If
    # the file will not go, neither will its folder, so this returns rather
    # than falling through.
    try:
        shortcut_path.unlink(missing_ok=True)
    except Exception:
        return

    # Tidying an emptied Start Menu folder is a courtesy. The guard makes the
    # intent explicit; `rmdir` would refuse a non-empty directory anyway, and
    # a folder left behind is litter rather than a failure.
    try:
        if shortcut_path.parent.exists() and not any(shortcut_path.parent.iterdir()):
            shortcut_path.parent.rmdir()
    except Exception:
        return
