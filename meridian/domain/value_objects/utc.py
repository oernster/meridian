"""The one rule for turning a time into an instant Meridian can compare."""

from datetime import datetime, timezone


def as_utc(value: datetime) -> datetime:
    """The same instant in UTC; a time with no zone is taken as UTC already."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
