"""GNU LGPL v3 license text for display in the installer UI."""

from __future__ import annotations

import sys
from pathlib import Path


def _read_lgpl3_text() -> str:
    """Load LGPL v3 text from repo-root `LICENSE`."""

    # Each probe below is guarded on its own so that a source which does not
    # apply removes one candidate rather than all of them. The installer runs
    # frozen, from a source tree and from an extracted payload, and a
    # different probe is the working one in each case.
    candidates: list[Path] = []

    # Only present in a frozen bundle.
    try:
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "LICENSE")
    except Exception:
        pass

    # A onefile bootstrap can leave `sys.executable` pointing somewhere that
    # will not resolve.
    try:
        candidates.append(Path(sys.executable).resolve().parent / "LICENSE")
    except Exception:
        pass

    # `__file__` is absent under some import machinery, and `parents[2]`
    # assumes a layout that a relocated module may not have.
    try:
        candidates.append(Path(__file__).resolve().parents[2] / "LICENSE")
    except Exception:
        pass

    candidates.append(Path.cwd() / "LICENSE")

    # A candidate that cannot be read is simply not the right one, so the walk
    # moves on. Running out raises below, which means a genuinely missing
    # licence is reported rather than shown as an empty dialog.
    for p in candidates:
        try:
            if p.exists() and p.is_file():
                return p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

    raise FileNotFoundError(
        "Unable to locate LICENSE. Tried: " + ", ".join(str(p) for p in candidates)
    )


LGPL_V3_TEXT = _read_lgpl3_text()
