"""Every way Meridian reaches the network has one home; nothing else may.

The README names six: the feeds subscribed to and the media they point at,
Feedly's search, Wikipedia's topic suggestions, YouTube's embedded player and
GitHub's releases. Until this file the list was held by the documents alone and
DECISIONS-TRADEOFFS.md said so: a new outbound call would not have failed the
suite. Now each Python route is pinned to its package and each QML route to
its component:

- feeds and Feedly: `meridian/infrastructure/fetching/`
- the update check: `meridian/infrastructure/update/`
- the web engine the YouTube embed needs: started in `meridian/main.py`,
  drawn only in `MediaPlayerPanel.qml`
- Wikipedia's suggestions: `XMLHttpRequest` only in `DiscoveryQueryField.qml`

What this cannot see: an `Image` or `MediaPlayer` loading the address a feed
gave (the second place on the list, held to HTTPS by the parsers rather than
here) or a connection a library opens through a module not listed below. It
reads source, not the frozen build.
"""

from __future__ import annotations

import re
from pathlib import Path

from tests.structural.test_boundaries import get_imports

_ROOT = Path(__file__).resolve().parents[2]
_QML = _ROOT / "meridian" / "ui" / "qml"
_SHIPPED_PACKAGES = ("meridian", "installer")
# Build output and a delivery script inside a shipped package's folder.
_NOT_SHIPPED_DIRS = {"payload", "__pycache__"}
_DELIVERY_SCRIPTS = {"installer/build_payload.py"}

_NETWORK_ROOTS = {
    "socket",
    "ssl",
    "http",
    "smtplib",
    "imaplib",
    "poplib",
    "ftplib",
    "telnetlib",
    "xmlrpc",
    "requests",
    "httpx",
    "aiohttp",
    "urllib3",
    "websocket",
    "websockets",
}
# Matched as prefixes: the Qt names cover every WebEngine module at once.
_NETWORK_PREFIXES = (
    "urllib.request",
    "urllib.error",
    "PySide6.QtNetwork",
    "PySide6.QtWebEngine",
    "PySide6.QtWebSockets",
)

# Packages that may import any networking module, with the route each serves.
NETWORK_PACKAGES = {
    "meridian/infrastructure/fetching": "the feeds and Feedly's search",
    "meridian/infrastructure/update": "the GitHub releases check",
}
# Single files granted named modules only.
NETWORK_FILES = {
    "meridian/main.py": {"PySide6.QtWebEngineQuick"},
}

# QML constructs that reach the network, each allowed in one component only.
QML_ROUTES = {
    "XMLHttpRequest": (re.compile(r"\bXMLHttpRequest\b"), "DiscoveryQueryField.qml"),
    "the web engine": (
        re.compile(r"^\s*import\s+QtWebEngine\b|\bWebEngineView\b"),
        "MediaPlayerPanel.qml",
    ),
    "WebSocket": (re.compile(r"\bWebSocket\b"), None),
}
_COMMENT = re.compile(r"^\s*(//|/\*|\*)")


def _relative(path: Path) -> str:
    return path.relative_to(_ROOT).as_posix()


def shipped_python() -> list[Path]:
    found = []
    for package in _SHIPPED_PACKAGES:
        for path in sorted((_ROOT / package).rglob("*.py")):
            if _NOT_SHIPPED_DIRS.intersection(path.relative_to(_ROOT).parts):
                continue
            if _relative(path) not in _DELIVERY_SCRIPTS:
                found.append(path)
    return found


def is_network_module(module: str) -> bool:
    return module.split(".")[0] in _NETWORK_ROOTS or module.startswith(
        _NETWORK_PREFIXES
    )


def _network_imports(path: Path) -> set[str]:
    return {m for m in get_imports(path) if is_network_module(m)}


def _granted(module: str, grants: set[str]) -> bool:
    """A grant covers its module and every name taken from it, since
    `from a import b` records `a.b` whether `b` is a submodule or a class."""
    return any(module == g or module.startswith(g + ".") for g in grants)


def _in_network_package(rel: str) -> bool:
    return any(rel.startswith(package + "/") for package in NETWORK_PACKAGES)


def qml_route_lines(path: Path, pattern: re.Pattern[str]) -> list[int]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [
        n
        for n, line in enumerate(lines, start=1)
        if not _COMMENT.match(line) and pattern.search(line)
    ]


class TestPython:
    def test_only_the_named_homes_import_networking(self) -> None:
        problems = []
        for path in shipped_python():
            rel = _relative(path)
            if _in_network_package(rel):
                continue
            granted = NETWORK_FILES.get(rel, set())
            extra = sorted(
                m for m in _network_imports(path) if not _granted(m, granted)
            )
            if extra:
                problems.append(f"{rel} imports {extra}")
        assert problems == []

    def test_every_granted_file_still_needs_its_grant(self) -> None:
        for rel, granted in NETWORK_FILES.items():
            assert granted <= _network_imports(_ROOT / rel), rel

    def test_every_network_package_exists_and_reaches_the_network(self) -> None:
        for package in NETWORK_PACKAGES:
            files = [p for p in shipped_python() if _in_network_package(_relative(p))]
            reached = [p for p in files if _relative(p).startswith(package + "/")]
            assert any(_network_imports(p) for p in reached), package

    def test_the_scan_covers_what_ships(self) -> None:
        scanned = {_relative(p) for p in shipped_python()}
        assert "meridian/main.py" in scanned
        assert "installer/app.py" in scanned
        assert scanned.isdisjoint(_DELIVERY_SCRIPTS)
        assert not any("payload" in name.split("/") for name in scanned)


class TestQml:
    def test_each_route_lives_in_its_one_component(self) -> None:
        problems = []
        for path in sorted(_QML.glob("*.qml")):
            for route, (pattern, home) in QML_ROUTES.items():
                if path.name == home:
                    continue
                for line in qml_route_lines(path, pattern):
                    problems.append(f"{path.name}:{line} uses {route}")
        assert problems == []

    def test_each_home_still_holds_its_route(self) -> None:
        for route, (pattern, home) in QML_ROUTES.items():
            if home is not None:
                assert qml_route_lines(_QML / home, pattern), f"{home}: {route}"


class TestRecognition:
    def test_network_modules_are_recognised(self) -> None:
        for module in ("httpx", "socket", "urllib.request", "PySide6.QtWebEngineQuick"):
            assert is_network_module(module), module
        for module in ("urllib.parse", "defusedxml", "PySide6.QtQml", "httpxyz"):
            assert not is_network_module(module), module

    def test_a_submodule_imported_from_its_package_is_seen(self, tmp_path) -> None:
        probe = tmp_path / "probe.py"
        probe.write_text("from PySide6 import QtNetwork\n", encoding="utf-8")
        assert "PySide6.QtNetwork" in get_imports(probe)

    def test_a_qml_comment_is_not_a_route(self, tmp_path) -> None:
        probe = tmp_path / "Probe.qml"
        probe.write_text(
            "// an XMLHttpRequest lives elsewhere\n  * a WebEngineView\n"
            "var x = new XMLHttpRequest()\n",
            encoding="utf-8",
        )
        pattern = QML_ROUTES["XMLHttpRequest"][0]
        assert qml_route_lines(probe, pattern) == [3]
