from meridian.application.services.source_type_inference import infer_source_type
from meridian.domain.value_objects.source_type import SourceType


class TestInferSourceType:
    def test_json_extension(self):
        assert infer_source_type("https://example.com/feed.json") == SourceType.MFEED

    def test_mmsp_in_url(self):
        assert (
            infer_source_type("https://example.com/.well-known/mmsp.json")
            == SourceType.MFEED
        )

    def test_atom_extension(self):
        assert infer_source_type("https://example.com/feed.atom") == SourceType.ATOM

    def test_youtube(self):
        assert (
            infer_source_type("https://www.youtube.com/feeds/videos.xml?channel_id=X")
            == SourceType.ATOM
        )

    def test_podcast_in_url(self):
        assert (
            infer_source_type("https://example.com/podcast/feed.xml")
            == SourceType.PODCAST
        )

    def test_rss_extension_default(self):
        assert infer_source_type("https://example.com/feed.rss") == SourceType.RSS

    def test_generic_xml_default(self):
        assert infer_source_type("https://example.com/rss/feed.xml") == SourceType.RSS

    def test_trailing_slash_stripped(self):
        assert infer_source_type("https://example.com/feed.atom/") == SourceType.ATOM

    def test_case_insensitive(self):
        assert infer_source_type("https://EXAMPLE.COM/FEED.ATOM") == SourceType.ATOM
