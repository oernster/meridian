"""Install operations, exercised against a temporary directory.

`installer/` sits outside the coverage source and had no tests at all until
2026-08-09. These cover the part with the real exposure: `_swap_in_bundle`
moves a live installation aside and puts a new one in its place, so a failure
partway leaves a user with no application at all unless the rollback works.

Windows side effects are replaced by hand-written fakes rather than a mock
library: a recorder in place of the registry writer, and a rename that fails
only for the path under test. Everything else runs for real against `tmp_path`.
"""

from __future__ import annotations

from pathlib import Path
import zipfile

import pytest

from installer.constants import InstallerIdentity
from installer.ops import install_ops
from installer.ops.errors import InstallerOperationError
from installer.ops.install_ops import (
    InstallOptions,
    _apply_shortcuts,
    _check_cancel,
    _extract_payload_to,
    _progress,
    _register_uninstall,
    _swap_in_bundle,
)
from installer.ops.shortcuts import ShortcutPaths


class _CancelledEvent:
    def is_set(self) -> bool:
        return True


class _LiveEvent:
    def is_set(self) -> bool:
        return False


def _bundle(root: Path, marker: str = "one") -> Path:
    """Build something shaped like an extracted payload."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "Meridian.exe").write_text(marker, encoding="utf-8")
    internal = root / "_internal"
    internal.mkdir(exist_ok=True)
    (internal / "base_library.zip").write_text(marker, encoding="utf-8")
    return root


def _fail_rename_for(monkeypatch: pytest.MonkeyPatch, doomed: Path) -> None:
    """Make exactly one path un-renameable, leaving every other rename real."""
    real = Path.rename

    def fake(self: Path, target):  # noqa: ANN001
        if self == doomed:
            raise OSError("simulated cross-device rename")
        return real(self, target)

    monkeypatch.setattr(Path, "rename", fake)


# ── _progress and _check_cancel ────────────────────────────────────────────


def test_progress_is_silent_without_a_callback() -> None:
    _progress(None, pct=10, message="ignored")


def test_progress_sends_a_percentage_payload_when_given_one() -> None:
    seen: list[object] = []
    _progress(seen.append, pct=42, message="Extracting")
    assert seen == [{"pct": 42, "message": "Extracting"}]


def test_progress_sends_a_bare_message_when_there_is_no_percentage() -> None:
    seen: list[object] = []
    _progress(seen.append, pct=None, message="Working")
    assert seen == ["Working"]


def test_check_cancel_passes_when_there_is_no_event() -> None:
    _check_cancel(None)
    _check_cancel(_LiveEvent())


def test_check_cancel_raises_once_the_event_is_set() -> None:
    with pytest.raises(InstallerOperationError, match="Cancelled"):
        _check_cancel(_CancelledEvent())


# ── _swap_in_bundle ────────────────────────────────────────────────────────


def test_swap_installs_into_an_empty_target(tmp_path: Path) -> None:
    staging = _bundle(tmp_path / "staging")
    target = tmp_path / "Meridian"

    _swap_in_bundle(staging, target)

    assert (target / "Meridian.exe").read_text(encoding="utf-8") == "one"
    assert (target / "_internal" / "base_library.zip").exists()
    assert not staging.exists()


def test_swap_replaces_an_existing_install_and_clears_the_backup(
    tmp_path: Path,
) -> None:
    target = _bundle(tmp_path / "Meridian", marker="old")
    staging = _bundle(tmp_path / "staging", marker="new")

    _swap_in_bundle(staging, target)

    assert (target / "Meridian.exe").read_text(encoding="utf-8") == "new"
    leftovers = [p for p in tmp_path.iterdir() if ".old." in p.name]
    assert leftovers == [], f"backup directory left behind: {leftovers}"


def test_swap_refuses_when_the_existing_install_cannot_be_moved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _bundle(tmp_path / "Meridian", marker="old")
    staging = _bundle(tmp_path / "staging", marker="new")
    _fail_rename_for(monkeypatch, target.resolve())

    with pytest.raises(InstallerOperationError, match="Unable to replace"):
        _swap_in_bundle(staging, target)

    assert (target / "Meridian.exe").read_text(encoding="utf-8") == "old"


def test_swap_restores_the_previous_install_when_the_new_one_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The rollback is the whole point: a failed upgrade must not erase the app."""
    target = _bundle(tmp_path / "Meridian", marker="old")
    staging = _bundle(tmp_path / "staging", marker="new")

    _fail_rename_for(monkeypatch, staging.resolve())

    def _explode(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        raise RuntimeError("copy failed halfway")

    monkeypatch.setattr(install_ops.shutil, "copytree", _explode)

    with pytest.raises(RuntimeError, match="copy failed halfway"):
        _swap_in_bundle(staging, target)

    assert target.exists(), "the previous installation was not restored"
    assert (target / "Meridian.exe").read_text(encoding="utf-8") == "old"


# ── _extract_payload_to ────────────────────────────────────────────────────


def _payload_zip(path: Path, *, complete: bool) -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("Meridian.exe", "exe")
        if complete:
            zf.writestr("_internal/base_library.zip", "lib")
    return path


def test_extract_unpacks_the_payload_and_reports_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    zip_path = _payload_zip(tmp_path / "payload.zip", complete=True)
    monkeypatch.setattr(install_ops, "payload_zip_path", lambda: zip_path)
    staging = tmp_path / "staging"
    seen: list[object] = []

    _extract_payload_to(staging, progress=seen.append, cancel_event=_LiveEvent())

    assert (staging / "Meridian.exe").exists()
    assert (staging / "_internal").exists()
    assert seen == [{"pct": 10, "message": "Extracting payload..."}]


def test_extract_rejects_a_payload_missing_its_internal_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    zip_path = _payload_zip(tmp_path / "payload.zip", complete=False)
    monkeypatch.setattr(install_ops, "payload_zip_path", lambda: zip_path)

    with pytest.raises(InstallerOperationError, match="Payload is missing"):
        _extract_payload_to(tmp_path / "staging")


def test_extract_stops_before_unpacking_when_already_cancelled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _unreachable():  # noqa: ANN202
        raise AssertionError("the payload was opened despite cancellation")

    monkeypatch.setattr(install_ops, "payload_zip_path", _unreachable)

    with pytest.raises(InstallerOperationError, match="Cancelled"):
        _extract_payload_to(tmp_path / "staging", cancel_event=_CancelledEvent())


# ── _register_uninstall ────────────────────────────────────────────────────


class _RegistryRecorder:
    """Stands in for the HKCU writer; records rather than touching the registry."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, key: str, **kwargs) -> None:  # noqa: ANN003
        self.calls.append((key, kwargs))

    @property
    def only(self) -> dict:
        assert len(self.calls) == 1, f"expected one write, got {len(self.calls)}"
        return self.calls[0][1]


def _register(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> _RegistryRecorder:
    recorder = _RegistryRecorder()
    monkeypatch.setattr(install_ops, "write_uninstall_entry", recorder)
    _register_uninstall(
        InstallerIdentity(),
        install_dir=tmp_path,
        installer_copy=tmp_path / "MeridianSetup.exe",
        shortcut_desktop=True,
        shortcut_start_menu=False,
    )
    return recorder


def test_registration_points_the_icon_at_the_executable_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recorded = _register(tmp_path, monkeypatch).only
    assert recorded["display_icon"] == str(tmp_path / "Meridian.exe")


def test_registration_prefers_a_bundled_icon_file_when_one_is_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "meridian.ico").write_bytes(b"icon")
    recorded = _register(tmp_path, monkeypatch).only
    assert recorded["display_icon"] == str(tmp_path / "meridian.ico")


def test_registration_quotes_the_uninstall_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The installer path contains spaces on a normal machine."""
    recorded = _register(tmp_path, monkeypatch).only
    assert (
        recorded["uninstall_string"]
        == f'"{tmp_path / "MeridianSetup.exe"}" --uninstall'
    )
    assert recorded["shortcut_desktop"] is True
    assert recorded["shortcut_start_menu"] is False


# ── _apply_shortcuts ───────────────────────────────────────────────────────


def _shortcut_fakes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[ShortcutPaths, list[tuple[Path, Path]]]:
    paths = ShortcutPaths(
        desktop_lnk=tmp_path / "Desktop" / "Meridian.lnk",
        start_menu_lnk=tmp_path / "StartMenu" / "Meridian.lnk",
    )
    created: list[tuple[Path, Path]] = []

    def _create(exe: Path, lnk: Path, *, working_dir=None) -> None:  # noqa: ANN001
        lnk.parent.mkdir(parents=True, exist_ok=True)
        lnk.write_text("lnk", encoding="utf-8")
        created.append((exe, lnk))

    monkeypatch.setattr(install_ops, "get_shortcut_paths", lambda identity: paths)
    monkeypatch.setattr(install_ops, "create_shortcut", _create)
    return paths, created


def test_selected_shortcuts_are_created(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths, created = _shortcut_fakes(tmp_path, monkeypatch)
    opts = InstallOptions(
        target_dir=tmp_path,
        create_desktop_shortcut=True,
        create_start_menu_shortcut=True,
    )

    _apply_shortcuts(InstallerIdentity(), tmp_path, opts)

    assert [lnk for _, lnk in created] == [paths.desktop_lnk, paths.start_menu_lnk]


def test_deselected_shortcuts_are_removed_rather_than_left_stale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths, created = _shortcut_fakes(tmp_path, monkeypatch)
    for lnk in (paths.desktop_lnk, paths.start_menu_lnk):
        lnk.parent.mkdir(parents=True, exist_ok=True)
        lnk.write_text("stale", encoding="utf-8")

    opts = InstallOptions(
        target_dir=tmp_path,
        create_desktop_shortcut=False,
        create_start_menu_shortcut=False,
    )
    _apply_shortcuts(InstallerIdentity(), tmp_path, opts)

    assert not paths.desktop_lnk.exists()
    assert not paths.start_menu_lnk.exists()
    assert created == []


def test_removing_an_absent_shortcut_is_not_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _shortcut_fakes(tmp_path, monkeypatch)
    opts = InstallOptions(
        target_dir=tmp_path,
        create_desktop_shortcut=False,
        create_start_menu_shortcut=False,
    )
    _apply_shortcuts(InstallerIdentity(), tmp_path, opts)
