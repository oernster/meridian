"""GitHubReleaseSource: one GET, every failure mode collapsing to None."""

import json

import httpx
import pytest
import respx

from meridian.infrastructure.update.github_release_source import (
    _ACCEPT_HEADER,
    _API_URL,
    _TIMEOUT_SECONDS,
    GitHubReleaseSource,
)

_PAYLOAD = {
    "tag_name": "v2.6.0",
    "html_url": "https://github.com/oernster/meridian/releases/tag/v2.6.0",
    "assets": [
        {
            "name": "MeridianSetup.exe",
            "browser_download_url": "https://example.com/MeridianSetup.exe",
        },
        {
            "name": "meridian.dmg",
            "browser_download_url": "https://example.com/meridian.dmg",
        },
    ],
}


def _source() -> GitHubReleaseSource:
    return GitHubReleaseSource(httpx.Client())


class TestGitHubReleaseSource:
    @respx.mock
    def test_happy_path(self):
        respx.get(_API_URL).mock(
            return_value=httpx.Response(200, content=json.dumps(_PAYLOAD).encode())
        )
        release = _source().latest_release()
        assert release.version == "v2.6.0"
        assert release.page_url == _PAYLOAD["html_url"]
        assert len(release.assets) == 2
        assert release.assets[0].name == "MeridianSetup.exe"

    @respx.mock
    def test_request_target_and_accept_header(self):
        route = respx.get(_API_URL).mock(
            return_value=httpx.Response(200, content=json.dumps(_PAYLOAD).encode())
        )
        _source().latest_release()
        request = route.calls.last.request
        assert str(request.url) == _API_URL
        assert request.headers["accept"] == _ACCEPT_HEADER

    def test_default_client_carries_the_timeout(self):
        client = GitHubReleaseSource()._client
        assert client.timeout == httpx.Timeout(_TIMEOUT_SECONDS)

    @respx.mock
    @pytest.mark.parametrize("status_code", [301, 404, 403, 500])
    def test_non_200_returns_none(self, status_code):
        respx.get(_API_URL).mock(return_value=httpx.Response(status_code))
        assert _source().latest_release() is None

    @respx.mock
    def test_transport_error_returns_none(self):
        respx.get(_API_URL).mock(side_effect=httpx.ConnectError("unreachable"))
        assert _source().latest_release() is None

    @respx.mock
    def test_unparseable_body_returns_none(self):
        respx.get(_API_URL).mock(return_value=httpx.Response(200, content=b"not json"))
        assert _source().latest_release() is None

    @respx.mock
    def test_non_dict_body_returns_none(self):
        respx.get(_API_URL).mock(return_value=httpx.Response(200, content=b"[1]"))
        assert _source().latest_release() is None

    @respx.mock
    @pytest.mark.parametrize("tag", [None, "", "   ", 42])
    def test_missing_or_invalid_tag_returns_none(self, tag):
        payload = dict(_PAYLOAD)
        if tag is None:
            del payload["tag_name"]
        else:
            payload["tag_name"] = tag
        respx.get(_API_URL).mock(
            return_value=httpx.Response(200, content=json.dumps(payload).encode())
        )
        assert _source().latest_release() is None

    @respx.mock
    @pytest.mark.parametrize("page_url", [None, "", 42])
    def test_missing_or_invalid_page_url_becomes_none(self, page_url):
        payload = dict(_PAYLOAD)
        if page_url is None:
            del payload["html_url"]
        else:
            payload["html_url"] = page_url
        respx.get(_API_URL).mock(
            return_value=httpx.Response(200, content=json.dumps(payload).encode())
        )
        release = _source().latest_release()
        assert release is not None
        assert release.page_url is None

    @respx.mock
    @pytest.mark.parametrize("assets", [None, "nope", 42])
    def test_missing_or_non_list_assets_become_empty(self, assets):
        payload = dict(_PAYLOAD)
        if assets is None:
            del payload["assets"]
        else:
            payload["assets"] = assets
        respx.get(_API_URL).mock(
            return_value=httpx.Response(200, content=json.dumps(payload).encode())
        )
        release = _source().latest_release()
        assert release is not None
        assert release.assets == ()

    @respx.mock
    def test_malformed_asset_entries_are_filtered(self):
        payload = dict(_PAYLOAD)
        payload["assets"] = [
            "not-a-dict",
            {"browser_download_url": "https://x/no-name"},
            {"name": "", "browser_download_url": "https://x/empty-name"},
            {"name": "no-url.exe"},
            {"name": 42, "browser_download_url": "https://x/int-name"},
            {"name": "good.exe", "browser_download_url": "https://x/good"},
        ]
        respx.get(_API_URL).mock(
            return_value=httpx.Response(200, content=json.dumps(payload).encode())
        )
        release = _source().latest_release()
        assert len(release.assets) == 1
        assert release.assets[0].download_url == "https://x/good"
