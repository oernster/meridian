from meridian.domain.value_objects.item_type import ItemType
from meridian.infrastructure.fetching.parser import podcast_parser

_ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
_PC_NS = "https://podcastindex.org/namespace/1.0"

_PODCAST_FEED = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="{_ITUNES_NS}"
     xmlns:podcast="{_PC_NS}">
  <channel>
    <title>My Podcast</title>
    <link>https://podcast.example.com</link>
    <item>
      <guid>https://podcast.example.com/ep/1</guid>
      <title>Episode 1 RSS Title</title>
      <link>https://podcast.example.com/ep/1</link>
      <pubDate>Mon, 01 Jan 2026 00:00:00 +0000</pubDate>
      <enclosure url="https://podcast.example.com/ep1.mp3" type="audio/mpeg" length="10000000"/>
      <itunes:title>Episode 1 iTunes Title</itunes:title>
      <itunes:duration>01:02:30</itunes:duration>
      <itunes:episode>1</itunes:episode>
      <itunes:season>2</itunes:season>
      <itunes:explicit>yes</itunes:explicit>
      <itunes:image href="https://podcast.example.com/cover.jpg"/>
      <podcast:transcript url="https://podcast.example.com/ep1.txt" type="text/plain" language="en"/>
      <podcast:person role="host">Alice</podcast:person>
    </item>
  </channel>
</rss>""".encode()

_PODCAST_SIMPLE = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="{_ITUNES_NS}">
  <channel>
    <title>Simple Podcast</title>
    <item>
      <guid>https://podcast.example.com/ep/2</guid>
      <title>Episode 2</title>
      <link>https://podcast.example.com/ep/2</link>
      <pubDate>Mon, 01 Jan 2026 00:00:00 +0000</pubDate>
      <enclosure url="https://podcast.example.com/ep2.mp3" type="audio/mpeg" length="5000000"/>
      <itunes:duration>45:00</itunes:duration>
      <itunes:explicit>no</itunes:explicit>
    </item>
  </channel>
</rss>""".encode()


