"""The installer's failure paths.

Every branch here fires only when something has already gone wrong: a rename
across volumes, a locked shortcut, a registry key that will not delete, a
platform guard. They are the branches least likely to be exercised by hand and
the most likely to matter when they run, so they are pinned deliberately.

One of these records a defect rather than desired behaviour. See
`test_a_failed_rollback_currently_discards_the_backup`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from installer.constants import InstallerIdentity
from installer.ops import install_ops, repair_ops, shortcuts, uninstall_ops
from installer.ops.errors import InstallerOperationError
from installer.ops.install_ops import _swap_in_bundle
from installer.ops.payload import ManifestEntry, PayloadManifest
from installer.ops.repair_ops import RepairOptions
from installer.ops.shortcuts import (
    ShortcutPaths,
    _default_icon_location_for,
    get_shortcut_paths,
    remove_shortcut,
)
from installer.ops.uninstall_ops import UninstallOptions
from installer.ui._main_window_types import UiSelections
from installer.ui._operation_dispatch import operation_callable
from installer.state.model import Operation


def _bundle(root: Path, marker: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "Meridian.exe").write_text(marker, encoding="utf-8")
    (root / "_internal").mkdir(exist_ok=True)
    return root


def _fail_renames(monkeypatch: pytest.MonkeyPatch, doomed) -> None:  # noqa: ANN001
    real = Path.rename

    def fake(self: Path, target):  # noqa: ANN001
        if doomed(self):
            raise OSError("simulated rename failure")
        return real(self, target)

    monkeypatch.setattr(Path, "rename", fake)


def _fail_method(
    monkeypatch: pytest.MonkeyPatch, name: str, doomed
) -> None:  # noqa: ANN001
    real = getattr(Path, name)

    def fake(self: Path, *args, **kwargs):  # noqa: ANN002, ANN003
        if doomed(self):
            raise OSError(f"simulated {name} failure")
        return real(self, *args, **kwargs)

    monkeypatch.setattr(Path, name, fake)


def _fail_stat_after(
    monkeypatch: pytest.MonkeyPatch, doomed, after: int
) -> None:  # noqa: ANN001
    """Let the first `stat` calls through, then fail.

    `Path.exists()` routes through `stat`, so failing every call would break
    the existence check before the size check it is aimed at.
    """
    real = Path.stat
    seen = {"n": 0}

    def fake(self: Path, *args, **kwargs):  # noqa: ANN002, ANN003
        if doomed(self):
            seen["n"] += 1
            if seen["n"] > after:
                raise OSError("simulated stat failure")
        return real(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", fake)


# ── the bundle swap across a volume boundary ───────────────────────────────


def test_a_rename_across_volumes_falls_back_to_copying(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Staging and target land on different drives more often than not."""
    staging = _bundle(tmp_path / "staging", "new")
    target = tmp_path / "Meridian"
    _fail_renames(monkeypatch, lambda p: p == staging.resolve())

    _swap_in_bundle(staging, target)

    assert (target / "Meridian.exe").read_text(encoding="utf-8") == "new"
    assert not staging.exists()


