"""The self-reading surface: its pace, its holds and how a reader takes over.

The cycle is driven here by calling `tick()` rather than by waiting on the
timer, because every phase is measured in whole ticks and a test that waits
five real seconds for the opening hold would be both slow and flaky. The
fixture stops the component's own timer first, so nothing else advances the
state machine while a test is reading it.

One tick is 40ms, so the numbers below are the canon in ticks: 125 for the
5000ms opening hold, one pixel every second tick down, 125 again at the
bottom, then 15 pixels a tick back up.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QObject, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QTest

from tests.ui.window_stub import QML_DIR, THEME

_TICKS_PER_STEP = 2
_START_HOLD_TICKS = 5000 // 40
_BOTTOM_HOLD_TICKS = 5000 // 40
# 2500 is not a whole number of ticks, so the manual hold runs out part way
# through the 63rd and the phase turns there.
_MANUAL_HOLD_TICKS = 2500 // 40 + 1
_REWIND_PX = 15

_USE_SITE = """
import QtQuick

Item {
    width: 300
    height: 200

    Flickable {
        id: surface
        objectName: "surface"
        anchors.fill: parent
        contentWidth: 300
        contentHeight: 1000

        Item {
            width: 300
            height: surface.contentHeight

            Item {
                id: focusTarget
                objectName: "focusTarget"
                width: 10
                height: 10
                activeFocusOnTab: true
            }
        }
    }

    AutoScroller {
        objectName: "scroller"
        flick: surface
        active: true
    }
}
"""


@pytest.fixture
def surface(qapp):  # noqa: ANN001, ANN201
    engine = QQmlEngine()
    engine.rootContext().setContextProperty("appTheme", THEME)

    component = QQmlComponent(engine)
    component.setData(
        _USE_SITE.encode("utf-8"),
        QUrl.fromLocalFile(str(QML_DIR / "use_site.qml")),
    )
    assert component.status() != QQmlComponent.Status.Error, component.errorString()
    item = component.create()
    assert item is not None, component.errorString()

    win = QQuickWindow()
    win.resize(300, 200)
    item.setParentItem(win.contentItem())
    win.show()
    QTest.qWaitForWindowExposed(win)
    QGuiApplication.processEvents()

    scroller = item.findChild(QObject, "scroller")
    assert scroller is not None, "the scroller was never created"
    # Nothing but the test advances the machine.
    ticker = scroller.findChild(QObject, "autoScrollTicker")
    assert ticker is not None, "the ticker was never created"
    ticker.setProperty("running", False)

    yield scroller, item.findChild(QQuickItem, "surface"), win

    win.close()
    del component
    del engine


def _tick(scroller, times: int = 1) -> None:  # noqa: ANN001
    for _ in range(times):
        scroller.metaObject().invokeMethod(scroller, "tick")


def _run_to_descent(scroller) -> None:  # noqa: ANN001
    """Spend the opening hold, leaving the machine about to descend."""
    _tick(scroller, _START_HOLD_TICKS)
    assert scroller.property("phase") == "down"


def _run_until(scroller, phase: str, limit: int = 4000) -> None:  # noqa: ANN001
    """Let it read its way there rather than placing it, which would suspend."""
    for _ in range(limit):
        if scroller.property("phase") == phase:
            return
        _tick(scroller)
    raise AssertionError(f"never reached {phase} in {limit} ticks")


def test_it_holds_still_before_the_first_descent(surface) -> None:  # noqa: ANN001
    """A reader orients before anything moves."""
    scroller, flick, _ = surface

    _tick(scroller, _START_HOLD_TICKS - 1)

    assert scroller.property("phase") == "pauseTop"
    assert flick.property("contentY") == 0


def test_the_descent_starts_once_the_hold_is_spent(surface) -> None:  # noqa: ANN001
    scroller, flick, _ = surface
    _run_to_descent(scroller)

    _tick(scroller, _TICKS_PER_STEP)

    assert flick.property("contentY") == 1


def test_it_descends_one_pixel_every_second_tick(surface) -> None:  # noqa: ANN001
    """The app-wide reading pace: halved, because the first cut read too fast."""
    scroller, flick, _ = surface
    _run_to_descent(scroller)

    _tick(scroller, 20 * _TICKS_PER_STEP)

    assert flick.property("contentY") == 20


def test_it_holds_at_the_bottom_before_rewinding(surface) -> None:  # noqa: ANN001
    """Long enough to finish the tail before the rewind takes it away."""
    scroller, flick, _ = surface
    _run_to_descent(scroller)
    maximum = flick.property("contentHeight") - flick.property("height")
    _run_until(scroller, "pauseBottom")
    assert flick.property("contentY") == maximum

    _tick(scroller, _BOTTOM_HOLD_TICKS - 1)
    assert flick.property("contentY") == maximum, "it rewound before the hold ended"

    _tick(scroller, 1)
    assert scroller.property("phase") == "up"


def test_the_rewind_is_a_reposition_not_a_reading_pass(surface) -> None:  # noqa: ANN001
    """Fifteen pixels a tick, against one every second tick going down."""
    scroller, flick, _ = surface
    _run_to_descent(scroller)
    maximum = flick.property("contentHeight") - flick.property("height")
    _run_until(scroller, "pauseBottom")
    _tick(scroller, _BOTTOM_HOLD_TICKS)
    assert scroller.property("phase") == "up"

    _tick(scroller, 1)

    assert flick.property("contentY") == maximum - _REWIND_PX


def test_reaching_the_top_holds_then_reads_again(surface) -> None:  # noqa: ANN001
    scroller, flick, _ = surface
    _run_to_descent(scroller)
    _run_until(scroller, "pauseBottom")
    _tick(scroller, _BOTTOM_HOLD_TICKS)

    _run_until(scroller, "pauseTop")
    assert flick.property("contentY") == 0

    _tick(scroller, 2000 // 40)
    assert scroller.property("phase") == "down"


def test_a_reader_moving_it_suspends_the_cycle(surface) -> None:  # noqa: ANN001
    """Any hand on the surface stops the descent without switching it off."""
    scroller, flick, _ = surface
    _run_to_descent(scroller)
    _tick(scroller, 10 * _TICKS_PER_STEP)

    flick.setProperty("contentY", 400)
    QGuiApplication.processEvents()

    assert scroller.property("phase") == "manual"
    _tick(scroller, _MANUAL_HOLD_TICKS - 1)
    assert flick.property("contentY") == 400, "it moved while the reader was reading"


def test_it_resumes_from_where_the_reader_left_it(surface) -> None:  # noqa: ANN001
    """Not from the top: the cycle picks up in place."""
    scroller, flick, _ = surface
    _run_to_descent(scroller)
    flick.setProperty("contentY", 400)
    QGuiApplication.processEvents()

    _tick(scroller, _MANUAL_HOLD_TICKS)
    assert scroller.property("phase") == "down"

    _tick(scroller, _TICKS_PER_STEP)
    assert flick.property("contentY") == 401


def test_it_rewinds_when_the_reader_left_it_at_the_bottom(
    surface,
) -> None:  # noqa: ANN001
    """Down is not available, so the only way on is back up."""
    scroller, flick, _ = surface
    _run_to_descent(scroller)
    maximum = flick.property("contentHeight") - flick.property("height")

    flick.setProperty("contentY", maximum)
    QGuiApplication.processEvents()
    assert scroller.property("phase") == "manual"

    _tick(scroller, _MANUAL_HOLD_TICKS)

    assert scroller.property("phase") == "up"


def test_focus_arriving_by_keyboard_suspends_it(surface) -> None:  # noqa: ANN001
    """A reader who tabs in is reading; the surface stops moving under them."""
    scroller, flick, _ = surface
    _run_to_descent(scroller)
    target = flick.findChild(QQuickItem, "focusTarget")
    assert target is not None, "the focus target was never created"

    target.forceActiveFocus(Qt.TabFocusReason)
    QGuiApplication.processEvents()

    assert scroller.property("phase") == "manual"


def test_it_is_frozen_rather_than_stopped_while_inactive(
    surface,
) -> None:  # noqa: ANN001
    """Phase, position and the rest of the hold all survive the freeze."""
    scroller, flick, _ = surface
    _run_to_descent(scroller)
    _tick(scroller, 6 * _TICKS_PER_STEP)
    scroller.setProperty("phase", "pauseBottom")
    scroller.setProperty("wait", 1000)
    was_at = flick.property("contentY")

    scroller.setProperty("active", False)
    _tick(scroller, 200)

    assert scroller.property("phase") == "pauseBottom"
    assert scroller.property("wait") == 1000
    assert flick.property("contentY") == was_at


def test_a_surface_that_fits_is_left_alone(surface) -> None:  # noqa: ANN001
    """Attaching it to content that does not overflow costs nothing."""
    scroller, flick, _ = surface
    flick.setProperty("contentHeight", flick.property("height"))
    QGuiApplication.processEvents()
    scroller.metaObject().invokeMethod(scroller, "restart")

    _tick(scroller, _START_HOLD_TICKS * 2)

    assert scroller.property("phase") == "pauseTop"
    assert scroller.property("wait") == 5000, "it spent a hold on content that fits"
    assert flick.property("contentY") == 0


def test_reopening_a_surface_holds_still_again(surface) -> None:  # noqa: ANN001
    scroller, flick, _ = surface
    _run_to_descent(scroller)
    _tick(scroller, 10 * _TICKS_PER_STEP)

    scroller.setProperty("active", False)
    scroller.setProperty("active", True)

    assert scroller.property("phase") == "pauseTop"
    assert scroller.property("wait") == 5000
