"""The filter use cases the window needs: checking one and cutting it into terms.

Both read the filter with the domain's own grammar, so the filter dialog never
splits a filter differently from how it is evaluated. It used to split on the
literal text " AND ", which cut a quoted `keyword:"salt AND pepper"` in two.
"""

from __future__ import annotations

from meridian.domain.services.filter_grammar import conjunction_terms, parse_filter
from meridian.domain.value_objects.filter_expression import FilterSyntaxError


def check_filter(expression: str) -> None:
    """Raise FilterSyntaxError, saying where, unless the filter can be used."""
    parse_filter(expression)


def filter_terms(expression: str) -> list[str]:
    """The rows the filter dialog shows: one per term of a top-level AND.

    A filter that cannot be read is one row holding all of it, so it can still
    be seen and switched off; nothing the user wrote is dropped.
    """
    text = expression.strip()
    if not text:
        return []
    try:
        return conjunction_terms(text)
    except FilterSyntaxError:
        return [text]
