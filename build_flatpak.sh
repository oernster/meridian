#!/usr/bin/env bash
# build_flatpak.sh — Build meridian.flatpak for Linux
# Usage: ./build_flatpak.sh
# Tested on Ubuntu/Debian with GNOME. Works on all distros with flatpak support.

set -euo pipefail

APP_ID="uk.codecrafter.Meridian"
APP_VERSION=$(python3 -c "import sys; sys.path.insert(0,'.'); exec(open('meridian/version.py').read()); print(__version__)")
BUNDLE="meridian.flatpak"
BUILD_DIR=".flatpak-build"
REPO_DIR=".flatpak-repo"
MANIFEST="${APP_ID}.yml"

RUNTIME="org.freedesktop.Platform"
RUNTIME_VERSION="24.08"
SDK="org.freedesktop.Sdk"
PYTHON_RUNTIME="org.freedesktop.Sdk.Extension.python312"

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
    "${PYTHON_RUNTIME}//${RUNTIME_VERSION}" \
    || true   # continue if already installed

# ── Generate manifest ─────────────────────────────────────────────────────────
section "Writing manifest ${MANIFEST}"

cat > "${MANIFEST}" <<YAML
app-id: ${APP_ID}
runtime: ${RUNTIME}
runtime-version: "${RUNTIME_VERSION}"
sdk: ${SDK}
sdk-extensions:
  - ${PYTHON_RUNTIME}

command: meridian

build-options:
  append-path: /usr/lib/sdk/python312/bin
  env:
    PYTHONPATH: /app/lib/python3.12/site-packages

finish-args:
  - --share=network
  - --share=ipc
  - --socket=fallback-x11
  - --socket=wayland
  - --socket=pulseaudio
  - --device=dri
  - --filesystem=home
  - --env=QT_QPA_PLATFORM=xcb

modules:

  # ── Python dependencies ────────────────────────────────────────────────────
  - name: python-deps
    buildsystem: simple
    build-commands:
      - pip3 install --prefix=/app --no-index --find-links=wheels
          SQLAlchemy
          httpx
          defusedxml
          python-dateutil
          bleach
    sources:
      - type: shell
        commands:
          - pip3 download --dest=wheels --no-deps
              "SQLAlchemy>=2.0"
              "httpx>=0.27"
              "defusedxml>=0.7"
              "python-dateutil>=2.9"
              "bleach>=6.1"

  # ── PySide6 (Qt for Python) ────────────────────────────────────────────────
  - name: pyside6
    buildsystem: simple
    build-commands:
      - pip3 install --prefix=/app --no-index --find-links=pyside6-wheels PySide6
    sources:
      - type: shell
        commands:
          - pip3 download --dest=pyside6-wheels --no-deps "PySide6>=6.7"

  # ── Meridian application ───────────────────────────────────────────────────
  - name: meridian
    buildsystem: simple
    build-commands:
      - pip3 install --prefix=/app --no-deps .
      - install -Dm755 packaging/meridian.sh /app/bin/meridian
      - install -Dm644 packaging/${APP_ID}.desktop /app/share/applications/${APP_ID}.desktop
      - install -Dm644 packaging/${APP_ID}.metainfo.xml /app/share/metainfo/${APP_ID}.metainfo.xml
    sources:
      - type: dir
        path: .
YAML

echo "  Manifest written."

# ── packaging/ helpers ────────────────────────────────────────────────────────
section "Writing packaging helpers"
mkdir -p packaging

cat > packaging/meridian.sh <<'LAUNCHER'
#!/bin/sh
exec python3 -m meridian.main "$@"
LAUNCHER
chmod +x packaging/meridian.sh

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

# ── setup.py shim (needed by flatpak pip install .) ───────────────────────────
if [ ! -f setup.py ] && [ ! -f pyproject.toml ]; then
cat > setup.py <<SETUP
from setuptools import setup, find_packages
setup(
    name="meridian",
    version="${APP_VERSION}",
    packages=find_packages(exclude=["tests*", "venv*", "installer*"]),
    package_data={"meridian": ["ui/qml/*.qml"]},
    install_requires=[],
)
SETUP
echo "  Generated setup.py shim."
fi

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
