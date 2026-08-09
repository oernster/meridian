"""The remaining install-time fallbacks.

Icon deployment, the staging pre-clean and the shortcut clears each degrade
rather than fail, so nothing surfaces when they misfire. They are covered here
so the degradation is a decision on record rather than an accident.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pytest

from installer.constants import InstallerIdentity
from installer.ops import install_ops
from installer.ops.install_ops import (
    InstallOptions,
    _apply_shortcuts,
    _deploy_runtime_icon_assets,
    install_new,
    upgrade_or_reinstall,
)
from installer.ops.shortcuts import ShortcutPaths

_PAYLOAD = {"Meridian.exe": b"the application", "_internal/base.zip": b"the runtime"}


def _payload_zip(tmp_path: Path) -> Path:
    zip_path = tmp_path / "payload.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for name, data in _PAYLOAD.items():
            zf.writestr(name, data)
    return zip_path


# ── icon deployment ────────────────────────────────────────────────────────


def test_icons_are_copied_from_the_project_root(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "meridian.png").write_bytes(b"png")
    install_dir = tmp_path / "install"
    install_dir.mkdir()

    _deploy_runtime_icon_assets(install_dir=install_dir, project_root=root)

    assert (install_dir / "meridian.png").read_bytes() == b"png"


def test_a_frozen_bundle_is_searched_when_the_project_root_has_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Running frozen, the assets sit in the extraction directory instead."""
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "meridian.ico").write_bytes(b"ico")
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)
    install_dir = tmp_path / "install"
    install_dir.mkdir()

    _deploy_runtime_icon_assets(install_dir=install_dir, project_root=tmp_path / "none")

    assert (install_dir / "meridian.ico").read_bytes() == b"ico"


def test_an_asset_present_nowhere_is_skipped(tmp_path: Path) -> None:
    install_dir = tmp_path / "install"
    install_dir.mkdir()

    _deploy_runtime_icon_assets(
        install_dir=install_dir, project_root=tmp_path / "empty"
    )

    assert list(install_dir.iterdir()) == []


def test_an_icon_that_will_not_copy_does_not_fail_the_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "meridian.png").write_bytes(b"png")
    install_dir = tmp_path / "install"
    install_dir.mkdir()

    def _refuse(src, dst):  # noqa: ANN001
        raise OSError("access denied")

    monkeypatch.setattr(install_ops.shutil, "copy2", _refuse)

    _deploy_runtime_icon_assets(install_dir=install_dir, project_root=root)

    assert list(install_dir.iterdir()) == []


# ── staging pre-clean ──────────────────────────────────────────────────────


class _FixedHex:
    hex = "fixed"


