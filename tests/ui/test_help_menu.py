"""Help drops a menu holding the Guide and About; the Guide reads itself.

Driven through the real `main.qml` with delivered key presses, like the
window's focus ring, because every behaviour here is a `Keys` handler on
whichever item holds focus: a dropped wire compiles and leaves the user stuck.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from PySide6.QtCore import QObject, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from tests.ui.window_stub import StubController, feed_dto, load_main_window


@pytest.fixture
def window(qapp):
    controller = StubController([feed_dto(1, "Alpha", unread=3)])
    engine, component, win = load_main_window(controller)
    QTest.qWaitForWindowExposed(win)
    QGuiApplication.processEvents()

    yield win

    win.setProperty("visible", False)
    QGuiApplication.processEvents()
    del component
    del engine


def _named(win, name: str):
    found = win.findChild(QObject, name)
    assert found is not None, f"{name} was never created"
    return found


def _focused(win) -> str:
    item = win.activeFocusItem()
    while item is not None:
        if item.objectName():
            return item.objectName()
        item = item.parentItem()
    return "<nothing>"


def _key(win, key) -> None:
    QTest.keyClick(win, key)
    QGuiApplication.processEvents()


def _open_menu(win, key=Qt.Key_Return) -> None:
    # Found as a QQuickItem: a plain QObject wrapper offers only QML's
    # argument-free forceActiveFocus, so the focus reason would be refused.
    button = win.findChild(QQuickItem, "helpBtn")
    assert button is not None, "helpBtn was never created"
    button.forceActiveFocus(Qt.TabFocusReason)
    QGuiApplication.processEvents()
    _key(win, key)


def _is_open(win, name: str) -> bool:
    return _named(win, name).property("visible") is True


@pytest.mark.parametrize("key", [Qt.Key_Return, Qt.Key_Space, Qt.Key_Down])
def test_the_help_button_drops_the_menu_onto_its_first_entry(window, key) -> None:
    _open_menu(window, key)

    assert _is_open(window, "helpMenu")
    assert _focused(window) == "helpMenu_guide"


def test_up_and_down_walk_the_entries_and_wrap(window) -> None:
    _open_menu(window)

    _key(window, Qt.Key_Down)
    assert _focused(window) == "helpMenu_about"
    _key(window, Qt.Key_Down)
    assert _focused(window) == "helpMenu_guide"
    _key(window, Qt.Key_Up)
    assert _focused(window) == "helpMenu_about"


def test_escape_closes_the_menu_back_onto_the_button(window) -> None:
    _open_menu(window)

    _key(window, Qt.Key_Escape)

    assert not _is_open(window, "helpMenu")
    assert _focused(window) == "helpBtn"


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        (Qt.Key_Tab, "checkAll"),
        (Qt.Key_Right, "checkAll"),
        (Qt.Key_Backtab, "themeToggleBtn"),
        (Qt.Key_Left, "themeToggleBtn"),
    ],
)
def test_the_ring_steps_out_of_the_open_menu(window, key, expected) -> None:
    _open_menu(window)

    _key(window, key)

    assert not _is_open(window, "helpMenu")
    assert _focused(window) == expected


def test_choosing_the_guide_opens_it_on_close(window) -> None:
    _open_menu(window)

    _key(window, Qt.Key_Return)

    assert not _is_open(window, "helpMenu")
    assert _is_open(window, "guideDialog")
    assert _focused(window) == "guideCloseBtn"


def test_choosing_about_opens_about(window) -> None:
    _open_menu(window)
    _key(window, Qt.Key_Down)

    _key(window, Qt.Key_Space)

    assert _is_open(window, "aboutDialog")
    assert not _is_open(window, "guideDialog")


def test_closing_the_guide_returns_focus_to_help(window) -> None:
    _open_menu(window)
    _key(window, Qt.Key_Return)

    _key(window, Qt.Key_Escape)

    assert not _is_open(window, "guideDialog")
    assert _focused(window) == "helpBtn"


def test_every_picture_in_the_guide_is_a_real_file(window) -> None:
    html = _named(window, "guideDialog").property("guideHtml")
    sources = re.findall(r'<img src="([^"]+)"', html)

    assert sources, "the guide shows no marks at all"
    missing = [s for s in sources if not Path(QUrl(s).toLocalFile()).is_file()]
    assert missing == []


def test_the_guide_shows_the_palette_the_toggle_offers(window) -> None:
    """The toggle's mark flips with the palette, so the guide's must too."""
    html = _named(window, "guideDialog").property("guideHtml")
    header_toggle = _named(window, "themeToggleBtn").property("iconSource")

    assert QUrl(header_toggle).fileName() in html
