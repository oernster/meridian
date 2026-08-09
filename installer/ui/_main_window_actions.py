from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from installer.state.model import InstalledInfo, InstallerState, Operation
from installer.ui._main_window_types import UiSelections
from installer.ui._operation_dispatch import operation_callable
from installer.ui.licence_dialog import InstallerLicenceDialog
from meridian.version import APP_NAME, __version__

if TYPE_CHECKING:  # pragma: no cover
    from installer.ui.main_window import InstallerMainWindow


def _wire(connect: Callable[[], None]) -> None:
    """Run one signal connection, tolerating a control this layout never built.

    The window builds its controls conditionally, so a control named here can
    be absent. Degrading to an unwired control is deliberate: aborting the
    wiring partway would leave a window whose remaining buttons do nothing,
    which is worse than one button that does nothing.

    The whole connection runs inside the guard, attribute lookup included,
    because the missing piece is usually the widget rather than the slot.
    """
    try:
        connect()
    except Exception:
        pass


def connect_signals(window: InstallerMainWindow) -> None:
    _wire(lambda: window._licence_btn.clicked.connect(window._show_installer_licence))
    _wire(lambda: window._theme_toggle_btn.clicked.connect(window._toggle_theme))
    if getattr(window, "_browse_btn", None) is not None:
        _wire(lambda: window._browse_btn.clicked.connect(window._browse_install_dir))
    _wire(
        lambda: window._btn_primary_left.clicked.connect(
            lambda: window._request_operation(Operation.INSTALL)
        )
    )
    _wire(
        lambda: window._btn_primary_right.clicked.connect(
            lambda: window._request_operation(Operation.REPAIR)
        )
    )
    _wire(
        lambda: window._btn_uninstall.clicked.connect(
            lambda: window._request_operation(Operation.UNINSTALL)
        )
    )


def show_installer_licence(window: InstallerMainWindow) -> None:
    existing = getattr(window, "_installer_licence_dialog", None)
    if isinstance(existing, QDialog):
        # The Python reference outlives the C++ widget, so raising an
        # already-destroyed dialog raises rather than returning. Falling
        # through builds a fresh one, which is the desired outcome anyway.
        try:
            existing.raise_()
            existing.activateWindow()
            return
        except Exception:
            pass
    dlg = InstallerLicenceDialog(parent=window)
    window._installer_licence_dialog = dlg

    def _clear_ref() -> None:
        # Runs while the dialog is being torn down, by which point the window
        # may be going too. Failing to drop the reference costs one dialog's
        # worth of memory for the rest of the process, so it is not worth
        # raising out of a teardown callback.
        try:
            if getattr(window, "_installer_licence_dialog", None) is dlg:
                window._installer_licence_dialog = None
        except Exception:
            pass

    # Losing this connection only means the reference is cleared later, when
    # the dialog is reopened. The dialog itself must still be shown.
    try:
        dlg.finished.connect(_clear_ref)
    except Exception:
        pass

    dlg.open()


