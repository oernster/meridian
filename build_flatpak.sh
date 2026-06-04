#!/usr/bin/env bash
# build_flatpak.sh — Build meridian.flatpak for Linux
# Usage: ./build_flatpak.sh

set -euo pipefail

APP_ID="uk.codecrafter.Meridian"
APP_VERSION=$(python3 -c "import sys; sys.path.insert(0,'.'); exec(open('meridian/version.py').read()); print(__version__)")
BUNDLE="meridian.flatpak"
BUILD_DIR=".flatpak-build"
REPO_DIR=".flatpak-repo"
MANIFEST="${APP_ID}.yml"

RUNTIME="org.kde.Platform"
SDK="org.kde.Sdk"
RUNTIME_VERSION="6.8"

# ── Colour helpers ────────────────────────────────────────────────────────────
bold=$(tput bold 2>/dev/null || true)
reset=$(tput sgr0 2>/dev/null || true)
section() { echo; echo "${bold}=== $* ===${reset}"; }

# ── Tool checks / install ─────────────────────────────────────────────────────
section "Checking dependencies"

install_if_missing() {
    local pkg="$1"
    if ! command -v "$pkg" &>/dev/null; then
        echo "  $pkg not found — installing..."
        if command -v apt-get &>/dev/null; then
            sudo apt-get update -qq && sudo apt-get install -y "$pkg"
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y "$pkg"
        elif command -v pacman &>/dev/null; then
            sudo pacman -Sy --noconfirm "$pkg"
        else
            echo "ERROR: Cannot install $pkg — unsupported package manager." >&2
            exit 1
        fi
    else
        echo "  $pkg: OK"
    fi
}

install_if_missing flatpak
install_if_missing flatpak-builder

# ── Flatpak remotes ───────────────────────────────────────────────────────────
section "Configuring Flathub remote"
flatpak remote-add --if-not-exists --user flathub \
    https://dl.flathub.org/repo/flathub.flatpakrepo

# ── Runtime / SDK ─────────────────────────────────────────────────────────────
section "Installing runtime and SDK"
flatpak install --user --noninteractive flathub \
    "${RUNTIME}//${RUNTIME_VERSION}" \
    "${SDK}//${RUNTIME_VERSION}" \
    || true

# ── packaging/ helpers ────────────────────────────────────────────────────────
section "Writing packaging helpers"
mkdir -p packaging

if command -v convert &>/dev/null; then
    convert meridian.png -resize 512x512 packaging/meridian-icon.png
else
    python3 -c "
from PIL import Image
img = Image.open('meridian.png')
img = img.resize((512, 512), Image.LANCZOS)
img.save('packaging/meridian-icon.png')
"
fi
echo "  Icon resized to 512x512."

cat > packaging/meridian-launcher.sh <<'LAUNCHER'
#!/bin/sh
export PYTHONPATH="/app/lib/python3.12/site-packages${PYTHONPATH:+:$PYTHONPATH}"
export QT_PLUGIN_PATH="/app/lib/python3.12/site-packages/PySide6/Qt/plugins"
export QT_QPA_PLATFORM_PLUGIN_PATH="/app/lib/python3.12/site-packages/PySide6/Qt/plugins/platforms"
export QML2_IMPORT_PATH="/app/lib/python3.12/site-packages/PySide6/Qt/qml"
export QTWEBENGINE_DISABLE_SANDBOX=1
if [ -n "$WAYLAND_DISPLAY" ] && [ -z "$FORCE_X11" ]; then
    export QT_QPA_PLATFORM=wayland
elif [ -n "$DISPLAY" ]; then
    export QT_QPA_PLATFORM=xcb
else
    export QT_QPA_PLATFORM=xcb
fi
exec python3 -m meridian.main "$@"
LAUNCHER
chmod +x packaging/meridian-launcher.sh

cat > "packaging/${APP_ID}.desktop" <<DESKTOP
[Desktop Entry]
Name=Meridian
Comment=MMSP / RSS / Atom / Podcast Feed Reader
Exec=meridian
Icon=${APP_ID}
Terminal=false
Type=Application
Categories=Network;News;
DESKTOP

