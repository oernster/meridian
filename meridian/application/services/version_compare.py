"""Dotted-integer version comparison for the update check.

Anything unparseable compares as not-newer, so a malformed tag (or a
``0.0.0-dev`` fallback build) can never raise a spurious prompt.
"""

from __future__ import annotations


def _parse(version: str) -> tuple[int, ...] | None:
    text = version.strip()
    if text[:1] in ("v", "V"):
        text = text[1:]
    try:
        return tuple(int(part) for part in text.split("."))
    except ValueError:
        return None


def is_newer(latest: str, current: str) -> bool:
    """True when ``latest`` is a strictly newer version than ``current``."""
    latest_parts = _parse(latest)
    current_parts = _parse(current)
    if latest_parts is None or current_parts is None:
        return False
    return latest_parts > current_parts
