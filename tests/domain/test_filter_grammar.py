"""The Appendix A filter grammar: what is refused, how bounds compare, the terms.

Three things were wrong and each has its own class. A filter with text left
over after a complete expression was accepted and only its prefix evaluated.
A date bound written without an offset or as a date alone could not be
compared with a stored time, which broke the feed rather than the filter. An
item with no duration matched `duration:<=60` because a missing duration was
read as zero, though the specification's own conformance suite says absent
means no match.
"""

from datetime import datetime, timedelta, timezone

import pytest

from meridian.domain.entities.item import Item
from meridian.domain.services.filter_evaluator import FilterEvaluator
from meridian.domain.services.filter_grammar import conjunction_terms
from meridian.domain.value_objects.filter_expression import (
    FilterExpression,
    FilterSyntaxError,
)
from meridian.domain.value_objects.item_type import ItemType
from meridian.domain.value_objects.media import ContentRating

_PLUS_FIVE = timezone(timedelta(hours=5))


def _item(**kwargs) -> Item:
    defaults = dict(
        item_id="https://example.com/1",
        type=ItemType.ARTICLE,
        title="Hello World",
        url="https://example.com/1",
        published=datetime(2026, 3, 15, 12, 0, tzinfo=timezone.utc),
    )
    return Item(**{**defaults, **kwargs})


def _eval(expr: str, item: Item) -> bool:
    return FilterEvaluator(FilterExpression(expr)).matches(item)


class TestTrailingInputIsRefused:
    @pytest.mark.parametrize(
        "expr",
        [
            "type:article type:video",
            'tag:"a") OR tag:"b"',
            "type:video )",
            'tag:"b" tag:"zzz"',
            "(type:video) lang:en",
        ],
    )
    def test_text_after_a_complete_expression_is_refused(self, expr):
        with pytest.raises(FilterSyntaxError, match="after a complete"):
            FilterEvaluator(FilterExpression(expr))

    @pytest.mark.parametrize("expr", ["type:video AND", "NOT", "(", "AND type:video"])
    def test_an_incomplete_expression_is_refused(self, expr):
        with pytest.raises(FilterSyntaxError):
            FilterEvaluator(FilterExpression(expr))

    def test_an_unknown_word_is_refused_with_its_position(self):
        with pytest.raises(FilterSyntaxError, match="position 15"):
            FilterEvaluator(FilterExpression("type:video OR banana"))

    def test_a_syntax_error_is_still_a_value_error(self):
        """Callers that caught ValueError before keep working."""
        assert issubclass(FilterSyntaxError, ValueError)


class TestValuesAreCheckedWhenTheFilterIsRead:
    @pytest.mark.parametrize(
        "expr",
        [
            "duration:>=abc",
            "duration:<=",
            "duration:[1,2,3]",
            "duration:[1]",
            "duration:60",
            "published:>=notadate",
            "published:[2026-01-01]",
            "published:2026-01-01",
        ],
    )
    def test_a_bound_that_is_not_a_number_or_a_time_is_refused(self, expr):
        with pytest.raises(FilterSyntaxError, match="not a valid"):
            FilterEvaluator(FilterExpression(expr))


class TestDurationNeedsADuration:
    @pytest.mark.parametrize(
        "expr", ["duration:<=60", "duration:>=0", "duration:[0,7200]"]
    )
    def test_an_item_with_no_duration_matches_no_duration_filter(self, expr):
        assert not _eval(expr, _item(duration=None))

    def test_not_turns_the_absence_into_a_match(self):
        assert _eval("NOT duration:<=60", _item(duration=None))

    def test_a_zero_duration_is_still_a_duration(self):
        assert _eval("duration:<=60", _item(duration=0))

    def test_fractional_bounds_are_numbers(self):
        assert _eval("duration:[0.5,1.5]", _item(duration=1))


