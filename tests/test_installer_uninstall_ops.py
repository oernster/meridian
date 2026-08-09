"""The uninstall operation.

This is the operation that removes files from a user's machine, so the cases
that matter are the refusals: uninstalling something that is not installed,
and uninstalling while the application is still running. Both were previously
unasserted anywhere.

Every Windows side effect is replaced by a hand-written recorder. The one real
filesystem action, clearing the user's data and cache directories, is pointed
at `tmp_path` so the assertion is that the directories actually go.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from installer.constants import InstallerIdentity
from installer.ops import uninstall_ops
from installer.ops.errors import AppRunningError, InstallerOperationError
from installer.ops.shortcuts import ShortcutPaths
from installer.ops.uninstall_ops import (
    UninstallOptions,
    uninstall,
    uninstall_with_feedback,
)
from installer.state.registry import UninstallEntry


class _Recorder:
    """Collects what the uninstall did instead of letting it do it."""

    def __init__(self) -> None:
        self.removed_shortcuts: list[Path] = []
        self.deleted_keys: list[str] = []
        self.scheduled: list[Path] = []
        self.running = False


def _entry(location: Path, **overrides) -> UninstallEntry:  # noqa: ANN003
    fields = {
        "display_name": "Meridian",
        "display_version": "2.5.0",
        "install_location": location,
        "uninstall_string": "unused",
    }
    fields.update(overrides)
    return UninstallEntry(**fields)


@pytest.fixture
def rig(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):  # noqa: ANN201
    """Wire every Windows edge to a recorder, leaving the logic real."""
    rec = _Recorder()
    paths = ShortcutPaths(
        desktop_lnk=tmp_path / "Desktop" / "Meridian.lnk",
        start_menu_lnk=tmp_path / "StartMenu" / "Meridian.lnk",
    )

    monkeypatch.setattr(uninstall_ops, "get_shortcut_paths", lambda identity: paths)
    monkeypatch.setattr(uninstall_ops, "remove_shortcut", rec.removed_shortcuts.append)
    monkeypatch.setattr(
        uninstall_ops, "delete_uninstall_entry", rec.deleted_keys.append
    )
    monkeypatch.setattr(
        uninstall_ops, "_schedule_delete_after_exit", rec.scheduled.append
    )
    monkeypatch.setattr(uninstall_ops, "is_app_running", lambda exe: rec.running)
    monkeypatch.setattr(
        uninstall_ops, "user_data_dir", lambda *a, **k: str(tmp_path / "data")
    )
    monkeypatch.setattr(
        uninstall_ops, "user_cache_dir", lambda *a, **k: str(tmp_path / "cache")
    )

    rec.paths = paths
    return rec


def _installed(tmp_path: Path) -> Path:
    install_dir = tmp_path / "Meridian"
    install_dir.mkdir()
    (install_dir / "Meridian.exe").write_text("exe", encoding="utf-8")
    return install_dir


def _found(monkeypatch: pytest.MonkeyPatch, entry: UninstallEntry | None) -> None:
    monkeypatch.setattr(uninstall_ops, "read_uninstall_entry", lambda key: entry)


# ── refusals ───────────────────────────────────────────────────────────────


def test_uninstalling_something_that_is_not_installed_is_refused(
    rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    _found(monkeypatch, None)
    monkeypatch.setattr(uninstall_ops, "try_read_install_location", lambda key: None)

    with pytest.raises(InstallerOperationError, match="not detected as installed"):
        uninstall(InstallerIdentity(), UninstallOptions())

    assert rig.scheduled == [], "a deletion was scheduled for a missing install"


def test_uninstalling_while_the_application_runs_is_refused(
    rig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deleting a running application leaves a half-removed install."""
    install_dir = _installed(tmp_path)
    _found(monkeypatch, _entry(install_dir))
    rig.running = True

    with pytest.raises(AppRunningError, match="currently running"):
        uninstall(InstallerIdentity(), UninstallOptions())

    assert rig.deleted_keys == []
    assert rig.scheduled == []


def test_a_stale_registry_entry_still_yields_a_location(
    rig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A partly-written key has no full entry but still names the directory."""
    install_dir = _installed(tmp_path)
    _found(monkeypatch, None)
    monkeypatch.setattr(
        uninstall_ops, "try_read_install_location", lambda key: install_dir
    )

    uninstall(InstallerIdentity(), UninstallOptions())

    assert rig.scheduled == [install_dir.resolve()]


# ── the ordinary path ──────────────────────────────────────────────────────


def test_uninstall_removes_shortcuts_the_key_records(
    rig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_dir = _installed(tmp_path)
    _found(monkeypatch, _entry(install_dir))

    uninstall(InstallerIdentity(), UninstallOptions())

    assert rig.removed_shortcuts == [
        rig.paths.desktop_lnk,
        rig.paths.start_menu_lnk,
    ]
    assert rig.deleted_keys == [InstallerIdentity().uninstall_key]


def test_a_shortcut_the_user_declined_is_not_hunted_for(
    rig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_dir = _installed(tmp_path)
    _found(
        monkeypatch,
        _entry(install_dir, shortcut_desktop=False, shortcut_start_menu=True),
    )

    uninstall(InstallerIdentity(), UninstallOptions())

    assert rig.removed_shortcuts == [rig.paths.start_menu_lnk]


def test_user_data_goes_only_when_the_option_says_so(
    rig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_dir = _installed(tmp_path)
    _found(monkeypatch, _entry(install_dir))
    for name in ("data", "cache"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "meridian.db").write_text("rows", encoding="utf-8")

    uninstall(InstallerIdentity(), UninstallOptions(remove_user_data=False))

    assert (tmp_path / "data").exists()
    assert (tmp_path / "cache").exists()

    uninstall(InstallerIdentity(), UninstallOptions(remove_user_data=True))

    assert not (tmp_path / "data").exists()
    assert not (tmp_path / "cache").exists()


def test_the_install_directory_is_scheduled_for_deletion_last(
    rig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The installer cannot delete the directory it is running from."""
    install_dir = _installed(tmp_path)
    _found(monkeypatch, _entry(install_dir))

    uninstall(InstallerIdentity(), UninstallOptions())

    assert rig.scheduled == [install_dir.resolve()]


# ── the progress wrapper ───────────────────────────────────────────────────


def test_feedback_wrapper_reports_either_side_of_the_work(
    rig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_dir = _installed(tmp_path)
    _found(monkeypatch, _entry(install_dir))
    seen: list[str] = []

    uninstall_with_feedback(
        InstallerIdentity(), UninstallOptions(), progress=seen.append
    )

    assert len(seen) == 2
    assert rig.scheduled == [install_dir.resolve()]


def test_feedback_wrapper_stops_before_touching_anything_when_cancelled(
    rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _Cancelled:
        def is_set(self) -> bool:
            return True

    def _unreachable(key):  # noqa: ANN001, ANN202
        raise AssertionError("the registry was read despite cancellation")

    monkeypatch.setattr(uninstall_ops, "read_uninstall_entry", _unreachable)

    with pytest.raises(InstallerOperationError, match="Cancelled"):
        uninstall_with_feedback(
            InstallerIdentity(), UninstallOptions(), cancel_event=_Cancelled()
        )

    assert rig.scheduled == []
