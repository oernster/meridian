"""A wire that redirects, for building a fetcher exactly the way main.py does.

Only the transport is swapped, so every hop goes through the production
client's own redirect handling rather than a bare client that never follows.
"""

import httpx


def redirecting_transport(
    redirects: dict[str, tuple[int, str]], body: bytes, seen: list[str]
) -> httpx.MockTransport:
    """Answer each URL in redirects with (status, location); anything else, body.

    URLs are matched without their query string. Every requested URL, query
    included, is appended to seen so a test can assert which hosts were reached.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        seen.append(url)
        hop = redirects.get(url.split("?")[0])
        if hop is None:
            return httpx.Response(200, content=body)
        status, location = hop
        return httpx.Response(status, headers={"location": location})

    return httpx.MockTransport(handler)
