"""
Client-side filter evaluator implementing Appendix A ABNF grammar.

filter       = expr
expr         = term *(SP bool-op SP term)
bool-op      = "AND" / "OR"
term         = ["NOT" SP] atom / "(" expr ")"
atom         = type-filter / tag-filter / author-filter / lang-filter /
               duration-filter / date-filter / keyword-filter / rating-filter
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Sequence

from meridian.domain.entities.item import Item
from meridian.domain.value_objects.filter_expression import FilterExpression


class _TokenKind(Enum):
    AND = auto()
    OR = auto()
    NOT = auto()
    LPAREN = auto()
    RPAREN = auto()
    ATOM = auto()
    EOF = auto()


@dataclass(frozen=True, slots=True)
class _Token:
    kind: _TokenKind
    value: str = ""


_ATOM_RE = re.compile(
    r'(?:type|tag|author|lang|duration|published|keyword|rating):'
    r'(?:"[^"]*"|\[[-\d:TZ.,]+\]|[^\s()]+)'
)


def _tokenize(text: str) -> list[_Token]:
    tokens: list[_Token] = []
    i = 0
    while i < len(text):
        if text[i].isspace():
            i += 1
            continue
        if text[i:i + 3] == "AND" and (i + 3 >= len(text) or not text[i + 3].isalnum()):
            tokens.append(_Token(_TokenKind.AND, "AND"))
            i += 3
        elif text[i:i + 2] == "OR" and (i + 2 >= len(text) or not text[i + 2].isalnum()):
            tokens.append(_Token(_TokenKind.OR, "OR"))
            i += 2
        elif text[i:i + 3] == "NOT" and (i + 3 >= len(text) or not text[i + 3].isalnum()):
            tokens.append(_Token(_TokenKind.NOT, "NOT"))
            i += 3
        elif text[i] == "(":
            tokens.append(_Token(_TokenKind.LPAREN, "("))
            i += 1
        elif text[i] == ")":
            tokens.append(_Token(_TokenKind.RPAREN, ")"))
            i += 1
        else:
            m = _ATOM_RE.match(text, i)
            if m:
                tokens.append(_Token(_TokenKind.ATOM, m.group()))
                i = m.end()
            else:
                raise ValueError(f"Unrecognized token at position {i}: {text[i:]!r}")
    tokens.append(_Token(_TokenKind.EOF))
    return tokens


class _Parser:
    def __init__(self, tokens: list[_Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    def _peek(self) -> _Token:
        return self._tokens[self._pos]

    def _consume(self) -> _Token:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def parse_expr(self) -> "_Node":
        left = self._parse_term()
        while self._peek().kind in (_TokenKind.AND, _TokenKind.OR):
            op = self._consume().kind
            right = self._parse_term()
            left = _BoolNode(op, left, right)
        return left

    def _parse_term(self) -> "_Node":
        if self._peek().kind == _TokenKind.NOT:
            self._consume()
            inner = self._parse_term()
            return _NotNode(inner)
        if self._peek().kind == _TokenKind.LPAREN:
            self._consume()
            node = self.parse_expr()
            if self._peek().kind != _TokenKind.RPAREN:
                raise ValueError("Expected closing parenthesis")
            self._consume()
            return node
        if self._peek().kind == _TokenKind.ATOM:
            return _AtomNode(self._consume().value)
        raise ValueError(f"Unexpected token: {self._peek()}")


class _Node:
    def evaluate(self, item: Item) -> bool:
        raise NotImplementedError


@dataclass
class _BoolNode(_Node):
    op: _TokenKind
    left: _Node
    right: _Node

    def evaluate(self, item: Item) -> bool:
        if self.op == _TokenKind.AND:
            return self.left.evaluate(item) and self.right.evaluate(item)
        return self.left.evaluate(item) or self.right.evaluate(item)


@dataclass
class _NotNode(_Node):
    inner: _Node

    def evaluate(self, item: Item) -> bool:
        return not self.inner.evaluate(item)


@dataclass
class _AtomNode(_Node):
    raw: str

    def evaluate(self, item: Item) -> bool:
        field, _, value = self.raw.partition(":")
        value = value.strip('"')
        match field:
            case "type":
                return item.type.value == value
            case "tag":
                return value in item.tags
            case "author":
                return any(a.name == value for a in item.authors)
            case "lang":
                return item.language == value
            case "duration":
                return _eval_range(item.duration or 0, value)
            case "published":
                return _eval_date_range(item.published, value)
            case "keyword":
                haystack = f"{item.title} {item.description or ''}".lower()
                return value.lower() in haystack
            case "rating":
                return (
                    item.content_rating is not None
                    and item.content_rating.rating == value
                )
            case _:
                return False


def _eval_range(actual: int | float, expr: str) -> bool:
    if expr.startswith(">="):
        return actual >= float(expr[2:])
    if expr.startswith("<="):
        return actual <= float(expr[2:])
    if expr.startswith("["):
        lo, hi = expr.strip("[]").split(",")
        return float(lo) <= actual <= float(hi)
    return False


def _eval_date_range(actual: datetime, expr: str) -> bool:
    if expr.startswith(">="):
        return actual >= datetime.fromisoformat(expr[2:])
    if expr.startswith("<="):
        return actual <= datetime.fromisoformat(expr[2:])
    if expr.startswith("["):
        lo, hi = expr.strip("[]").split(",")
        return datetime.fromisoformat(lo) <= actual <= datetime.fromisoformat(hi)
    return False


class FilterEvaluator:
    def __init__(self, expression: FilterExpression) -> None:
        self._expression = expression
        tokens = _tokenize(expression.expr)
        parser = _Parser(tokens)
        self._ast = parser.parse_expr()

    def matches(self, item: Item) -> bool:
        return self._ast.evaluate(item)

    def filter(self, items: Sequence[Item]) -> list[Item]:
        return [i for i in items if self.matches(i)]
