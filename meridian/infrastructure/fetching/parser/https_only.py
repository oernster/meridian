"""The one statement of which parsed addresses Meridian will ever fetch: HTTPS.

A feed itself may be plain HTTP; nothing it points at is followed in the
clear: a thumbnail the window draws, a media file the player opens, a
transcript or caption track. Every parser asks this module rather than writing
its own scheme test. Six copies of `startswith("https://")` sat in three
parsers while the RSS and Atom thumbnails and every address in an MFEED
document went unchecked, which the documents had claimed were dropped.
"""

from __future__ import annotations

_SCHEME = "https://"


def is_https(url: object) -> bool:
    """True when `url` is text naming an HTTPS address (the scheme in any case)."""
    return isinstance(url, str) and url[: len(_SCHEME)].lower() == _SCHEME
