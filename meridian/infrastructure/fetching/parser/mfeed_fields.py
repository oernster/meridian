"""Reading the members of an MFEED document by the tolerance rules of MMSP 6.15.

A REQUIRED item field that is missing or of the wrong JSON type makes the item
invalid: `InvalidItem` is raised and the parser skips that item alone. An
OPTIONAL field that is present but malformed is read as absent, so the item is
kept without it; in a list, the malformed entry is dropped and the rest kept.
Every reader here is one of those two rules, so the parser never decides it
case by case.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import TypeVar

from meridian.infrastructure.fetching.parser.iso_time import parse_iso_time

T = TypeVar("T")

# What a builder raises when an object lacks a member or holds the wrong kind.
_MALFORMED = (KeyError, TypeError, ValueError, AttributeError)


class InvalidItem(ValueError):
    """An item that lacks a REQUIRED field or carries one of the wrong type."""


def required_text(raw: dict, key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str):
        raise InvalidItem(f"{key!r} is missing or is not text")
    return value


def required_time(raw: dict, key: str) -> datetime:
    text = required_text(raw, key)
    try:
        return parse_iso_time(text)
    except ValueError:
        raise InvalidItem(f"{key!r} is not an ISO 8601 time") from None


def optional_text(raw: dict, key: str) -> str | None:
    value = raw.get(key)
    return value if isinstance(value, str) else None


def optional_int(raw: dict, key: str) -> int | None:
    value = raw.get(key)
    # bool is an int to Python and never a count to JSON.
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def optional_time(raw: dict, key: str) -> datetime | None:
    value = optional_text(raw, key)
    if value is None:
        return None
    try:
        return parse_iso_time(value)
    except ValueError:
        return None


def optional_object(raw: dict, key: str, build: Callable[[dict], T]) -> T | None:
    value = raw.get(key)
    if not isinstance(value, dict):
        return None
    try:
        return build(value)
    except _MALFORMED:
        return None


def entries(
    raw: dict,
    key: str,
    build: Callable[[dict], T],
    keep: Callable[[dict], bool] = lambda entry: True,
) -> tuple[T, ...]:
    """Every well-formed object in the list at `key` that `keep` accepts."""
    value = raw.get(key)
    if not isinstance(value, list):
        return ()
    built: list[T] = []
    for entry in value:
        if not isinstance(entry, dict) or not keep(entry):
            continue
        try:
            built.append(build(entry))
        except _MALFORMED:
            continue
    return tuple(built)


def texts(raw: dict, key: str) -> tuple[str, ...]:
    value = raw.get(key)
    if not isinstance(value, list):
        return ()
    return tuple(entry for entry in value if isinstance(entry, str))
