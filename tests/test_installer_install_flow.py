"""The install and upgrade flows end to end, against a temporary directory.

`test_installer_install_ops.py` covers the pieces. These cover the sequence:
extract, swap, deploy icons, copy the installer in for later uninstallation,
register the key, apply shortcuts, and clean the staging directory whatever
happened. The staging cleanup is the one that matters on a failure, since a
half-extracted payload left beside a user's install is both confusing and
large.

The payload is a real zip and the copies are real copies. Only the registry
and the COM shortcut call are replaced by recorders.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from installer.constants import InstallerIdentity
from installer.ops import install_ops
from installer.ops.errors import AppRunningError, InstallerOperationError
from installer.ops.install_ops import InstallOptions, install_new, upgrade_or_reinstall
from installer.ops.shortcuts import ShortcutPaths

_PAYLOAD = {
    "Meridian.exe": b"the application",
    "_internal/base_library.zip": b"the runtime",
}


class _Rig:
    def __init__(self) -> None:
        self.registered: list[dict] = []
        self.created: list[Path] = []
        self.running = False


@pytest.fixture
def rig(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):  # noqa: ANN201
    rec = _Rig()

    zip_path = tmp_path / "payload.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for name, data in _PAYLOAD.items():
            zf.writestr(name, data)

    paths = ShortcutPaths(
        desktop_lnk=tmp_path / "Desktop" / "Meridian.lnk",
        start_menu_lnk=tmp_path / "StartMenu" / "Meridian.lnk",
    )

    def _create(exe: Path, lnk: Path, *, working_dir=None) -> None:  # noqa: ANN001
        rec.created.append(lnk)

    monkeypatch.setattr(install_ops, "payload_zip_path", lambda: zip_path)
    monkeypatch.setattr(install_ops, "get_shortcut_paths", lambda identity: paths)
    monkeypatch.setattr(install_ops, "create_shortcut", _create)
    monkeypatch.setattr(
        install_ops,
        "write_uninstall_entry",
        lambda key, **kw: rec.registered.append(kw),
    )
    monkeypatch.setattr(install_ops, "is_app_running", lambda exe: rec.running)

    rec.zip_path = zip_path
    rec.paths = paths
    return rec


def _opts(
    target: Path, *, desktop: bool = True, start_menu: bool = False
):  # noqa: ANN202
    return InstallOptions(
        target_dir=target,
        create_desktop_shortcut=desktop,
        create_start_menu_shortcut=start_menu,
    )


def _staging_left(root: Path) -> list[Path]:
    return [p for p in root.iterdir() if p.name.startswith(".meridian_staging")]


# ── install ────────────────────────────────────────────────────────────────


def test_install_lays_down_the_payload_and_registers_itself(
    rig, tmp_path: Path
) -> None:
    target = tmp_path / "Meridian"
    seen: list[object] = []

    install_new(InstallerIdentity(), _opts(target), progress=seen.append)

    assert (target / "Meridian.exe").read_bytes() == _PAYLOAD["Meridian.exe"]
    assert (target / "_internal" / "base_library.zip").exists()
    assert len(rig.registered) == 1
    assert rig.registered[0]["install_location"] == target.resolve()
    assert seen[-1] == {"pct": 100, "message": "Completed"}


def test_install_copies_the_installer_in_so_it_can_be_uninstalled_later(
    rig, tmp_path: Path
) -> None:
    """The Apps list needs an uninstaller that survives the setup file being deleted."""
    target = tmp_path / "Meridian"
    identity = InstallerIdentity()

    install_new(identity, _opts(target))

    copied = identity.installer_exe_path(target.resolve())
    assert copied.is_file()
    assert rig.registered[0]["installer_path"] == str(copied)


def test_install_creates_only_the_shortcuts_that_were_selected(
    rig, tmp_path: Path
) -> None:
    target = tmp_path / "Meridian"

    install_new(InstallerIdentity(), _opts(target, desktop=True, start_menu=False))

    assert rig.created == [rig.paths.desktop_lnk]


def test_install_leaves_no_staging_directory_behind(rig, tmp_path: Path) -> None:
    target = tmp_path / "Meridian"

    install_new(InstallerIdentity(), _opts(target))

    assert _staging_left(tmp_path) == []


def test_a_failed_install_still_clears_its_staging_directory(
    rig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A half-extracted payload beside the install is confusing and large."""
    broken = tmp_path / "broken.zip"
    with zipfile.ZipFile(broken, "w") as zf:
        zf.writestr("Meridian.exe", "exe")
    monkeypatch.setattr(install_ops, "payload_zip_path", lambda: broken)
    target = tmp_path / "Meridian"

    with pytest.raises(InstallerOperationError, match="Payload is missing"):
        install_new(InstallerIdentity(), _opts(target))

    assert _staging_left(tmp_path) == []


def test_install_stops_when_cancelled_before_the_shortcuts(rig, tmp_path: Path) -> None:
    class _AfterExtract:
        def __init__(self) -> None:
            self.calls = 0

        def is_set(self) -> bool:
            self.calls += 1
            return self.calls > 2

    target = tmp_path / "Meridian"

    with pytest.raises(InstallerOperationError, match="Cancelled"):
        install_new(InstallerIdentity(), _opts(target), cancel_event=_AfterExtract())

    assert rig.created == []
    assert _staging_left(tmp_path) == []


# ── upgrade and reinstall ──────────────────────────────────────────────────


def test_upgrading_while_the_application_runs_is_refused(rig, tmp_path: Path) -> None:
    current = tmp_path / "Meridian"
    current.mkdir()
    (current / "Meridian.exe").write_bytes(b"old")
    rig.running = True

    with pytest.raises(AppRunningError, match="currently running"):
        upgrade_or_reinstall(
            InstallerIdentity(),
            current_install_dir=current,
            opts=_opts(current),
        )

    assert (current / "Meridian.exe").read_bytes() == b"old"


def test_upgrading_in_place_replaces_the_application(rig, tmp_path: Path) -> None:
    current = tmp_path / "Meridian"
    current.mkdir()
    (current / "Meridian.exe").write_bytes(b"old")

    upgrade_or_reinstall(
        InstallerIdentity(), current_install_dir=current, opts=_opts(current)
    )

    assert (current / "Meridian.exe").read_bytes() == _PAYLOAD["Meridian.exe"]
    assert _staging_left(tmp_path) == []


def test_upgrading_to_a_new_location_clears_the_old_one(rig, tmp_path: Path) -> None:
    current = tmp_path / "MeridianOld"
    current.mkdir()
    (current / "Meridian.exe").write_bytes(b"old")
    target = tmp_path / "MeridianNew"

    upgrade_or_reinstall(
        InstallerIdentity(), current_install_dir=current, opts=_opts(target)
    )

    assert (target / "Meridian.exe").read_bytes() == _PAYLOAD["Meridian.exe"]
    assert not current.exists(), "the previous installation was left behind"
    assert rig.registered[0]["install_location"] == target.resolve()


def test_upgrading_reports_progress_through_to_completion(rig, tmp_path: Path) -> None:
    current = tmp_path / "Meridian"
    current.mkdir()
    (current / "Meridian.exe").write_bytes(b"old")
    seen: list[object] = []

    upgrade_or_reinstall(
        InstallerIdentity(),
        current_install_dir=current,
        opts=_opts(current),
        progress=seen.append,
    )

    assert seen[-1] == {"pct": 100, "message": "Completed"}
    assert any(
        isinstance(m, dict) and "Replacing application files" in m["message"]
        for m in seen
    )