def test_a_failed_rollback_currently_discards_the_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DEFECT, recorded rather than endorsed.

    When the swap fails and the rollback rename also fails, the `finally`
    block removes the backup directory anyway, because its only condition is
    that the backup still exists. The user is left with neither the new
    installation nor the old one.

    This test pins the behaviour as it stands so the fix has something to
    change. It is not a statement that this is correct.
    """
    target = _bundle(tmp_path / "Meridian", "old")
    staging = _bundle(tmp_path / "staging", "new")

    _fail_renames(monkeypatch, lambda p: p == staging.resolve() or ".old." in p.name)

    def _explode(*args, **kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("copy failed halfway")

    monkeypatch.setattr(install_ops.shutil, "copytree", _explode)

    with pytest.raises(RuntimeError, match="copy failed halfway"):
        _swap_in_bundle(staging, target)

    assert not target.exists()
    assert [p for p in tmp_path.iterdir() if ".old." in p.name] == []


# ── platform guards ────────────────────────────────────────────────────────


def test_shortcut_paths_are_refused_off_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shortcuts.os, "name", "posix")

    with pytest.raises(RuntimeError, match="Windows only"):
        get_shortcut_paths(InstallerIdentity())


def test_repair_is_refused_off_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repair_ops.os, "name", "posix")
    opts = RepairOptions(
        restore_desktop_shortcut=False, restore_start_menu_shortcut=False
    )

    with pytest.raises(InstallerOperationError, match="Windows-only"):
        repair_ops.repair(InstallerIdentity(), opts)


def test_uninstall_is_refused_off_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(uninstall_ops.os, "name", "posix")

    with pytest.raises(InstallerOperationError, match="Windows-only"):
        uninstall_ops.uninstall(InstallerIdentity(), UninstallOptions())


# ── degradation branches ───────────────────────────────────────────────────


def test_an_unresolvable_executable_still_yields_an_icon_location(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exe = tmp_path / "Meridian.exe"
    _fail_method(monkeypatch, "resolve", lambda p: p == exe)

    assert _default_icon_location_for(exe) == str(exe)


def test_a_shortcut_that_will_not_delete_does_not_fail_the_uninstall(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = tmp_path / "Programs"
    folder.mkdir()
    lnk = folder / "Meridian.lnk"
    lnk.write_text("lnk", encoding="utf-8")
    _fail_method(monkeypatch, "unlink", lambda p: p == lnk)

    remove_shortcut(lnk)

    assert lnk.exists()
    assert folder.exists(), "the folder was removed despite the shortcut surviving"


def test_a_folder_that_will_not_be_removed_is_not_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = tmp_path / "Programs"
    folder.mkdir()
    lnk = folder / "Meridian.lnk"
    lnk.write_text("lnk", encoding="utf-8")
    _fail_method(monkeypatch, "rmdir", lambda p: p == folder)

    remove_shortcut(lnk)

    assert not lnk.exists()
    assert folder.exists()


def test_an_unreadable_file_is_treated_as_needing_repair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A file that cannot be measured is exactly the one repair exists for."""
    import zipfile

    content = b"the runtime"
    entry_path = "_internal/base_library.zip"
    zip_path = tmp_path / "payload.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(entry_path, content)

    install_dir = tmp_path / "Meridian"
    (install_dir / "_internal").mkdir(parents=True)
    (install_dir / "Meridian.exe").write_bytes(b"exe")
    damaged = install_dir / "_internal" / "base_library.zip"
    damaged.write_bytes(b"wrong")

    from installer.state.registry import UninstallEntry

    monkeypatch.setattr(repair_ops, "payload_zip_path", lambda: zip_path)
    monkeypatch.setattr(
        repair_ops,
        "load_manifest",
        lambda: PayloadManifest(
            installer_version="2.5.0",
            entries=(ManifestEntry(path=entry_path, size=len(content), sha256="x"),),
        ),
    )
    monkeypatch.setattr(
        repair_ops,
        "read_uninstall_entry",
        lambda key: UninstallEntry(
            display_name="Meridian",
            display_version="2.5.0",
            install_location=install_dir,
            uninstall_string="unused",
        ),
    )
    monkeypatch.setattr(repair_ops, "is_app_running", lambda exe: False)
    monkeypatch.setattr(
        repair_ops,
        "get_shortcut_paths",
        lambda identity: ShortcutPaths(
            desktop_lnk=tmp_path / "Desktop.lnk",
            start_menu_lnk=tmp_path / "StartMenu.lnk",
        ),
    )
    monkeypatch.setattr(repair_ops, "write_uninstall_entry", lambda key, **kw: None)
    _fail_stat_after(monkeypatch, lambda p: p == damaged, after=1)

    repair_ops.repair(
        InstallerIdentity(),
        RepairOptions(
            restore_desktop_shortcut=False, restore_start_menu_shortcut=False
        ),
    )

    assert damaged.read_bytes() == content


def test_a_key_that_will_not_delete_does_not_abort_the_uninstall(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The files are already going; a stale Apps-list row is the lesser harm."""
    from installer.state.registry import UninstallEntry

    install_dir = tmp_path / "Meridian"
    install_dir.mkdir()
    scheduled: list[Path] = []

    def _refuse(key: str) -> None:
        raise OSError("access denied")

    monkeypatch.setattr(
        uninstall_ops,
        "read_uninstall_entry",
        lambda key: UninstallEntry(
            display_name="Meridian",
            display_version="2.5.0",
            install_location=install_dir,
            uninstall_string="unused",
        ),
    )
    monkeypatch.setattr(uninstall_ops, "is_app_running", lambda exe: False)
    monkeypatch.setattr(
        uninstall_ops,
        "get_shortcut_paths",
        lambda identity: ShortcutPaths(
            desktop_lnk=tmp_path / "Desktop.lnk",
            start_menu_lnk=tmp_path / "StartMenu.lnk",
        ),
    )
    monkeypatch.setattr(uninstall_ops, "remove_shortcut", lambda p: None)
    monkeypatch.setattr(uninstall_ops, "delete_uninstall_entry", _refuse)
    monkeypatch.setattr(uninstall_ops, "_schedule_delete_after_exit", scheduled.append)

    uninstall_ops.uninstall(
        InstallerIdentity(), UninstallOptions(remove_user_data=False)
    )

    assert scheduled == [install_dir.resolve()]


# ── dispatch without an injected reader ────────────────────────────────────


class _BareWindow:
    """No `_read_uninstall_entry`, so the dispatch imports the real one."""

    def __init__(self) -> None:
        self._identity = InstallerIdentity()


def test_the_dispatch_falls_back_to_the_real_registry_reader() -> None:
    selections = UiSelections(
        install_dir=Path("C:/target"),
        shortcut_desktop=False,
        shortcut_start_menu=False,
    )

    fn, kwargs = operation_callable(_BareWindow(), Operation.INSTALL, selections)

    assert fn is install_ops.install_new
    assert kwargs["opts"].target_dir == Path("C:/target")
