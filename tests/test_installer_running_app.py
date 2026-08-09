"""Detecting whether the application is already running.

This one predicate gates both upgrade and uninstall, so a false negative lets
the installer delete files out from under a running application. The process
table is replaced by a hand-written list: a real one is neither reproducible
nor safe to assert against.

The skipped-process paths matter as much as the match. A process table walk
hits processes that die mid-walk and processes the user may not inspect, and
either must be stepped over rather than ending the search early.
"""

from __future__ import annotations

from pathlib import Path

import psutil
import pytest

from installer.ops import running_app
from installer.ops.running_app import is_app_running


class _Proc:
    def __init__(self, exe: str | None) -> None:
        self.info = {"exe": exe}


class _Unreadable:
    """A process that refuses to describe itself, as a dying or foreign one does."""

    def __init__(self, error: BaseException) -> None:
        self._error = error

    @property
    def info(self) -> dict:
        raise self._error


def _table(monkeypatch: pytest.MonkeyPatch, procs: list[object]) -> None:
    monkeypatch.setattr(running_app.psutil, "process_iter", lambda attrs=None: procs)


def test_a_matching_process_means_the_app_is_running(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exe = tmp_path / "Meridian.exe"
    exe.write_text("exe", encoding="utf-8")
    _table(monkeypatch, [_Proc(str(exe))])

    assert is_app_running(exe) is True


def test_an_empty_process_table_means_it_is_not_running(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _table(monkeypatch, [])

    assert is_app_running(tmp_path / "Meridian.exe") is False


def test_another_application_is_not_mistaken_for_this_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exe = tmp_path / "Meridian.exe"
    exe.write_text("exe", encoding="utf-8")
    other = tmp_path / "SomethingElse.exe"
    other.write_text("exe", encoding="utf-8")
    _table(monkeypatch, [_Proc(str(other))])

    assert is_app_running(exe) is False


@pytest.mark.parametrize("missing", [None, ""])
def test_a_process_with_no_executable_path_is_stepped_over(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, missing: str | None
) -> None:
    exe = tmp_path / "Meridian.exe"
    exe.write_text("exe", encoding="utf-8")
    _table(monkeypatch, [_Proc(missing), _Proc(str(exe))])

    assert is_app_running(exe) is True


@pytest.mark.parametrize(
    "error",
    [psutil.NoSuchProcess(pid=1), psutil.AccessDenied(), RuntimeError("odd")],
)
def test_an_unreadable_process_does_not_end_the_search(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: BaseException
) -> None:
    """A process dying mid-walk must not be read as 'not running'."""
    exe = tmp_path / "Meridian.exe"
    exe.write_text("exe", encoding="utf-8")
    _table(monkeypatch, [_Unreadable(error), _Proc(str(exe))])

    assert is_app_running(exe) is True


@pytest.mark.parametrize(
    "error",
    [psutil.NoSuchProcess(pid=1), psutil.AccessDenied(), RuntimeError("odd")],
)
def test_a_table_of_only_unreadable_processes_reports_not_running(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: BaseException
) -> None:
    _table(monkeypatch, [_Unreadable(error)])

    assert is_app_running(tmp_path / "Meridian.exe") is False
