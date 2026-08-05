from pathlib import Path

from meridian.version import (
    FALLBACK_VERSION,
    VERSION_FILE_CANDIDATES,
    __version__,
    read_version,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent


def test_version_is_semver_string():
    assert isinstance(__version__, str)
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


def test_version_matches_the_root_version_file():
    assert (_REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip() == __version__


def test_candidates_cover_package_parent_then_package():
    assert VERSION_FILE_CANDIDATES == (
        _REPO_ROOT / "VERSION",
        _REPO_ROOT / "meridian" / "VERSION",
    )


def test_read_version_returns_first_readable_file(tmp_path):
    present = tmp_path / "VERSION"
    present.write_text("9.9.9\n", encoding="utf-8")
    assert read_version([present]) == "9.9.9"


def test_read_version_skips_a_missing_file_and_uses_the_next(tmp_path):
    later = tmp_path / "later" / "VERSION"
    later.parent.mkdir()
    later.write_text("1.2.3\n", encoding="utf-8")
    assert read_version([tmp_path / "absent" / "VERSION", later]) == "1.2.3"


def test_read_version_treats_an_empty_file_as_absent(tmp_path):
    empty = tmp_path / "VERSION"
    empty.write_text("   \n", encoding="utf-8")
    assert read_version([empty]) == FALLBACK_VERSION


def test_read_version_falls_back_when_nothing_is_found(tmp_path):
    assert read_version([tmp_path / "nowhere" / "VERSION"]) == FALLBACK_VERSION
