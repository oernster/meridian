"""The installer's operation dispatch, pinned without a QApplication.

`operation_callable` was extracted from `installer/ui/_main_window_actions.py`,
which sat at 383 lines inside the danger band of the module cap. It is the one
part of that module touching no Qt type: it reads two attributes off the
window and is otherwise a pure mapping from an `Operation` to the
`installer.ops` callable that performs it, plus that callable's keyword
arguments.

Nothing under `installer/` had a test before this file. These pin the mapping
so the extraction is verifiable rather than merely plausible, and so a later
change to the operation set fails here rather than in a user's install.

The window stand-in is hand written rather than mocked, and the ops callables
are compared by identity: the dispatch's job is choosing them, never running
them, so none is invoked here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from installer.constants import InstallerIdentity
from installer.ops.errors import InstallerOperationError
from installer.ops.install_ops import install_new, upgrade_or_reinstall
from installer.ops.repair_ops import repair
from installer.ops.uninstall_ops import uninstall_with_feedback
from installer.state.model import Operation
from installer.state.registry import UninstallEntry
from installer.ui._main_window_types import UiSelections
from installer.ui._operation_dispatch import operation_callable

_TARGET = Path("C:/Users/example/AppData/Local/Meridian")
_EXISTING = Path("C:/Users/example/AppData/Local/MeridianOld")

_SELECTIONS = UiSelections(
    install_dir=_TARGET,
    shortcut_desktop=True,
    shortcut_start_menu=False,
)


class _StubWindow:
    """Carries only the two attributes the dispatch reads off a window."""

    def __init__(self, entry: UninstallEntry | None = None) -> None:
        self._identity = InstallerIdentity()
        self._entry = entry
        self.keys_read: list[str] = []

    def _read_uninstall_entry(self, key: str) -> UninstallEntry | None:
        self.keys_read.append(key)
        return self._entry


def _installed(location: Path = _EXISTING) -> UninstallEntry:
    return UninstallEntry(
        display_name="Meridian",
        display_version="2.4.0",
        install_location=location,
        uninstall_string="unused",
    )


def test_install_selects_install_new_and_carries_the_selections() -> None:
    window = _StubWindow()
    fn, kwargs = operation_callable(window, Operation.INSTALL, _SELECTIONS)

    assert fn is install_new
    assert kwargs["identity"] is window._identity
    opts = kwargs["opts"]
    assert opts.target_dir == _TARGET
    assert opts.create_desktop_shortcut is True
    assert opts.create_start_menu_shortcut is False


def test_dispatch_reads_the_entry_under_the_identity_key() -> None:
    window = _StubWindow()
    operation_callable(window, Operation.INSTALL, _SELECTIONS)
    assert window.keys_read == [window._identity.uninstall_key]


@pytest.mark.parametrize("op", [Operation.UPGRADE, Operation.REINSTALL])
def test_upgrade_and_reinstall_pass_the_existing_location(op: Operation) -> None:
    window = _StubWindow(_installed())
    fn, kwargs = operation_callable(window, op, _SELECTIONS)

    assert fn is upgrade_or_reinstall
    assert kwargs["current_install_dir"] == _EXISTING
    assert kwargs["opts"].target_dir == _TARGET


@pytest.mark.parametrize("op", [Operation.UPGRADE, Operation.REINSTALL])
def test_upgrade_without_an_installation_is_refused(op: Operation) -> None:
    window = _StubWindow(None)
    with pytest.raises(InstallerOperationError, match="No existing installation"):
        operation_callable(window, op, _SELECTIONS)


def test_repair_restores_whichever_shortcuts_are_selected() -> None:
    window = _StubWindow(_installed())
    fn, kwargs = operation_callable(window, Operation.REPAIR, _SELECTIONS)

    assert fn is repair
    assert kwargs["opts"].restore_desktop_shortcut is True
    assert kwargs["opts"].restore_start_menu_shortcut is False


def test_uninstall_always_removes_user_data() -> None:
    window = _StubWindow(_installed())
    fn, kwargs = operation_callable(window, Operation.UNINSTALL, _SELECTIONS)

    assert fn is uninstall_with_feedback
    assert kwargs["opts"].remove_user_data is True


def test_an_unknown_operation_is_refused_rather_than_guessed() -> None:
    window = _StubWindow()
    with pytest.raises(InstallerOperationError, match="Unsupported operation"):
        operation_callable(window, "not-an-operation", _SELECTIONS)
