"""`CandidateRow` gets its content from the model and nothing from its caller.

The row used to be an inline `Component` inside `FeedDiscovery.qml`, reading
`model.*` for its content and reaching out to `root` and `controller` for its
selected state and its actions. Now it declares six `required` properties and
emits two signals instead, which moves two failure modes out of reach of the
compile check:

* The six names have to match `FeedCandidateModel`'s role names exactly. If one
  drifts, the view cannot satisfy the requirement and the delegate never
  instantiates. The rename compiles perfectly and produces an empty results
  list.
* Any surviving reference to the old outer scope also compiles. It resolves
  through the creating context whenever the row happens to sit inside
  `FeedDiscovery.qml`, so it stays invisible until the row is used anywhere
  else. The engine reports it as a warning rather than an error, so the
  warnings are collected and asserted on.

The row is therefore exercised as a real delegate of a real `ListView` over a
real `FeedCandidateModel`, which is the only arrangement that binds required
properties at all.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem  # noqa: F401  registers the QQuickItem converter

from meridian.application.dto.feed_candidate_dto import FeedCandidateDTO
from meridian.ui.models import FeedCandidateModel

_QML_DIR = Path(__file__).resolve().parents[2] / "meridian" / "ui" / "qml"

# Every colour role CandidateRow reads.
_THEME = {
    "base": "#1e1e2e",
    "mantle": "#181825",
    "surface0": "#313244",
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
        is_subscribed=False,
    ),
    FeedCandidateDTO(
        url="https://b.example.com/feed",
        title="Beta Feed",
        description="Second",
        favicon_url="",
        source_type="atom",
        is_subscribed=True,
    ),
]

# No `root` and no `controller` anywhere: the row has to stand on its own.
_USE_SITE = """
import QtQuick
import QtQuick.Controls

ListView {
    width: 400
    height: 300
    model: candidateModel
    currentIndex: 0

    property int toggles: 0
    property int subscribes: 0

    delegate: CandidateRow {
        width: 400
        theme: appTheme
        selected: false
        onToggleRequested: ListView.view.toggles++
        onSubscribeRequested: ListView.view.subscribes++
    }
}
"""


@pytest.fixture
def results(qapp):  # noqa: ANN001, ANN201
    model = FeedCandidateModel()
    model.refresh(_CANDIDATES)

    engine = QQmlEngine()
    engine.rootContext().setContextProperty("appTheme", _THEME)
    engine.rootContext().setContextProperty("candidateModel", model)

    warnings: list[str] = []
    engine.warnings.connect(lambda errs: warnings.extend(e.toString() for e in errs))

    component = QQmlComponent(engine)
    component.setData(
        _USE_SITE.encode("utf-8"),
        QUrl.fromLocalFile(str(_QML_DIR / "use_site.qml")),
    )
    assert component.status() != QQmlComponent.Status.Error, component.errorString()
    view = component.create()
    assert view is not None, component.errorString()

    yield view, warnings

    view.deleteLater()
    engine.deleteLater()


def _row(view, index: int):  # noqa: ANN001, ANN202
    view.setProperty("currentIndex", index)
    current = view.property("currentItem")
    assert current is not None, f"no delegate was instantiated for row {index}"
    return current


def test_the_view_instantiates_a_row_per_candidate(results) -> None:  # noqa: ANN001
    """A required property the model cannot satisfy leaves the list empty."""
    view, _ = results
    assert view.property("count") == len(_CANDIDATES)
    assert _row(view, 0) is not None


def test_each_role_reaches_the_property_of_that_name(results) -> None:  # noqa: ANN001
    """The binding is by name, so a renamed role fails silently at runtime."""
    view, _ = results
    first = _row(view, 0)

    assert first.property("candidateUrl") == "https://a.example.com/feed"
    assert first.property("candidateTitle") == "Alpha Feed"
    assert first.property("candidateDescription") == "First"
    assert first.property("candidateFaviconUrl") == ""
    assert first.property("candidateSourceType") == "rss"
    assert first.property("candidateIsSubscribed") is False


def test_the_row_reads_nothing_from_its_caller(results) -> None:  # noqa: ANN001
    """Creating it outside FeedDiscovery.qml is what exposes an outer read."""
    _, warnings = results
    assert warnings == []


def test_the_painted_content_comes_from_the_model(results) -> None:  # noqa: ANN001
    """Asserted on the labels: a property that never reaches one shows nothing."""
    view, _ = results
    first = _row(view, 0)

    assert _named(first, "titleLabel").property("text") == "Alpha Feed"
    assert _named(first, "badgeLabel").property("text") == "RSS"


def test_a_subscribed_row_offers_no_second_subscribe(results) -> None:  # noqa: ANN001
    """The guard against re-subscribing sits on the row, not on the caller."""
    view, _ = results
    subscribed = _row(view, 1)

    assert subscribed.property("candidateIsSubscribed") is True
    assert _named(subscribed, "rowActionLabel").property("text") == "Subscribed"
    assert _named(subscribed, "rowActionMouse").property("enabled") is False


def test_an_unsubscribed_row_offers_the_action(results) -> None:  # noqa: ANN001
    view, _ = results
    first = _row(view, 0)

    assert _named(first, "rowActionLabel").property("text") == "Subscribe"
    assert _named(first, "rowActionMouse").property("enabled") is True


def _named(root, name: str):  # noqa: ANN001, ANN202
    found = root.findChild(object, name)
    assert found is not None, f"{name} was never created"
    return found
