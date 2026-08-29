"""Every button in either band is readable and its mark actually loaded.

The buttons carry no words. That makes two failures silent that were not
silent before. A mark whose source does not resolve draws nothing rather than
raising, leaving an empty box where a control was; a button with no tooltip
leaves the user a picture and no way to find out what it does. Neither shows up
in the QML compile check, which stops short of instantiating anything.

So this instantiates the real window and asks each button what it is carrying.
The mark is proved loaded through its implicit size, which stays zero until the
source resolves, rather than through a status enum Qt will not hand back across
the binding.

`_TRAY_BUTTONS` is the header AND the foot. It was the header alone once; moving
the two licences down while adding the specification button left three stops
that nothing here checked; a list that names a band rather than every
stop in it goes quietly out of date exactly when the bands are rearranged.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from tests.ui.window_stub import StubController, feed_dto, load_main_window

# Every stop in both bands, in the order the user walks them: the header from
# its first button to its last, then the foot.
_TRAY_BUTTONS = (
    "importBtn",
    "exportBtn",
    "discoverBtn",
    "manageBtn",
    "specBtn",
    "themeToggleBtn",
    "aboutBtn",
    "donateBtn",
    "uiLicenceBtn",
    "modelLicenceBtn",
)


@pytest.fixture
def window(qapp):  # noqa: ANN001, ANN201
    controller = StubController([feed_dto(1, "Alpha", unread=3)])
    engine, component, win = load_main_window(controller)
    QTest.qWaitForWindowExposed(win)
    QGuiApplication.processEvents()

    yield win

    win.setProperty("visible", False)
    QGuiApplication.processEvents()
    del component
    del engine


def _named(root, name: str) -> QQuickItem:  # noqa: ANN001
    for child in root.childItems():
        if child.objectName() == name:
            return child
        hit = _named(child, name)
        if hit is not None:
            return hit
    return None


def _button(win, name: str) -> QQuickItem:  # noqa: ANN001
    found = _named(win.contentItem(), name)
    assert found is not None, f"{name} was never created"
    return found


def _mark(button: QQuickItem) -> QQuickItem:
    for child in button.childItems():
        if child.metaObject().className().startswith("QQuickImage"):
            return child
    raise AssertionError(f"{button.objectName()} carries no Image")


@pytest.mark.parametrize("name", _TRAY_BUTTONS)
def test_every_tray_button_says_what_it_does(window, name: str) -> None:  # noqa: ANN001
    tooltip = _button(window, name).property("tooltip")
    assert tooltip, f"{name} carries a mark and no tooltip, so it cannot be read"


@pytest.mark.parametrize("name", _TRAY_BUTTONS)
def test_every_tray_mark_resolved(window, name: str) -> None:  # noqa: ANN001
    """An unresolvable source is not an error in QML; it just draws nothing."""
    mark = _mark(_button(window, name))
    assert mark.property("implicitWidth") > 0, (
        f"{name}'s mark did not load from {mark.property('source').toString()}.\n"
        "Run create_icons.py; check the name against build_resources.ART_NAMES."
    )
    assert mark.width() > 0 and mark.height() > 0


@pytest.mark.parametrize("name", _TRAY_BUTTONS)
def test_no_tray_button_carries_words(window, name: str) -> None:  # noqa: ANN001
    """Both bands are marks alone; a label would make a row uneven."""
    button = _button(window, name)
    labels = [
        child
        for child in button.findChildren(QObject)
        if child.metaObject().className().startswith("QQuickText")
        and child.property("text")
        and child.parent() is button
    ]
    assert not labels, f"{name} draws text beside its mark"


def test_the_toggle_offers_the_palette_it_would_switch_to(  # noqa: ANN001
    window,
) -> None:
    toggle = _button(window, "themeToggleBtn")
    assert toggle.property("tooltip") == "Switch to the light palette"

    toggle.forceActiveFocus(Qt.TabFocusReason)
    QTest.keyClick(window, Qt.Key_Return)
    QGuiApplication.processEvents()

    assert toggle.property("tooltip") == "Switch to the dark palette"
