"""Installer operation errors."""

from __future__ import annotations


class InstallerOperationError(RuntimeError):
    pass


class AppRunningError(InstallerOperationError):
    """Raised when Meridian is running and the operation requires it closed."""
