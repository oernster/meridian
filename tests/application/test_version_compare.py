"""is_newer: anything unparseable compares as not-newer, never as an error."""

import pytest

from meridian.application.services.version_compare import is_newer


class TestIsNewer:
    def test_newer(self):
        assert is_newer("2.6.0", "2.5.1") is True

    def test_equal(self):
        assert is_newer("2.5.1", "2.5.1") is False

    def test_older(self):
        assert is_newer("2.5.0", "2.5.1") is False

    def test_v_prefix_stripped(self):
        assert is_newer("v2.6.0", "2.5.1") is True

    def test_uppercase_v_prefix_stripped(self):
        assert is_newer("V2.6.0", "2.5.1") is True

    def test_whitespace_tolerated(self):
        assert is_newer("  2.6.0  ", "2.5.1") is True

    def test_extra_component_compares_positionally(self):
        assert is_newer("2.6", "2.5.1") is True
        assert is_newer("2.5.1.1", "2.5.1") is True

    @pytest.mark.parametrize("latest", ["", "not-a-version", "2.6.0-rc1", "2..0"])
    def test_malformed_latest_is_not_newer(self, latest):
        assert is_newer(latest, "2.5.1") is False

    @pytest.mark.parametrize("current", ["", "0.0.0-dev", "garbage"])
    def test_malformed_current_is_not_newer(self, current):
        assert is_newer("2.6.0", current) is False
