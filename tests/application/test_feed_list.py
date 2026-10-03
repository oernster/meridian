"""The exported feed list: what it carries, which files read back, which do not.

Export used to write only each feed's address, type and title, so every filter
a user had written was lost on the path the README gives for keeping their
data. Import refused a file saved with a byte order mark and said why in codec
text; it never looked at the `version` key at all.
"""

import codecs
import json

import pytest

from meridian.application.dto.feed_dto import FeedDTO
from meridian.application.services.feed_list import (
    FEED_LIST_VERSION,
    NotAFeedList,
    build_feed_list,
    decode_feed_list,
    feed_list_entries,
)


def _dto(url, **kwargs) -> FeedDTO:
    fields = dict(
        id=1,
        url=url,
        source_type="rss",
        title="T",
        description=None,
        icon=None,
        language=None,
        filter_expr=None,
        unread_count=0,
    )
    return FeedDTO(**{**fields, **kwargs})


class TestBuild:
    def test_every_field_a_feed_needs_to_come_back_is_written(self):
        feed = _dto(
            "https://p.example/x",
            source_type="platform",
            filter_expr='NOT tag:"sponsored"',
            platform_id="example",
            rss_fallback_url="https://p.example/rss",
        )
        assert build_feed_list([feed]) == {
            "version": FEED_LIST_VERSION,
            "feeds": [
                {
                    "url": "https://p.example/x",
                    "source_type": "platform",
                    "title": "T",
                    "filter_expr": 'NOT tag:"sponsored"',
                    "platform_id": "example",
                    "rss_fallback_url": "https://p.example/rss",
                }
            ],
        }

    def test_an_unset_optional_field_is_left_out(self):
        """A feed with nothing extra writes what version 1 always wrote."""
        [entry] = build_feed_list([_dto("https://a/feed", title=None)])["feeds"]
        assert entry == {"url": "https://a/feed", "source_type": "rss", "title": None}

    def test_the_version_stays_one(self):
        """The new members are optional additions, so version 1 still reads."""
        assert FEED_LIST_VERSION == 1


_PAYLOAD = {"version": 1, "feeds": [{"url": "https://e/rss", "title": "Café"}]}


class TestDecode:

    @pytest.mark.parametrize(
        "encode",
        [
            lambda text: text.encode("utf-8"),
            lambda text: codecs.BOM_UTF8 + text.encode("utf-8"),
            lambda text: text.encode("utf-16"),
            lambda text: codecs.BOM_UTF16_BE + text.encode("utf-16-be"),
        ],
        ids=["utf-8", "utf-8 with BOM", "utf-16 LE with BOM", "utf-16 BE with BOM"],
    )
    def test_utf8_and_utf16_files_read(self, encode):
        raw = encode(json.dumps(_PAYLOAD, ensure_ascii=False))
        assert decode_feed_list(raw) == _PAYLOAD

    def test_text_in_another_encoding_is_refused_plainly(self):
        raw = json.dumps(_PAYLOAD, ensure_ascii=False).encode("cp1252")
        with pytest.raises(NotAFeedList) as refused:
            decode_feed_list(raw)
        assert str(refused.value) == "the file is not UTF-8 or UTF-16 text"

    @pytest.mark.parametrize("raw", [b"", b"{not json", b"\xef\xbb\xbf"])
    def test_a_file_that_is_not_json_is_refused_plainly(self, raw):
        with pytest.raises(NotAFeedList) as refused:
            decode_feed_list(raw)
        assert str(refused.value) == "the file is not a Meridian feed list"


class TestEntries:
    def test_the_entries_of_a_version_one_file(self):
        assert feed_list_entries({"version": 1, "feeds": [{"url": "x"}]}) == [
            {"url": "x"}
        ]

    def test_a_file_with_no_version_is_read_as_version_one(self):
        assert feed_list_entries({"feeds": []}) == []

    @pytest.mark.parametrize("version", [2, 99, "1", 1.0, True, None])
    def test_any_other_version_is_refused_and_named(self, version):
        with pytest.raises(NotAFeedList) as refused:
            feed_list_entries({"version": version, "feeds": []})
        assert str(refused.value) == (
            f"the file is feed list version {version!r}; "
            "this Meridian reads version 1"
        )

    @pytest.mark.parametrize(
        "data", [[], "feeds", None, {}, {"feeds": "x"}, {"feeds": {"url": "y"}}]
    )
    def test_anything_but_the_envelope_is_refused_whole(self, data):
        with pytest.raises(NotAFeedList, match="not a Meridian feed list"):
            feed_list_entries(data)
