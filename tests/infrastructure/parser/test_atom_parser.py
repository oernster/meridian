from meridian.domain.value_objects.item_type import ItemType
from meridian.infrastructure.fetching.parser import atom_parser

_ATOM_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Blog</title>
  <id>https://example.com/atom</id>
  <entry>
    <id>https://example.com/entry/1</id>
    <title>First Entry</title>
    <link rel="alternate" href="https://example.com/entry/1"/>
    <published>2026-01-01T00:00:00Z</published>
    <updated>2026-01-02T00:00:00Z</updated>
    <summary>A summary of the entry.</summary>
    <author>
      <name>Bob</name>
      <uri>https://bob.example.com</uri>
    </author>
    <category term="tech"/>
    <category term="python"/>
  </entry>
</feed>"""

_ATOM_WITH_VIDEO = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Video Feed</title>
  <entry>
    <id>https://example.com/video/1</id>
    <title>My Video</title>
    <link rel="alternate" href="https://example.com/video/1"/>
    <link rel="enclosure" href="https://example.com/video.mp4"
          type="video/mp4" length="5000000"/>
    <published>2026-01-01T00:00:00Z</published>
  </entry>
</feed>"""

_ATOM_NO_NS = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed>
  <title>No-NS Feed</title>
  <entry>
    <id>https://example.com/1</id>
    <title>Item</title>
    <link rel="alternate" href="https://example.com/1"/>
    <published>2026-01-01T00:00:00Z</published>
  </entry>
</feed>"""


class TestAtomParser:
    def test_basic_entry(self):
        items, config = atom_parser.parse(1, "https://example.com/atom", _ATOM_FEED)
        assert len(items) == 1
        item = items[0]
        assert item.type == ItemType.ARTICLE
        assert item.title == "First Entry"
        assert item.url == "https://example.com/entry/1"

    def test_author_extracted(self):
        items, _ = atom_parser.parse(1, "https://example.com/atom", _ATOM_FEED)
        assert len(items[0].authors) == 1
        assert items[0].authors[0].name == "Bob"
        assert items[0].authors[0].url == "https://bob.example.com"

    def test_tags_extracted(self):
        items, _ = atom_parser.parse(1, "https://example.com/atom", _ATOM_FEED)
        assert "tech" in items[0].tags
        assert "python" in items[0].tags

    def test_description_from_summary(self):
        items, _ = atom_parser.parse(1, "https://example.com/atom", _ATOM_FEED)
        assert items[0].description == "A summary of the entry."

    def test_video_type_inferred(self):
        items, _ = atom_parser.parse(1, "https://example.com/atom", _ATOM_WITH_VIDEO)
        assert items[0].type == ItemType.VIDEO
        assert items[0].media[0].mime_type == "video/mp4"

    def test_source_field(self):
        items, _ = atom_parser.parse(1, "https://example.com/atom", _ATOM_FEED)
        assert items[0].source.type == "atom"
        assert items[0].source.feed_title == "Atom Blog"

    def test_no_namespace(self):
        items, _ = atom_parser.parse(1, "https://example.com/atom", _ATOM_NO_NS)
        assert len(items) == 1

    def test_poll_config_default(self):
        _, config = atom_parser.parse(1, "https://example.com/atom", _ATOM_FEED)
        assert config.min_interval_seconds == 300

    def test_audio_type_inferred(self):
        raw = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Audio Feed</title>
  <entry>
    <id>https://example.com/ep/1</id>
    <title>Episode</title>
    <link rel="alternate" href="https://example.com/ep/1"/>
    <link rel="enclosure" href="https://example.com/audio.mp3"
          type="audio/mpeg" length="5000000"/>
    <published>2026-01-01T00:00:00Z</published>
  </entry>
</feed>"""
        items, _ = atom_parser.parse(1, "https://example.com/atom", raw)
        assert items[0].type.value == "audio"

    def test_image_type_inferred(self):
        raw = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Image Feed</title>
  <entry>
    <id>https://example.com/photo/1</id>
    <title>Photo</title>
    <link rel="alternate" href="https://example.com/photo/1"/>
    <link rel="enclosure" href="https://example.com/photo.jpg"
          type="image/jpeg" length="200000"/>
    <published>2026-01-01T00:00:00Z</published>
  </entry>
</feed>"""
        items, _ = atom_parser.parse(1, "https://example.com/atom", raw)
        assert items[0].type.value == "image"

    def test_no_published_uses_now(self):
        raw = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>T</title>
  <entry>
    <id>https://example.com/1</id>
    <title>No Date</title>
    <link rel="alternate" href="https://example.com/1"/>
  </entry>
</feed>"""
        items, _ = atom_parser.parse(1, "https://example.com/atom", raw)
        assert items[0].published is not None

    def test_content_preferred_over_summary(self):
        raw = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>T</title>
  <entry>
    <id>https://example.com/1</id>
    <title>Item</title>
    <link rel="alternate" href="https://example.com/1"/>
    <published>2026-01-01T00:00:00Z</published>
    <summary>Summary text</summary>
    <content>Full content text</content>
  </entry>
