import pytest
from datetime import datetime, timezone

from meridian.domain.entities.item import Item
from meridian.domain.services.deduplication import deduplicate
from meridian.domain.services.filter_evaluator import FilterEvaluator
from meridian.domain.value_objects.filter_expression import FilterExpression
from meridian.domain.value_objects.item_type import ItemType
from meridian.domain.value_objects.media import Author, ContentRating


def _item(**kwargs) -> Item:
    defaults = dict(
        item_id="https://example.com/1",
        type=ItemType.ARTICLE,
        title="Hello World",
        url="https://example.com/1",
        published=datetime(2026, 3, 15, tzinfo=timezone.utc),
    )
    return Item(**{**defaults, **kwargs})


def _eval(expr: str, item: Item) -> bool:
    return FilterEvaluator(FilterExpression(expr)).matches(item)


class TestTypeFilter:
    def test_matches_correct_type(self):
        assert _eval("type:article", _item(type=ItemType.ARTICLE))

    def test_no_match_wrong_type(self):
        assert not _eval("type:video", _item(type=ItemType.ARTICLE))


class TestTagFilter:
    def test_matches_tag(self):
        item = _item(tags=("tech", "python"))
        assert _eval('tag:"tech"', item)

    def test_no_match_absent_tag(self):
        item = _item(tags=("tech",))
        assert not _eval('tag:"python"', item)


class TestAuthorFilter:
    def test_matches_author(self):
        item = _item(authors=(Author(name="Alice"),))
        assert _eval('author:"Alice"', item)

    def test_no_match_wrong_author(self):
        item = _item(authors=(Author(name="Bob"),))
        assert not _eval('author:"Alice"', item)


class TestLangFilter:
    def test_matches_language(self):
        item = _item(language="en")
        assert _eval("lang:en", item)

    def test_no_match_null_language(self):
        assert not _eval("lang:en", _item())


class TestDurationFilter:
    def test_gte(self):
        item = _item(duration=600)
        assert _eval("duration:>=300", item)
        assert not _eval("duration:>=700", item)

    def test_lte(self):
        item = _item(duration=200)
        assert _eval("duration:<=300", item)
        assert not _eval("duration:<=100", item)

    def test_range(self):
        item = _item(duration=400)
        assert _eval("duration:[300,500]", item)
        assert not _eval("duration:[500,800]", item)


class TestPublishedFilter:
    def test_gte(self):
        item = _item(published=datetime(2026, 6, 1, tzinfo=timezone.utc))
        assert _eval("published:>=2026-01-01T00:00:00+00:00", item)
        assert not _eval("published:>=2027-01-01T00:00:00+00:00", item)


class TestKeywordFilter:
    def test_matches_title(self):
        item = _item(title="Python 3.13 release notes")
        assert _eval('keyword:"python"', item)

    def test_matches_description(self):
        item = _item(description="This is about climate change")
        assert _eval('keyword:"climate"', item)

    def test_case_insensitive(self):
        assert _eval('keyword:"hello"', _item(title="Hello World"))


class TestRatingFilter:
    def test_matches_rating(self):
        item = _item(content_rating=ContentRating(rating="explicit"))
        assert _eval("rating:explicit", item)

    def test_no_match_no_rating(self):
        assert not _eval("rating:explicit", _item())


class TestBooleanOps:
    def test_and_both_true(self):
        item = _item(type=ItemType.VIDEO, duration=600)
        assert _eval("type:video AND duration:>=300", item)

    def test_and_one_false(self):
        item = _item(type=ItemType.VIDEO, duration=100)
        assert not _eval("type:video AND duration:>=300", item)

    def test_or_one_true(self):
        item = _item(type=ItemType.ARTICLE)
        assert _eval("type:video OR type:article", item)

    def test_not(self):
        item = _item(tags=("sponsored",))
        assert not _eval('NOT tag:"sponsored"', item)
        assert _eval('NOT tag:"paid"', item)

    def test_nested_parens(self):
        item = _item(type=ItemType.ARTICLE, tags=("sponsored",))
        assert not _eval(
            'NOT tag:"sponsored" AND (type:article OR type:newsletter)', item
        )

    def test_complex_expression(self):
        item = _item(type=ItemType.ARTICLE, language="en", title="climate future")
        assert _eval('keyword:"climate" AND lang:en AND type:article', item)


class TestFilterMethod:
    def test_filter_list(self):
        items = [
            _item(item_id="https://example.com/1", type=ItemType.VIDEO),
            _item(item_id="https://example.com/2", type=ItemType.ARTICLE),
        ]
        result = FilterEvaluator(FilterExpression("type:video")).filter(items)
        assert len(result) == 1
        assert result[0].type == ItemType.VIDEO


class TestInvalidTokens:
    def test_bad_token_raises(self):
        with pytest.raises(ValueError):
            FilterEvaluator(FilterExpression("INVALID_TOKEN_HERE"))

    def test_unclosed_paren_raises(self):
        with pytest.raises((ValueError, Exception)):
            FilterEvaluator(FilterExpression("(type:video"))

    def test_unexpected_token_at_term(self):
        from meridian.domain.services.filter_evaluator import (
            _Parser,
            _Token,
            _TokenKind,
        )

        tokens = [_Token(_TokenKind.AND, "AND"), _Token(_TokenKind.EOF)]
        parser = _Parser(tokens)
        with pytest.raises(ValueError, match="Unexpected token"):
            parser.parse_expr()

    def test_node_base_not_implemented(self):
        from meridian.domain.services.filter_evaluator import _Node

        with pytest.raises(NotImplementedError):
            _Node().evaluate(_item())

    def test_atom_node_unknown_field(self):
        from meridian.domain.services.filter_evaluator import _AtomNode

        node = _AtomNode("unknown:value")
        assert not node.evaluate(_item())

    def test_eval_range_no_match(self):
        from meridian.domain.services.filter_evaluator import _eval_range

        assert not _eval_range(100, "100")

    def test_eval_date_range_lte(self):
        item = _item(published=datetime(2026, 1, 1, tzinfo=timezone.utc))
        assert _eval("published:<=2027-01-01T00:00:00+00:00", item)

    def test_eval_date_range_bracket(self):
        item = _item(published=datetime(2026, 6, 1, tzinfo=timezone.utc))
        assert _eval(
            "published:[2026-01-01T00:00:00+00:00,2026-12-31T00:00:00+00:00]", item
        )

    def test_eval_date_range_no_match(self):
        from meridian.domain.services.filter_evaluator import _eval_date_range

        actual = datetime(2026, 1, 1, tzinfo=timezone.utc)
        assert not _eval_date_range(actual, "100")


class TestDeduplication:
    def test_dedup_by_canonical_url(self):
        items = [
            _item(
                item_id="https://example.com/1", canonical_url="https://canonical.com/x"
            ),
            _item(
                item_id="https://example.com/2", canonical_url="https://canonical.com/x"
            ),
            _item(
                item_id="https://example.com/3", canonical_url="https://canonical.com/y"
            ),
        ]
        result = deduplicate(items)
        assert len(result) == 2

    def test_dedup_by_item_id(self):
        items = [
            _item(item_id="https://example.com/1"),
            _item(item_id="https://example.com/1"),
            _item(item_id="https://example.com/2"),
        ]
        result = deduplicate(items)
        assert len(result) == 2

    def test_no_duplicates_unchanged(self):
        items = [
            _item(item_id="https://example.com/1"),
            _item(item_id="https://example.com/2"),
        ]
        assert len(deduplicate(items)) == 2
