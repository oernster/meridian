"""Shortcut path resolution and removal.

`shortcuts.py` decides where a user's Desktop and Start Menu entries land and
removes them again at uninstall. `create_shortcut` itself is excluded: it is a
COM call that writes a real `.lnk` into the running user's profile, which is
the class of Win32 side effect this suite deliberately does not exercise.
Everything around it is ordinary path and filesystem work, and is covered here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from installer.constants import InstallerIdentity
from installer.ops.shortcuts import (
    _default_icon_location_for,
    get_shortcut_paths,
    remove_shortcut,
)

# ── icon location ──────────────────────────────────────────────────────────


def test_icon_falls_back_to_the_executable_when_no_icon_sits_beside_it(
    tmp_path: Path,
) -> None:
    exe = tmp_path / "Meridian.exe"
    exe.write_text("exe", encoding="utf-8")

    assert _default_icon_location_for(exe) == str(exe)


def test_icon_prefers_a_sibling_ico_and_reports_it_with_forward_slashes(
    tmp_path: Path,
) -> None:
    """Windows accepts either separator here; the shell is happier with one."""
    exe = tmp_path / "Meridian.exe"
    exe.write_text("exe", encoding="utf-8")
    (tmp_path / "meridian.ico").write_bytes(b"icon")

    located = _default_icon_location_for(exe)

    assert located.endswith("/meridian.ico")
    assert "\\" not in located


def test_a_directory_named_like_the_icon_is_not_used_as_one(tmp_path: Path) -> None:
    exe = tmp_path / "Meridian.exe"
    exe.write_text("exe", encoding="utf-8")
    (tmp_path / "meridian.ico").mkdir()

    assert _default_icon_location_for(exe) == str(exe)


# ── shortcut paths ─────────────────────────────────────────────────────────


def test_shortcut_paths_sit_under_the_users_own_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both are per-user locations, which is what keeps the install admin-free."""
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    identity = InstallerIdentity()

    paths = get_shortcut_paths(identity)

    assert paths.desktop_lnk == tmp_path / "Desktop" / f"{identity.shortcut_name}.lnk"
    assert paths.start_menu_lnk == (
        tmp_path
        / "Roaming"
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / identity.start_menu_folder
        / f"{identity.shortcut_name}.lnk"
    )


def test_shortcut_paths_fall_back_when_appdata_is_not_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.delenv("APPDATA", raising=False)

    paths = get_shortcut_paths(InstallerIdentity())

    assert "AppData" in paths.start_menu_lnk.parts
    assert "Roaming" in paths.start_menu_lnk.parts


# ── removal ────────────────────────────────────────────────────────────────


def test_removing_a_shortcut_deletes_it(tmp_path: Path) -> None:
    folder = tmp_path / "Programs" / "Meridian"
    folder.mkdir(parents=True)
    lnk = folder / "Meridian.lnk"
    lnk.write_text("lnk", encoding="utf-8")

    remove_shortcut(lnk)

    assert not lnk.exists()


def test_removing_the_last_shortcut_takes_its_folder_with_it(tmp_path: Path) -> None:
    """An empty Start Menu folder is litter in the user's own menu."""
    folder = tmp_path / "Programs" / "Meridian"
    folder.mkdir(parents=True)
    lnk = folder / "Meridian.lnk"
    lnk.write_text("lnk", encoding="utf-8")

    remove_shortcut(lnk)

    assert not folder.exists()


def test_a_folder_holding_anything_else_is_left_alone(tmp_path: Path) -> None:
    folder = tmp_path / "Programs" / "Meridian"
    folder.mkdir(parents=True)
    lnk = folder / "Meridian.lnk"
    lnk.write_text("lnk", encoding="utf-8")
    (folder / "Something else.lnk").write_text("lnk", encoding="utf-8")

    remove_shortcut(lnk)

    assert folder.exists()
    assert (folder / "Something else.lnk").exists()


def test_removing_a_shortcut_that_is_already_gone_is_not_an_error(
    tmp_path: Path,
) -> None:
    remove_shortcut(tmp_path / "nowhere" / "Meridian.lnk")
