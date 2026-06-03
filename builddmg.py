#!/usr/bin/env python3
"""macOS DMG builder for Meridian.

Requires macOS with Xcode command-line tools and Homebrew.
Run from the repository root:
    python builddmg.py

Optional env vars:
    DEVELOPER_ID_APPLICATION  — override the default signing identity
    APPLE_ID                  — Apple ID for notarization (skipped if not set)
    APPLE_APP_PASSWORD        — app-specific password for notarization
    APPLE_TEAM_ID             — Team ID for notarization (defaults to W7K465GKFJ)
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _read_version() -> str:
    spec = importlib.util.spec_from_file_location(
        "version", Path(__file__).parent / "meridian" / "version.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.__version__


# ── Constants ──────────────────────────────────────────────────────────────────

APP_NAME = "Meridian"
APP_VERSION = _read_version()
BUNDLE_ID = "uk.codecrafter.Meridian"
FINAL_DMG = "meridian.dmg"
VOLUME_NAME = f"Install {APP_NAME}"

DEVELOPER_ID = os.environ.get(
    "DEVELOPER_ID_APPLICATION",
    "Developer ID Application: Oliver Ernster (W7K465GKFJ)",
)
APPLE_ID = os.environ.get("APPLE_ID", "")
APPLE_APP_PASSWORD = os.environ.get("APPLE_APP_PASSWORD", "")
APPLE_TEAM_ID = os.environ.get("APPLE_TEAM_ID", "W7K465GKFJ")

ENTITLEMENTS = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
    <key>com.apple.security.network.client</key>
    <true/>
</dict>
</plist>
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def run(cmd: list[str], check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    return subprocess.run(cmd, check=check, **kwargs)


def require(tool: str, brew_pkg: str | None = None) -> None:
    if shutil.which(tool):
        return
    pkg = brew_pkg or tool
    print(f"{tool} not found — installing via brew...")
    run(["brew", "install", pkg])
    if not shutil.which(tool):
        sys.exit(f"ERROR: {tool} still not found after brew install. Aborting.")


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


# ── Steps ─────────────────────────────────────────────────────────────────────

def check_platform() -> None:
    section("Platform check")
    if sys.platform != "darwin":
        sys.exit("ERROR: This script must run on macOS.")
    result = subprocess.run(["sw_vers", "-productVersion"], capture_output=True, text=True)
    print(f"  macOS {result.stdout.strip()}")
    require("pyinstaller", "pyinstaller")
    require("create-dmg", "create-dmg")
    require("codesign")
    print("  All tools present.")


def clean() -> None:
    section("Clean previous build")
    for path in ["build", "dist", FINAL_DMG, "meridian.spec", "_dmg_staging"]:
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            print(f"  Removed: {path}")


def build_app_bundle(entitlements_path: Path) -> Path:
    section("PyInstaller: build .app bundle")

    qml_dir = Path("meridian/ui/qml")
    if not qml_dir.exists():
        sys.exit(f"ERROR: QML directory not found: {qml_dir}")

    icon_args: list[str] = []
    icon_path = Path("assets/meridian.icns")
    if icon_path.exists():
        icon_args = ["--icon", str(icon_path)]

    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--windowed",
        "--name", APP_NAME,
        "--osx-bundle-identifier", BUNDLE_ID,
        "--add-data", f"{qml_dir}:meridian/ui/qml",
        "--hidden-import", "meridian.ui.bridge",
        "--hidden-import", "PySide6.QtQml",
        "--hidden-import", "PySide6.QtQuick",
        "--hidden-import", "PySide6.QtMultimedia",
        "--hidden-import", "PySide6.QtWebEngine",
        "--hidden-import", "PySide6.QtWebEngineCore",
        "--hidden-import", "PySide6.QtWebEngineWidgets",
        "--codesign-identity", DEVELOPER_ID,
        "--osx-entitlements-file", str(entitlements_path),
        *icon_args,
        "meridian/main.py",
    ]

    run(cmd)

    app_path = Path("dist") / f"{APP_NAME}.app"
    if not app_path.exists():
        sys.exit(f"ERROR: Expected app bundle not found: {app_path}")
    print(f"  Built: {app_path}")
    return app_path


def sign_bundle(app_path: Path, entitlements_path: Path) -> None:
    section("Code signing")
    run([
        "codesign",
        "--force",
        "--deep",
        "--options", "runtime",
        "--entitlements", str(entitlements_path),
        "--sign", DEVELOPER_ID,
        str(app_path),
    ])
    run(["codesign", "--verify", "--deep", "--strict", str(app_path)])
    print("  Signature verified.")


def create_dmg(app_path: Path) -> None:
    section("Create DMG")

    staging = Path("_dmg_staging")
    staging.mkdir(exist_ok=True)
    shutil.copytree(app_path, staging / app_path.name, dirs_exist_ok=True)

    if os.path.exists(FINAL_DMG):
        os.remove(FINAL_DMG)

    cmd = [
        "create-dmg",
        "--volname", VOLUME_NAME,
        "--window-pos", "200", "120",
        "--window-size", "640", "400",
        "--icon-size", "100",
        "--text-size", "14",
        "--app-drop-link", "520", "180",
        "--icon", f"{APP_NAME}.app", "120", "180",
        FINAL_DMG,
        str(staging / f"{APP_NAME}.app"),
    ]

    result = run(cmd, check=False)
    if result.returncode not in (0, 2):
        sys.exit(f"ERROR: create-dmg failed (exit {result.returncode})")

    shutil.rmtree(staging)
    print(f"  DMG created: {FINAL_DMG}")


def sign_dmg() -> None:
    section("Sign DMG")
    run([
        "codesign",
        "--force",
        "--sign", DEVELOPER_ID,
        FINAL_DMG,
    ])
    print("  DMG signed.")


def notarize_dmg() -> None:
    if not APPLE_ID or not APPLE_APP_PASSWORD:
        print("\n  Notarization skipped (set APPLE_ID and APPLE_APP_PASSWORD to enable).")
        return

    section("Notarize DMG")
    run([
        "xcrun", "notarytool", "submit", FINAL_DMG,
        "--apple-id", APPLE_ID,
        "--password", APPLE_APP_PASSWORD,
        "--team-id", APPLE_TEAM_ID,
        "--wait",
    ])
    run(["xcrun", "stapler", "staple", FINAL_DMG])
    print("  Notarization complete and stapled.")


def verify_dmg() -> None:
    section("Verify DMG")
    run(["codesign", "--verify", FINAL_DMG])
    size_mb = os.path.getsize(FINAL_DMG) / (1024 * 1024)
    print(f"  {FINAL_DMG}  ({size_mb:.1f} MB)  — ready for distribution")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    print(f"\nMERIDIAN DMG BUILDER  v{APP_VERSION}")
    print(f"Signing identity: {DEVELOPER_ID}")

    check_platform()
    clean()

    with tempfile.NamedTemporaryFile(suffix=".entitlements", mode="w",
                                     delete=False) as f:
        f.write(ENTITLEMENTS)
        entitlements_path = Path(f.name)

    try:
        app_path = build_app_bundle(entitlements_path)
        sign_bundle(app_path, entitlements_path)
        create_dmg(app_path)
        sign_dmg()
        notarize_dmg()
        verify_dmg()
    finally:
        entitlements_path.unlink(missing_ok=True)

    print(f"\nDone.  Distribute: {FINAL_DMG}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
