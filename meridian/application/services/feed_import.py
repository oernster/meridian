"""Importing a feed list: what was added, what was already there, what was not.

An import touches many feeds at once, so its honest answer is a tally rather
than a yes or no. Every entry in the file lands in exactly one of three groups;
the sentence the reader sees is built from all three. A feed that could not be
added is named with its reason, never only logged: the import used to log each
refusal and say nothing, so a partial import read as a whole one.
"""

from __future__ import annotations

from dataclasses import dataclass

from meridian.application.services.subscription_service import SubscriptionService

# A file of bad entries could name hundreds; the report names this many and
# counts the rest, so the dialog stays readable.
NAMED_SKIP_LIMIT = 10


class NotAFeedList(ValueError):
    """The file parsed but does not have the shape of a Meridian feed list."""


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

    @property
    def complete(self) -> bool:
        """True when every entry in the file was either added or already held."""
        return not self.skipped

    def describe(self) -> str:
        """The report as the reader sees it, naming every feed that was refused."""
        if not (self.added or self.already_subscribed or self.skipped):
            return "The file lists no feeds."
        if self.added:
            lines = [f"Imported {_feeds(self.added)}."]
        else:
            lines = ["No new feeds were imported."]
        if self.already_subscribed:
            lines.append(f"{_feeds(self.already_subscribed)} already subscribed.")
        if self.skipped:
            lines.append(f"{_feeds(len(self.skipped))} could not be imported:")
            named = self.skipped[:NAMED_SKIP_LIMIT]
            lines.extend(f"{s.entry}: {s.reason}" for s in named)
            unnamed = len(self.skipped) - len(named)
            if unnamed:
                lines.append(f"... and {unnamed} more.")
        return "\n".join(lines)


def _feeds(count: int) -> str:
    return f"{count} feed" if count == 1 else f"{count} feeds"


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def import_feeds(data: object, subscriptions: SubscriptionService) -> ImportReport:
    """Subscribe to every new feed in a parsed feed list; report each entry.

    Raises `NotAFeedList` when `data` is not the exported envelope. A single
    entry that cannot be subscribed never ends the import; it is reported.
    """
    feeds = data.get("feeds") if isinstance(data, dict) else None
    if not isinstance(feeds, list):
        raise NotAFeedList("the file is not a Meridian feed list")
    known = {feed.url for feed in subscriptions.list_feeds()}
    added = already = 0
    skipped: list[SkippedEntry] = []
    for position, entry in enumerate(feeds, start=1):
        if not isinstance(entry, dict):
            skipped.append(SkippedEntry(f"Entry {position}", "not a feed entry"))
            continue
        url = _text(entry.get("url"))
        if not url:
            skipped.append(SkippedEntry(f"Entry {position}", "no address"))
            continue
        if url in known:
            already += 1
            continue
        try:
            subscriptions.subscribe(
                url,
                source_type=entry.get("source_type"),
                title=_text(entry.get("title")) or None,
            )
        # Any refusal, from a bad source type to a store that will not save,
        # belongs to this entry alone; the rest of the file still imports.
        except Exception as exc:  # noqa: BLE001 (deliberate: see above)
            skipped.append(SkippedEntry(url, str(exc) or type(exc).__name__))
            continue
        known.add(url)
        added += 1
    return ImportReport(added, already, tuple(skipped))
