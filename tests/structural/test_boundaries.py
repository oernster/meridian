"""
AST-based structural tests enforcing layer boundary invariant:
  UI -> Application -> Domain <- Infrastructure

Domain must not import Application, Infrastructure, or UI.
Application must not import Infrastructure or UI.
"""

import ast
import subprocess
from pathlib import Path

import pytest

_SRC = Path(__file__).parent.parent.parent / "meridian"

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
        elif isinstance(node, ast.ImportFrom):
            if node.module:
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


def test_all_source_files_under_400_lines() -> None:
    oversized = []
    for path in _SRC.rglob("*.py"):
        lines = len(path.read_text(encoding="utf-8").splitlines())
        if lines > 400:
            oversized.append(f"{path.relative_to(_SRC.parent)}: {lines} lines")
    assert not oversized, "Source modules over 400 lines:\n" + "\n".join(oversized)


def test_black_compliance() -> None:
    result = subprocess.run(
        ["black", "--check", "--quiet", str(_SRC)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_flake8_compliance() -> None:
    result = subprocess.run(
        [
            "flake8",
            "--max-line-length=88",
            "--extend-ignore=E203,W503",
            str(_SRC),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
