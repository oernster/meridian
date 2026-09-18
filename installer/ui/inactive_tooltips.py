"""Tooltips that show while another program has focus.

Qt Widgets shows a tooltip only over the active window unless that window
carries `WA_AlwaysShowToolTips`; measured on the real Windows platform with
the cursor moved over an inactive window, the tip stayed hidden without the
attribute and appeared with it. The attribute belongs to each top-level
window, dialogs and message boxes included, so an application-wide filter
sets it on every window as it is shown rather than each window opting in.
Installed once, at the setup program's composition root.

The application itself does not need it. Its window is QML, whose declared
ToolTip opens on the MouseArea's hover rather than through QToolTip; measured
on the real Windows platform, the TrayButton pattern opened its tip over an
inactive window with no attribute set.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QWidget


class _TooltipsOnInactiveWindows(QObject):
    """Marks every top-level window as it is shown so its tooltips always show."""

    def eventFilter(self, watched, event) -> bool:
        if (
            event.type() == QEvent.Type.Show
            and isinstance(watched, QWidget)
            and watched.isWindow()
        ):
            watched.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips, True)
        return False


def install(app) -> None:
    """Show `app`'s tooltips over an inactive window too.

    The filter is parented to `app`, which keeps it alive for the
    application's lifetime.
    """
    app.installEventFilter(_TooltipsOnInactiveWindows(app))
