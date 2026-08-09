"""
AST-based structural tests enforcing layer boundary invariant:
  UI -> Application -> Domain <- Infrastructure

Domain must not import Application, Infrastructure, or UI.
Application must not import Infrastructure or UI.

The size rule covers QML and the test tree as well as the Python package. It
walked ``*.py`` under ``meridian/`` only, which reported a clean repository
while four QML files carried 3736 lines between them and one test module ran
to 1029. A rule that cannot see most of the UI is not a rule.
``_LEGACY_OVER_LIMIT`` carries what is left of those as tracked debt: the set
may only shrink, so ``test_legacy_allowlist_has_no_stale_entries`` fails if an
entry is no longer over the limit or no longer exists. `FeedDiscovery.qml` left
it on 2026-08-09 by that route.
"""

import ast
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent.parent
_SRC = _ROOT / "meridian"

_MAX_LINES = 400

# The top 5% of the cap. A file landing here is one edit from breaking the cap,
# so shaving a line off it buys nothing: the same file comes back for the same
# refactor. The rule is to take it to _BAND_TARGET or below in one go. Both
# bounds derive from the cap rather than being written as second literals, so
# the numbers cannot drift apart.
_DANGER_BAND_START = _MAX_LINES - _MAX_LINES // 20
_BAND_TARGET = 350

# Trees the size rule reads, with the suffixes it measures in each. Delivery
# scripts sit at the repository root and are deliberately absent: they are
# linear recipes read top to bottom, where splitting a sequence of flags and
# steps across modules costs more than it buys.
#
# `installer` was absent until 2026-08-09, which is why this file twice
# recorded that no installer module exceeded the cap: true both times, guarded
# neither, while `installer/ui/_main_window_actions.py` sat at 383 unreported.
_SIZE_SCAN: dict[str, tuple[str, ...]] = {
    "meridian": (".py", ".qml"),
    "tests": (".py",),
    "installer": (".py",),
}

# Files already over the limit when the scan widened to QML and to the tests.
# Tracked debt: this set may only shrink. Do not add to it; decompose instead.
_LEGACY_OVER_LIMIT = frozenset(
    {
        "meridian/ui/qml/main.qml",
        "meridian/ui/qml/SubscriptionManager.qml",
        "meridian/ui/qml/FeedReader.qml",
        "tests/ui/test_bridge.py",
    }
)

FORBIDDEN: dict[str, list[str]] = {
    "domain": ["application", "infrastructure", "ui"],
    "application": ["infrastructure", "ui"],
}


def _get_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def _collect_python_files(layer: str) -> list[Path]:
    return list((_SRC / layer).rglob("*.py"))


@pytest.mark.parametrize("layer,forbidden_layers", list(FORBIDDEN.items()))
def test_layer_boundary(layer: str, forbidden_layers: list[str]) -> None:
    files = _collect_python_files(layer)
    assert files, f"No Python files found in meridian/{layer}"
    violations: list[str] = []
    for path in files:
        for imp in _get_imports(path):
            for forbidden in forbidden_layers:
                if f"meridian.{forbidden}" in imp:
                    violations.append(
                        f"{path.relative_to(_SRC.parent)} imports {imp!r} "
                        f"(forbidden: meridian.{forbidden} in {layer} layer)"
                    )
    assert not violations, "Layer boundary violations:\n" + "\n".join(violations)


def _rel(path: Path) -> str:
    return path.relative_to(_ROOT).as_posix()


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def _scanned_files() -> list[Path]:
    files: list[Path] = []
    for tree, suffixes in _SIZE_SCAN.items():
        for path in sorted((_ROOT / tree).rglob("*")):
            if path.suffix in suffixes and "__pycache__" not in path.parts:
                files.append(path)
    return files


def test_all_source_files_within_line_limit() -> None:
    oversized = []
    for path in _scanned_files():
        rel = _rel(path)
        if rel in _LEGACY_OVER_LIMIT:
            continue
        lines = _line_count(path)
        if lines > _MAX_LINES:
            oversized.append(f"{rel}: {lines} lines (limit {_MAX_LINES})")
    assert not oversized, "Files over the line limit (decompose them):\n" + "\n".join(
        sorted(oversized)
    )


def test_no_source_file_sits_in_the_danger_band() -> None:
    banded = []
    for path in _scanned_files():
        rel = _rel(path)
        if rel in _LEGACY_OVER_LIMIT:
            continue
        lines = _line_count(path)
        if _DANGER_BAND_START < lines < _MAX_LINES:
            banded.append(f"{rel}: {lines} lines")
    assert not banded, (
        f"Files in the danger band ({_DANGER_BAND_START + 1} to "
        f"{_MAX_LINES - 1} lines). Extract a cohesive module and take each to "
        f"{_BAND_TARGET} or below, rather than shaving a line off the cap:\n"
        + "\n".join(sorted(banded))
    )


def test_legacy_allowlist_has_no_stale_entries() -> None:
    stale = []
    for rel in sorted(_LEGACY_OVER_LIMIT):
        path = _ROOT / rel
        if not path.exists():
            stale.append(f"{rel}: missing (remove from allowlist)")
        elif _line_count(path) <= _MAX_LINES:
            stale.append(f"{rel}: now within limit (remove from allowlist)")
    assert not stale, "Stale legacy allowlist entries:\n" + "\n".join(stale)


def _format_targets() -> list[str]:
    """Every Python file the formatters hold, which is all of them.

    This read `meridian/` alone until 2026-08-09, which is how `builddmg.py`
    drifted into failing `black --check` while every other delivery script
    stayed clean and nothing said so. The delivery scripts are exempt from the
    module-size cap because they are linear recipes read top to bottom; that
    exemption is about length and says nothing about formatting.
    """
    targets = [str(_ROOT / tree) for tree in ("meridian", "installer", "tests")]
    targets += [str(path) for path in sorted(_ROOT.glob("*.py"))]
    return targets


def test_black_compliance() -> None:
    result = subprocess.run(
        ["black", "--check", "--quiet", *_format_targets()],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_flake8_compliance() -> None:
    result = subprocess.run(
        [
            "flake8",
            "--max-line-length=88",
            "--extend-ignore=E203,W503",
            *_format_targets(),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
