"""Builders and stand-ins shared by the bridge test modules.

These were private helpers inside `test_bridge.py`. Splitting that file by
bridge surface left every group needing the same handful, so they live here
rather than being copied four ways.
"""

import time
from unittest.mock import AsyncMock, MagicMock

from meridian.application.dto.feed_candidate_dto import FeedCandidateDTO
from meridian.application.dto.feed_dto import FeedDTO
from meridian.application.dto.item_dto import ItemDTO
from meridian.ui.bridge import AppController


def feed_dto(feed_id: int = 1, unread: int = 0) -> FeedDTO:
    return FeedDTO(
        id=feed_id,
        url=f"https://example.com/feed/{feed_id}",
        source_type="mfeed",
        title=f"Feed {feed_id}",
        description=None,
        icon=None,
        language=None,
        filter_expr=None,
        unread_count=unread,
    )


def item_dto(item_id: int = 1) -> ItemDTO:
    return ItemDTO(
        id=item_id,
        feed_id=1,
        item_id=f"https://example.com/item/{item_id}",
        type="article",
        title=f"Item {item_id}",
        url=f"https://example.com/item/{item_id}",
        published_iso="2026-01-01T00:00:00+00:00",
        description="A test item",
        thumbnail_url=None,
        duration=None,
        is_read=False,
    )


def candidate_dto(
    url: str = "https://example.com/feed", subscribed: bool = False
) -> FeedCandidateDTO:
    return FeedCandidateDTO(
        url=url,
        title="Feed",
        description="A feed",
        favicon_url=None,
        source_type="rss",
        is_subscribed=subscribed,
    )


# Long enough for a worker on a loaded machine, short enough to fail fast.
SETTLE_TIMEOUT_SECONDS = 5.0


def settle(qapp, condition) -> None:
    """Spin the event loop until `condition()`; fail if it never holds.

    The import runs on a worker and reports on the UI thread, so a test waits
    for the report the way the window does: by letting the loop run.
    """
    deadline = time.monotonic() + SETTLE_TIMEOUT_SECONDS
    while not condition() and time.monotonic() < deadline:
        qapp.processEvents()
    assert condition(), "the result never arrived on the UI thread"


def make_controller(qapp, sub_svc, item_svc, discovery_svc=None):
    if discovery_svc is None:
        discovery_svc = MagicMock()
        discovery_svc.search = AsyncMock(return_value=[])
    return AppController(sub_svc, item_svc, discovery_svc)
