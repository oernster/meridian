"""The repair operation.

Repair walks the payload manifest, compares each file on disk against its
recorded size and hash then rewrites only what differs. The interesting cases
are the ones that decide whether a file is rewritten at all: an intact file
must be left alone, so a repair of a healthy installation is close to a no-op
rather than a silent reinstall.

The payload and manifest are built for real in `tmp_path`. Only the Windows
edges are replaced by hand-written recorders.
"""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest

from installer.constants import InstallerIdentity
from installer.ops import repair_ops
from installer.ops.errors import AppRunningError, InstallerOperationError
from installer.ops.payload import ManifestEntry, PayloadManifest
from installer.ops.repair_ops import RepairOptions, repair
from installer.ops.shortcuts import ShortcutPaths
from installer.state.registry import UninstallEntry

_FILES = {
    "Meridian.exe": b"the application",
    "_internal/base_library.zip": b"the runtime",
}


class _Rig:
    def __init__(self) -> None:
        self.created: list[Path] = []
        self.written: list[dict] = []
        self.running = False
        self.progress: list[str] = []


def _manifest() -> PayloadManifest:
    entries = tuple(
        ManifestEntry(
            path=name,
            size=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
        )
        for name, data in _FILES.items()
    )
    return PayloadManifest(installer_version="2.5.0", entries=entries)


def _entry(location: Path) -> UninstallEntry:
    return UninstallEntry(
        display_name="Meridian",
        display_version="2.4.0",
        install_location=location,
        uninstall_string='"setup.exe" --uninstall',
        installer_path="setup.exe",
    )


@pytest.fixture
def rig(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):  # noqa: ANN201
    rec = _Rig()

    zip_path = tmp_path / "payload.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for name, data in _FILES.items():
            zf.writestr(name, data)

    install_dir = tmp_path / "Meridian"
    install_dir.mkdir()

    paths = ShortcutPaths(
        desktop_lnk=tmp_path / "Desktop" / "Meridian.lnk",
        start_menu_lnk=tmp_path / "StartMenu" / "Meridian.lnk",
    )

    def _create(exe: Path, lnk: Path, *, working_dir=None) -> None:  # noqa: ANN001
        rec.created.append(lnk)

    monkeypatch.setattr(repair_ops, "payload_zip_path", lambda: zip_path)
    monkeypatch.setattr(repair_ops, "load_manifest", _manifest)
    monkeypatch.setattr(repair_ops, "get_shortcut_paths", lambda identity: paths)
    monkeypatch.setattr(repair_ops, "create_shortcut", _create)
    monkeypatch.setattr(
        repair_ops, "write_uninstall_entry", lambda key, **kw: rec.written.append(kw)
    )
    monkeypatch.setattr(repair_ops, "is_app_running", lambda exe: rec.running)
    monkeypatch.setattr(
        repair_ops, "read_uninstall_entry", lambda key: _entry(install_dir)
    )

    rec.install_dir = install_dir
    rec.paths = paths
    return rec


def _place(install_dir: Path, name: str, data: bytes) -> Path:
    dst = install_dir / name
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)
    return dst


def _intact(install_dir: Path) -> None:
    for name, data in _FILES.items():
        _place(install_dir, name, data)


_BOTH = RepairOptions(restore_desktop_shortcut=True, restore_start_menu_shortcut=True)
_NEITHER = RepairOptions(
    restore_desktop_shortcut=False, restore_start_menu_shortcut=False
)


# ── refusals ───────────────────────────────────────────────────────────────


