"""Build standalone EXE with PyInstaller."""

import shutil
import subprocess
import sys
from pathlib import Path

from build_resources import LICENCE_FILES
from bundle_prune import run_pyinstaller


def _regen_splash(root: Path) -> int:
    print("Regenerating splash screen...")
    result = subprocess.run(
        [sys.executable, str(root / "create_splash.py")], cwd=root, check=False
    )
    if result.returncode != 0:
        print("Splash generation failed")
        return 1
    return 0


def build_exe() -> int:
    print("Building Meridian EXE...")

    root = Path(__file__).parent

    if _regen_splash(root) != 0:
        return 1

    dist_dir = root / "dist-pyinstaller"
    build_dir = root / "build"
    spec_file = root / "Meridian.spec"

    if shutil.which("pyinstaller") is None:
        print(
            "Error: pyinstaller not found. "
            "Activate the venv and install requirements-dev.txt"
        )
        return 1

    if spec_file.exists():
        spec_file.unlink()

    if dist_dir.exists():
        shutil.rmtree(dist_dir)

    if build_dir.exists():
        shutil.rmtree(build_dir)

    makespec_args = [
        "--onedir",
        "--windowed",
        "--paths=.",
        "--add-data=meridian/ui/qml:meridian/ui/qml",
        "--add-data=VERSION:.",
        "--add-data=meridian.png:.",
        "--add-data=meridian_16.png:.",
        "--add-data=meridian_20.png:.",
        "--add-data=meridian_24.png:.",
        "--add-data=meridian_28.png:.",
        "--add-data=meridian_32.png:.",
        "--add-data=meridian_40.png:.",
        "--add-data=meridian_48.png:.",
        "--add-data=meridian_56.png:.",
        "--add-data=meridian_64.png:.",
        "--add-data=meridian_72.png:.",
        "--add-data=meridian_96.png:.",
        "--add-data=meridian_128.png:.",
        "--add-data=meridian_256.png:.",
        "--add-data=meridian_512.png:.",
        "--add-data=meridian.ico:.",
        *[f"--add-data={name}:." for name in LICENCE_FILES],
        "--icon=meridian.ico",
        "--splash=meridian_splash.png",
        "--hidden-import=PySide6.QtMultimedia",
        "--hidden-import=PySide6.QtQml",
        "--hidden-import=PySide6.QtQuick",
        "--hidden-import=PySide6.QtQuickControls2",
        "--hidden-import=sqlalchemy.dialects.sqlite",
        "--hidden-import=defusedxml",
        "--hidden-import=defusedxml.ElementTree",
        "--hidden-import=dateutil",
        "meridian/main.py",
    ]

    returncode = run_pyinstaller(
        "Meridian",
        makespec_args,
        [f"--distpath={dist_dir}", f"--workpath={build_dir}"],
        root=root,
    )
    if returncode != 0:
        print("PyInstaller build failed")
        return 1

    exe_path = dist_dir / "Meridian" / "Meridian.exe"
    if exe_path.exists():
        print(f"[OK] EXE created: {exe_path}")
        print(f"Size: {exe_path.stat().st_size / (1024*1024):.1f} MB")
        return 0

    print("EXE not found after build")
    return 1


if __name__ == "__main__":
    sys.exit(build_exe())