</feed>"""
        items, _ = atom_parser.parse(1, "https://example.com/atom", raw)
        assert items[0].description == "Full content text"

    def test_media_thumbnail_extracted(self):
        _MEDIA_NS = "http://search.yahoo.com/mrss/"
        raw = f"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:media="{_MEDIA_NS}">
  <title>T</title>
  <entry>
    <id>https://example.com/1</id>
    <title>Item</title>
    <link rel="alternate" href="https://example.com/1"/>
    <published>2026-01-01T00:00:00Z</published>
    <media:thumbnail url="https://example.com/thumb.jpg" width="320" height="180"/>
  </entry>
</feed>""".encode()
        items, _ = atom_parser.parse(1, "https://example.com/atom", raw)
        assert len(items[0].thumbnail) == 1

    def test_media_group_non_youtube_content(self):
        _MEDIA_NS = "http://search.yahoo.com/mrss/"
        raw = f"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:media="{_MEDIA_NS}">
  <title>Podcast</title>
  <entry>
    <id>https://example.com/ep/1</id>
    <title>Episode 1</title>
    <link rel="alternate" href="https://example.com/ep/1"/>
    <published>2026-01-01T00:00:00Z</published>
    <media:group>
      <media:thumbnail url="https://example.com/thumb.jpg" width="640" height="360"/>
      <media:content url="https://example.com/video.mp4" type="video/mp4"/>
      <media:description>Group description</media:description>
    </media:group>
  </entry>
</feed>""".encode()
        items, _ = atom_parser.parse(1, "https://example.com/atom", raw)
        assert len(items[0].thumbnail) == 1
        assert items[0].thumbnail[0].width == 640
        assert len(items[0].media) == 1
        assert items[0].media[0].url == "https://example.com/video.mp4"
        assert items[0].description == "Group description"

    def test_media_group_thumbnail_no_url_ignored(self):
        _MEDIA_NS = "http://search.yahoo.com/mrss/"
        raw = f"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:media="{_MEDIA_NS}">
  <title>T</title>
  <entry>
    <id>https://example.com/1</id><title>Item</title>
    <link rel="alternate" href="https://example.com/1"/>
    <published>2026-01-01T00:00:00Z</published>
    <media:group>
      <media:thumbnail/>
    </media:group>
  </entry>
</feed>""".encode()
        items, _ = atom_parser.parse(1, "https://example.com/atom", raw)
        assert len(items[0].thumbnail) == 0

    def test_media_group_youtube_content_url_excluded(self):
        _MEDIA_NS = "http://search.yahoo.com/mrss/"
        raw = f"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:media="{_MEDIA_NS}">
  <title>YT</title>
  <entry>
    <id>https://www.youtube.com/watch?v=abc</id><title>Video</title>
    <link rel="alternate" href="https://www.youtube.com/watch?v=abc"/>
    <published>2026-01-01T00:00:00Z</published>
    <media:group>
      <media:content url="https://www.youtube.com/v/abc" type="video/mp4"/>
    </media:group>
  </entry>
</feed>""".encode()
        items, _ = atom_parser.parse(
            1, "https://www.youtube.com/feeds/videos.xml?channel_id=UC123", raw
        )
        assert len(items[0].media) == 0

    def test_media_group_description_not_overridden_if_already_set(self):
        _MEDIA_NS = "http://search.yahoo.com/mrss/"
        raw = f"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:media="{_MEDIA_NS}">
  <title>T</title>
  <entry>
    <id>https://example.com/1</id>
    <title>Item</title>
    <link rel="alternate" href="https://example.com/1"/>
    <published>2026-01-01T00:00:00Z</published>
    <summary>Atom summary</summary>
    <media:group>
      <media:description>Group desc</media:description>
    </media:group>
  </entry>
</feed>""".encode()
        items, _ = atom_parser.parse(1, "https://example.com/atom", raw)
        assert items[0].description == "Atom summary"

    def test_youtube_feed_url_infers_video_type(self):
        raw = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>YT Channel</title>
  <entry>
    <id>https://www.youtube.com/watch?v=abc</id>
    <title>A Video</title>
    <link rel="alternate" href="https://www.youtube.com/watch?v=abc"/>
    <published>2026-01-01T00:00:00Z</published>
  </entry>
