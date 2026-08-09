"""The autocomplete debounce still gates on query length after the move.

The field, its debounce timer and the suggestion fetch were three separate
top-level pieces of `FeedDiscovery.qml`, wired together by id. They moved into
`DiscoveryQueryField.qml` as one unit. The rule that holds them together is
the minimum query length: below it no request is made, at or above it a request
is scheduled rather than sent per keystroke.

The fetch itself reaches the network, so it is not exercised here. What is
checked is the gate in front of it, which is the part that decides whether a
request happens at all.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem  # noqa: F401  registers the QQuickItem converter

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
}

_USE_SITE = """
import QtQuick

DiscoveryQueryField {
    width: 300
    theme: appTheme
    searchState: "idle"
}
"""


@pytest.fixture
def field(qapp):  # noqa: ANN001, ANN201
    engine = QQmlEngine()
    engine.rootContext().setContextProperty("appTheme", _THEME)
    component = QQmlComponent(engine)
    component.setData(
        _USE_SITE.encode("utf-8"),
        QUrl.fromLocalFile(str(_QML_DIR / "use_site.qml")),
    )
    assert component.status() != QQmlComponent.Status.Error, component.errorString()
    created = component.create()
    assert created is not None, component.errorString()
    yield created
    created.deleteLater()
    engine.deleteLater()


def _child(root, name: str):  # noqa: ANN001, ANN202
    found = root.findChild(QObject, name)
    assert found is not None, f"{name} was never created"
    return found


def test_a_query_below_the_minimum_schedules_nothing(field) -> None:  # noqa: ANN001
    """One character is not worth a request, so the timer never starts."""
    _child(field, "queryInput").setProperty("text", "p")

    assert _child(field, "suggestionDebounce").property("running") is False


def test_a_long_enough_query_schedules_a_fetch(field) -> None:  # noqa: ANN001
    _child(field, "queryInput").setProperty("text", "py")

    assert _child(field, "suggestionDebounce").property("running") is True


def test_falling_back_under_the_minimum_cancels_it(field) -> None:  # noqa: ANN001
    """Deleting back to one character stops the request and drops the list.

    The suggestions are seeded here rather than fetched: they normally arrive
    from the network, so an assertion that they are empty is worth nothing
    unless they were non-empty first.
    """
    input_ = _child(field, "queryInput")
    input_.setProperty("text", "py")
    assert _child(field, "suggestionDebounce").property("running") is True
    field.setProperty("_suggestions", ["python", "pytorch"])

    input_.setProperty("text", "p")

    assert _child(field, "suggestionDebounce").property("running") is False
    assert field.property("_suggestions").toVariant() == []


def test_the_field_text_is_readable_from_the_root(field) -> None:  # noqa: ANN001
    """The search bar reads it to decide whether Search is a tab stop."""
    _child(field, "queryInput").setProperty("text", "python")

    assert field.property("text") == "python"
