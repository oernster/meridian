"""Client-side filtering of items by an MMSP Appendix A filter expression.

The grammar is read in `filter_grammar` and its atoms in `filter_atoms`; this
is the face the application uses. Building an evaluator reads the whole
filter, so an invalid one raises `FilterSyntaxError` here rather than while
items are being tested.
"""

from __future__ import annotations

from typing import Sequence

from meridian.domain.entities.item import Item
from meridian.domain.services.filter_grammar import parse_filter
from meridian.domain.value_objects.filter_expression import FilterExpression


class FilterEvaluator:
    def __init__(self, expression: FilterExpression) -> None:
        self._expression = expression
        self._test = parse_filter(expression.expr)

    def matches(self, item: Item) -> bool:
        return self._test(item)

    def filter(self, items: Sequence[Item]) -> list[Item]:
        return [i for i in items if self.matches(i)]
