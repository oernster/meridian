"""The exported feed list: the one statement of its shape, both ways.

    {"version": 1, "feeds": [{"url": ..., "source_type": ..., "title": ...,
                              "filter_expr": ..., "platform_id": ...,
                              "rss_fallback_url": ...}]}

An entry carries everything a feed needs to come back as it was. Export used
to write only the address, the type and the title, so every filter was lost on
the path the README gives for keeping your data. The three later members are
optional and written only when set, so the format is still version 1: a file
from before them reads as it always did; an older Meridian reading a new
file ignores members it does not know. Read state does not travel.
"""

from __future__ import annotations

import codecs
import json

from meridian.application.dto.feed_dto import FeedDTO

FEED_LIST_VERSION = 1
_VERSION_KEY = "version"
_FEEDS_KEY = "feeds"
# Written only when the feed has one; a file without them is still version 1.
_OPTIONAL_MEMBERS = ("filter_expr", "platform_id", "rss_fallback_url")
# A byte order mark names its encoding; a file without one is read as UTF-8.
_BYTE_ORDER_MARKS = (
    (codecs.BOM_UTF8, "utf-8-sig"),
    (codecs.BOM_UTF16_LE, "utf-16"),
    (codecs.BOM_UTF16_BE, "utf-16"),
)
_PLAIN_TEXT = "utf-8"


class NotAFeedList(ValueError):
    """The file cannot be read as a Meridian feed list; the message says why."""


def build_feed_list(feeds: list[FeedDTO]) -> dict:
    """The envelope export writes for these feeds."""
    return {_VERSION_KEY: FEED_LIST_VERSION, _FEEDS_KEY: [_entry(f) for f in feeds]}


def _entry(feed: FeedDTO) -> dict:
    entry = {"url": feed.url, "source_type": feed.source_type, "title": feed.title}
    for member in _OPTIONAL_MEMBERS:
        value = getattr(feed, member)
        if value is not None:
            entry[member] = value
    return entry


def decode_feed_list(raw: bytes) -> object:
    """The parsed contents of a file: UTF-8 with or without a mark; UTF-16 with one."""
    encoding = next(
        (name for mark, name in _BYTE_ORDER_MARKS if raw.startswith(mark)),
        _PLAIN_TEXT,
    )
    try:
        text = raw.decode(encoding)
    except UnicodeDecodeError:
        raise NotAFeedList("the file is not UTF-8 or UTF-16 text") from None
    try:
        return json.loads(text)
    except ValueError:
        raise NotAFeedList("the file is not a Meridian feed list") from None


def feed_list_entries(data: object) -> list:
    """The entries of a parsed feed list; raises NotAFeedList for anything else.

    A file with no version key is read as version 1, which is what every
    export has written; any other version is refused by name rather than
    guessed at.
    """
    if not isinstance(data, dict) or not isinstance(data.get(_FEEDS_KEY), list):
        raise NotAFeedList("the file is not a Meridian feed list")
    version = data.get(_VERSION_KEY, FEED_LIST_VERSION)
    # bool and float compare equal to 1 in Python; neither is what export wrote.
    if type(version) is not int or version != FEED_LIST_VERSION:
        raise NotAFeedList(
            f"the file is feed list version {version!r}; "
            f"this Meridian reads version {FEED_LIST_VERSION}"
        )
    return data[_FEEDS_KEY]
