from unittest.mock import MagicMock

from meridian.domain.value_objects.item_type import ItemType
from meridian.infrastructure.fetching.parser import platform_parser, rss_parser

_RSS_FALLBACK = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Platform Fallback Feed</title>
    <item>
      <guid>https://platform.example.com/item/1</guid>
      <title>Platform Item</title>
      <link>https://platform.example.com/item/1</link>
      <pubDate>Mon, 01 Jan 2026 00:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>"""


class TestPlatformParser:
    def setup_method(self):
        platform_parser._ADAPTERS.clear()

    def test_falls_back_to_rss_no_adapter(self):
        items, _ = platform_parser.parse(
            1,
            "https://platform.example.com/feed",
            _RSS_FALLBACK,
            platform_id=None,
        )
        assert len(items) == 1
        assert items[0].title == "Platform Item"

    def test_falls_back_to_rss_unknown_adapter(self):
        items, _ = platform_parser.parse(
            1,
            "https://platform.example.com/feed",
            _RSS_FALLBACK,
            platform_id="unknown-platform",
        )
        assert len(items) == 1

    def test_uses_registered_adapter(self):
        from meridian.domain.value_objects.poll_config import PollConfig
        from datetime import datetime, timezone
        from meridian.domain.entities.item import Item
        from meridian.domain.value_objects.item_type import ItemType

        mock_item = Item(
            feed_id=1,
            item_id="https://platform.example.com/item/special",
            type=ItemType.VIDEO,
            title="Special Platform Item",
            url="https://platform.example.com/item/special",
            published=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        adapter = MagicMock()
        adapter.parse.return_value = ([mock_item], PollConfig())
        platform_parser.register_adapter("my-platform", adapter)

        items, _ = platform_parser.parse(
            1,
            "https://platform.example.com/feed",
            b"",
            platform_id="my-platform",
        )
        assert len(items) == 1
        assert items[0].title == "Special Platform Item"
        adapter.parse.assert_called_once()

    def test_uses_rss_fallback_url(self):
        items, _ = platform_parser.parse(
            1,
            "https://platform.example.com/native",
            _RSS_FALLBACK,
            platform_id=None,
            rss_fallback_url="https://platform.example.com/rss",
        )
        assert len(items) == 1
