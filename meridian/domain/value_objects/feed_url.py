"""What a feed address must be; when two addresses name the same feed.

Two rules of different strength. `require_feed_scheme` is what every stored
feed already meets, so it is all that is asked of a feed read back from the
store: a stricter rule there would make one old row stop the whole list
loading. `check_feed_url` is asked of every address on its way in: it must
parse and name a host, so `https://` and `https://not a url at all` are
refused rather than stored.

`feed_identity` is the duplicate check's key. The scheme and the host are
case-insensitive by RFC 3986, so they compare that way; the path is the
publisher's and is kept exactly, which is why `/rss` and `/rss/` stay two
feeds: a server may answer them differently.
"""

from urllib.parse import urlsplit, urlunsplit

_SCHEMES = ("https://", "http://")
_USERINFO_END = "@"


def require_feed_scheme(url: str) -> None:
    if not url.startswith(_SCHEMES):
        raise ValueError(f"Feed URL must use http:// or https://: {url}")


def check_feed_url(url: str) -> None:
    """Raise ValueError, with a plain reason, unless `url` can be subscribed to."""
    require_feed_scheme(url)
    if any(character.isspace() for character in url):
        raise ValueError(f"Feed URL is not a valid address: {url}")
    try:
        parts = urlsplit(url)
        _ = parts.port  # reading it is what checks it
    except ValueError:
        raise ValueError(f"Feed URL is not a valid address: {url}") from None
    if not parts.hostname:
        raise ValueError(f"Feed URL names no host: {url}")


def feed_identity(url: str) -> str:
    """The address with its scheme and host in lower case, the rest as given."""
    parts = urlsplit(url)
    userinfo, separator, host = parts.netloc.rpartition(_USERINFO_END)
    netloc = userinfo + separator + host.lower()
    return urlunsplit(parts._replace(scheme=parts.scheme.lower(), netloc=netloc))
