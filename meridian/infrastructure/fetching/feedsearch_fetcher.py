"""Feed discovery via Feedly's search API.

Note: Feedly indexes RSS/Atom/Podcast sources only. MFEED/MMSP
discovery requires a separate fetcher implementation when a suitable
directory service becomes available.
"""

from __future__ import annotations

import asyncio

import httpx

from meridian.application.dto.feed_candidate_dto import FeedCandidateDTO
from meridian.application.interfaces.discovery_fetcher import (
    DEFAULT_RESULT_CAP,
    DiscoveryError,
    DiscoveryFetcher,
)
from meridian.application.services.source_type_inference import infer_source_type

_API_URL = "https://cloud.feedly.com/v3/search/feeds"
_USER_AGENT = "Meridian/1.0"
_TIMEOUT = 15.0


class FeedsearchFetcher(DiscoveryFetcher):
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
            timeout=_TIMEOUT,
        )

    async def search(
        self,
        query: str,
        limit: int = DEFAULT_RESULT_CAP,
        page: int = 0,
    ) -> list[FeedCandidateDTO]:
        params: dict[str, int | str] = {"query": query, "count": limit}
        try:
            response = await self._client.get(_API_URL, params=params)
            response.raise_for_status()
            data = response.json()
        except asyncio.CancelledError:
            raise
        except httpx.TimeoutException:
            raise DiscoveryError(
                "Search timed out. Check your connection and try again."
            )
        except httpx.ConnectError:
            raise DiscoveryError(
                "Could not reach the feed directory. Check your connection."
            )
        except httpx.HTTPStatusError as exc:
            raise DiscoveryError(
                f"Feed directory returned an error (HTTP {exc.response.status_code})."
            )
        except DiscoveryError:
            raise
        except Exception as exc:
            raise DiscoveryError(f"Unexpected error during search: {exc}") from exc

        if not isinstance(data, dict) or "results" not in data:
            raise DiscoveryError("Unexpected response format from feed directory.")
        return [
            _parse_candidate(item)
            for item in data["results"]
            if isinstance(item, dict) and _extract_url(item)
        ]

    async def aclose(self) -> None:
        await self._client.aclose()


def _extract_url(item: dict) -> str:
    feed_id = item.get("feedId", "")
    if feed_id.startswith("feed/"):
        return feed_id[len("feed/") :]
    return item.get("website", "")


def _parse_candidate(item: dict) -> FeedCandidateDTO:
    url = _extract_url(item)
    source_type = infer_source_type(url)
    return FeedCandidateDTO(
        url=url,
        title=item.get("title") or None,
        description=item.get("description") or None,
        favicon_url=item.get("iconUrl") or None,
        source_type=source_type.value,
    )
