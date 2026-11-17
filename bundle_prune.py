"""Leave out of every bundle what Meridian never loads.

`build_resources.py` says what is left out; this module does the leaving out,
for all four delivery routes, so they cannot disagree.

The three PyInstaller builds (`buildexe.py`, `buildinstaller.py` and
`builddmg.py`) call `run_pyinstaller`. It writes the spec through pyi-makespec
and inserts a call to `filter_analysis` between the Analysis and the PYZ, so a
dropped file is never packed at all. That is the only point that works for the
onefile setup program, which leaves no tree behind to prune. On macOS it also
runs before anything is signed.

The Flatpak installs the PySide6 wheel whole with pip, so it prunes the
installed tree instead:

    python3 bundle_prune.py /app/lib/python3.12/site-packages

Either way the result is audited before it is accepted: if any binary that
stays links a library that was dropped, the build stops and names both. A
bundle that would fail to load a library at launch never leaves the machine.
"""

from __future__ import annotations

import posixpath
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path, PurePosixPath

from build_resources import (
    DROPPED_FILES,
    DROPPED_PLUGIN_DIRS,
    DROPPED_PLUGIN_MARKERS,
    DROPPED_QML_MODULES,
    DROPPED_QT_MODULE_PREFIXES,
    DROPPED_RESOURCE_PREFIXES,
    DROPPED_RESOURCE_SUFFIXES,
    EXCLUDED_MODULES,
    KEPT_WEBENGINE_LOCALES,
    WEBENGINE_LOCALE_DIR,
    WHEEL_DEV_DIRS,
    WHEEL_TOOLS,
)

PYSIDE_DIR = "PySide6"
QT_DIR = "Qt"
QML_DIR = "qml"
PLUGINS_DIR = "plugins"
TOOL_DIRS = ("libexec", "bin")
EXE_SUFFIX = ".exe"
MEBIBYTE = 1024 * 1024

# Where pyi-makespec leaves the Analysis and starts packing; the filter goes in
# between. A spec without it is a PyInstaller change this module must hear of.
SPEC_ANCHOR = "pyz = PYZ("

# PyInstaller TOC type codes for files that are loaded as code.
_LINKED_TYPECODES = ("BINARY", "EXTENSION")
# A link entry, whose source field is the link's target rather than a file.
_SYMLINK_TYPECODE = "SYMLINK"

# How each platform spells a Qt module's file: the Windows DLL, the Linux shared
# object, the Python binding (any platform) and the macOS framework folder.
_LIBRARY_PATTERNS = (
    re.compile(r"^Qt6(?P<module>\w+?)\.dll$"),
    re.compile(r"^libQt6(?P<module>\w+?)\.so(?:\.\d+)*$"),
    re.compile(r"^Qt(?P<module>\w+?)\.(?:pyd|pyi|abi3\.so|cpython-[\w-]+\.so)$"),
)
_FRAMEWORK_PATTERN = re.compile(r"^Qt(?P<module>\w+)\.framework$")
_BINARY_NAME = re.compile(r"\.(?:dll|pyd|exe|dylib|so)(?:\.\d+)*$", re.IGNORECASE)
_NEEDED_LINE = re.compile(r"\(NEEDED\).*\[(?P<name>[^\]]+)\]")

TocEntry = tuple[str, str, str]


def _pyside_parts(path: str) -> tuple[str, ...]:
    """The path's segments below the PySide6 folder; empty when outside it."""
    parts = PurePosixPath(path.replace("\\", "/")).parts
    if PYSIDE_DIR not in parts:
        return ()
    return parts[parts.index(PYSIDE_DIR) + 1 :]


def _qt_module(parts: tuple[str, ...]) -> str | None:
    """The Qt module a file belongs to, read from its name or its framework."""
    for pattern in _LIBRARY_PATTERNS:
        match = pattern.match(parts[-1])
        if match:
            return match.group("module")
    for segment in parts:
        match = _FRAMEWORK_PATTERN.match(segment)
        if match:
            return match.group("module")
    return None


def _below(parts: tuple[str, ...], folder: str) -> tuple[str, ...]:
    """Segments after the first `folder` segment; empty when there is none."""
    if folder not in parts[:-1]:
        return ()
    return parts[parts.index(folder) + 1 :]


