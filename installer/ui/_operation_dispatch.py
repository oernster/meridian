"""Maps an `Operation` onto the `installer.ops` callable that performs it.

Extracted from `_main_window_actions`, which was 383 lines and so inside the
danger band of the module cap. This half is the natural seam: it touches no Qt
type, reads two attributes off the window and is otherwise a pure mapping from
an operation to a callable plus its keyword arguments. That makes it the only
part of the actions module testable without a `QApplication`, using a stand-in
window carrying `_identity` and optionally `_read_uninstall_entry`.

Behaviour is unchanged from the extracted original, including the lazy
`read_uninstall_entry` import that lets a caller inject its own reader.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from installer.ops.errors import InstallerOperationError
from installer.ops.install_ops import InstallOptions, install_new, upgrade_or_reinstall
from installer.ops.repair_ops import RepairOptions, repair
from installer.ops.uninstall_ops import UninstallOptions, uninstall_with_feedback
from installer.state.model import Operation
from installer.ui._main_window_types import UiSelections

if TYPE_CHECKING:  # pragma: no cover
    from installer.ui.main_window import InstallerMainWindow


def operation_callable(
    window: InstallerMainWindow,
    op: Operation,
    selections: UiSelections,
):
    read_entry = getattr(window, "_read_uninstall_entry", None)
    if read_entry is None:
        from installer.state.registry import read_uninstall_entry as read_entry

    entry = read_entry(window._identity.uninstall_key)
    current_install_dir = entry.install_location if entry else None

    if op == Operation.INSTALL:
        return (
            install_new,
            {
                "identity": window._identity,
                "opts": InstallOptions(
                    target_dir=selections.install_dir,
                    create_desktop_shortcut=selections.shortcut_desktop,
                    create_start_menu_shortcut=selections.shortcut_start_menu,
                ),
            },
        )

    if op in {Operation.UPGRADE, Operation.REINSTALL}:
        if current_install_dir is None:
            raise InstallerOperationError("No existing installation detected")
        return (
            upgrade_or_reinstall,
            {
                "identity": window._identity,
                "current_install_dir": current_install_dir,
                "opts": InstallOptions(
                    target_dir=selections.install_dir,
                    create_desktop_shortcut=selections.shortcut_desktop,
                    create_start_menu_shortcut=selections.shortcut_start_menu,
                ),
            },
        )

    if op == Operation.REPAIR:
        return (
            repair,
            {
                "identity": window._identity,
                "opts": RepairOptions(
                    restore_desktop_shortcut=selections.shortcut_desktop,
                    restore_start_menu_shortcut=selections.shortcut_start_menu,
                ),
            },
        )

    if op == Operation.UNINSTALL:
        return (
            uninstall_with_feedback,
            {
                "identity": window._identity,
                "opts": UninstallOptions(remove_user_data=True),
            },
        )

    raise InstallerOperationError(f"Unsupported operation: {op}")
