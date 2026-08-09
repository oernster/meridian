#!/usr/bin/env python3
"""macOS DMG builder for Meridian.

Requires macOS with Xcode command-line tools and Homebrew.
Run from the repository root:
    python builddmg.py

Optional env vars:
    DEVELOPER_ID_APPLICATION: override the default signing identity
    APPLE_ID: Apple ID for notarization (skipped if not set)
    APPLE_APP_PASSWORD: app-specific password for notarization
    APPLE_TEAM_ID: Team ID for notarization (defaults to W7K465GKFJ)
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import struct
import zlib
import subprocess
import sys
import tempfile
from pathlib import Path

from build_resources import LICENCE_FILES

VERSION_FILE = Path(__file__).parent / "VERSION"


def read_version() -> str:
    """Read the repository-root VERSION file, the single source of truth."""
    return VERSION_FILE.read_text(encoding="utf-8").strip()


# ── Constants ──────────────────────────────────────────────────────────────────

APP_NAME = "Meridian"
APP_VERSION = read_version()
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
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
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
    print(f"{tool} not found, installing via brew...")
    run(["brew", "install", pkg])
    if not shutil.which(tool):
        sys.exit(f"ERROR: {tool} still not found after brew install. Aborting.")


def require_importable(module: str) -> None:
    """Ensure a Python module is importable in the interpreter running this build.

    PyInstaller analyses the app with whichever interpreter invokes it. To bundle
    a dependency (e.g. PySide6) it must be importable in THAT interpreter. The
    build therefore drives PyInstaller through sys.executable -m PyInstaller;
    every runtime dependency must live in the same environment. A bare on-PATH
    `pyinstaller` (e.g. Homebrew's, in its own isolated venv) would silently build
    an app missing these modules, which then crashes at launch.
    """
    if importlib.util.find_spec(module) is not None:
        return
    sys.exit(
        f"ERROR: '{module}' is not importable in {sys.executable}.\n"
        f"       Install the build dependencies into this interpreter, e.g.:\n"
        f"         {sys.executable} -m pip install -r requirements.txt pyinstaller\n"
        f"       then re-run:  {sys.executable} {Path(__file__).name}"
    )


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


# ── Steps ─────────────────────────────────────────────────────────────────────


def check_platform() -> None:
    section("Platform check")
    if sys.platform != "darwin":
        sys.exit("ERROR: This script must run on macOS.")
    result = subprocess.run(
        ["sw_vers", "-productVersion"], capture_output=True, text=True
    )
    print(f"  macOS {result.stdout.strip()}")
    require_importable("PySide6")
    require_importable("PyInstaller")
    require("create-dmg", "create-dmg")
    require("codesign")
    print("  All tools present.")


def clean() -> None:
    section("Clean previous build")
    for path in [
        "build",
        "dist",
        FINAL_DMG,
        "meridian.spec",
        "_dmg_staging",
        "_meridian_rw.dmg",
    ]:
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            print(f"  Removed: {path}")


def build_app_bundle(entitlements_path: Path, icns_path: Path | None = None) -> Path:
    section("PyInstaller: build .app bundle")

    qml_dir = Path("meridian/ui/qml")
    if not qml_dir.exists():
        sys.exit(f"ERROR: QML directory not found: {qml_dir}")

    icon_args = ["--icon", str(icns_path)] if icns_path else []

    licence_args: list[str] = []
    for name in LICENCE_FILES:
        licence_args += ["--add-data", f"{name}:."]

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--windowed",
        "--name",
        APP_NAME,
        "--osx-bundle-identifier",
        BUNDLE_ID,
        "--add-data",
        f"{qml_dir}:meridian/ui/qml",
        "--add-data",
        "VERSION:.",
        "--add-data",
        "meridian.png:.",
        *licence_args,
        "--hidden-import",
        "meridian.ui.bridge",
        "--hidden-import",
        "PySide6.QtQml",
        "--hidden-import",
        "PySide6.QtQuick",
        "--hidden-import",
        "PySide6.QtMultimedia",
        "--hidden-import",
        "PySide6.QtWebEngine",
        "--hidden-import",
        "PySide6.QtWebEngineCore",
        "--hidden-import",
        "PySide6.QtWebEngineWidgets",
        "--codesign-identity",
        DEVELOPER_ID,
        "--osx-entitlements-file",
        str(entitlements_path),
        *icon_args,
        "meridian/main.py",
    ]

    run(cmd)

    app_path = Path("dist") / f"{APP_NAME}.app"
    if not app_path.exists():
        sys.exit(f"ERROR: Expected app bundle not found: {app_path}")
    print(f"  Built: {app_path}")
    return app_path


def strip_build_artifacts(app_path: Path) -> None:
    section("Strip build artifacts")
    # PySide6 ships .cpp.o object files inside its QML plugin directories.
    # They are Mach-O relocatable binaries that codesign --deep silently skips
    # but Gatekeeper flags as unsigned, causing the entire bundle to be rejected.
    removed = 0
    for f in app_path.rglob("*.o"):
        if f.is_file():
            f.unlink()
            removed += 1
    # Prune any now-empty directories that held only those .o files.
    for d in sorted(app_path.rglob("objects-*"), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    print(f"  Removed {removed} intermediate object file(s)")


def sign_bundle(app_path: Path, entitlements_path: Path) -> None:
    section("Code signing")

    # Pass 1: sign the whole bundle (including all nested code) with our identity.
    run(
        [
            "codesign",
            "--force",
            "--deep",
            "--options",
            "runtime",
            "--entitlements",
            str(entitlements_path),
            "--sign",
            DEVELOPER_ID,
            str(app_path),
        ]
    )

    # Pass 2: re-sign the QtWebEngineProcess helper with its own entitlements.
    # --deep above overwrites the helper's pre-packaged signature, stripping the
    # allow-jit and disable-executable-page-protection entitlements that V8 requires
    # to allocate JIT memory.  Sign it again explicitly so those entitlements are
    # restored, then re-seal the outer bundle so its CodeResources hash is current.
    webengine_helper = (
        app_path
        / "Contents"
        / "Frameworks"
        / "PySide6"
        / "Qt"
        / "lib"
        / "QtWebEngineCore.framework"
        / "Versions"
        / "A"
        / "Helpers"
        / "QtWebEngineProcess.app"
    )
    webengine_ents = (
        webengine_helper / "Contents" / "Resources" / "QtWebEngineProcess.entitlements"
    )
    if webengine_helper.exists() and webengine_ents.exists():
        run(
            [
                "codesign",
                "--force",
                "--options",
                "runtime",
                "--entitlements",
                str(webengine_ents),
                "--sign",
                DEVELOPER_ID,
                str(webengine_helper),
            ]
        )
        # Re-seal the outer bundle to record the helper's updated signing hash.
        run(
            [
                "codesign",
                "--force",
                "--options",
                "runtime",
                "--entitlements",
                str(entitlements_path),
                "--sign",
                DEVELOPER_ID,
                str(app_path),
            ]
        )
        print("  QtWebEngineProcess re-signed with JIT entitlements.")

    run(["codesign", "--verify", "--deep", "--strict", str(app_path)])
    print("  Signature verified.")


def _fill_png_background(path: Path, bg: tuple[int, int, int]) -> None:
    """Composite an RGBA PNG over a solid RGB background colour in-place.

    macOS renders ICNS icons against whatever surface is below them (white in
    Finder/installation windows).  Without an opaque background the transparent
    areas of the icon look white there, while appearing dark in the dark-themed
    app UI.  Filling the background once at ICNS-generation time makes the icon
    consistent everywhere.
    """
    data = path.read_bytes()
    pos, width, height, idat_chunks = 8, 0, 0, []
    while pos < len(data) - 12:
        n = struct.unpack(">I", data[pos : pos + 4])[0]
        ctype = data[pos + 4 : pos + 8]
        cdata = data[pos + 8 : pos + 8 + n]
        if ctype == b"IHDR":
            width, height = struct.unpack(">II", cdata[0:8])
            if cdata[8] != 8 or cdata[9] != 6:
                return  # not 8-bit RGBA, leave as-is
        elif ctype == b"IDAT":
            idat_chunks.append(cdata)
        pos += 12 + n

    # Decompress and reconstruct pixels through PNG filters.
    # sips uses filter types 0/1/2/4; we must un-filter before reading values.
    bpp = 4  # RGBA
    filtered = bytearray(zlib.decompress(b"".join(idat_chunks)))
    stride = width * bpp + 1  # 1 filter byte + bpp bytes per pixel
    pixels = bytearray(height * width * bpp)  # reconstructed, no filter bytes

    def _paeth(a: int, b: int, c: int) -> int:
        p = a + b - c
        pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
        return a if pa <= pb and pa <= pc else (b if pb <= pc else c)

    for r in range(height):
        filt = filtered[r * stride]
        row = r * width * bpp
        prev_row = (r - 1) * width * bpp
        for i in range(width * bpp):
            x = filtered[r * stride + 1 + i]
            # References into already-written pixels (correct reconstruction).
            a = pixels[row + i - bpp] if i >= bpp else 0  # left
            b = pixels[prev_row + i] if r > 0 else 0  # above
            c = pixels[prev_row + i - bpp] if r > 0 and i >= bpp else 0  # above-left
            if filt == 0:
                pixels[row + i] = x
            elif filt == 1:
                pixels[row + i] = (x + a) & 0xFF
            elif filt == 2:
                pixels[row + i] = (x + b) & 0xFF
            elif filt == 3:
                pixels[row + i] = (x + (a + b) // 2) & 0xFF
            elif filt == 4:
                pixels[row + i] = (x + _paeth(a, b, c)) & 0xFF

    # Composite each pixel over the background colour.
    br, bg_, bb = bg
    for idx in range(width * height):
        off = idx * 4
        pa = pixels[off + 3]
        if pa == 255:
            continue
        if pa == 0:
            pixels[off], pixels[off + 1], pixels[off + 2], pixels[off + 3] = (
                br,
                bg_,
                bb,
                255,
            )
        else:
            a = pa / 255.0
            pixels[off] = int(pixels[off] * a + br * (1 - a))
            pixels[off + 1] = int(pixels[off + 1] * a + bg_ * (1 - a))
            pixels[off + 2] = int(pixels[off + 2] * a + bb * (1 - a))
            pixels[off + 3] = 255

    # Re-encode as PNG with filter type 0 (no filtering).
    raw_out = bytearray()
    for r in range(height):
        raw_out.append(0)  # filter type None
        raw_out.extend(pixels[r * width * bpp : (r + 1) * width * bpp])

    def _chunk(name: bytes, payload: bytes) -> bytes:
        crc = zlib.crc32(name + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + name + payload + struct.pack(">I", crc)

    ihdr_payload = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png_out = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr_payload)
        + _chunk(b"IDAT", zlib.compress(bytes(raw_out), 6))
        + _chunk(b"IEND", b"")
    )
    path.write_bytes(png_out)


def png_to_icns(png_path: Path, work_dir: Path) -> Path:
    # Catppuccin Mocha base, matching the app's dark-theme background so the
    # icon looks the same in the Dock/About dialog and in Finder/installer windows.
    BG = (0x1E, 0x1E, 0x2E)

    iconset = work_dir / "meridian.iconset"
    iconset.mkdir(parents=True, exist_ok=True)
    sizes = [16, 32, 128, 256, 512]
    for size in sizes:
        for suffix, px in [
            (f"icon_{size}x{size}.png", size),
            (f"icon_{size}x{size}@2x.png", size * 2),
        ]:
            out = iconset / suffix
            run(
                ["sips", "-z", str(px), str(px), str(png_path), "--out", str(out)],
                capture_output=True,
            )
            _fill_png_background(out, BG)
    icns_path = work_dir / "meridian.icns"
    run(["iconutil", "--convert", "icns", str(iconset), "--output", str(icns_path)])
    shutil.rmtree(iconset)
    return icns_path


def _find_mount_point(hdiutil_stdout: str) -> str | None:
    for line in hdiutil_stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and parts[-1].strip().startswith("/Volumes/"):
            return parts[-1].strip()
    return None


def set_volume_icon(icns_path: Path) -> None:
    section("Set volume icon")
    rw_dmg = Path("_meridian_rw.dmg")

    # UDZO (compressed) DMGs are read-only; convert to a writable image first.
    run(["hdiutil", "convert", FINAL_DMG, "-format", "UDRW", "-o", str(rw_dmg)])
    try:
        result = subprocess.run(
            ["hdiutil", "attach", "-noverify", str(rw_dmg)],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"  $ hdiutil attach -noverify {rw_dmg}")
        mount_point = _find_mount_point(result.stdout)
        if not mount_point:
            sys.exit(
                f"ERROR: could not find mount point in hdiutil output:\n{result.stdout}"
            )

        try:
            shutil.copy(icns_path, Path(mount_point) / ".VolumeIcon.icns")
            # create-dmg relies on SetFile, which is not in PATH because it
            # lives inside Xcode.app. Call it through xcrun so it is found
            # regardless of PATH.
            set_file = subprocess.run(
                ["xcrun", "-f", "SetFile"], capture_output=True, text=True
            ).stdout.strip()
            if set_file:
                subprocess.run([set_file, "-a", "C", mount_point], check=True)
            else:
                # Fallback: write kHasCustomIcon (0x0400) into
                # FolderInfo.frFlags via xattr.
                finder_info = bytearray(32)
                finder_info[8] = 0x04  # high byte of 0x0400, big-endian
                subprocess.run(
                    [
                        "xattr",
                        "-wx",
                        "com.apple.FinderInfo",
                        " ".join(f"{b:02x}" for b in finder_info),
                        mount_point,
                    ],
                    check=True,
                )
            print(f"  Volume icon embedded; custom-icon flag set on {mount_point}")
        finally:
            run(["hdiutil", "detach", mount_point], check=False)

        # Convert writable image back to a compressed DMG.
        Path(FINAL_DMG).unlink(missing_ok=True)
        run(["hdiutil", "convert", str(rw_dmg), "-format", "UDZO", "-o", FINAL_DMG])
    finally:
        rw_dmg.unlink(missing_ok=True)


def create_dmg(app_path: Path) -> None:
    section("Create DMG")

    staging = Path("_dmg_staging")
    staging.mkdir(exist_ok=True)
    dest = staging / app_path.name
    if dest.exists():
        shutil.rmtree(dest)
    # symlinks=True is required: macOS frameworks use symlinks (e.g.
    # Python.framework/Python -> Versions/Current/Python). Without it,
    # shutil.copytree dereferences them into regular files, which invalidates
    # all embedded code signatures and causes dlopen failures at runtime.
    run(["ditto", str(app_path), str(dest)])

    if os.path.exists(FINAL_DMG):
        os.remove(FINAL_DMG)

    cmd = [
        "create-dmg",
        "--volname",
        VOLUME_NAME,
        "--window-pos",
        "200",
        "120",
        "--window-size",
        "640",
        "400",
        "--icon-size",
        "100",
        "--text-size",
        "14",
        "--app-drop-link",
        "520",
        "180",
        "--icon",
        f"{APP_NAME}.app",
        "120",
        "180",
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
    run(
        [
            "codesign",
            "--force",
            "--sign",
            DEVELOPER_ID,
            FINAL_DMG,
        ]
    )
    print("  DMG signed.")


def notarize_dmg() -> None:
    if not APPLE_ID or not APPLE_APP_PASSWORD:
        print(
            "\n  Notarization skipped (set APPLE_ID and APPLE_APP_PASSWORD to enable)."
        )
        return

    section("Notarize DMG")
    run(
        [
            "xcrun",
            "notarytool",
            "submit",
            FINAL_DMG,
            "--apple-id",
            APPLE_ID,
            "--password",
            APPLE_APP_PASSWORD,
            "--team-id",
            APPLE_TEAM_ID,
            "--wait",
        ]
    )
    run(["xcrun", "stapler", "staple", FINAL_DMG])
    print("  Notarization complete and stapled.")


def verify_dmg() -> None:
    section("Verify DMG")
    run(["codesign", "--verify", FINAL_DMG])
    size_mb = os.path.getsize(FINAL_DMG) / (1024 * 1024)
    print(f"  {FINAL_DMG}  ({size_mb:.1f} MB): ready for distribution")


def apply_file_icon(png_path: Path) -> None:
    section("Apply file icon")
    require("fileicon")
    run(["fileicon", "set", FINAL_DMG, str(png_path)])
    print(f"  Icon applied to {FINAL_DMG}")


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> int:
    print(f"\nMERIDIAN DMG BUILDER  v{APP_VERSION}")
    print(f"Signing identity: {DEVELOPER_ID}")

    check_platform()
    clean()

    with tempfile.NamedTemporaryFile(
        suffix=".entitlements", mode="w", delete=False
    ) as f:
        f.write(ENTITLEMENTS)
        entitlements_path = Path(f.name)

    with tempfile.TemporaryDirectory() as icon_tmp:
        png_path = Path(__file__).parent / "meridian.png"
        icns_path = png_to_icns(png_path, Path(icon_tmp)) if png_path.exists() else None
        if not icns_path:
            print(f"  WARNING: {png_path} not found, building without custom icon.")

        try:
            app_path = build_app_bundle(entitlements_path, icns_path)
            strip_build_artifacts(app_path)
            sign_bundle(app_path, entitlements_path)
            create_dmg(app_path)
            if icns_path:
                set_volume_icon(icns_path)
            sign_dmg()
            notarize_dmg()
            verify_dmg()
            if icns_path:
                apply_file_icon(png_path)
        finally:
            entitlements_path.unlink(missing_ok=True)

    print(f"\nDone.  Distribute: {FINAL_DMG}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
