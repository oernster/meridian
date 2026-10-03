from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMessageBox

from installer.cli import wants_remove_user_data
from installer.ops.uninstall_ops import uninstall_confirmation_text
from installer.state.model import Operation

if TYPE_CHECKING:  # pragma: no cover
    from installer.ui.main_window import InstallerMainWindow


def confirm_and_run_uninstall(window: InstallerMainWindow) -> None:
    box = QMessageBox(window)
    box.setIcon(QMessageBox.Warning)
    box.setWindowTitle("Confirm uninstall")
    # The same decision `_operation_dispatch` hands the uninstall, so the box
    # says what the operation will do with the user's data.
    box.setText(uninstall_confirmation_text(wants_remove_user_data(window._cli_args)))
    uninstall_btn = box.addButton("Uninstall", QMessageBox.AcceptRole)
    box.addButton("Cancel", QMessageBox.RejectRole)
    box.exec()
    if box.clickedButton() == uninstall_btn:
        window._request_operation(Operation.UNINSTALL)