def test_a_leftover_staging_directory_is_cleared_before_use(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A previous run killed partway leaves one behind under a stale name."""
    monkeypatch.setattr(install_ops, "payload_zip_path", lambda: _payload_zip(tmp_path))
    monkeypatch.setattr(install_ops.uuid, "uuid4", lambda: _FixedHex)
    monkeypatch.setattr(install_ops, "write_uninstall_entry", lambda key, **kw: None)
    monkeypatch.setattr(
        install_ops,
        "get_shortcut_paths",
        lambda identity: ShortcutPaths(
            desktop_lnk=tmp_path / "d.lnk", start_menu_lnk=tmp_path / "s.lnk"
        ),
    )

    stale = tmp_path / ".meridian_staging.install.fixed"
    stale.mkdir()
    (stale / "junk.txt").write_text("left over", encoding="utf-8")

    target = tmp_path / "Meridian"
    install_new(
        InstallerIdentity(),
        InstallOptions(
            target_dir=target,
            create_desktop_shortcut=False,
            create_start_menu_shortcut=False,
        ),
    )

    assert (target / "Meridian.exe").read_bytes() == _PAYLOAD["Meridian.exe"]
    assert not (target / "junk.txt").exists()


def test_an_upgrade_clears_its_own_leftover_staging_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(install_ops, "payload_zip_path", lambda: _payload_zip(tmp_path))
    monkeypatch.setattr(install_ops.uuid, "uuid4", lambda: _FixedHex)
    monkeypatch.setattr(install_ops, "write_uninstall_entry", lambda key, **kw: None)
    monkeypatch.setattr(install_ops, "is_app_running", lambda exe: False)
    monkeypatch.setattr(
        install_ops,
        "get_shortcut_paths",
        lambda identity: ShortcutPaths(
            desktop_lnk=tmp_path / "d.lnk", start_menu_lnk=tmp_path / "s.lnk"
        ),
    )

    stale = tmp_path / ".meridian_staging.upgrade.fixed"
    stale.mkdir()

    current = tmp_path / "Meridian"
    current.mkdir()
    (current / "Meridian.exe").write_bytes(b"old")

    upgrade_or_reinstall(
        InstallerIdentity(),
        current_install_dir=current,
        opts=InstallOptions(
            target_dir=current,
            create_desktop_shortcut=False,
            create_start_menu_shortcut=False,
        ),
    )

    assert (current / "Meridian.exe").read_bytes() == _PAYLOAD["Meridian.exe"]


def test_an_old_install_that_will_not_delete_does_not_fail_the_upgrade(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The new install is already in place, so stale files are not a failure."""
    monkeypatch.setattr(install_ops, "payload_zip_path", lambda: _payload_zip(tmp_path))
    monkeypatch.setattr(install_ops, "write_uninstall_entry", lambda key, **kw: None)
    monkeypatch.setattr(install_ops, "is_app_running", lambda exe: False)
    monkeypatch.setattr(
        install_ops,
        "get_shortcut_paths",
        lambda identity: ShortcutPaths(
            desktop_lnk=tmp_path / "d.lnk", start_menu_lnk=tmp_path / "s.lnk"
        ),
    )

    current = tmp_path / "MeridianOld"
    current.mkdir()
    (current / "Meridian.exe").write_bytes(b"old")
    target = tmp_path / "MeridianNew"

    real_rmtree = install_ops.shutil.rmtree

    def _refuse(path, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        if Path(path) == current.resolve():
            raise OSError("access denied")
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(install_ops.shutil, "rmtree", _refuse)

    upgrade_or_reinstall(
        InstallerIdentity(),
        current_install_dir=current,
        opts=InstallOptions(
            target_dir=target,
            create_desktop_shortcut=False,
            create_start_menu_shortcut=False,
        ),
    )

    assert (target / "Meridian.exe").read_bytes() == _PAYLOAD["Meridian.exe"]


def test_a_partly_written_target_is_not_overwritten_by_the_rollback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The copy can fail after creating the directory, so the target exists.

    The rollback is guarded on the target being absent. Renaming the backup
    over a partly-written target would fail anyway, so the original error is
    raised untouched and the backup is cleared.
    """
    from installer.ops.install_ops import _swap_in_bundle

    target = tmp_path / "Meridian"
    target.mkdir()
    (target / "Meridian.exe").write_bytes(b"old")
    staging = tmp_path / "staging"
    staging.mkdir()
    (staging / "Meridian.exe").write_bytes(b"new")

    real_rename = Path.rename

    def _fail_staging(self: Path, other):  # noqa: ANN001
        if self == staging.resolve():
            raise OSError("cross-device")
        return real_rename(self, other)

    def _half_copy(src, dst, **kwargs):  # noqa: ANN001, ANN003
        Path(dst).mkdir(parents=True, exist_ok=True)
        raise RuntimeError("copy failed after creating the directory")

    monkeypatch.setattr(Path, "rename", _fail_staging)
    monkeypatch.setattr(install_ops.shutil, "copytree", _half_copy)

    with pytest.raises(RuntimeError, match="after creating the directory"):
        _swap_in_bundle(staging, target)

    assert target.exists()
    assert [p for p in tmp_path.iterdir() if ".old." in p.name] == []


def test_a_failed_upgrade_clears_its_staging_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from installer.ops.errors import InstallerOperationError

    broken = tmp_path / "broken.zip"
    with zipfile.ZipFile(broken, "w") as zf:
        zf.writestr("Meridian.exe", "exe")
    monkeypatch.setattr(install_ops, "payload_zip_path", lambda: broken)
    monkeypatch.setattr(install_ops, "is_app_running", lambda exe: False)

    current = tmp_path / "Meridian"
    current.mkdir()
    (current / "Meridian.exe").write_bytes(b"old")

    with pytest.raises(InstallerOperationError, match="Payload is missing"):
        upgrade_or_reinstall(
            InstallerIdentity(),
            current_install_dir=current,
            opts=InstallOptions(
                target_dir=current,
                create_desktop_shortcut=False,
                create_start_menu_shortcut=False,
            ),
        )

    leftovers = [p for p in tmp_path.iterdir() if ".meridian_staging" in p.name]
    assert leftovers == []


# ── clearing declined shortcuts ────────────────────────────────────────────


@pytest.mark.parametrize("attr", ["desktop_lnk", "start_menu_lnk"])
def test_a_declined_shortcut_that_will_not_delete_is_not_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, attr: str
) -> None:
    paths = ShortcutPaths(
        desktop_lnk=tmp_path / "Desktop.lnk",
        start_menu_lnk=tmp_path / "StartMenu.lnk",
    )
    doomed = getattr(paths, attr)
    doomed.write_text("stale", encoding="utf-8")
    monkeypatch.setattr(install_ops, "get_shortcut_paths", lambda identity: paths)

    real_unlink = Path.unlink

    def _refuse(self: Path, *args, **kwargs):  # noqa: ANN002, ANN003
        if self == doomed:
            raise OSError("locked")
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", _refuse)

    _apply_shortcuts(
        InstallerIdentity(),
        tmp_path,
        InstallOptions(
            target_dir=tmp_path,
            create_desktop_shortcut=False,
            create_start_menu_shortcut=False,
        ),
    )

    assert doomed.exists()
