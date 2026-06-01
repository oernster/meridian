from meridian.domain.value_objects.item_type import ItemType
from meridian.infrastructure.fetching.parser import rss_parser

_RSS_MINIMAL = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>My Blog</title>
    <link>https://example.com</link>
    <item>
      <guid>https://example.com/post/1</guid>
      <title>Hello World</title>
      <link>https://example.com/post/1</link>
      <description>A test post</description>
      <pubDate>Mon, 01 Jan 2026 00:00:00 +0000</pubDate>
      <author>alice@example.com (Alice)</author>
      <category>tech</category>
    </item>
  </channel>
</rss>"""

_RSS_WITH_VIDEO = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Video Blog</title>
    <item>
      <guid>https://example.com/video/1</guid>
      <title>My Video</title>
      <link>https://example.com/video/1</link>
      <pubDate>Mon, 01 Jan 2026 00:00:00 +0000</pubDate>
      <enclosure url="https://example.com/video.mp4"
                 type="video/mp4" length="10000000"/>
    </item>
  </channel>
</rss>"""

_RSS_WITH_AUDIO = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Podcast</title>
    <item>
      <guid>https://example.com/ep/1</guid>
      <title>Episode 1</title>
      <link>https://example.com/ep/1</link>
      <pubDate>Mon, 01 Jan 2026 00:00:00 +0000</pubDate>
      <enclosure url="https://example.com/audio.mp3"
                 type="audio/mpeg" length="5000000"/>
    </item>
  </channel>
</rss>"""

_RSS_WITH_TTL = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Fast Feed</title>
    <ttl>60</ttl>
    <item>
      <guid>https://example.com/1</guid>
      <title>Item</title>
      <link>https://example.com/1</link>
      <pubDate>Mon, 01 Jan 2026 00:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>"""


class TestRssParser:
    def test_minimal_article(self):
        items, config = rss_parser.parse(
            1, "https://example.com/feed.xml", _RSS_MINIMAL
        )
        assert len(items) == 1
        item = items[0]
        assert item.type == ItemType.ARTICLE
        assert item.title == "Hello World"
        assert item.url == "https://example.com/post/1"

    def test_author_extracted(self):
        items, _ = rss_parser.parse(1, "https://example.com/feed.xml", _RSS_MINIMAL)
        assert len(items[0].authors) == 1
        assert items[0].authors[0].name == "Alice"

    def test_tags_extracted(self):
        items, _ = rss_parser.parse(1, "https://example.com/feed.xml", _RSS_MINIMAL)
        assert "tech" in items[0].tags

    def test_description_extracted(self):
        items, _ = rss_parser.parse(1, "https://example.com/feed.xml", _RSS_MINIMAL)
        assert items[0].description == "A test post"

    def test_content_encoded_preferred_over_description(self):
        feed = b"""<?xml version="1.0"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel><title>T</title>
    <item>
      <guid>https://example.com/1</guid>
      <title>T</title>
      <description>short summary</description>
      <content:encoded><![CDATA[<p>Full article HTML</p>]]></content:encoded>
    </item>
  </channel>
</rss>"""
        items, _ = rss_parser.parse(1, "https://example.com/feed.xml", feed)
        assert items[0].description == "<p>Full article HTML</p>"

    def test_video_type_inferred(self):
        items, _ = rss_parser.parse(1, "https://example.com/feed.xml", _RSS_WITH_VIDEO)
        assert items[0].type == ItemType.VIDEO
        assert len(items[0].media) == 1
        assert items[0].media[0].mime_type == "video/mp4"

    def test_audio_type_inferred(self):
        items, _ = rss_parser.parse(1, "https://example.com/feed.xml", _RSS_WITH_AUDIO)
        assert items[0].type == ItemType.AUDIO

    def test_ttl_as_poll_interval(self):
        _, config = rss_parser.parse(1, "https://example.com/feed.xml", _RSS_WITH_TTL)
        assert config.min_interval_seconds == 3600

    def test_poll_config_floor_enforced(self):
        raw = _RSS_WITH_TTL.replace(b"<ttl>60</ttl>", b"<ttl>1</ttl>")
        _, config = rss_parser.parse(1, "https://example.com/feed.xml", raw)
        assert config.min_interval_seconds == 300

    def test_source_field(self):
        items, _ = rss_parser.parse(1, "https://example.com/feed.xml", _RSS_MINIMAL)
        assert items[0].source is not None
        assert items[0].source.type == "rss"
        assert items[0].source.feed_title == "My Blog"

    def test_https_only_enclosure(self):
        raw = _RSS_WITH_VIDEO.replace(
            b'url="https://example.com/video.mp4"',
            b'url="http://example.com/video.mp4"',
        )
        items, _ = rss_parser.parse(1, "https://example.com/feed.xml", raw)
        assert len(items[0].media) == 0

    def test_invalid_ttl_ignored(self):
        raw = _RSS_WITH_TTL.replace(b"<ttl>60</ttl>", b"<ttl>not-a-number</ttl>")
        _, config = rss_parser.parse(1, "https://example.com/feed.xml", raw)
        assert config.min_interval_seconds == 300

    def test_non_http_guid_prefixed(self):
        raw = _RSS_MINIMAL.replace(
            b"<guid>https://example.com/post/1</guid>",
            b"<guid>local-post-id-1</guid>",
        )
        items, _ = rss_parser.parse(1, "https://example.com/feed.xml", raw)
        assert items[0].item_id.startswith("https://example.com/feed.xml#")

    def test_image_type_inferred(self):
        raw = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Image Blog</title>
    <item>
      <guid>https://example.com/img/1</guid>
      <title>My Image</title>
      <link>https://example.com/img/1</link>
      <pubDate>Mon, 01 Jan 2026 00:00:00 +0000</pubDate>
      <enclosure url="https://example.com/photo.jpg" type="image/jpeg" length="50000"/>
    </item>
  </channel>
