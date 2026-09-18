"""The Guide names every button on both bands, by the mark the button draws.

Every control on the header and the foot is a picture with no word beside it,
so the Guide is the one place a picture is put next to its name. A button
added to either band with no line in the Guide leaves a picture nobody can
look up; a Guide line naming a mark that no longer exists shows an empty box.
Both are silent at run time, so both are checked here, against the same
reading of the two bands the tray-art test makes.
"""

from __future__ import annotations

import re
from pathlib import Path

from tests.structural.test_tray_art import _QML_DIR, _sourced_marks

_GUIDE_QML = _QML_DIR / "GuideDialog.qml"
_ART_DIR = _QML_DIR / "art"


def _guide_marks() -> set[str]:
    """Every mark file the Guide asks for, by name without the extension."""
    text = _GUIDE_QML.read_text(encoding="utf-8")
    return set(re.findall(r'"([a-z-]+)\.png"', text))


def test_every_band_mark_has_a_line_in_the_guide() -> None:
    missing = set(_sourced_marks()) - _guide_marks()

    assert missing == set()


def test_every_guide_mark_is_a_render_in_the_tree() -> None:
    absent = [m for m in _guide_marks() if not Path(_ART_DIR / f"{m}.png").is_file()]

    assert absent == []
