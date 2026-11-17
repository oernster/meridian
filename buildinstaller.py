"""Build MeridianSetup.exe (single-file per-user installer).

Workflow:

1) Build app bundle:     python buildexe.py
2) Build payload+setup:  python buildinstaller.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from build_resources import (
    INSTALLER_DROPPED_QT_MODULE_PREFIXES,
    INSTALLER_EXCLUDED_MODULES,
)
from bundle_prune import run_pyinstaller

PROJECT_ROOT = Path(__file__).resolve().parent


def _require_windows() -> None:
    if os.name != "nt":
        raise SystemExit("buildinstaller.py is Windows-only")


def _run(cmd: list[str]) -> None:
    print("\n> " + " ".join(cmd))
    subprocess.check_call(cmd)


def _retry_unlink(path: Path, *, attempts: int = 20, delay_s: float = 0.15) -> None:
    if not path.exists():
        return

    last_exc: Exception | None = None
    for _ in range(attempts):
        try:
            path.unlink(missing_ok=True)
            return
        except OSError as exc:
            last_exc = exc
            time.sleep(delay_s)
    if last_exc:
        raise last_exc


def _replace_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        _retry_unlink(dst)
    shutil.move(str(src), str(dst))


def main() -> int:
    _require_windows()

    _run([sys.executable, "-m", "installer.build_payload"])

    final_dist_root = PROJECT_ROOT / "dist-installer"
    work_root = PROJECT_ROOT / "build" / "installer"
    temp_dist_root = PROJECT_ROOT / "dist-installer.build"

    for p in [temp_dist_root, work_root]:
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)

    entrypoint = PROJECT_ROOT / "installer" / "app.py"
    icon_ico = PROJECT_ROOT / "meridian.ico"

    payload_zip = PROJECT_ROOT / "installer" / "payload" / "payload.zip"
    manifest_json = PROJECT_ROOT / "installer" / "payload" / "manifest.json"

    if not payload_zip.exists() or not manifest_json.exists():
        raise SystemExit("Payload build did not produce payload.zip/manifest.json")

    add_data = [
        f"{payload_zip};installer/payload",
        f"{manifest_json};installer/payload",
        f"{PROJECT_ROOT / 'LICENSE'};.",
        f"{PROJECT_ROOT / 'VERSION'};.",
    ]

    for asset in [
        "meridian.png",
        "meridian_16.png",
        "meridian_20.png",
        "meridian_24.png",
        "meridian_28.png",
        "meridian_32.png",
        "meridian_40.png",
        "meridian_48.png",
        "meridian_56.png",
        "meridian_64.png",
        "meridian_72.png",
        "meridian_96.png",
        "meridian_128.png",
        "meridian_256.png",
        "meridian_512.png",
        "meridian.ico",
    ]:
        p = PROJECT_ROOT / asset
        if p.exists():
            add_data.append(f"{p};.")

    makespec_args = [
        "--onefile",
        "--windowed",
        "--paths=.",
        *(["--icon", str(icon_ico)] if icon_ico.exists() else []),
    ]
    for spec in add_data:
        makespec_args.extend(["--add-data", spec])

    makespec_args.extend(["--hidden-import", "installer.ui.worker"])

    makespec_args.append(str(entrypoint))
    returncode = run_pyinstaller(
        "MeridianSetup",
        makespec_args,
        [
            "--clean",
            "--distpath",
            str(temp_dist_root),
            "--workpath",
            str(work_root),
        ],
        root=PROJECT_ROOT,
        extra_excludes=INSTALLER_EXCLUDED_MODULES,
        extra_qt_prefixes=INSTALLER_DROPPED_QT_MODULE_PREFIXES,
    )
    if returncode != 0:
        raise SystemExit(f"PyInstaller failed with exit code {returncode}")

    built_exe = temp_dist_root / "MeridianSetup.exe"
    final_exe = final_dist_root / "MeridianSetup.exe"

    if built_exe.exists():
        try:
            _replace_file(built_exe, final_exe)
        except PermissionError as exc:
            raise SystemExit(
                "Unable to overwrite the installer EXE because it is in use.\n"
                "Close any running installer instances.\n"
                "Then try again."
            ) from exc

        shutil.rmtree(temp_dist_root, ignore_errors=True)

        print(f"\nBuilt: {final_exe}")
        return 0

    print("\nBuild finished; expected installer exe not found.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
