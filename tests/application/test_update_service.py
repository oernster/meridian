"""UpdateService: what gets offered, with which download, and when."""

import pytest

from meridian.application.dto.update_info import ReleaseAsset, ReleaseInfo
from meridian.application.interfaces.release_source import ReleaseSource
from meridian.application.services.update_service import (
    UpdateService,
    platform_key_for,
    select_asset_url,
)

_ASSETS = (
    ReleaseAsset("MeridianSetup.exe", "https://example.com/MeridianSetup.exe"),
    ReleaseAsset("meridian.dmg", "https://example.com/meridian.dmg"),
    ReleaseAsset("meridian.flatpak", "https://example.com/meridian.flatpak"),
)


class FakeSource(ReleaseSource):
    def __init__(self, release: ReleaseInfo | None) -> None:
        self._release = release

    def latest_release(self) -> ReleaseInfo | None:
        return self._release


def _release(version="v2.6.0", assets=_ASSETS):
    return ReleaseInfo(
        version=version,
        page_url="https://github.com/oernster/meridian/releases/latest",
        assets=assets,
    )


class TestCheck:
    def test_unreachable_source_returns_none(self):
        service = UpdateService(FakeSource(None), "2.5.1", "windows")
        assert service.check() is None

    def test_newer_release_offers_update_with_asset_and_page(self):
        service = UpdateService(FakeSource(_release()), "2.5.1", "windows")
        status = service.check()
        assert status.update_available is True
        assert status.latest == "v2.6.0"
        assert status.current == "2.5.1"
        assert status.download_url == "https://example.com/MeridianSetup.exe"
        assert status.page_url is not None

    def test_same_version_is_not_offered(self):
        service = UpdateService(FakeSource(_release("v2.5.1")), "2.5.1", "windows")
        status = service.check()
        assert status.update_available is False
        assert status.download_url is None

    def test_skipped_version_is_seen_but_not_offered(self):
        service = UpdateService(FakeSource(_release()), "2.5.1", "windows")
        status = service.check(skipped_version="v2.6.0")
        assert status.update_available is False
        assert status.latest == "v2.6.0"
        assert status.download_url is None

    def test_different_skipped_version_still_offers(self):
        service = UpdateService(FakeSource(_release()), "2.5.1", "windows")
        status = service.check(skipped_version="v2.5.9")
        assert status.update_available is True

    @pytest.mark.parametrize(
        "platform_key,expected",
        [
            ("windows", "https://example.com/MeridianSetup.exe"),
            ("macos", "https://example.com/meridian.dmg"),
            ("linux", "https://example.com/meridian.flatpak"),
        ],
    )
    def test_platform_asset_selection(self, platform_key, expected):
        service = UpdateService(FakeSource(_release()), "2.5.1", platform_key)
        assert service.check().download_url == expected

    def test_no_matching_asset_falls_back_to_page_only(self):
        release = _release(assets=(ReleaseAsset("checksums.txt", "https://x/c"),))
        service = UpdateService(FakeSource(release), "2.5.1", "windows")
        status = service.check()
        assert status.update_available is True
        assert status.download_url is None


class TestSelectAssetUrl:
    def test_suffix_match_is_case_insensitive(self):
        assets = (ReleaseAsset("MERIDIANSETUP.EXE", "https://x/setup"),)
        assert select_asset_url(assets, "windows") == "https://x/setup"

    def test_empty_assets(self):
        assert select_asset_url((), "windows") is None

    def test_unknown_platform_key(self):
        assert select_asset_url(_ASSETS, "beos") is None


class TestPlatformKeyFor:
    @pytest.mark.parametrize(
        "sys_platform,expected",
        [
            ("win32", "windows"),
            ("darwin", "macos"),
            ("linux", "linux"),
            ("freebsd14", "linux"),
        ],
    )
    def test_mapping(self, sys_platform, expected):
        assert platform_key_for(sys_platform) == expected