def default_install_dir() -> Path:
    local = os.getenv("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(local) / APP_NAME


def browse_install_dir(window: InstallerMainWindow) -> None:
    current = Path(
        window._install_dir_edit.text().strip() or str(default_install_dir())
    )
    chosen = QFileDialog.getExistingDirectory(
        window, "Select installation directory", str(current)
    )
    if chosen:
        window._install_dir_edit.setText(chosen)


def refresh_state(window: InstallerMainWindow) -> None:
    read_entry = getattr(window, "_read_uninstall_entry", None)
    if read_entry is None:
        from installer.state.registry import read_uninstall_entry as read_entry

    entry = read_entry(window._identity.uninstall_key)
    installed = None
    if entry and entry.install_location.exists():
        exe = entry.install_location / "Meridian.exe"
        if exe.exists():
            installed = InstalledInfo(
                version=entry.display_version, location=entry.install_location
            )

    state = InstallerState(installer_version=__version__, installed=installed)
    window._state = state

    window._status_line.setText(state.status_line(APP_NAME))

    allowed = state.allowed_operations()
    set_buttons_for_allowed_ops(window, allowed)

    if entry is not None:
        if entry.shortcut_desktop is not None:
            window._desktop_cb.setChecked(entry.shortcut_desktop)
        if entry.shortcut_start_menu is not None:
            window._startmenu_cb.setChecked(entry.shortcut_start_menu)

        window._install_dir_edit.setText(str(entry.install_location))


def set_buttons_for_allowed_ops(
    window: InstallerMainWindow,
    allowed: set[Operation] | frozenset[Operation],
) -> None:
    window._btn_uninstall.setVisible(Operation.UNINSTALL in allowed)

    primary_ops: list[Operation] = [
        op
        for op in [
            Operation.INSTALL,
            Operation.UPGRADE,
            Operation.REINSTALL,
            Operation.REPAIR,
        ]
        if op in allowed
    ]
    left = primary_ops[0] if primary_ops else None
    right = primary_ops[1] if len(primary_ops) > 1 else None

    def _label(op: Operation) -> str:
        return {
            Operation.INSTALL: "Install",
            Operation.UPGRADE: "Upgrade",
            Operation.REINSTALL: "Reinstall",
            Operation.REPAIR: "Repair",
        }[op]

    def _bind(button, op: Operation | None) -> None:  # noqa: ANN001
        """Relabel one primary button and point it at `op`, or hide it."""
        if op is None:
            button.setVisible(False)
            return
        button.setVisible(True)
        button.setText(_label(op))
        # Qt raises when a button carries no connection, which is the normal
        # case the first time it is labelled, so an empty button is expected
        # rather than an error worth surfacing.
        try:
            button.clicked.disconnect()
        except Exception:
            pass
        button.clicked.connect(lambda: window._request_operation(op))

    _bind(window._btn_primary_left, left)
    _bind(window._btn_primary_right, right)


def validate_install_dir(path: Path) -> bool:
    """Probe the directory by writing to it, since permission is not readable.

    Any failure means the same thing to the caller: this installer cannot
    write here without elevation. The specific errno does not change the
    answer, and the caller reports it as one message.
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
        test = path / ".meridian_installer_write_test"
        test.write_text("ok", encoding="utf-8")
        test.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def current_selections(window: InstallerMainWindow) -> UiSelections:
    p = Path(window._install_dir_edit.text().strip() or str(default_install_dir()))
    return UiSelections(
        install_dir=p,
        shortcut_desktop=bool(window._desktop_cb.isChecked()),
        shortcut_start_menu=bool(window._startmenu_cb.isChecked()),
    )


def request_operation(window: InstallerMainWindow, op: Operation) -> None:
    selections = current_selections(window)
    if op in {Operation.INSTALL, Operation.UPGRADE, Operation.REINSTALL}:
        if not validate_install_dir(selections.install_dir):
            QMessageBox.critical(
                window,
                "Invalid installation directory",
                "The selected installation directory is not writable without "
                "administrator privileges.",
            )
            return

    if window._op_controller.is_running:
        return

    refresh_state(window)

    window._set_ui_busy(True)
    window._progress.setText("Working...")
    window._progress_bar.setValue(0)

    fn, kwargs = operation_callable(window, op, selections)
    window._debug_last_op = op
    window._debug_last_kwargs = kwargs
    window._op_controller.start(
        fn,
        kwargs=kwargs,
        on_progress=window._on_progress,
        on_finished=lambda r: window._on_operation_finished(op, r),
        on_app_running=lambda msg: window._on_app_running(op, msg),
    )


def on_progress(window: InstallerMainWindow, payload) -> None:  # noqa: ANN001
    if isinstance(payload, dict):
        pct = payload.get("pct")
        msg = payload.get("message", "")
        if isinstance(pct, int):
            window._progress_bar.setValue(max(0, min(100, pct)))
        if msg:
            window._progress.setText(str(msg))
        return

    if isinstance(payload, str) and payload:
        window._progress.setText(payload)


def set_ui_busy(window: InstallerMainWindow, busy: bool) -> None:
    window._progress_bar.setVisible(busy)
    for w in [
        window._btn_primary_left,
        window._btn_primary_right,
        window._btn_uninstall,
        window._licence_btn,
        window._theme_toggle_btn,
        window._install_dir_edit,
        window._desktop_cb,
        window._startmenu_cb,
    ]:
        w.setEnabled(not busy)


def on_app_running(window: InstallerMainWindow, op: Operation, msg: str) -> None:
    del msg

    window._set_ui_busy(False)
    window._progress.setText("")
    box = QMessageBox(window)
    box.setIcon(QMessageBox.Warning)
    box.setWindowTitle(f"{APP_NAME} is running")
    box.setText(f"Please close {APP_NAME} and click Retry.")
    retry = box.addButton("Retry", QMessageBox.AcceptRole)
    box.addButton("Cancel", QMessageBox.RejectRole)
    box.exec()
    if box.clickedButton() == retry:
        window._request_operation(op)


def on_operation_finished(
    window: InstallerMainWindow,
    op: Operation,
    result,
) -> None:  # noqa: ANN001
    window._set_ui_busy(False)
    if result.ok:
        window._progress_bar.setValue(100)
        if op == Operation.UNINSTALL:
            window._progress.setText("Uninstalled")
        else:
            window._progress.setText("Done")
    else:
        if result.message and result.message != "app_running":
            QMessageBox.critical(window, "Operation failed", result.message)
        window._progress.setText("")
        window._progress_bar.setValue(0)

    refresh_state(window)

    # Cosmetic: clears the finished message after a beat. If the timer cannot
    # be armed the message simply stays until the next operation overwrites
    # it, which is a worse-looking success rather than a failure.
    try:
        from PySide6.QtCore import QTimer

        QTimer.singleShot(1200, lambda: window._progress.setText(""))
    except Exception:
        pass

    if op == Operation.UNINSTALL and result.ok:
        if getattr(window._cli_args, "uninstall", False):
            # The delay only lets the user read "Uninstalled" before the
            # window goes. Closing immediately is the correct degradation,
            # so this handler closes rather than swallowing.
            try:
                from PySide6.QtCore import QTimer

                QTimer.singleShot(600, window.close)
            except Exception:
                window.close()
        return
