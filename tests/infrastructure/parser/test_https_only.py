"""Nothing a feed points at is fetched in the clear, whatever format it is in.

The scheme test lives once, in `parser/https_only.py`. These tests hold every
parser to it for the addresses the window draws or plays: thumbnails and media
in all four formats, plus the transcript and caption tracks a document names.
The RSS and Atom thumbnails and every MFEED address were once kept whatever
their scheme, while the documents said they were dropped.
"""

import json

import pytest

from meridian.infrastructure.fetching.parser import (
    atom_parser,
    mfeed_parser,
    podcast_parser,
    rss_parser,
)
from meridian.infrastructure.fetching.parser.https_only import is_https

_FEED_URL = "https://example.com/feed"
_MEDIA_NS = "http://search.yahoo.com/mrss/"
_ATOM_NS = "http://www.w3.org/2005/Atom"
_SECURE = "https://cdn.example.com/a.jpg"
_INSECURE = "http://cdn.example.com/a.jpg"


class TestTheRule:
    @pytest.mark.parametrize("url", [_SECURE, "HTTPS://cdn.example.com/a.jpg"])
    def test_https_in_any_case_is_fetched(self, url):
        assert is_https(url)

    @pytest.mark.parametrize(
        "url", [_INSECURE, "ftp://x/a", "https:/x", "", None, 7, "//x/a.jpg"]
    )
    def test_anything_else_is_not(self, url):
        assert not is_https(url)


def _rss(thumbnail_url: str) -> bytes:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="{_MEDIA_NS}"><channel><title>T</title>
  <item><guid>https://example.com/1</guid><title>I</title>
    <link>https://example.com/1</link>
    <pubDate>Mon, 01 Jan 2026 00:00:00 +0000</pubDate>
    <media:thumbnail url="{thumbnail_url}" width="120" height="90"/>
  </item></channel></rss>""".encode()


def _atom(thumbnail_url: str, grouped: bool) -> bytes:
    thumb = f'<media:thumbnail url="{thumbnail_url}" width="480" height="360"/>'
    body = f"<media:group>{thumb}</media:group>" if grouped else thumb
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="{_ATOM_NS}" xmlns:media="{_MEDIA_NS}"><title>T</title>
  <entry><id>https://example.com/1</id><title>I</title>
    <link rel="alternate" href="https://example.com/1"/>
    <published>2026-01-01T00:00:00Z</published>{body}</entry></feed>""".encode()


class TestThumbnails:
    def test_rss_keeps_an_https_thumbnail(self):
        items, _ = rss_parser.parse(1, _FEED_URL, _rss(_SECURE))
        assert items[0].primary_thumbnail_url() == _SECURE
        assert (items[0].thumbnail[0].width, items[0].thumbnail[0].height) == (
            120,
            90,
        )

    def test_rss_drops_a_plain_http_thumbnail(self):
        items, _ = rss_parser.parse(1, _FEED_URL, _rss(_INSECURE))
        assert items[0].thumbnail == ()

    def test_podcast_drops_a_plain_http_media_thumbnail_it_inherits(self):
        items, _ = podcast_parser.parse(1, _FEED_URL, _rss(_INSECURE))
        assert items[0].thumbnail == ()

    @pytest.mark.parametrize("grouped", [True, False])
    def test_atom_keeps_an_https_thumbnail(self, grouped):
        items, _ = atom_parser.parse(1, _FEED_URL, _atom(_SECURE, grouped))
        assert items[0].primary_thumbnail_url() == _SECURE
        assert (items[0].thumbnail[0].width, items[0].thumbnail[0].height) == (
            480,
            360,
        )

    @pytest.mark.parametrize("grouped", [True, False])
    def test_atom_drops_a_plain_http_thumbnail(self, grouped):
        items, _ = atom_parser.parse(1, _FEED_URL, _atom(_INSECURE, grouped))
        assert items[0].thumbnail == ()

    def test_atom_thumbnail_without_a_size_has_none(self):
        raw = _atom(_SECURE, grouped=False).replace(b' width="480" height="360"', b"")
        items, _ = atom_parser.parse(1, _FEED_URL, raw)
        assert (items[0].thumbnail[0].width, items[0].thumbnail[0].height) == (
            None,
            None,
        )


def _mfeed(**fields) -> bytes:
    item = {
        "id": "https://example.com/1",
        "type": "audio",
        "title": "I",
        "url": "https://example.com/1",
        "published": "2026-01-01T00:00:00Z",
        **fields,
    }
    return json.dumps(
        {"mmsp": "1.0", "id": _FEED_URL, "title": "T", "items": [item]}
    ).encode()


def _parse_mfeed(**fields):
    items, _ = mfeed_parser.parse(1, _FEED_URL, _mfeed(**fields))
    return items[0]


class TestMfeed:
    def test_only_https_media_is_kept(self):
        item = _parse_mfeed(
            media=[
                {"url": "http://cdn.example.com/a.mp3", "mime_type": "audio/mpeg"},
                {"url": "https://cdn.example.com/b.mp3", "mime_type": "audio/mpeg"},
            ]
        )
        assert [m.url for m in item.media] == ["https://cdn.example.com/b.mp3"]

    def test_only_https_thumbnails_are_kept(self):
        item = _parse_mfeed(thumbnail=[{"url": _INSECURE}, {"url": _SECURE}])
        assert [t.url for t in item.thumbnail] == [_SECURE]

    def test_only_https_captions_are_kept(self):
        track = {"mime_type": "text/vtt", "language": "en"}
        item = _parse_mfeed(
            captions=[
                {**track, "url": "http://cdn.example.com/en.vtt"},
                {**track, "url": "https://cdn.example.com/en.vtt"},
            ]
        )
        assert [c.url for c in item.captions] == ["https://cdn.example.com/en.vtt"]

    def test_an_https_transcript_is_kept(self):
        url = "https://cdn.example.com/t.vtt"
        item = _parse_mfeed(transcript={"url": url, "mime_type": "text/vtt"})
        assert item.transcript.url == url

    def test_a_plain_http_transcript_is_dropped(self):
        item = _parse_mfeed(
            transcript={"url": "http://cdn.example.com/t.vtt", "mime_type": "text/vtt"}
        )
        assert item.transcript is None