def test_repairing_something_not_installed_is_refused(
    rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(repair_ops, "read_uninstall_entry", lambda key: None)

    with pytest.raises(InstallerOperationError, match="not installed"):
        repair(InstallerIdentity(), _BOTH)


def test_repairing_a_key_pointing_at_a_missing_directory_is_refused(
    rig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The key can outlive the directory if a user deletes it by hand."""
    monkeypatch.setattr(
        repair_ops, "read_uninstall_entry", lambda key: _entry(tmp_path / "gone")
    )

    with pytest.raises(InstallerOperationError, match="not installed"):
        repair(InstallerIdentity(), _BOTH)


def test_repairing_while_the_application_runs_is_refused(rig) -> None:
    _intact(rig.install_dir)
    rig.running = True

    with pytest.raises(AppRunningError, match="currently running"):
        repair(InstallerIdentity(), _BOTH)

    assert rig.written == []


def test_cancellation_stops_the_walk(rig) -> None:
    _intact(rig.install_dir)

    class _Cancelled:
        def is_set(self) -> bool:
            return True

    with pytest.raises(InstallerOperationError, match="Cancelled"):
        repair(InstallerIdentity(), _BOTH, cancel_event=_Cancelled())

    assert rig.written == []


# ── what gets rewritten ────────────────────────────────────────────────────


def test_a_missing_file_is_restored(rig) -> None:
    _place(rig.install_dir, "Meridian.exe", _FILES["Meridian.exe"])

    repair(InstallerIdentity(), _NEITHER)

    restored = rig.install_dir / "_internal" / "base_library.zip"
    assert restored.read_bytes() == _FILES["_internal/base_library.zip"]


def test_a_file_of_the_wrong_length_is_restored(rig) -> None:
    _intact(rig.install_dir)
    damaged = _place(rig.install_dir, "Meridian.exe", b"truncated")

    repair(InstallerIdentity(), _NEITHER)

    assert damaged.read_bytes() == _FILES["Meridian.exe"]


def test_a_file_of_the_right_length_but_the_wrong_content_is_restored(rig) -> None:
    """Size alone would pass this one, which is why the hash is checked."""
    _intact(rig.install_dir)
    original = _FILES["Meridian.exe"]
    damaged = _place(rig.install_dir, "Meridian.exe", b"X" * len(original))

    repair(InstallerIdentity(), _NEITHER)

    assert damaged.read_bytes() == original


def test_an_intact_file_is_left_alone(rig) -> None:
    """A repair of a healthy install must not rewrite every file."""
    _intact(rig.install_dir)
    exe = rig.install_dir / "Meridian.exe"
    before = exe.stat().st_mtime_ns

    repair(InstallerIdentity(), _NEITHER)

    assert exe.stat().st_mtime_ns == before
    assert exe.read_bytes() == _FILES["Meridian.exe"]


def test_a_directory_where_a_file_belongs_is_reported_rather_than_ignored(
    rig,
) -> None:
    """`stat` on a directory succeeds, so the size check alone would misread it."""
    _intact(rig.install_dir)
    exe = rig.install_dir / "Meridian.exe"
    exe.unlink()
    exe.mkdir()

    with pytest.raises(OSError):
        repair(InstallerIdentity(), _NEITHER)


# ── shortcuts and registry ─────────────────────────────────────────────────


def test_only_missing_shortcuts_are_recreated(rig) -> None:
    _intact(rig.install_dir)
    rig.paths.desktop_lnk.parent.mkdir(parents=True, exist_ok=True)
    rig.paths.desktop_lnk.write_text("still here", encoding="utf-8")

    repair(InstallerIdentity(), _BOTH)

    assert rig.created == [rig.paths.start_menu_lnk]


def test_an_existing_start_menu_entry_is_not_recreated(rig) -> None:
    _intact(rig.install_dir)
    rig.paths.start_menu_lnk.parent.mkdir(parents=True, exist_ok=True)
    rig.paths.start_menu_lnk.write_text("still here", encoding="utf-8")

    repair(InstallerIdentity(), _BOTH)

    assert rig.created == [rig.paths.desktop_lnk]


def test_no_shortcut_is_created_when_neither_is_wanted(rig) -> None:
    _intact(rig.install_dir)

    repair(InstallerIdentity(), _NEITHER)

    assert rig.created == []


def test_repair_rewrites_the_key_keeping_what_the_install_recorded(rig) -> None:
    _intact(rig.install_dir)

    repair(InstallerIdentity(), _BOTH)

    assert len(rig.written) == 1
    written = rig.written[0]
    assert written["display_version"] == "2.4.0"
    assert written["uninstall_string"] == '"setup.exe" --uninstall'
    assert written["installer_path"] == "setup.exe"
    assert written["shortcut_desktop"] is True
    assert written["shortcut_start_menu"] is True


def test_repair_reports_progress_for_each_file(rig) -> None:
    _intact(rig.install_dir)
    seen: list[object] = []

    repair(InstallerIdentity(), _BOTH, progress=seen.append)

    messages = [p["message"] for p in seen]
    assert any("Verifying" in m for m in messages)
    assert any("Restoring shortcuts" in m for m in messages)
    assert any("Restoring registry metadata" in m for m in messages)


def test_repair_moves_the_progress_bar_rather_than_only_the_status_line(rig) -> None:
    """Every payload carries a percentage, which is what fills the bar.

    A repair used to report its work in bare strings. The window writes those
    to the status line and leaves the bar alone, so the whole operation ran
    behind an empty groove that read as a progress bar failing to appear.
    """
    _intact(rig.install_dir)
    seen: list[object] = []

    repair(InstallerIdentity(), _BOTH, progress=seen.append)

    assert seen, "a repair that reports nothing cannot show progress at all"
    assert all(isinstance(p, dict) and isinstance(p["pct"], int) for p in seen)

    percentages = [p["pct"] for p in seen]
    assert percentages == sorted(percentages), "the bar must never run backwards"
    assert percentages[-1] == 100
    assert min(percentages) > 0