def _is_dev_part(parts: tuple[str, ...]) -> bool:
    top = parts[1:] if parts[0] == QT_DIR else parts
    if len(top) > 1 and top[0] in WHEEL_DEV_DIRS:
        return True
    name = parts[-1].removesuffix(EXE_SUFFIX)
    at_tool_home = len(parts) == 1 or parts[-2] in TOOL_DIRS
    return at_tool_home and name in WHEEL_TOOLS


def _is_dropped_qml(parts: tuple[str, ...]) -> bool:
    module_path = "/".join(_below(parts, QML_DIR))
    return any(
        module_path == prefix or module_path.startswith(prefix + "/")
        for prefix in DROPPED_QML_MODULES
    )


def _is_dropped_plugin(parts: tuple[str, ...]) -> bool:
    inside = _below(parts, PLUGINS_DIR)
    if not inside:
        return False
    if len(inside) > 1 and inside[0] in DROPPED_PLUGIN_DIRS:
        return True
    name = parts[-1].lower()
    return any(marker in name for marker in DROPPED_PLUGIN_MARKERS)


def _is_dropped_resource(parts: tuple[str, ...]) -> bool:
    name = parts[-1]
    if name.endswith(DROPPED_RESOURCE_SUFFIXES):
        return True
    if name.startswith(DROPPED_RESOURCE_PREFIXES):
        return True
    in_locales = len(parts) > 1 and parts[-2] == WEBENGINE_LOCALE_DIR
    return in_locales and name not in KEPT_WEBENGINE_LOCALES


def is_dropped(path: str, extra_qt_prefixes: Sequence[str] = ()) -> bool:
    """True when the file at `path` (any separator) is left out of a bundle.

    Only files under a `PySide6` folder are ever dropped; the application's
    own files and every other package pass through untouched.
    """
    parts = _pyside_parts(path)
    if not parts:
        return False
    if parts[-1] in DROPPED_FILES or _is_dev_part(parts):
        return True
    module = _qt_module(parts)
    prefixes = (*DROPPED_QT_MODULE_PREFIXES, *extra_qt_prefixes)
    if module is not None and module.startswith(prefixes):
        return True
    return (
        _is_dropped_qml(parts)
        or _is_dropped_plugin(parts)
        or _is_dropped_resource(parts)
    )


def _linked_names(path: str) -> list[str] | None:
    """File names of the libraries `path` links; None when nothing can tell."""
    if sys.platform == "win32":
        import pefile

        try:
            image = pefile.PE(path, fast_load=True)
        except pefile.PEFormatError:
            return []
        image.parse_data_directories(
            directories=[
                pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
                pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"],
            ]
        )
        names = []
        for table in ("DIRECTORY_ENTRY_IMPORT", "DIRECTORY_ENTRY_DELAY_IMPORT"):
            names += [entry.dll.decode() for entry in getattr(image, table, [])]
        image.close()
        return names
    tool = "otool" if sys.platform == "darwin" else "readelf"
    if shutil.which(tool) is None:
        return None
    if tool == "otool":
        result = subprocess.run(
            ["otool", "-L", path], capture_output=True, text=True, check=False
        )
        lines = result.stdout.splitlines()[1:]
        return [PurePosixPath(line.strip().split(" (")[0]).name for line in lines]
    result = subprocess.run(
        ["readelf", "-d", path], capture_output=True, text=True, check=False
    )
    matches = map(_NEEDED_LINE.search, result.stdout.splitlines())
    return [match.group("name") for match in matches if match]


def _file_name(dest: str) -> str:
    return PurePosixPath(dest.replace("\\", "/")).name.lower()


def audit_links(kept: Iterable[TocEntry], dropped: Iterable[TocEntry]) -> None:
    """Stop the build when a kept binary links a library that was dropped."""
    kept = list(kept)
    kept_names = {_file_name(dest) for dest, *_ in kept}
    gone = {_file_name(dest) for dest, *_ in dropped} - kept_names
    offenders = []
    for dest, source, typecode in kept:
        if typecode not in _LINKED_TYPECODES or not Path(source).is_file():
            continue
        linked = _linked_names(source)
        if linked is None:
            print("  Link audit skipped: no otool or readelf on this machine.")
            return
        offenders += [f"{dest} links {n}" for n in linked if n.lower() in gone]
    if offenders:
        raise SystemExit(
            "bundle_prune: a kept binary links a dropped library. Narrow the rule\n"
            "in build_resources.py that drops it:\n  " + "\n  ".join(offenders)
        )


