"""The discovery focus ring still closes now that it spans three files.

The ring is query field, result cap, Search button, results list, back to the
query field. It used to be wired by id inside one file. It now crosses two
component boundaries. Each crossing is a signal the composition happens to
connect: `DiscoverySearchBar.focusForwardRequested` reaches `DiscoveryResults`,
while `DiscoveryResults.focusForwardRequested` and `focusBackwardRequested` go
back the other way. A missed connection compiles, leaves every component
correct on its own and simply strands the user at whichever end the ring broke.

Real key events through a real window are the only thing that shows it: the
handlers are `Keys.onTabPressed` on whichever item holds focus, so nothing
short of a delivered key exercises the path.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Property, QObject, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QTest

from meridian.application.dto.feed_candidate_dto import FeedCandidateDTO
from meridian.ui.models import FeedCandidateModel

_QML_DIR = Path(__file__).resolve().parents[2] / "meridian" / "ui" / "qml"

_THEME = {
    "base": "#1e1e2e",
    "mantle": "#181825",
    "surface0": "#313244",
    "surface1": "#45475a",
    "text": "#cdd6f4",
    "subtext": "#a6adc8",
    "overlay": "#6c7086",
    "blue": "#89b4fa",
    "green": "#a6e3a1",
    "amber": "#f9e2af",
    "isDark": True,
}

_CANDIDATES = [
    FeedCandidateDTO(
        url="https://a.example.com/feed",
        title="Alpha Feed",
        description="First",
        favicon_url="",
        source_type="rss",
    ),
]

_USE_SITE = """
import QtQuick

FeedDiscovery {
    width: 700
    height: 600
    theme: appTheme
}
"""


class _StubController(QObject):
    """Only the surface FeedDiscovery reaches for."""

    searchStarted = Signal()
    searchFinished = Signal()
    searchError = Signal(str)
    searchCancelled = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._model = FeedCandidateModel()
        self._model.refresh(_CANDIDATES)
        self.searched: list[str] = []
        self.caps: list[int] = []
        self.cancelled = 0

    @Property(QObject, constant=True)
    def candidateModel(self) -> QObject:
        return self._model

    @Slot(str)
    def subscribeFromDiscovery(self, url: str) -> None:
        pass

    @Slot(list)
    def bulkSubscribeFromDiscovery(self, urls: list) -> None:
        pass

    @Slot(str)
    def searchFeeds(self, query: str) -> None:
        self.searched.append(query)

    @Slot()
    def cancelSearch(self) -> None:
        self.cancelled += 1

    @Slot(int)
    def setResultCap(self, cap: int) -> None:
        self.caps.append(cap)


@pytest.fixture
def panel(qapp):  # noqa: ANN001, ANN201
    controller = _StubController()

    engine = QQmlEngine()
    engine.rootContext().setContextProperty("controller", controller)
    engine.rootContext().setContextProperty("appTheme", _THEME)

    component = QQmlComponent(engine)
    component.setData(
        _USE_SITE.encode("utf-8"),
        QUrl.fromLocalFile(str(_QML_DIR / "use_site.qml")),
    )
    assert component.status() != QQmlComponent.Status.Error, component.errorString()
    discovery = component.create()
    assert discovery is not None, component.errorString()

    window = QQuickWindow()
    window.resize(700, 600)
    discovery.setParentItem(window.contentItem())
    window.show()
    QTest.qWaitForWindowExposed(window)

    # The list only exists in the results state, which the controller would
    # normally set through onSearchFinished.
    discovery.setProperty("_searchState", "results")
    QGuiApplication.processEvents()

    yield discovery, window, controller

    window.close()
    discovery.deleteLater()
    engine.deleteLater()


def _named(root, name: str):  # noqa: ANN001, ANN202
    found = root.findChild(QQuickItem, name)
    assert found is not None, f"{name} was never created"
    return found


def _focused(window) -> str:  # noqa: ANN001
    """The nearest named ancestor of whatever holds focus.

    A focused ListView passes active focus down to its current delegate, so
    the deepest focus item is a CandidateRow rather than the list. Naming the
    stop the ring actually landed on is what the assertions are about.
    """
    item = window.activeFocusItem()
    if item is None:
        return "<nothing>"
    while item is not None:
        if item.objectName():
            return item.objectName()
        item = item.parentItem()
    return window.activeFocusItem().metaObject().className()


def _tab(window, back: bool = False) -> None:  # noqa: ANN001
    QTest.keyClick(window, Qt.Key_Backtab if back else Qt.Key_Tab)
    QGuiApplication.processEvents()


def test_tab_walks_the_ring_and_wraps(panel) -> None:  # noqa: ANN001
    """Each step here is a signal crossing a file boundary."""
    discovery, window, _ = panel
    field = _named(discovery, "queryInput")
    field.setProperty("text", "python")

    discovery.metaObject().invokeMethod(discovery, "focusSearch")
    QGuiApplication.processEvents()
    assert _focused(window) == "queryInput"

    _tab(window)
    assert _focused(window) == "capCombo"

    _tab(window)
    assert _focused(window) == "searchBtn"

    _tab(window)
    assert _focused(window) == "resultsList"

    _tab(window)
    assert _focused(window) == "queryInput", "the ring did not wrap"


def test_shift_tab_walks_the_ring_backwards(panel) -> None:  # noqa: ANN001
    discovery, window, _ = panel
    field = _named(discovery, "queryInput")
    field.setProperty("text", "python")

    _named(discovery, "resultsList").forceActiveFocus(Qt.TabFocusReason)
    QGuiApplication.processEvents()
    assert _focused(window) == "resultsList"

    _tab(window, back=True)
    assert _focused(window) == "searchBtn"

    _tab(window, back=True)
    assert _focused(window) == "capCombo"


def test_an_empty_query_skips_the_search_button(panel) -> None:  # noqa: ANN001
    """It is not a tab stop with nothing to search for, so Tab skips it."""
    discovery, window, _ = panel

    discovery.metaObject().invokeMethod(discovery, "focusSearch")
    QGuiApplication.processEvents()
    assert _focused(window) == "queryInput"

    _tab(window)
    assert _focused(window) == "capCombo"

    _tab(window)
    assert _focused(window) == "resultsList", "the disabled button stalled the ring"


def test_the_search_bar_reaches_the_controller(panel) -> None:  # noqa: ANN001
    """The bar emits; the composition is what calls the controller."""
    discovery, window, controller = panel
    field = _named(discovery, "queryInput")
    field.setProperty("text", "  python  ")

    _named(_named(discovery, "searchBar"), "searchBtn").forceActiveFocus()
    QTest.keyClick(window, Qt.Key_Return)
    QGuiApplication.processEvents()

    assert controller.searched == ["python"], "the query never reached searchFeeds"


def test_the_cap_selector_reaches_the_controller(panel) -> None:  # noqa: ANN001
    """The default cap is applied on load, as it was before the split."""
    _, _, controller = panel
    assert controller.caps == [25]
