"""Importing a feed list: what was added, what was already there, what was not.

An import touches many feeds at once, so its honest answer is a tally rather
than a yes or no. Every entry in the file lands in exactly one of four groups;
the sentence the reader sees is built from all four. A feed that could not be
added is named with its reason, never only logged: the import used to log each
refusal and say nothing, so a partial import read as a whole one.

A feed counts as the one already held when its address matches with the scheme
and host compared without case (`feed_identity`); a held feed is left exactly
as it is, whatever title or type the file gives it. An entry naming a feed
listed earlier in the same file is counted as a repeat, not as held. Its
address must parse and name a host before anything is stored. A store that
refuses an entry is reported in plain words; its own text, which carries SQL,
goes to the log only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from meridian.application.services.feed_list import feed_list_entries
from meridian.application.services.subscription_service import SubscriptionService
from meridian.domain.value_objects.feed_url import check_feed_url, feed_identity

_LOG = logging.getLogger(__name__)

# A file of bad entries could name hundreds; the report names this many and
# counts the rest, so the dialog stays readable.
NAMED_SKIP_LIMIT = 10
STORE_REFUSAL = "the feed store could not save it"


@dataclass(frozen=True, slots=True)
class SkippedEntry:
    """An entry that was not imported: its address (or position) and why."""

    entry: str
    reason: str


@dataclass(frozen=True, slots=True)
class ImportReport:
    added: int
    already_subscribed: int
    skipped: tuple[SkippedEntry, ...]
    repeated: int = 0

    @property
    def complete(self) -> bool:
        """True when every feed in the file is now held."""
        return not self.skipped

    def describe(self) -> str:
        """The report as the reader sees it, naming every feed that was refused."""
        if not (self.added or self.already_subscribed or self.skipped):
            return "The file lists no feeds."
        if self.added:
            lines = [f"Imported {_count(self.added, 'feed')}."]
        else:
            lines = ["No new feeds were imported."]
        if self.already_subscribed:
            lines.append(
                f"{_count(self.already_subscribed, 'feed')} already subscribed."
            )
        if self.repeated:
            verb = "repeats" if self.repeated == 1 else "repeat"
            lines.append(
                f"{_count(self.repeated, 'entry', 'entries')} {verb} "
                "a feed listed earlier in the file."
            )
        if self.skipped:
            lines.append(f"{_count(len(self.skipped), 'feed')} could not be imported:")
            named = self.skipped[:NAMED_SKIP_LIMIT]
            lines.extend(f"{s.entry}: {s.reason}" for s in named)
            unnamed = len(self.skipped) - len(named)
            if unnamed:
                lines.append(f"... and {unnamed} more.")
        return "\n".join(lines)


def _count(count: int, noun: str, plural: str | None = None) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {plural or noun + 's'}"


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def import_feeds(data: object, subscriptions: SubscriptionService) -> ImportReport:
    """Subscribe to every new feed in a parsed feed list; report each entry.

    Raises `NotAFeedList` when `data` is not the exported envelope or names a
    version this Meridian cannot read. A single entry that cannot be
    subscribed never ends the import; it is reported.
    """
    entries = feed_list_entries(data)
    held = {feed_identity(feed.url) for feed in subscriptions.list_feeds()}
    in_file: set[str] = set()
    added = already = repeated = 0
    skipped: list[SkippedEntry] = []
    for position, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            skipped.append(SkippedEntry(f"Entry {position}", "not a feed entry"))
            continue
        url = _text(entry.get("url"))
        if not url:
            skipped.append(SkippedEntry(f"Entry {position}", "no address"))
            continue
        try:
            check_feed_url(url)
        except ValueError as exc:
            skipped.append(SkippedEntry(url, str(exc)))
            continue
        identity = feed_identity(url)
        if identity in in_file:
            repeated += 1
            continue
        if identity in held:
            already += 1
            in_file.add(identity)
            continue
        reason = _subscribe(subscriptions, url, entry)
        if reason:
            skipped.append(SkippedEntry(url, reason))
            continue
        held.add(identity)
        in_file.add(identity)
        added += 1
    return ImportReport(added, already, tuple(skipped), repeated)


def _subscribe(subscriptions: SubscriptionService, url: str, entry: dict) -> str:
    """Subscribe to one entry; return why it was refused ("" once stored)."""
    try:
        subscriptions.subscribe(
            url,
            source_type=entry.get("source_type"),
            platform_id=_text(entry.get("platform_id")) or None,
            rss_fallback_url=_text(entry.get("rss_fallback_url")) or None,
            title=_text(entry.get("title")) or None,
            filter_expr=_text(entry.get("filter_expr")) or None,
        )
    # A refusal of the entry itself (a bad source type, a platform feed with
    # no platform) is a ValueError and its message is plain. Anything else is
    # the store, whose message is SQL: the log gets it, the reader does not.
    except ValueError as exc:
        return str(exc) or type(exc).__name__
    except Exception:  # noqa: BLE001 (deliberate: one entry, never the import)
        _LOG.exception("The store refused the imported feed %s", url)
        return STORE_REFUSAL
    return ""
