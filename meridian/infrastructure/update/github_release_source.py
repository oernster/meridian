"""GitHub releases adapter for the update check.

``releases/latest`` returns only a published, non-draft, non-prerelease
release, so a tag pushed mid-development is structurally invisible; the guard
is the endpoint's own contract. One check at launch plus one per day sits far
inside the unauthenticated rate limit, so there are no retries.
"""

from __future__ import annotations

import httpx

from meridian.application.dto.update_info import ReleaseAsset, ReleaseInfo
from meridian.application.interfaces.release_source import ReleaseSource

_API_URL = "https://api.github.com/repos/oernster/meridian/releases/latest"
_ACCEPT_HEADER = "application/vnd.github+json"
_TIMEOUT_SECONDS = 5.0


def _parse_assets(raw: object) -> tuple[ReleaseAsset, ...]:
    if not isinstance(raw, list):
        return ()
    assets: list[ReleaseAsset] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        download_url = entry.get("browser_download_url")
        if isinstance(name, str) and name and isinstance(download_url, str):
            assets.append(ReleaseAsset(name=name, download_url=download_url))
    return tuple(assets)


class GitHubReleaseSource(ReleaseSource):
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=_TIMEOUT_SECONDS)

    def latest_release(self) -> ReleaseInfo | None:
        try:
            response = self._client.get(_API_URL, headers={"Accept": _ACCEPT_HEADER})
            if response.status_code != httpx.codes.OK:
                return None
            payload = response.json()
        except (httpx.HTTPError, OSError, ValueError):
            return None
        if not isinstance(payload, dict):
            return None
        tag = payload.get("tag_name")
        if not isinstance(tag, str) or not tag.strip():
            return None
        page_url = payload.get("html_url")
        return ReleaseInfo(
            version=tag.strip(),
            page_url=page_url if isinstance(page_url, str) and page_url else None,
            assets=_parse_assets(payload.get("assets")),
        )
