"""Starting the installed application once an operation has finished.

The decision and the act are kept apart. Deciding whether anything should
start is pure, lives here and is measured by the coverage gate. Actually
starting it and putting its window in front are two Windows side effects that
cannot be exercised without launching a real application on the developer's
machine, so each carries `# pragma: no cover` and is named in ARCHITECTURE.md
alongside the other omissions.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from installer.state.model import Operation

logger = logging.getLogger("installer.launch")

# Every operation that leaves an installation behind. Uninstall is absent
# because once it has run there is nothing left to start.
LAUNCHABLE_OPERATIONS = frozenset(
    {
        Operation.INSTALL,
        Operation.UPGRADE,
        Operation.REINSTALL,
        Operation.REPAIR,
    }
)


def exe_to_launch(
    *,
    op: Operation,
    succeeded: bool,
    requested: bool,
    installed_exe: Path | None,
) -> Path | None:
    """Return the executable to start now an operation has finished.

    `None` means start nothing. The rule lives here rather than in the window
    because the Qt slot that calls it sits outside the coverage gate. Starting
    the application after a failed install or after an uninstall that has just
    deleted it is the kind of mistake that would otherwise only appear on a
    user's machine.
    """
    if not requested:
        return None
    if not succeeded:
        return None
    if op not in LAUNCHABLE_OPERATIONS:
        return None
    if installed_exe is None or not installed_exe.exists():
        return None
    return installed_exe


def launch(exe_path: Path) -> subprocess.Popen | None:  # pragma: no cover
    """Start the installed application without waiting for it.

    Excluded from coverage deliberately and recorded in ARCHITECTURE.md:
    exercising it means starting a real application on the developer's
    machine. The caller is covered and asserts what it is handed.

    A failure to start is reported as `None` rather than raised. The operation
    itself has already succeeded by this point, so an application that will
    not start is a disappointing finish to a good install, never a failed one.
    """
    try:
        return subprocess.Popen([str(exe_path)], cwd=str(exe_path.parent))
    except OSError:
        logger.warning("Unable to start %s", exe_path)
        return None


def bring_process_window_to_front(pid: int) -> bool:  # pragma: no cover
    """Front the process's first visible top-level window, if it has one yet.

    Windows denies the foreground to a window that appears after the process
    which asked for it has exited, so the installer fronts the application
    while it still owns the foreground itself. Without this the application
    opens behind whatever was already on screen and only flashes on the
    taskbar.

    Excluded from coverage for the same reason as `launch`: there is no window
    to front without first starting a real application.
    """
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    found: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _on_window(hwnd: int, _lparam: int) -> bool:
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
            return False
        return True

    user32.EnumWindows(_on_window, 0)
    if not found:
        return False
    user32.SetForegroundWindow(found[0])
    return True
