"""The atoms of the MMSP Appendix A filter grammar, each read once into a test.

An atom's value is checked when the filter is read, not when an item is
tested: a bound that is not a number or a time is a filter the user must be
told about before it is saved, never an error that breaks the feed later.

    range-expr      = ">=" number / "<=" number / "[" number "," number "]"
    date-range-expr = ">=" iso8601 / "<=" iso8601 / "[" iso8601 "," iso8601 "]"

Two readings are this client's, where the grammar is silent. An item with no
duration matches no duration filter, as the specification's own conformance
suite holds. A time bound with no offset is UTC; a bound that is a date alone
covers that whole day, so `published:<=2026-03-15` takes in the evening of
the fifteenth.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date, datetime, time, timezone

from meridian.domain.entities.item import Item
from meridian.domain.value_objects.filter_expression import FilterSyntaxError
from meridian.domain.value_objects.utc import as_utc

ItemTest = Callable[[Item], bool]

_AT_LEAST = ">="
_AT_MOST = "<="
_RANGE_OPEN = "["
_RANGE_CLOSE = "]"
_RANGE_SEPARATOR = ","
_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_QUOTE = '"'


def _invalid(raw: str, what: str) -> FilterSyntaxError:
    return FilterSyntaxError(f"{raw!r} is not a valid {what}")


def _bounds(raw: str, value: str, what: str) -> tuple[str | None, str | None]:
    """Split a range expression into its lower and upper bound text."""
    if value.startswith(_AT_LEAST):
        return value[len(_AT_LEAST) :], None
    if value.startswith(_AT_MOST):
        return None, value[len(_AT_MOST) :]
    if value.startswith(_RANGE_OPEN) and value.endswith(_RANGE_CLOSE):
        parts = value[len(_RANGE_OPEN) : -len(_RANGE_CLOSE)].split(_RANGE_SEPARATOR)
        if len(parts) == 2:
            return parts[0], parts[1]
    raise _invalid(raw, what)


def _number(raw: str, text: str | None) -> float | None:
    if text is None:
        return None
    if not _NUMBER.fullmatch(text):
        raise _invalid(raw, "duration filter: a bound must be a number of seconds")
    return float(text)


def _instant(raw: str, text: str | None, upper: bool) -> datetime | None:
    if text is None:
        return None
    try:
        day = date.fromisoformat(text)
    except ValueError:
        pass
    else:
        clock = time.max if upper else time.min
        return datetime.combine(day, clock, tzinfo=timezone.utc)
    try:
        return as_utc(datetime.fromisoformat(text))
    except ValueError:
        raise _invalid(raw, "date filter: a bound must be an ISO 8601 time") from None


def _within(actual, low, high) -> bool:
    return (low is None or actual >= low) and (high is None or actual <= high)


def _duration(raw: str, value: str) -> ItemTest:
    low_text, high_text = _bounds(raw, value, "duration filter")
    low, high = _number(raw, low_text), _number(raw, high_text)
    return lambda item: item.duration is not None and _within(item.duration, low, high)


def _published(raw: str, value: str) -> ItemTest:
    low_text, high_text = _bounds(raw, value, "date filter")
    low = _instant(raw, low_text, upper=False)
    high = _instant(raw, high_text, upper=True)
    return lambda item: _within(as_utc(item.published), low, high)


def _text(value: str) -> str:
    return value.strip(_QUOTE)


def _type(raw: str, value: str) -> ItemTest:
    return lambda item: item.type.value == value


def _tag(raw: str, value: str) -> ItemTest:
    wanted = _text(value)
    return lambda item: wanted in item.tags


def _author(raw: str, value: str) -> ItemTest:
    wanted = _text(value)
    return lambda item: any(a.name == wanted for a in item.authors)


def _lang(raw: str, value: str) -> ItemTest:
    return lambda item: item.language == value


def _keyword(raw: str, value: str) -> ItemTest:
    wanted = _text(value).lower()
    return lambda item: wanted in f"{item.title} {item.description or ''}".lower()


def _rating(raw: str, value: str) -> ItemTest:
    return lambda item: (
        item.content_rating is not None and item.content_rating.rating == value
    )


# The one list of what a filter can name; the tokeniser's pattern is built
# from these keys, so an atom it accepts always has a reader here.
ATOM_READERS: dict[str, Callable[[str, str], ItemTest]] = {
    "type": _type,
    "tag": _tag,
    "author": _author,
    "lang": _lang,
    "duration": _duration,
    "published": _published,
    "keyword": _keyword,
    "rating": _rating,
}


def read_atom(raw: str) -> ItemTest:
    """The test one atom stands for; raises FilterSyntaxError for a bad value."""
    field, _, value = raw.partition(":")
    return ATOM_READERS[field](raw, value)