</rss>"""
        items, _ = rss_parser.parse(1, "https://example.com/feed.xml", raw)
        assert items[0].type.value == "image"

    def test_media_content_with_duration(self):
        _MEDIA_NS = "http://search.yahoo.com/mrss/"
        raw = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="{_MEDIA_NS}">
  <channel>
    <title>Media Feed</title>
    <item>
      <guid>https://example.com/v/1</guid>
      <title>Video</title>
      <link>https://example.com/v/1</link>
      <pubDate>Mon, 01 Jan 2026 00:00:00 +0000</pubDate>
      <media:content url="https://example.com/video.mp4"
                     type="video/mp4" duration="600"/>
    </item>
  </channel>
</rss>""".encode()
        items, _ = rss_parser.parse(1, "https://example.com/feed.xml", raw)
        assert len(items[0].media) == 1
        assert items[0].media[0].duration == 600

    def test_media_thumbnail_extracted(self):
        _MEDIA_NS = "http://search.yahoo.com/mrss/"
        raw = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="{_MEDIA_NS}">
  <channel>
    <title>Thumb Feed</title>
    <item>
      <guid>https://example.com/t/1</guid>
      <title>Item</title>
      <link>https://example.com/t/1</link>
      <pubDate>Mon, 01 Jan 2026 00:00:00 +0000</pubDate>
      <media:thumbnail url="https://example.com/thumb.jpg" width="320" height="180"/>
    </item>
  </channel>
</rss>""".encode()
        items, _ = rss_parser.parse(1, "https://example.com/feed.xml", raw)
        assert len(items[0].thumbnail) == 1
        assert items[0].thumbnail[0].width == 320

    def test_invalid_pubdate_uses_now(self):
        raw = _RSS_MINIMAL.replace(
            b"<pubDate>Mon, 01 Jan 2026 00:00:00 +0000</pubDate>",
            b"<pubDate>not-a-valid-date</pubDate>",
        )
        items, _ = rss_parser.parse(1, "https://example.com/feed.xml", raw)
        assert items[0].published is not None

    def test_author_without_parens(self):
        raw = _RSS_MINIMAL.replace(
            b"<author>alice@example.com (Alice)</author>",
            b"<author>Alice Smith</author>",
        )
        items, _ = rss_parser.parse(1, "https://example.com/feed.xml", raw)
        assert items[0].authors[0].name == "Alice Smith"

    def test_infer_type_multi_item_loop(self):
        from meridian.infrastructure.fetching.parser.rss_parser import _infer_type
        from meridian.domain.value_objects.media import Media
        from meridian.domain.value_objects.item_type import ItemType

        media = [
            Media(url="https://a.example.com/doc.pdf", mime_type="application/pdf"),
            Media(url="https://b.example.com/v.mp4", mime_type="video/mp4"),
        ]
        assert _infer_type(media) == ItemType.VIDEO

    def test_thumbnail_no_url_attribute(self):
        _MEDIA_NS = "http://search.yahoo.com/mrss/"
        raw = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="{_MEDIA_NS}">
  <channel>
    <title>T</title>
    <item>
      <guid>https://example.com/nothumb/1</guid>
      <title>No URL Thumb</title>
      <link>https://example.com/nothumb/1</link>
      <pubDate>Mon, 01 Jan 2026 00:00:00 +0000</pubDate>
      <media:thumbnail width="320" height="180"/>
    </item>
  </channel>
</rss>""".encode()
        items, _ = rss_parser.parse(1, "https://example.com/feed.xml", raw)
        assert len(items[0].thumbnail) == 0

    def test_author_whitespace_paren_excluded(self):
        raw = _RSS_MINIMAL.replace(
            b"<author>alice@example.com (Alice)</author>",
            b"<author>alice@example.com (   )</author>",
        )
        items, _ = rss_parser.parse(1, "https://example.com/feed.xml", raw)
        assert len(items[0].authors) == 0

    def test_media_content_http_excluded(self):
        _MEDIA_NS = "http://search.yahoo.com/mrss/"
        raw = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="{_MEDIA_NS}">
  <channel><title>T</title>
    <item>
      <guid>https://example.com/1</guid>
      <title>Item</title>
      <link>https://example.com/1</link>
      <pubDate>Mon, 01 Jan 2026 00:00:00 +0000</pubDate>
      <media:content url="http://insecure.example.com/v.mp4" type="video/mp4"/>
    </item>
  </channel>
</rss>""".encode()
        items, _ = rss_parser.parse(1, "https://example.com/feed.xml", raw)
        assert len(items[0].media) == 0

    def test_iso_date_without_timezone(self):
        raw = _RSS_MINIMAL.replace(
            b"<pubDate>Mon, 01 Jan 2026 00:00:00 +0000</pubDate>",
            b"<pubDate>2026-03-15T12:30:00</pubDate>",
        )
        items, _ = rss_parser.parse(1, "https://example.com/feed.xml", raw)
        from datetime import timezone

        assert items[0].published.tzinfo == timezone.utc
        assert items[0].published.year == 2026
