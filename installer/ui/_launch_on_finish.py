"""Start the application when an operation finishes, then close the installer.

Kept apart from `_main_window_actions` for two reasons. That module sits close
enough to the size cap that this would have pushed it into the danger band;
what happens here is also a small state machine of its own (start, wait for
the window, front it, close) rather than another handler.

Only the sequencing lives here. Whether to start anything at all is decided by
`installer.ops.launch_ops.exe_to_launch`, which is inside the coverage gate.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer

from installer.ops.launch_ops import bring_process_window_to_front, launch
from meridian.version import APP_NAME

if TYPE_CHECKING:  # pragma: no cover
    from installer.ui.main_window import InstallerMainWindow

# The application takes a few seconds to show its window. The installer stays
# open until it appears or until this passes, so that it is still the
# foreground process when the window arrives: Windows denies the foreground to
# a window whose starter has already gone.
_FOREGROUND_WAIT_S = 15.0
_FOREGROUND_POLL_MS = 200


def launch_and_close(window: InstallerMainWindow, exe_path: Path) -> None:
    """Start the application, front its window when it appears, then close."""
    process = launch(exe_path)
    if process is None:
        window.close()
        return

    window._progress.setText(f"Starting {APP_NAME}...")
    deadline = time.monotonic() + _FOREGROUND_WAIT_S
    timer = QTimer(window)

    def _poll() -> None:
        if bring_process_window_to_front(process.pid) or time.monotonic() > deadline:
            timer.stop()
            window.close()

    timer.timeout.connect(_poll)
    timer.start(_FOREGROUND_POLL_MS)
    # Held on the window as well as parented to it, so the timer is reachable
    # from a test and cannot be collected while the poll is still running.
    window._front_timer = timer
