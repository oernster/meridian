"""Meridian against the MMSP specification it is the reference implementation of.

The normative rules are expressed twice: once in the MMSP-Spec repository, as
JSON Schemas and a conformance suite; once here, as a parser. Nothing
checked that the two agreed, so this parser could drift from the specification
it is the reference for and both repositories would stay green.

The file has two halves.

The first always runs and pins meridian's own expression of the versioning
rule (Section 5.7) and the single place the protocol version now lives.

The second runs only when the MMSP-Spec repository is checked out beside this
one, at `../MMSP-Spec` or wherever `MMSP_SPEC_DIR` points; it reads its
published artefacts directly. It skips with a stated reason elsewhere rather
than being silently absent. That keeps the dependency one-directional and
needs no vendored copy of the schemas, which would be a third expression of
the same rules and a third thing to drift.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import pytest

from meridian.domain.value_objects.poll_config import POLL_FLOOR_SECONDS
from meridian.infrastructure.fetching import http_fetcher
from meridian.infrastructure.fetching.mmsp import (
    PROTOCOL_MAJOR,
    PROTOCOL_VERSION,
    accepts_document_version,
)
from meridian.infrastructure.fetching.parser import mfeed_parser

_SPEC_DIR = Path(
    os.environ.get("MMSP_SPEC_DIR") or Path(__file__).resolve().parents[3] / "MMSP-Spec"
)
_SCHEMA_DIR = _SPEC_DIR / "spec" / "schema"
_EXAMPLE_DIR = _SPEC_DIR / "spec" / "examples"

_HAVE_SPEC = _SCHEMA_DIR.is_dir() and _EXAMPLE_DIR.is_dir()
_needs_spec = pytest.mark.skipif(
    not _HAVE_SPEC,
    reason=(
        f"MMSP-Spec not found at {_SPEC_DIR}. Check it out beside this "
        "repository (or set MMSP_SPEC_DIR) to run the conformance checks."
    ),
)


def _feed(version: object = PROTOCOL_VERSION) -> dict:
    document = {
        "mmsp": version,
        "id": "https://example.com/feed",
        "title": "Test Feed",
        "feed_url": "https://example.com/feed",
        "items": [],
    }
    if version is None:
        del document["mmsp"]
    return document


# ── the versioning rule, as this client expresses it ───────────────────────


@pytest.mark.parametrize("version", ["1.0", "1.1", "1.99", "1.0000"])
def test_any_minor_of_the_major_is_accepted(version: str) -> None:
    """Section 5.7: a 1.x client accepts any 1.MINOR."""
    assert accepts_document_version(version) is True


@pytest.mark.parametrize(
    "version", ["2.0", "0.1", "1", "1.", ".1", "1.x", "not-a-version", "", None, 1.0]
)
def test_anything_else_is_refused(version: object) -> None:
    """A document that has not said what it is cannot be assumed to be 1.x."""
    assert accepts_document_version(version) is False


def test_a_future_major_is_refused_by_the_parser() -> None:
    raw = json.dumps(_feed("2.0")).encode("utf-8")

    with pytest.raises(ValueError, match="Unsupported MMSP document version"):
        mfeed_parser.parse(1, "https://example.com/feed", raw)


def test_a_document_that_declares_no_version_is_refused() -> None:
    raw = json.dumps(_feed(None)).encode("utf-8")

    with pytest.raises(ValueError, match="Unsupported MMSP document version"):
        mfeed_parser.parse(1, "https://example.com/feed", raw)


def test_a_later_minor_is_still_read() -> None:
    """Forward compatibility runs across minors, so 1.99 must still parse."""
    raw = json.dumps(_feed("1.99")).encode("utf-8")

    items, _ = mfeed_parser.parse(1, "https://example.com/feed", raw)

    assert items == []


def test_the_user_agent_carries_the_protocol_version() -> None:
    """It used to be the only place the version appeared."""
    assert http_fetcher._USER_AGENT == f"MMSP/{PROTOCOL_VERSION}"


# ── Sections 6.15 and 5.6: one bad item never costs the feed ───────────────

_GOOD_ITEM = {
    "id": "https://example.com/item/good",
    "type": "article",
    "title": "Good",
    "url": "https://example.com/item/good",
    "published": "2026-01-01T00:00:00Z",
}


def _beside_good(bad: dict, **manifest) -> list:
    document = {**_feed(), "items": [_GOOD_ITEM, bad], **manifest}
    items, _ = mfeed_parser.parse(1, "https://example.com/feed", json.dumps(document))
    return items


@pytest.mark.parametrize("member", ["id", "type", "title", "url", "published"])
def test_an_item_missing_a_required_field_is_skipped_alone(member: str) -> None:
    """6.15: MUST skip that single item and MUST continue."""
    bad = {**_GOOD_ITEM, "id": "x:2", "title": "Bad"}
    del bad[member]
    assert [i.title for i in _beside_good(bad)] == ["Good"]


@pytest.mark.parametrize(
    ("member", "value"),
    [
        ("title", 7),
        ("id", 7),
        ("url", ["https://x"]),
        ("type", None),
        ("published", 20260101),
        ("published", "yesterday"),
    ],
)
def test_an_item_with_a_required_field_of_the_wrong_kind_is_skipped(
    member: str, value: object
) -> None:
    bad = {**_GOOD_ITEM, "id": "x:3", member: value}
    assert [i.title for i in _beside_good(bad)] == ["Good"]


def test_an_item_that_is_not_an_object_is_skipped() -> None:
    assert [i.title for i in _beside_good("not an item")] == ["Good"]


@pytest.mark.parametrize(
    ("member", "value", "read"),
    [
        ("updated", "yesterday", lambda i: i.updated),
        ("expires", 5, lambda i: i.expires),
        ("description", 5, lambda i: i.description),
        ("language", 12345, lambda i: i.language),
        ("duration", "not-an-integer", lambda i: i.duration),
        ("duration", True, lambda i: i.duration),
        ("live_status", ["live"], lambda i: i.live_status),
        ("series", {"title": "no id"}, lambda i: i.series),
        ("content_rating", "teen", lambda i: i.content_rating),
        ("paywall", {"preview_available": True}, lambda i: i.paywall),
        ("transcript", {"url": "https://x/t.txt"}, lambda i: i.transcript),
        ("geo_restriction", {"type": "allowlist"}, lambda i: i.geo_restriction),
        (
            "geo_restriction",
            {"type": "allowlist", "regions": "GB"},
            lambda i: i.geo_restriction,
        ),
    ],
)
def test_a_malformed_optional_field_is_dropped_and_the_item_kept(
    member: str, value: object, read
) -> None:
    """6.15: ignore that field and render the item without it."""
    [_, kept] = _beside_good({**_GOOD_ITEM, "id": "x:4", member: value})
    assert kept.title == "Good" and read(kept) is None


@pytest.mark.parametrize(
    ("member", "entries", "read"),
    [
        ("media", [{"url": "https://x/a.mp3"}], lambda i: i.media),
        ("thumbnail", [{"width": 3}], lambda i: i.thumbnail),
        ("authors", [{"url": "https://x"}], lambda i: i.authors),
        ("chapters", [{"title": "no start"}], lambda i: i.chapters),
        ("captions", [{"url": "https://x/c.vtt"}], lambda i: i.captions),
        ("tags", [7, None], lambda i: i.tags),
        ("media", "not a list", lambda i: i.media),
    ],
)
def test_a_malformed_entry_in_a_list_is_dropped_alone(
    member: str, entries: object, read
) -> None:
    [_, kept] = _beside_good({**_GOOD_ITEM, "id": "x:5", member: entries})
    assert read(kept) == ()


def test_the_good_entries_beside_a_bad_one_are_kept() -> None:
    media = [
        {"url": "https://x/a.mp3"},
        {"url": "https://x/b.mp3", "mime_type": "audio/mpeg"},
    ]
    [_, kept] = _beside_good({**_GOOD_ITEM, "id": "x:6", "media": media})
    assert [m.url for m in kept.media] == ["https://x/b.mp3"]


def test_an_unknown_member_and_an_unknown_type_are_not_reasons_to_skip() -> None:
    bad = {**_GOOD_ITEM, "id": "x:7", "type": "hologram", "x-future": {"a": 1}}
    [_, kept] = _beside_good(bad)
    assert kept.type.value == "article"


@pytest.mark.parametrize(
    "poll", [None, "often", {"min_interval_seconds": "600"}, {"ttl_seconds": "x"}]
)
def test_a_malformed_poll_object_falls_back_to_the_defaults(poll: object) -> None:
    document = {**_feed(), "items": [_GOOD_ITEM], "poll": poll}
    items, config = mfeed_parser.parse(1, "https://e/f", json.dumps(document))
    assert len(items) == 1
    assert config.min_interval_seconds == POLL_FLOOR_SECONDS
    assert config.ttl_seconds is None


def test_a_feed_title_that_is_not_text_is_not_used() -> None:
    [good] = _beside_good({}, title=7)[:1]
    assert good.source.feed_title is None


def test_the_number_of_skipped_items_is_recorded(caplog) -> None:
    """6.15 Observability: SHOULD record how many items it skipped."""
    with caplog.at_level(logging.WARNING, logger=mfeed_parser.__name__):
        _beside_good({"title": "no id"})
    assert "skipped 1 of 2 items" in caplog.text


def test_items_that_is_not_an_array_rejects_the_manifest() -> None:
    """5.6: a REQUIRED manifest field of the wrong type rejects the manifest."""
    document = {**_feed(), "items": None}
    with pytest.raises(ValueError, match="items"):
        mfeed_parser.parse(1, "https://e/f", json.dumps(document))


def test_a_manifest_that_is_not_an_object_is_rejected() -> None:
    with pytest.raises(ValueError, match="not an MMSP feed"):
        mfeed_parser.parse(1, "https://e/f", b"[]")


# ── against the specification's own artefacts ──────────────────────────────


@_needs_spec
def test_the_declared_version_matches_the_published_schema() -> None:
    """A protocol revision in the spec must not pass unnoticed here."""
    schema = json.loads(
        (_SCHEMA_DIR / "mmsp-feed.schema.json").read_text(encoding="utf-8")
    )

    published = schema["$id"].rstrip("/").split("/")[-2]

    assert published == PROTOCOL_VERSION, (
        f"the published feed schema is version {published} while this client "
        f"claims {PROTOCOL_VERSION}"
    )


@_needs_spec
def test_every_published_example_parses() -> None:
    """The specification's own corpus is what a reference must read."""
    examples = sorted(_EXAMPLE_DIR.glob("*.json"))
    assert examples, f"no examples found under {_EXAMPLE_DIR}"

    for path in examples:
        raw = path.read_bytes()
        items, poll = mfeed_parser.parse(1, "https://example.com/feed", raw)
        assert poll.min_interval_seconds > 0, f"{path.name} produced no poll config"