cat > "packaging/${APP_ID}.metainfo.xml" <<XML
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>${APP_ID}</id>
  <name>Meridian</name>
  <summary>MMSP / RSS / Atom / Podcast Feed Reader</summary>
  <metadata_license>MIT</metadata_license>
  <project_license>LGPL-3.0</project_license>
  <description>
    <p>Meridian is a multimedia feed reader supporting RSS, Atom, podcast,
    YouTube, and MFEED/MMSP feeds with a native Qt Quick UI.</p>
  </description>
  <releases>
    <release version="${APP_VERSION}" date="2026-06-03"/>
  </releases>
  <url type="homepage">https://github.com/oernster/meridian</url>
</component>
XML

# ── Generate manifest ─────────────────────────────────────────────────────────
section "Writing manifest ${MANIFEST}"

cat > "${MANIFEST}" <<YAML
app-id: ${APP_ID}
runtime: ${RUNTIME}
runtime-version: "${RUNTIME_VERSION}"
sdk: ${SDK}

command: meridian

build-options:
  build-args:
    - --share=network
  env:
    PIP_CACHE_DIR: /run/build/meridian/pip-cache

finish-args:
  - --share=network
  - --share=ipc
  - --socket=fallback-x11
  - --socket=wayland
  - --socket=pulseaudio
  - --device=dri
  - --filesystem=home
  - --env=QTWEBENGINE_DISABLE_SANDBOX=1

modules:

  # ── MIT Kerberos 5 (provides libgssapi_krb5.so.2 needed by PySide6/Qt) ────
  - name: krb5
    subdir: src
    config-opts:
      - --prefix=/app
      - --localstatedir=/var/lib
      - --sbindir=/app/bin
      - --disable-rpath
      - --disable-static
      - --without-ldap
      - --without-keyutils
    sources:
      - type: archive
        url: https://kerberos.org/dist/krb5/1.21/krb5-1.21.3.tar.gz
        sha256: b7a4cd5ead67fb08b980b21abd150ff7217e85ea320c9ed0c6dadd304840ad35

  # ── Ensure pip is available ────────────────────────────────────────────────
  - name: python3-pip
    buildsystem: simple
    build-commands:
      - python3 -m ensurepip --upgrade

  # ── Python dependencies ────────────────────────────────────────────────────
  - name: python-deps
    buildsystem: simple
    build-commands:
      - pip3 install --no-cache-dir --prefix=/app "SQLAlchemy>=2.0" "httpx>=0.27" "defusedxml>=0.7" "python-dateutil>=2.9" "bleach>=6.1"

  # ── PySide6 (Qt for Python) ────────────────────────────────────────────────
  - name: pyside6
    buildsystem: simple
    build-commands:
      - pip3 install --no-cache-dir --prefix=/app "PySide6>=6.7"

  # ── Meridian application ───────────────────────────────────────────────────
  - name: meridian
    buildsystem: simple
    build-commands:
      - pip3 install --no-cache-dir --no-deps --prefix=/app .
      - install -Dm644 LICENSE /app/lib/python3.12/site-packages/LICENSE
      - install -Dm644 meridian.png /app/lib/python3.12/site-packages/meridian.png
      - install -Dm755 packaging/meridian-launcher.sh /app/bin/meridian
      - install -Dm644 packaging/${APP_ID}.desktop /app/share/applications/${APP_ID}.desktop
      - install -Dm644 packaging/${APP_ID}.metainfo.xml /app/share/metainfo/${APP_ID}.metainfo.xml
      - install -Dm644 packaging/meridian-icon.png /app/share/icons/hicolor/512x512/apps/${APP_ID}.png
    sources:
      - type: dir
        path: .
YAML

echo "  Manifest written."

# ── Build ─────────────────────────────────────────────────────────────────────
section "Building Flatpak"
rm -rf "${BUILD_DIR}" "${REPO_DIR}"

flatpak-builder \
    --user \
    --install-deps-from=flathub \
    --force-clean \
    --repo="${REPO_DIR}" \
    "${BUILD_DIR}" \
    "${MANIFEST}"

# ── Bundle ────────────────────────────────────────────────────────────────────
section "Bundling to ${BUNDLE}"
flatpak build-bundle \
    --runtime-repo=https://dl.flathub.org/repo/flathub.flatpakrepo \
    "${REPO_DIR}" \
    "${BUNDLE}" \
    "${APP_ID}"

echo
echo "${bold}Build complete: ${BUNDLE}${reset}"
echo
echo "Install with:"
echo "  flatpak install --user ${BUNDLE}"
echo
echo "Run with:"
echo "  flatpak run ${APP_ID}"
