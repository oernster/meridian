"""`UrlListDialog` actually places what it is given.

Compiling proves the file parses. It does not prove the interesting part: the
component takes its buttons as default children and reparents them into the
footer row through a `default property alias`. If that alias were wrong the
buttons would land somewhere invisible, the dialog would still compile and
nothing would say so until someone opened it and found no way out.

The check has to follow the *visual* parent rather than the QObject parent.
Assigning into `Row.data` sets `parentItem`, while QObject ownership stays
with the scope the children were declared in, so `findChild` from the footer
finds nothing even when the layout is correct. Importing `QQuickItem` is what
registers the converter that makes `parentItem` readable from Python at all.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem  # noqa: F401  registers the QQuickItem converter

_QML_DIR = Path(__file__).resolve().parents[2] / "meridian" / "ui" / "qml"

# Every colour role UrlListDialog and its delegate read.
_THEME = {
    "base": "#1e1e2e",
    "mantle": "#181825",
    "surface0": "#313244",
    "text": "#cdd6f4",
    "subtext": "#a6adc8",
}

_USE_SITE = """
import QtQuick
import QtQuick.Controls

UrlListDialog {
    heading: "two feeds"
    urls: ["https://a.example.com/feed", "https://b.example.com/feed"]

    Item { objectName: "firstButton" }
    Item { objectName: "secondButton" }
}
"""


@pytest.fixture
def dialog(qapp):  # noqa: ANN001, ANN201
    engine = QQmlEngine()
    engine.rootContext().setContextProperty("theme", _THEME)
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


def _named(root, name: str):  # noqa: ANN001, ANN202
    found = root.findChild(object, name)
    assert found is not None, f"{name} was never created"
    return found


def test_default_children_are_reparented_into_one_row(dialog) -> None:  # noqa: ANN001
    """The alias is the whole point of the component's shape."""
    first = _named(dialog, "firstButton")
    second = _named(dialog, "secondButton")

    row = first.parentItem()
    assert row is not None, "the buttons were not reparented anywhere"
    assert row is second.parentItem(), "the buttons were split across parents"
    assert row.metaObject().className() == "QQuickRow", (
        f"the buttons landed in a {row.metaObject().className()} rather than the "
        "footer's row"
    )


def test_that_row_is_the_dialog_footer(dialog) -> None:  # noqa: ANN001
    """Buttons in the body rather than the footer would scroll out of reach."""
    row = _named(dialog, "firstButton").parentItem()
    footer = dialog.property("footer")

    assert footer is not None, "the dialog has no footer"
    assert row.parentItem() is footer, (
        "the button row is not inside the footer, so the buttons would not sit "
        "on the dialog's action bar"
    )


def test_the_list_is_driven_by_the_urls_property(dialog) -> None:  # noqa: ANN001
    """Asserted on the view, not the property: the binding is what can break."""
    assert dialog.property("urls").toVariant() == [
        "https://a.example.com/feed",
        "https://b.example.com/feed",
    ]
    assert _named(dialog, "urlList").property("count") == 2


def test_the_heading_reaches_the_label(dialog) -> None:  # noqa: ANN001
    assert _named(dialog, "headingLabel").property("text") == "two feeds"
