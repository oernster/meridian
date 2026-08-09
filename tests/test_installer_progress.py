"""The shared progress reporter and its step arithmetic.

These exist because the two payload shapes are not equivalent at the far end.
A bare string writes the status line and leaves the progress bar untouched, so
an operation reporting only text runs behind a bar that never fills. Repair and
uninstall both did, which is the defect this module was extracted to prevent
recurring.
"""

from __future__ import annotations

import pytest

from installer.ops.progress import report, step_pct


def test_reporting_without_a_callback_is_silent() -> None:
    report(None, pct=10, message="ignored")


def test_a_percentage_is_sent_as_a_payload_the_bar_can_read() -> None:
    seen: list[object] = []

    report(seen.append, pct=42, message="Extracting")

    assert seen == [{"pct": 42, "message": "Extracting"}]


def test_no_percentage_sends_the_message_alone() -> None:
    seen: list[object] = []

    report(seen.append, pct=None, message="Working")

    assert seen == ["Working"]


@pytest.mark.parametrize(
    ("index", "total", "expected"),
    [
        (0, 1, 85),
        (0, 4, 25),
        (1, 4, 45),
        (2, 4, 65),
        (3, 4, 85),
    ],
)
def test_a_step_lands_inside_its_band(index: int, total: int, expected: int) -> None:
    assert step_pct(index, total, first=5, last=85) == expected


def test_the_last_step_lands_exactly_on_the_end_of_the_band() -> None:
    """The next stage starts where this one stopped, so the join has to be exact."""
    for total in range(1, 40):
        assert step_pct(total - 1, total, first=5, last=85) == 85


def test_no_steps_at_all_reports_the_band_complete() -> None:
    """An empty manifest is a finished sweep, never a sweep stuck at the start."""
    assert step_pct(0, 0, first=5, last=85) == 85
