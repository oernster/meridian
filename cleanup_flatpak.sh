#!/usr/bin/env bash
# cleanup_flatpak.sh — Uninstall and purge meridian Flatpak
set -euo pipefail

APP_ID="uk.codecrafter.Meridian"

bold=$(tput bold 2>/dev/null || true)
reset=$(tput sgr0 2>/dev/null || true)
section() { echo; echo "${bold}=== $* ===${reset}"; }

section "Uninstalling ${APP_ID}"
if flatpak list --user | grep -q "${APP_ID}"; then
    flatpak uninstall --user -y "${APP_ID}"
    echo "  Uninstalled."
else
    echo "  Not installed, skipping."
fi

section "Removing build artefacts"
rm -f meridian.flatpak
rm -rf .flatpak-build .flatpak-repo .flatpak-builder
rm -f "${APP_ID}.yml"
rm -f packaging/meridian-icon.png
echo "  Done."

echo
echo "${bold}Purge complete.${reset}"
