"""Reporting an operation's progress to whatever is watching it.

One definition, shared by every operation, because the two payload shapes are
not interchangeable to the window at the other end. A payload carrying `pct`
moves the progress bar; a bare string only writes the status line. An operation
that reports its work in text alone therefore runs to completion behind a bar
that never fills, which is exactly what a repair used to look like.
"""

from __future__ import annotations

from collections.abc import Callable

ProgressCb = Callable[[object], None]


def report(progress: ProgressCb | None, *, message: str, pct: int | None) -> None:
    """Hand one update to the callback, if there is one to hand it to.

    `pct` of None sends the message alone. Prefer a percentage wherever the
    operation can honestly work one out: see the note in the module docstring
    for what a text-only operation looks like to the person watching it.
    """
    if not progress:
        return
    if pct is None:
        progress(message)
        return
    progress({"pct": int(pct), "message": message})


def step_pct(index: int, total: int, *, first: int, last: int) -> int:
    """Return the percentage for step `index` of `total` within a band.

    The band exists because a stepped stage is rarely the whole operation:
    something precedes it and something follows, so the stage is given the
    range between `first` and `last` rather than the whole bar. The last step
    lands exactly on `last`, which is what makes the bar arrive where the next
    stage expects to start.
    """
    if total <= 0:
        return last
    return first + round((last - first) * (index + 1) / total)