class TestPublishedBoundsCompareInstants:
    def test_a_bound_without_an_offset_is_read_as_utc(self):
        item = _item(published=datetime(2026, 1, 1, 0, 30, tzinfo=timezone.utc))
        assert _eval("published:>=2026-01-01T00:00:00", item)
        assert not _eval("published:>=2026-01-01T01:00:00", item)

    def test_a_date_alone_as_a_lower_bound_is_the_start_of_that_day(self):
        item = _item(published=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc))
        assert _eval("published:>=2026-01-01", item)
        assert not _eval("published:>=2026-01-02", item)

    def test_a_date_alone_as_an_upper_bound_takes_in_the_whole_day(self):
        late = _item(published=datetime(2026, 3, 15, 23, 59, tzinfo=timezone.utc))
        assert _eval("published:<=2026-03-15", late)
        assert not _eval("published:<=2026-03-14", late)

    def test_a_range_of_dates_alone_takes_in_both_whole_days(self):
        late = _item(published=datetime(2026, 3, 15, 23, 59, tzinfo=timezone.utc))
        assert _eval("published:[2026-03-15,2026-03-15]", late)

    def test_an_offset_bound_is_compared_as_an_instant(self):
        """10:00+05:00 is 05:00Z, which is before 06:00Z."""
        item = _item(published=datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc))
        assert _eval("published:>=2026-01-01T10:00:00+05:00", item)
        assert not _eval("published:<=2026-01-01T10:00:00+05:00", item)

    def test_a_range_may_carry_offsets(self):
        item = _item(published=datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc))
        assert _eval(
            "published:[2026-01-01T10:00:00+05:00,2026-01-01T12:00:00+05:00]", item
        )

    def test_an_item_stored_without_an_offset_is_read_as_utc(self):
        item = _item(published=datetime(2026, 1, 1, 6, 0))  # noqa: DTZ001
        assert _eval("published:>=2026-01-01T06:00:00Z", item)
        assert not _eval("published:>=2026-01-01T06:00:01Z", item)

    def test_an_item_in_another_zone_is_compared_as_an_instant(self):
        item = _item(published=datetime(2026, 1, 1, 10, 0, tzinfo=_PLUS_FIVE))
        assert _eval("published:<=2026-01-01T05:00:00Z", item)


class TestTheSpecificationsOwnExamples:
    """MMSP Appendix A.2, verbatim."""

    def test_example_one(self):
        assert _eval(
            "type:video AND duration:>=300",
            _item(type=ItemType.VIDEO, duration=300),
        )

    def test_example_two(self):
        assert _eval(
            'NOT tag:"sponsored" AND (type:article OR type:newsletter)', _item()
        )

    def test_example_three(self):
        item = _item(title="climate news", language="en")
        assert _eval(
            'keyword:"climate" AND lang:en AND published:>=2026-01-01T00:00:00Z',
            item,
        )

    def test_example_three_excludes_the_year_before(self):
        item = _item(
            title="climate news",
            language="en",
            published=datetime(2025, 12, 31, 23, 59, tzinfo=timezone.utc),
        )
        assert not _eval(
            'keyword:"climate" AND lang:en AND published:>=2026-01-01T00:00:00Z',
            item,
        )

    def test_rating_and_author_still_match(self):
        item = _item(content_rating=ContentRating(rating="teen"))
        assert _eval("rating:teen", item)


class TestConjunctionTerms:
    def test_a_conjunction_splits_into_its_terms(self):
        assert conjunction_terms("type:video AND lang:en") == ["type:video", "lang:en"]

    def test_and_inside_quotes_is_part_of_the_term(self):
        assert conjunction_terms('keyword:"salt AND pepper" AND lang:en') == [
            'keyword:"salt AND pepper"',
            "lang:en",
        ]

    def test_and_inside_parentheses_is_part_of_the_term(self):
        assert conjunction_terms('(type:video AND lang:en) AND NOT tag:"x"') == [
            "(type:video AND lang:en)",
            'NOT tag:"x"',
        ]

    def test_a_top_level_or_keeps_the_expression_whole(self):
        """Toggling one side of an OR off would change what the rest means."""
        expr = "type:video AND lang:en OR type:audio"
        assert conjunction_terms(expr) == [expr]

    def test_an_or_inside_parentheses_still_splits(self):
        assert conjunction_terms("(type:video OR type:audio) AND lang:en") == [
            "(type:video OR type:audio)",
            "lang:en",
        ]

    def test_a_single_term_is_one_term(self):
        assert conjunction_terms("  type:video  ") == ["type:video"]

    def test_an_invalid_expression_raises(self):
        with pytest.raises(FilterSyntaxError):
            conjunction_terms("type:video type:audio")
