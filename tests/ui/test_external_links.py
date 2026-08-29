"""The buttons that open a browser: what they ask for; being refused.

Two halves. The controller is exercised against a hand-written opener, which
is the whole reason the opener is injected: it is the only way to prove the
exact address was asked for without a browser opening in the middle of a test
run. The tray is exercised in the real window, because a button that is never
reached, never enabled or silent about leaving the application is not a working
button whatever the controller does.

`open_externally` itself is covered against the real Qt call, with an address
the desktop refuses. Measured rather than assumed: an unknown scheme comes back
True on Windows because the shell accepts it, so it would prove nothing; an
empty address comes back False and opens nothing.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from meridian.ui.external_links import ExternalLinkController
from meridian.ui.links import open_externally
from meridian.version import DONATE_URL, SPECIFICATION_URL
from tests.ui.window_stub import (
    StubController,
    StubLinkController,
    feed_dto,
    load_main_window,
)


class RecordingOpener:
    """Stands where the desktop would; records what it was asked to open."""

    def __init__(self, accepts: bool = True) -> None:
        self.accepts = accepts
        self.addresses: list[str] = []

    def __call__(self, address: str) -> bool:
        self.addresses.append(address)
        return self.accepts


def test_the_controller_asks_the_desktop_for_the_donation_page() -> None:
    opener = RecordingOpener()
    ExternalLinkController(opener).openDonation()
    assert opener.addresses == [DONATE_URL]


def test_the_controller_asks_the_desktop_for_the_specification() -> None:
    opener = RecordingOpener()
    ExternalLinkController(opener).openSpecification()
    assert opener.addresses == [SPECIFICATION_URL]


def test_a_desktop_that_opens_the_page_reports_nothing() -> None:
    controller = ExternalLinkController(RecordingOpener(accepts=True))
    failures = []
    controller.openFailed.connect(failures.append)

    controller.openDonation()
    controller.openSpecification()

    assert failures == []


@pytest.mark.parametrize(
    ("press", "described"),
    [
        ("openDonation", "the donation page"),
        ("openSpecification", "the MMSP specification"),
    ],
)
def test_a_desktop_that_refuses_says_which_page(press: str, described: str) -> None:
    """Silence leaves the user pressing a button that does nothing; a message
    naming no page is no use to someone who pressed one of two buttons."""
    controller = ExternalLinkController(RecordingOpener(accepts=False))
    failures = []
    controller.openFailed.connect(failures.append)

    getattr(controller, press)()

    assert failures == [described]


def test_the_opener_reports_an_address_the_desktop_will_not_take(
    qapp,
) -> None:  # noqa: ANN001, E501
    """The seam itself, against the real Qt call rather than a stand-in."""
    assert open_externally("") is False


@pytest.fixture
def window(qapp):  # noqa: ANN001, ANN201
    def _build(refuse: bool = False):  # noqa: ANN202
        links = StubLinkController(refuse=refuse)
        engine, component, win = load_main_window(
            StubController([feed_dto(1, "Alpha", unread=3)]),
            link_controller=links,
        )
        QTest.qWaitForWindowExposed(win)
        QGuiApplication.processEvents()
        _build.built.append((engine, component, win))
        return win, links

    _build.built = []
    yield _build

    for engine, component, win in _build.built:
        win.setProperty("visible", False)
        QGuiApplication.processEvents()
        del component
        del engine


def _named(win, name: str) -> QQuickItem:  # noqa: ANN001
    found = win.findChild(QQuickItem, name)
    assert found is not None, f"{name} was never created"
    return found


def test_the_foot_holds_donate_then_the_two_licences(window) -> None:  # noqa: ANN001
    """Donate is leftmost: it is the only one that opens a browser."""
    win, _ = window()
    tray = _named(win, "bottomTray")
    order = ["donateBtn", "uiLicenceBtn", "modelLicenceBtn"]
    lefts = [
        _named(win, name)
        .mapToItem(tray, _named(win, name).boundingRect().topLeft())
        .x()
        for name in order
    ]

    assert lefts == sorted(
        lefts
    ), f"the foot is out of order: {list(zip(order, lefts))}"
    assert lefts[0] < tray.width() / 2, "the row is not held at the left"


def test_the_licences_left_the_header(window) -> None:  # noqa: ANN001
    """They state what is true of the application, not of what is being read."""
    win, _ = window()
    header = _named(win, "header")

    for name in ("uiLicenceBtn", "modelLicenceBtn"):
        item = _named(win, name).parentItem()
        ancestors = []
        while item is not None:
            ancestors.append(item)
            item = item.parentItem()
        assert header not in ancestors, f"{name} is still on the header"


def test_the_button_says_that_pressing_it_leaves_the_application(
    window,
) -> None:  # noqa: ANN001, E501
    """A beer and a coffee do not tell anybody a browser is about to open."""
    win, _ = window()
    tooltip = _named(win, "donateBtn").property("tooltip")

    assert "browser" in tooltip.lower()


def test_the_foot_closes_the_ring(window) -> None:  # noqa: ANN001
    """Tab walks the three, then returns to the head of the header."""
    win, _ = window()
    button = _named(win, "donateBtn")

    button.forceActiveFocus(Qt.TabFocusReason)
    QGuiApplication.processEvents()
    assert win.activeFocusItem() is button

    walked = []
    for _ in range(3):
        QTest.keyClick(win, Qt.Key_Tab)
        QGuiApplication.processEvents()
        walked.append(win.activeFocusItem().objectName())

    assert walked == ["uiLicenceBtn", "modelLicenceBtn", "importBtn"]


@pytest.mark.parametrize(
    ("name", "asked"),
    [("donateBtn", "openDonation"), ("specBtn", "openSpecification")],
)
def test_pressing_a_link_button_asks_the_controller(
    window, name, asked
) -> None:  # noqa: ANN001, E501
    win, links = window()
    button = _named(win, name)

    button.forceActiveFocus(Qt.TabFocusReason)
    QTest.keyClick(win, Qt.Key_Return)
    QGuiApplication.processEvents()

    assert links.called(asked) == [(asked,)]


def test_a_refusal_reaches_the_user(window) -> None:  # noqa: ANN001
    """The window has no status bar, so the refusal opens the error dialog."""
    win, _ = window(refuse=True)
    button = _named(win, "donateBtn")

    button.forceActiveFocus(Qt.TabFocusReason)
    QTest.keyClick(win, Qt.Key_Return)
    QGuiApplication.processEvents()

    dialog = win.findChild(QObject, "errorDialog")
    assert dialog is not None
    assert dialog.property("visible") is True
    message = dialog.property("message")
    assert "browser" in message.lower()
    assert "donation page" in message, f"the message names no page: {message}"
