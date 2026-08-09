"""Decides whether an update should be offered, and with which download."""

from __future__ import annotations

from meridian.application.dto.update_info import ReleaseAsset, UpdateStatus
from meridian.application.interfaces.release_source import ReleaseSource
from meridian.application.services.version_compare import is_newer

_PLATFORM_SUFFIXES: dict[str, str] = {
    "windows": ".exe",
    "macos": ".dmg",
    "linux": ".flatpak",
}

_SYS_PLATFORM_KEYS: dict[str, str] = {
    "win32": "windows",
    "darwin": "macos",
}

_DEFAULT_PLATFORM_KEY = "linux"


def platform_key_for(sys_platform: str) -> str:
    """Map a ``sys.platform`` value to the asset-selection key."""
    return _SYS_PLATFORM_KEYS.get(sys_platform, _DEFAULT_PLATFORM_KEY)


def select_asset_url(assets: tuple[ReleaseAsset, ...], platform_key: str) -> str | None:
    """First asset whose name matches the platform's suffix, else None."""
    suffix = _PLATFORM_SUFFIXES.get(platform_key)
    if suffix is None:
        return None
    for asset in assets:
        if asset.name.lower().endswith(suffix):
            return asset.download_url
    return None


class UpdateService:
    def __init__(
        self,
        source: ReleaseSource,
        current_version: str,
        platform_key: str,
    ) -> None:
        self._source = source
        self._current_version = current_version
        self._platform_key = platform_key

    def check(self, skipped_version: str | None = None) -> UpdateStatus | None:
        """One update check. None when the release source is unreachable.

        ``skipped_version`` is the exact tag the user chose to skip; both sides
        come from the same endpoint, so string equality is enough. The manual
        check passes None here, which is how it ignores the skip.
        """
        release = self._source.latest_release()
        if release is None:
            return None
        newer = is_newer(release.version, self._current_version)
        available = newer and release.version != skipped_version
        download_url = (
            select_asset_url(release.assets, self._platform_key) if available else None
        )
        return UpdateStatus(
            current=self._current_version,
            latest=release.version,
            update_available=available,
            download_url=download_url,
            page_url=release.page_url,
        )