</feed>"""
        items, _ = atom_parser.parse(
            1, "https://www.youtube.com/feeds/videos.xml?channel_id=UC123", raw
        )
        assert items[0].type == ItemType.VIDEO

    def test_datetime_no_timezone(self):
        from meridian.infrastructure.fetching.parser.atom_parser import _parse_dt
        from datetime import timezone

        dt = _parse_dt("2026-01-01T00:00:00")
        assert dt.tzinfo == timezone.utc

    def test_author_without_uri(self):
        raw = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>T</title>
  <entry>
    <id>https://example.com/1</id>
    <title>Item</title>
    <link rel="alternate" href="https://example.com/1"/>
    <published>2026-01-01T00:00:00Z</published>
    <author><name>Bob</name></author>
  </entry>
</feed>"""
        items, _ = atom_parser.parse(1, "https://example.com/atom", raw)
        assert items[0].authors[0].url is None

    def test_enclosure_without_length(self):
        raw = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>T</title>
  <entry>
    <id>https://example.com/1</id>
    <title>Item</title>
    <link rel="alternate" href="https://example.com/1"/>
    <link rel="enclosure" href="https://example.com/video.mp4" type="video/mp4"/>
    <published>2026-01-01T00:00:00Z</published>
  </entry>
</feed>"""
        items, _ = atom_parser.parse(1, "https://example.com/atom", raw)
        assert items[0].media[0].size_bytes is None

    def test_author_name_el_no_text(self):
        raw = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>T</title>
  <entry>
    <id>https://example.com/1</id>
    <title>Item</title>
    <link rel="alternate" href="https://example.com/1"/>
    <published>2026-01-01T00:00:00Z</published>
    <author><name/></author>
  </entry>
</feed>"""
        items, _ = atom_parser.parse(1, "https://example.com/atom", raw)
        assert len(items[0].authors) == 0

    def test_category_no_term(self):
        raw = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>T</title>
  <entry>
    <id>https://example.com/1</id>
    <title>Item</title>
    <link rel="alternate" href="https://example.com/1"/>
    <published>2026-01-01T00:00:00Z</published>
    <category scheme="http://example.com"/>
  </entry>
</feed>"""
        items, _ = atom_parser.parse(1, "https://example.com/atom", raw)
        assert len(items[0].tags) == 0

    def test_enclosure_no_link_with_rel(self):
        raw = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>T</title>
  <entry>
    <id>https://example.com/1</id>
    <title>Item</title>
    <link rel="alternate" href="https://example.com/1"/>
    <link href="https://example.com/video.mp4"/>
    <published>2026-01-01T00:00:00Z</published>
  </entry>
</feed>"""
        items, _ = atom_parser.parse(1, "https://example.com/atom", raw)
        assert len(items[0].media) == 0

    def test_thumbnail_no_url(self):
        _MEDIA_NS = "http://search.yahoo.com/mrss/"
        raw = f"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:media="{_MEDIA_NS}">
  <title>T</title>
  <entry>
    <id>https://example.com/1</id>
    <title>Item</title>
    <link rel="alternate" href="https://example.com/1"/>
    <published>2026-01-01T00:00:00Z</published>
    <media:thumbnail width="320"/>
  </entry>
</feed>""".encode()
        items, _ = atom_parser.parse(1, "https://example.com/atom", raw)
        assert len(items[0].thumbnail) == 0

    def test_infer_type_multi_item_loop(self):
        from meridian.infrastructure.fetching.parser.atom_parser import _infer_type
        from meridian.domain.value_objects.media import Media
        from meridian.domain.value_objects.item_type import ItemType

        media = [
            Media(url="https://a.example.com/doc.pdf", mime_type="application/pdf"),
            Media(url="https://b.example.com/v.mp4", mime_type="video/mp4"),
        ]
        assert _infer_type(media) == ItemType.VIDEO

    def test_enclosure_http_url_excluded(self):
        raw = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>T</title>
  <entry>
    <id>https://example.com/1</id>
    <title>Item</title>
    <link rel="alternate" href="https://example.com/1"/>
    <link rel="enclosure" href="http://insecure.example.com/video.mp4"
          type="video/mp4"/>
    <published>2026-01-01T00:00:00Z</published>
  </entry>
</feed>"""
        items, _ = atom_parser.parse(1, "https://example.com/atom", raw)
        assert len(items[0].media) == 0

    def test_entry_no_alternate_link_uses_id(self):
        raw = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>T</title>
  <entry>
    <id>https://example.com/entry/fallback</id>
    <title>No Alternate Link</title>
    <link rel="related" href="https://example.com/related"/>
    <published>2026-01-01T00:00:00Z</published>
  </entry>
</feed>"""
        items, _ = atom_parser.parse(1, "https://example.com/atom", raw)
        assert items[0].url == "https://example.com/entry/fallback"
