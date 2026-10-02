"""The HTTP client every fetcher builds: redirects are followed to HTTPS only.

httpx follows a redirect itself when ``follow_redirects`` is on, so a check on
the final response comes too late: the plain-HTTP hop has already been made.
The veto therefore sits in a response hook, which httpx runs on every hop
before it builds the next request.
"""

from __future__ import annotations

from itertools import pairwise

import httpx

MAX_REDIRECT_HOPS = 5
_SECURE_SCHEME = "https"
_PERMANENT_REDIRECTS = frozenset(
    {httpx.codes.MOVED_PERMANENTLY, httpx.codes.PERMANENT_REDIRECT}
)


class InsecureRedirectError(Exception):
    """A redirect pointed at a target that is not HTTPS; it was not followed."""

    def __init__(self, source: str, target: str) -> None:
        self.source = source
        self.target = target
        super().__init__(f"Refused redirect from {source} to non-HTTPS {target}")


async def _refuse_insecure_hop(response: httpx.Response) -> None:
    if not response.has_redirect_location:
        return
    target = response.url.join(response.headers["location"])
    if target.scheme != _SECURE_SCHEME:
        raise InsecureRedirectError(str(response.url), str(target))


def build_https_only_client(
    user_agent: str,
    timeout: float,
    transport: httpx.AsyncBaseTransport | None = None,
) -> httpx.AsyncClient:
    """Follow at most MAX_REDIRECT_HOPS redirects, every one of them to HTTPS."""
    return httpx.AsyncClient(
        follow_redirects=True,
        max_redirects=MAX_REDIRECT_HOPS,
        event_hooks={"response": [_refuse_insecure_hop]},
        headers={"User-Agent": user_agent},
        timeout=timeout,
        transport=transport,
    )


def permanent_location(response: httpx.Response) -> str | None:
    """Where the resource now lives; None unless the first hop was permanent.

    The move is followed through the run of permanent hops at the start of the
    chain; a temporary hop ends it, since what lies past one is not a new home.
    """
    moved_to = None
    for hop, landed in pairwise([*response.history, response]):
        if hop.status_code not in _PERMANENT_REDIRECTS:
            break
        moved_to = str(landed.url)
    return moved_to
