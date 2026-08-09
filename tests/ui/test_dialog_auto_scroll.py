"""The dialogs that wear the self-reading surface: proof that they do.

A component that behaves perfectly and is wired to nothing passes every test in
`test_auto_scroller.py`, so these open the real dialogs, find the scroller by
name and let it read.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QTest

from tests.ui.window_stub import QML_DIR, THEME

_TICK_MS = 40
_START_HOLD_TICKS = 5000 // _TICK_MS
_TICKS_PER_STEP = 2

_LICENCE = "\n".join(
    f"Clause {n}: every licence overflows its dialog." for n in range(200)
)

_URLS = [f"https://example.com/feed/{n}" for n in range(60)]

_LICENCE_SITE = """
import QtQuick

LicenceDialog {
    theme: appTheme
    licenceTitle: "UI licence"
    licenceBody: licenceText
}
"""

# UrlListDialog reads `theme` from the scope that creates it rather than
# declaring a property, so the palette arrives as a context property here.
_URL_LIST_SITE = """
import QtQuick

UrlListDialog {
    heading: "Subscribe to these feeds?"
    urls: feedUrls
}
"""


def _open(qml: str, extra: dict):  # noqa: ANN001, ANN202
    engine = QQmlEngine()
    engine.rootContext().setContextProperty("appTheme", THEME)
    engine.rootContext().setContextProperty("theme", THEME)
    for name, value in extra.items():
        engine.rootContext().setContextProperty(name, value)

    component = QQmlComponent(engine)
    component.setData(
        qml.encode("utf-8"), QUrl.fromLocalFile(str(QML_DIR / "use_site.qml"))
    )
    assert component.status() != QQmlComponent.Status.Error, component.errorString()
    dialog = component.create()
    assert dialog is not None, component.errorString()

    win = QQuickWindow()
    win.resize(700, 700)
    dialog.setProperty("parent", win.contentItem())
    dialog.setProperty("visible", True)
    win.show()
    QTest.qWaitForWindowExposed(win)
    QGuiApplication.processEvents()
    return engine, component, dialog, win


def _scroller(dialog, name: str):  # noqa: ANN001, ANN202
    found = dialog.findChild(QObject, name)
    assert found is not None, f"{name} was never created"
    ticker = found.findChild(QObject, "autoScrollTicker")
    assert ticker is not None, "the ticker was never created"
    # Asserted before it is stopped: every test below drives the machine by
    # hand, so nothing else here would notice a timer that never ran.
    assert ticker.property("running") is True, "the cycle would never start"
    ticker.setProperty("running", False)
    return found


def _tick(scroller, times: int = 1) -> None:  # noqa: ANN001
    for _ in range(times):
        scroller.metaObject().invokeMethod(scroller, "tick")


@pytest.fixture
def licence(qapp):  # noqa: ANN001, ANN201
    engine, component, dialog, win = _open(_LICENCE_SITE, {"licenceText": _LICENCE})
    # The scrolling surface is the ScrollView's own Flickable contentItem.
    view = dialog.findChild(QQuickItem, "licenceScroll")
    assert view is not None, "the licence scroll view was never created"
    yield dialog, _scroller(dialog, "licenceScroller"), view.property("contentItem")
    win.close()
    del component
    del engine


@pytest.fixture
def url_list(qapp):  # noqa: ANN001, ANN201
    engine, component, dialog, win = _open(_URL_LIST_SITE, {"feedUrls": _URLS})
    surface = dialog.findChild(QQuickItem, "urlList")
    assert surface is not None, "the url list was never created"
    yield dialog, _scroller(dialog, "urlListScroller"), surface
    win.close()
    del component
    del engine


def test_the_licence_dialog_holds_the_full_opening_hold(
    licence,
) -> None:  # noqa: ANN001
    """The dialog focuses its text on open, which is not a reader taking hold."""
    _, scroller, surface = licence

    assert scroller.property("active") is True
    assert scroller.property("phase") == "pauseTop"

    _tick(scroller, _START_HOLD_TICKS - 1)
    assert scroller.property("phase") == "pauseTop", "the opening hold was cut short"
    assert surface.property("contentY") == 0


def test_the_licence_dialog_then_reads_itself(licence) -> None:  # noqa: ANN001
    _, scroller, surface = licence

    _tick(scroller, _START_HOLD_TICKS + 20 * _TICKS_PER_STEP)

    assert surface.property("contentY") == 20


def test_closing_the_licence_dialog_freezes_it(licence) -> None:  # noqa: ANN001
    """Frozen rather than stopped, so nothing is spent while it is closed.

    The snapshot is taken after the close rather than before it, because a
    popup stays `visible` through its exit transition and returns its view to
    the top on the way out, which the surface sees while it is still active.
    Reopening restarts the cycle regardless, so what matters here is the rule
    itself: once frozen, ticking spends nothing.
    """
    dialog, scroller, _ = licence
    _tick(scroller, _START_HOLD_TICKS + 10 * _TICKS_PER_STEP)

    dialog.setProperty("visible", False)
    QGuiApplication.processEvents()
    assert scroller.property("active") is False
    phase = scroller.property("phase")
    wait = scroller.property("wait")

    _tick(scroller, 200)

    assert scroller.property("phase") == phase
    assert scroller.property("wait") == wait


def test_the_url_list_reads_itself_when_it_overflows(url_list) -> None:  # noqa: ANN001
    """Sixty URLs is more than the dialog shows, so the list takes itself down."""
    _, scroller, surface = url_list
    assert scroller.property("active") is True

    _tick(scroller, _START_HOLD_TICKS + 20 * _TICKS_PER_STEP)

    assert surface.property("contentY") == 20