def _size(entries: Iterable[TocEntry]) -> int:
    return sum(Path(src).stat().st_size for _, src, _ in entries if Path(src).is_file())


def filter_analysis(
    binaries: list[TocEntry],
    datas: list[TocEntry],
    extra_qt_prefixes: Sequence[str] = (),
) -> tuple[list[TocEntry], list[TocEntry]]:
    """Return the Analysis lists without the dropped files, after the audit."""

    def dropped(entry: TocEntry) -> bool:
        dest, source, typecode = entry
        if is_dropped(dest, extra_qt_prefixes):
            return True
        # A link is judged by what it points at too: PyInstaller aliases each
        # macOS framework at the bundle root, where its own name matches no
        # rule; a link left pointing at a dropped file fails the signature.
        if typecode != _SYMLINK_TYPECODE:
            return False
        target = posixpath.join(posixpath.dirname(dest.replace("\\", "/")), source)
        return is_dropped(posixpath.normpath(target), extra_qt_prefixes)

    gone = [e for e in (*binaries, *datas) if dropped(e)]
    kept_binaries = [e for e in binaries if not dropped(e)]
    kept_datas = [e for e in datas if not dropped(e)]
    audit_links(kept_binaries, gone)
    print(
        f"bundle_prune: left out {len(gone)} files, "
        f"{_size(gone) / MEBIBYTE:.1f} MB before compression"
    )
    return kept_binaries, kept_datas


def run_pyinstaller(
    name: str,
    makespec_args: Sequence[str],
    build_args: Sequence[str] = (),
    *,
    root: Path,
    extra_excludes: Sequence[str] = (),
    extra_qt_prefixes: Sequence[str] = (),
) -> int:
    """Write `<root>/<name>.spec` with the filter in it, then build from it.

    `makespec_args` are the options that shape the bundle (everything
    pyi-makespec takes); `build_args` are the run options such as --distpath,
    --workpath and --clean. Returns PyInstaller's exit code.
    """
    excludes = [f"--exclude-module={m}" for m in (*EXCLUDED_MODULES, *extra_excludes)]
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller.utils.cliutils.makespec",
            f"--name={name}",
            f"--specpath={root}",
            *excludes,
            *makespec_args,
        ],
        cwd=root,
        check=True,
    )
    spec = root / f"{name}.spec"
    text = spec.read_text(encoding="utf-8")
    if SPEC_ANCHOR not in text:
        raise SystemExit(f"bundle_prune: {spec.name} has no '{SPEC_ANCHOR}' line")
    hook = (
        "# Added by bundle_prune.run_pyinstaller: leave out what is never loaded.\n"
        "import sys as _sys\n"
        "_sys.path.insert(0, SPECPATH)\n"
        "import bundle_prune as _bundle_prune\n"
        "a.binaries, a.datas = _bundle_prune.filter_analysis(\n"
        f"    a.binaries, a.datas, {tuple(extra_qt_prefixes)!r}\n"
        ")\n"
    )
    spec.write_text(text.replace(SPEC_ANCHOR, hook + SPEC_ANCHOR, 1), encoding="utf-8")
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", *build_args]
    return subprocess.run([*command, str(spec)], cwd=root, check=False).returncode


def prune_tree(root: Path) -> None:
    """Delete the dropped files under an installed site-packages folder."""
    gone: list[TocEntry] = []
    kept: list[TocEntry] = []
    for path in sorted(root.rglob("*")):
        if path.is_dir() and not path.is_symlink():
            continue
        rel = path.relative_to(root).as_posix()
        code = "BINARY" if _BINARY_NAME.search(path.name) else "DATA"
        (gone if is_dropped(rel) else kept).append((rel, str(path), code))
    audit_links(kept, gone)
    size = _size(e for e in gone if not Path(e[1]).is_symlink())
    for _, source, _ in gone:
        Path(source).unlink()
    for folder in sorted((root / PYSIDE_DIR).rglob("*"), reverse=True):
        if folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()
    print(f"bundle_prune: removed {len(gone)} files, {size / MEBIBYTE:.1f} MB")


if __name__ == "__main__":
    if len(sys.argv) != 2 or not Path(sys.argv[1], PYSIDE_DIR).is_dir():
        raise SystemExit("usage: python3 bundle_prune.py <site-packages folder>")
    prune_tree(Path(sys.argv[1]))
