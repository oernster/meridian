"""QML bridge for the two buttons that leave the application.

A separate QObject rather than another surface on AppController, for the same
reason the update check is one: AppController is about feeds and items, while a
button that opens a browser belongs to none of that.

It holds the addresses rather than exposing them, so QML never carries a second
copy of a string that must be right. The opener is injected, which is the whole
point of the seam: a test can prove the exact address was asked for without a
browser opening in the middle of a run.

One controller for both because they differ only in which constant they read.
The failure signal names what could not be opened, since "could not open a
browser" is no use to someone who pressed one of two buttons.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, Signal, Slot

from meridian.ui.links import open_externally
from meridian.version import DONATE_URL, SPECIFICATION_URL

__all__ = ["ExternalLinkController"]

# What the window says when the desktop will not open a browser. Named here
# rather than in the QML so the two slots below cannot describe themselves
# differently.
DONATION_DESCRIPTION = "the donation page"
SPECIFICATION_DESCRIPTION = "the MMSP specification"


class ExternalLinkController(QObject):
    """Opens an address in the user's browser; says so when it cannot."""

    # Carries what could not be opened, for the message the window shows.
    openFailed = Signal(str)

    def __init__(
        self,
        opener: Callable[[str], bool] = open_externally,
        donate_address: str = DONATE_URL,
        specification_address: str = SPECIFICATION_URL,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._opener = opener
        self._donate_address = donate_address
        self._specification_address = specification_address

    @Slot()
    def openDonation(self) -> None:
        """Hand the donation page to whatever the desktop opens links with."""
        self._open(self._donate_address, DONATION_DESCRIPTION)

    @Slot()
    def openSpecification(self) -> None:
        """Hand the MMSP specification to the same place."""
        self._open(self._specification_address, SPECIFICATION_DESCRIPTION)

    def _open(self, address: str, description: str) -> None:
        # Silence would leave the user pressing a button that appears to do
        # nothing, so a refusal is reported rather than swallowed.
        if not self._opener(address):
            self.openFailed.emit(description)
