"""Every QML file compiles.

The QML carries the application's user-facing behaviour and is measured by
nothing: the coverage gate reads Python only, and `qmllint` reports 198
unqualified-access warnings on one file alone because the whole front end is
driven by context properties, so it cannot be turned into a gate without
annotating the lot.

Compiling is the check that can be made to hold. It catches what a careless
edit actually breaks: a syntax error, a property assigned on a type that has
no such property, an unresolvable component. That is precisely the class of
mistake extracting components out of the four oversized files can introduce,
and none of it is visible until the application is launched otherwise.

It stops short of instantiating anything. Bindings against context properties
resolve at run time, and the context belongs to `main.py`, so building the
object graph here would test the fixture rather than the QML.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

_QML_DIR = Path(__file__).resolve().parents[2] / "meridian" / "ui" / "qml"


def _qml_files() -> list[Path]:
    return sorted(_QML_DIR.glob("*.qml"))


def test_there_are_qml_files_to_check() -> None:
    """A rename must not turn the check below into a vacuous pass."""
    assert _qml_files(), f"no QML found under {_QML_DIR}"


@pytest.mark.parametrize("path", _qml_files(), ids=lambda p: p.name)
def test_qml_compiles(qapp, path: Path) -> None:  # noqa: ANN001
    engine = QQmlEngine()
    try:
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(path)))
        assert (
            component.status() != QQmlComponent.Status.Error
        ), f"{path.name} does not compile:\n{component.errorString()}"
    finally:
        engine.deleteLater()
