"""Reading a filter written in the MMSP Appendix A grammar.

    filter       = expr
    expr         = term *(SP bool-op SP term)
    bool-op      = "AND" / "OR"
    term         = ["NOT" SP] atom / "(" expr ")"

A filter is read whole or refused: text left after a complete expression is an
error, where it used to be dropped while its first part was evaluated. The
operators apply left to right with no precedence between AND and OR; the
specification is silent on precedence and that reading is kept.

`conjunction_terms` is the one place a filter is cut into the terms its
top-level AND joins; those are the filter dialog's rows. It cuts on the
parser's own tokens, so an AND inside quotes or parentheses stays inside its
term.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto

from meridian.domain.services.filter_atoms import ATOM_READERS, ItemTest, read_atom
from meridian.domain.value_objects.filter_expression import FilterSyntaxError


class _Kind(Enum):
    CONJUNCTION = auto()
    DISJUNCTION = auto()
    NEGATION = auto()
    LPAREN = auto()
    RPAREN = auto()
    ATOM = auto()
    END = auto()


@dataclass(frozen=True, slots=True)
class _Token:
    kind: _Kind
    start: int
    end: int


_KEYWORDS = {"AND": _Kind.CONJUNCTION, "OR": _Kind.DISJUNCTION, "NOT": _Kind.NEGATION}
_PUNCTUATION = {"(": _Kind.LPAREN, ")": _Kind.RPAREN}
_KEYWORD_RE = re.compile(r"(AND|OR|NOT)(?![A-Za-z0-9])")
_ATOM_RE = re.compile(
    "(?:" + "|".join(ATOM_READERS) + "):" + r'(?:"[^"]*"|\[[^\]\s]*\]|[^\s()]+)'
)


def _tokenize(text: str) -> list[_Token]:
    tokens: list[_Token] = []
    i = 0
    while i < len(text):
        if text[i].isspace():
            i += 1
            continue
        if text[i] in _PUNCTUATION:
            tokens.append(_Token(_PUNCTUATION[text[i]], i, i + 1))
            i += 1
            continue
        match = _KEYWORD_RE.match(text, i) or _ATOM_RE.match(text, i)
        if match is None:
            raise FilterSyntaxError(
                f"Unrecognised text at position {i + 1}: {text[i:]!r}"
            )
        kind = _KEYWORDS.get(match.group(), _Kind.ATOM)
        tokens.append(_Token(kind, i, match.end()))
        i = match.end()
    tokens.append(_Token(_Kind.END, len(text), len(text)))
    return tokens


class _Parser:
    def __init__(self, text: str) -> None:
        self._text = text
        self._tokens = _tokenize(text)
        self._pos = 0

    def parse(self) -> ItemTest:
        test = self._expr()
        if self._peek().kind != _Kind.END:
            rest = self._text[self._peek().start :]
            raise FilterSyntaxError(f"Unexpected {rest!r} after a complete expression")
        return test

    def _peek(self) -> _Token:
        return self._tokens[self._pos]

    def _take(self) -> _Token:
        token = self._tokens[self._pos]
        self._pos += 1
        return token

    def _expr(self) -> ItemTest:
        left = self._term()
        while self._peek().kind in (_Kind.CONJUNCTION, _Kind.DISJUNCTION):
            left = _join(self._take().kind, left, self._term())
        return left

    def _term(self) -> ItemTest:
        token = self._take()
        if token.kind == _Kind.NEGATION:
            inner = self._term()
            return lambda item: not inner(item)
        if token.kind == _Kind.LPAREN:
            inner = self._expr()
            if self._take().kind != _Kind.RPAREN:
                raise FilterSyntaxError("A parenthesis is opened and never closed")
            return inner
        if token.kind == _Kind.ATOM:
            return read_atom(self._text[token.start : token.end])
        found = self._text[token.start :] or "the end of the filter"
        raise FilterSyntaxError(f"Expected a filter term but found {found!r}")


def _join(kind: _Kind, left: ItemTest, right: ItemTest) -> ItemTest:
    if kind == _Kind.CONJUNCTION:
        return lambda item: left(item) and right(item)
    return lambda item: left(item) or right(item)


def parse_filter(text: str) -> ItemTest:
    """The test a whole filter stands for; raises FilterSyntaxError otherwise."""
    return _Parser(text).parse()


def conjunction_terms(text: str) -> list[str]:
    """The terms the filter's top-level AND joins, each as written.

    A filter with a top-level OR is one term: since the operators apply left
    to right, removing one term beside an OR would change what the rest means.
    Raises FilterSyntaxError for a filter that does not parse.
    """
    parse_filter(text)
    terms: list[str] = []
    depth = 0
    first: _Token | None = None
    last: _Token | None = None
    for token in _tokenize(text):
        if depth == 0 and token.kind == _Kind.DISJUNCTION:
            return [text.strip()]
        if depth == 0 and token.kind in (_Kind.CONJUNCTION, _Kind.END):
            terms.append(text[first.start : last.end])
            first = None
            continue
        depth += {_Kind.LPAREN: 1, _Kind.RPAREN: -1}.get(token.kind, 0)
        first = first or token
        last = token
    return terms