class TestPodcastParser:
    def test_type_is_audio(self):
        items, _ = podcast_parser.parse(1, "https://podcast.example.com/feed.xml", _PODCAST_FEED)
        assert items[0].type == ItemType.AUDIO

    def test_itunes_title_overrides_rss(self):
        items, _ = podcast_parser.parse(1, "https://podcast.example.com/feed.xml", _PODCAST_FEED)
        assert items[0].title == "Episode 1 iTunes Title"

    def test_duration_hhmmss(self):
        items, _ = podcast_parser.parse(1, "https://podcast.example.com/feed.xml", _PODCAST_FEED)
        assert items[0].duration == 3750

    def test_duration_mmss(self):
        items, _ = podcast_parser.parse(1, "https://podcast.example.com/feed.xml", _PODCAST_SIMPLE)
        assert items[0].duration == 2700

    def test_series_populated(self):
        items, _ = podcast_parser.parse(1, "https://podcast.example.com/feed.xml", _PODCAST_FEED)
        assert items[0].series is not None
        assert items[0].series.episode_number == 1
        assert items[0].series.season_number == 2

    def test_explicit_rating(self):
        items, _ = podcast_parser.parse(1, "https://podcast.example.com/feed.xml", _PODCAST_FEED)
        assert items[0].content_rating is not None
        assert items[0].content_rating.rating == "explicit"

    def test_general_rating(self):
        items, _ = podcast_parser.parse(1, "https://podcast.example.com/feed.xml", _PODCAST_SIMPLE)
        assert items[0].content_rating is not None
        assert items[0].content_rating.rating == "general"

    def test_thumbnail_from_itunes_image(self):
        items, _ = podcast_parser.parse(1, "https://podcast.example.com/feed.xml", _PODCAST_FEED)
        assert len(items[0].thumbnail) == 1
        assert items[0].thumbnail[0].url == "https://podcast.example.com/cover.jpg"

    def test_transcript(self):
        items, _ = podcast_parser.parse(1, "https://podcast.example.com/feed.xml", _PODCAST_FEED)
        assert items[0].transcript is not None
        assert items[0].transcript.mime_type == "text/plain"

    def test_host_as_author(self):
        items, _ = podcast_parser.parse(1, "https://podcast.example.com/feed.xml", _PODCAST_FEED)
        assert len(items[0].authors) == 1
        assert items[0].authors[0].name == "Alice"

    def test_source_type_podcast(self):
        items, _ = podcast_parser.parse(1, "https://podcast.example.com/feed.xml", _PODCAST_FEED)
        assert items[0].source.type == "podcast"

    def test_duration_seconds_only(self):
        _ITUNES_NS_L = "http://www.itunes.com/dtds/podcast-1.0.dtd"
        raw = f"""<?xml version="1.0"?>
<rss version="2.0" xmlns:itunes="{_ITUNES_NS_L}">
  <channel><title>T</title>
    <item>
      <guid>https://podcast.example.com/ep/s</guid>
      <title>Short</title>
      <link>https://podcast.example.com/ep/s</link>
      <pubDate>Mon, 01 Jan 2026 00:00:00 +0000</pubDate>
      <enclosure url="https://podcast.example.com/s.mp3" type="audio/mpeg" length="100000"/>
      <itunes:duration>90</itunes:duration>
    </item>
  </channel>
</rss>""".encode()
        items, _ = podcast_parser.parse(1, "https://podcast.example.com/feed.xml", raw)
        assert items[0].duration == 90

    def test_itunes_int_invalid(self):
        from meridian.infrastructure.fetching.parser.podcast_parser import _itunes_int
        import defusedxml.ElementTree as ET
        _ITUNES_NS_L = "http://www.itunes.com/dtds/podcast-1.0.dtd"
        el = ET.fromstring(f"""<item xmlns:itunes="{_ITUNES_NS_L}">
            <itunes:episode>not-a-number</itunes:episode>
        </item>""")
        assert _itunes_int(el, "episode") is None

    def test_itunes_int_none_when_tag_missing(self):
        from meridian.infrastructure.fetching.parser.podcast_parser import _itunes_int
        import defusedxml.ElementTree as ET
        el = ET.fromstring("<item/>")
        assert _itunes_int(el, "episode") is None

    def test_pc_person_no_match(self):
        from meridian.infrastructure.fetching.parser.podcast_parser import _pc_person
        import defusedxml.ElementTree as ET
        _PC_NS_L = "https://podcastindex.org/namespace/1.0"
        el = ET.fromstring(f"""<item xmlns:podcast="{_PC_NS_L}">
            <podcast:person role="guest">Charlie</podcast:person>
        </item>""")
        assert _pc_person(el, "host") is None

    def test_duration_invalid_raises_none(self):
        from meridian.infrastructure.fetching.parser.podcast_parser import _parse_duration
        import defusedxml.ElementTree as ET
        _ITUNES_NS_L = "http://www.itunes.com/dtds/podcast-1.0.dtd"
        el = ET.fromstring(f"""<item xmlns:itunes="{_ITUNES_NS_L}">
            <itunes:duration>not:a:duration</itunes:duration>
        </item>""")
        assert _parse_duration(el) is None

    def test_no_series_when_no_episode_season(self):
        _ITUNES_NS_L = "http://www.itunes.com/dtds/podcast-1.0.dtd"
        raw = f"""<?xml version="1.0"?>
<rss version="2.0" xmlns:itunes="{_ITUNES_NS_L}">
  <channel><title>T</title>
    <item>
      <guid>https://podcast.example.com/ep/ns</guid>
      <title>No Series</title>
      <link>https://podcast.example.com/ep/ns</link>
      <pubDate>Mon, 01 Jan 2026 00:00:00 +0000</pubDate>
      <enclosure url="https://podcast.example.com/ns.mp3" type="audio/mpeg" length="100000"/>
    </item>
  </channel>
</rss>""".encode()
        items, _ = podcast_parser.parse(1, "https://podcast.example.com/feed.xml", raw)
        assert items[0].series is None

    def test_transcript_http_excluded(self):
        _ITUNES_NS_L = "http://www.itunes.com/dtds/podcast-1.0.dtd"
        _PC_NS_L = "https://podcastindex.org/namespace/1.0"
        raw = f"""<?xml version="1.0"?>
<rss version="2.0" xmlns:itunes="{_ITUNES_NS_L}" xmlns:podcast="{_PC_NS_L}">
  <channel><title>T</title>
    <item>
      <guid>https://podcast.example.com/ep/tr</guid>
      <title>Transcript Test</title>
      <link>https://podcast.example.com/ep/tr</link>
      <pubDate>Mon, 01 Jan 2026 00:00:00 +0000</pubDate>
      <enclosure url="https://podcast.example.com/tr.mp3" type="audio/mpeg" length="100000"/>
      <podcast:transcript url="http://insecure.example.com/tr.txt" type="text/plain"/>
    </item>
  </channel>
</rss>""".encode()
        items, _ = podcast_parser.parse(1, "https://podcast.example.com/feed.xml", raw)
        assert items[0].transcript is None

    def test_invalid_ttl_ignored(self):
        _ITUNES_NS_L = "http://www.itunes.com/dtds/podcast-1.0.dtd"
        raw = f"""<?xml version="1.0"?>
<rss version="2.0" xmlns:itunes="{_ITUNES_NS_L}">
  <channel><title>T</title><ttl>bad</ttl>
    <item>
      <guid>https://podcast.example.com/ep/ttl</guid>
      <title>TTL Test</title>
      <link>https://podcast.example.com/ep/ttl</link>
      <pubDate>Mon, 01 Jan 2026 00:00:00 +0000</pubDate>
      <enclosure url="https://podcast.example.com/ttl.mp3" type="audio/mpeg" length="100000"/>
    </item>
  </channel>
</rss>""".encode()
        _, config = podcast_parser.parse(1, "https://podcast.example.com/feed.xml", raw)
        assert config.min_interval_seconds == 300
