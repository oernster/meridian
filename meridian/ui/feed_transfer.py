"""The feed list file on disk: written whole or not at all, read off the UI thread.

Export used to write the file in place, so a write failing part way could
leave the previous export truncated. It now writes a temporary file beside
the target, flushes it to disk and swaps it in, so the old file survives
any failure.

The import is a job for `BackgroundJobs`: reading and storing two thousand
entries took eighteen seconds on the UI thread (measured), with the window
frozen throughout. What the reader is told when it fails is said here too:
the reason for a file that is not a feed list, a plain sentence for anything
else, with the detail in the log.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from collections.abc import Callable
from functools import partial
from pathlib import Path

from meridian.application.services.feed_import import ImportReport, import_feeds
from meridian.application.services.feed_list import NotAFeedList, decode_feed_list
from meridian.application.services.subscription_service import SubscriptionService

_LOG = logging.getLogger(__name__)
_TEMPORARY_SUFFIX = ".tmp"


def write_feed_list(path: Path, data: dict) -> None:
    """Replace `path` with `data` as JSON, atomically; raises OSError on failure."""
    text = json.dumps(data, indent=2, ensure_ascii=False)
    handle, temporary = tempfile.mkstemp(
        dir=path.parent, prefix=path.name, suffix=_TEMPORARY_SUFFIX
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError:
        Path(temporary).unlink(missing_ok=True)
        raise


def _read_and_import(path: Path, subscriptions: SubscriptionService) -> ImportReport:
    return import_feeds(decode_feed_list(path.read_bytes()), subscriptions)


def import_job(
    path: Path, subscriptions: SubscriptionService
) -> Callable[[], ImportReport]:
    """The import as a job holding only the path and the service."""
    return partial(_read_and_import, path, subscriptions)


def import_failure(exc: BaseException) -> str:
    """The sentence the window shows for an import that did not run."""
    if isinstance(exc, NotAFeedList):
        return f"Import failed: {exc}"
    _LOG.error("Import failed", exc_info=exc)
    if isinstance(exc, OSError):
        return "Import failed: the file could not be read."
    return "Import failed: the feed store could not be read."
