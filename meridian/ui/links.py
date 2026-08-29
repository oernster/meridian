"""Handing an address to whatever the desktop opens links with.

One function, in its own module, so it is a seam a controller can be given
instead of the real thing. Calling Qt's opener straight from a bridge would
leave no way to prove the right address is asked for without opening a browser
in the middle of a test run.

Nothing here fetches anything. The address is passed outward and the desktop
decides what to do with it, so the application still opens no connection of its
own; this is what leaves Meridian's local-first guarantee untouched by the
donate button existing.
"""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

__all__ = ["open_externally"]


def open_externally(address: str) -> bool:
    """Ask the desktop to open this address; False when it declined to.

    A refusal is reported rather than raised: failing to open a browser is
    worth telling the user about and is not worth ending anything over.
    """
    return QDesktopServices.openUrl(QUrl(address))