@_needs_spec
def test_this_clients_version_rule_agrees_with_the_published_schema() -> None:
    """The rule is written twice; this is the assertion that they agree.

    The schema expresses Section 5.7 as a pattern and this client expresses it
    as a predicate. Either can be edited without the other; this is what
    fails when one of them is.
    """
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(
        (_SCHEMA_DIR / "mmsp-feed.schema.json").read_text(encoding="utf-8")
    )
    validator = jsonschema.Draft202012Validator(schema)

    disagreements = []
    for version in ["1.0", "1.1", "1.99", "2.0", "0.1", "1", "1.x", "not-a-version"]:
        schema_accepts = validator.is_valid(_feed(version))
        client_accepts = accepts_document_version(version)
        if schema_accepts != client_accepts:
            disagreements.append(
                f"{version!r}: schema {schema_accepts}, client {client_accepts}"
            )

    assert not disagreements, (
        "the published schema and this client disagree about which document "
        "versions are readable:\n" + "\n".join(disagreements)
    )


@_needs_spec
def test_the_major_this_client_reads_is_the_published_major() -> None:
    schema = json.loads(
        (_SCHEMA_DIR / "mmsp-feed.schema.json").read_text(encoding="utf-8")
    )
    pattern = schema["properties"]["mmsp"]["pattern"]

    assert pattern.startswith(f"^{PROTOCOL_MAJOR}\\."), (
        f"the schema constrains versions to {pattern} while this client reads "
        f"{PROTOCOL_MAJOR}.x"
    )
