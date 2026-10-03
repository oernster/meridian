"""The one reading of an ISO 8601 time in a feed, for every parser that has one."""

from __future__ import annotations

from datetime import datetime, timezone


def parse_iso_time(value: str) -> datetime:
    """An ISO 8601 time; one written with no zone is taken as UTC."""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed
