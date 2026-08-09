"""The rule deciding whether the installer starts the application when done.

`exe_to_launch` holds the whole decision precisely so that it can be measured.
The Qt slot that calls it and the two Windows side effects it selects between
are all outside the coverage gate; without these tests the rule would rest on a
handler nothing exercises.

Each guard is asserted on its own, so a failure names which one gave way rather
than reporting only that nothing started.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from installer.ops.launch_ops import LAUNCHABLE_OPERATIONS, exe_to_launch
from installer.state.model import Operation


@pytest.fixture()
def installed_exe(tmp_path: Path) -> Path:
    exe = tmp_path / "Meridian.exe"
    exe.write_bytes(b"")
    return exe


def test_launches_after_a_successful_install(installed_exe: Path) -> None:
    assert (
        exe_to_launch(
            op=Operation.INSTALL,
            succeeded=True,
            requested=True,
            installed_exe=installed_exe,
        )
        is installed_exe
    )


@pytest.mark.parametrize("op", sorted(LAUNCHABLE_OPERATIONS, key=lambda o: o.value))
def test_every_operation_that_leaves_an_installation_launches(
    op: Operation, installed_exe: Path
) -> None:
    """Install, upgrade, reinstall and repair all end with a usable install."""
    assert (
        exe_to_launch(
            op=op, succeeded=True, requested=True, installed_exe=installed_exe
        )
        is installed_exe
    )


def test_uninstall_never_launches(installed_exe: Path) -> None:
    """The one operation with nothing left to start, even if the file survives.

    The uninstall clears the executable. The check is on the operation rather
    than on what is left on disk: a deletion that has not finished settling
    must not be read as an application worth starting.
    """
    assert Operation.UNINSTALL not in LAUNCHABLE_OPERATIONS
    assert (
        exe_to_launch(
            op=Operation.UNINSTALL,
            succeeded=True,
            requested=True,
            installed_exe=installed_exe,
        )
        is None
    )


def test_an_unticked_checkbox_launches_nothing(installed_exe: Path) -> None:
    """Everything else says launch, so only the checkbox can be stopping it."""
    assert (
        exe_to_launch(
            op=Operation.INSTALL,
            succeeded=True,
            requested=False,
            installed_exe=installed_exe,
        )
        is None
    )


def test_a_failed_operation_launches_nothing(installed_exe: Path) -> None:
    assert (
        exe_to_launch(
            op=Operation.REPAIR,
            succeeded=False,
            requested=True,
            installed_exe=installed_exe,
        )
        is None
    )


def test_no_recorded_executable_launches_nothing() -> None:
    assert (
        exe_to_launch(
            op=Operation.INSTALL,
            succeeded=True,
            requested=True,
            installed_exe=None,
        )
        is None
    )


def test_a_recorded_executable_that_is_gone_launches_nothing(tmp_path: Path) -> None:
    """The path is re-checked rather than trusted.

    It was proved to exist when the state was last read, which was before the
    operation ran. An upgrade that moved the installation elsewhere leaves the
    old path behind; starting it would run the wrong copy.
    """
    assert (
        exe_to_launch(
            op=Operation.UPGRADE,
            succeeded=True,
            requested=True,
            installed_exe=tmp_path / "Meridian.exe",
        )
        is None
    )
