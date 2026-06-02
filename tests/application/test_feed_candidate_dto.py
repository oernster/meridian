import dataclasses

import pytest

from meridian.application.dto.feed_candidate_dto import FeedCandidateDTO


def _make() -> FeedCandidateDTO:
    return FeedCandidateDTO(
        url="https://example.com/feed",
        title="Example",
        description="A feed",
        favicon_url="https://example.com/fav.ico",
        source_type="rss",
    )


class TestFeedCandidateDTO:
    def test_defaults(self):
        dto = _make()
        assert dto.is_subscribed is False

    def test_frozen(self):
        dto = _make()
        with pytest.raises(dataclasses.FrozenInstanceError):
            dto.url = "https://other.com"  # type: ignore[misc]

    def test_replace_is_subscribed(self):
        dto = _make()
        updated = dataclasses.replace(dto, is_subscribed=True)
        assert updated.is_subscribed is True
        assert dto.is_subscribed is False

    def test_optional_fields_none(self):
        dto = FeedCandidateDTO(
            url="https://example.com/feed",
            title=None,
            description=None,
            favicon_url=None,
            source_type="rss",
        )
        assert dto.title is None
        assert dto.description is None
        assert dto.favicon_url is None

    def test_slots(self):
        dto = _make()
        assert not hasattr(dto, "__dict__")
