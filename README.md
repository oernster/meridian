# <img width="128" height="128" alt="meridian" src="https://github.com/user-attachments/assets/e2ef5ef9-1ed9-4faf-9a8f-4af483072e59" /> Meridian

A desktop feed reader and subscription manager built on the [MMSP](https://github.com/MMSP-Spec) protocol. Supports RSS, Atom, podcast feeds, and YouTube channels with a native Qt Quick UI.

# <img width="273" height="136" alt="contrib" src="https://github.com/user-attachments/assets/8a1c1862-b9a3-4e07-a9cc-b15d9d29e2d7" /> This is NOT cool.  shubh2294 has made ZERO contributions 
# to the large amount of effort made by myself to create this project.  GitHub should be ASHAMED of themselves.  Credit where CREDIT IT NOT DUE!!!

<img width="1265" height="827" alt="meridian" src="https://github.com/user-attachments/assets/54ff3fbb-5abc-445b-a2ee-808829ec214e" />

## Installation

### Pre-built releases

Download the latest installer for your platform from the [Releases page](https://github.com/oernster/meridian/releases).

### Run from source

```bash
# 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python -m meridian.main
```

Or, if installed as a package:

```bash
pip install -e .
meridian
```

### Linux — Flatpak

```bash
# Build (requires flatpak and flatpak-builder)
./build_flatpak.sh

# Install the generated bundle
flatpak install --user meridian.flatpak

# Run
flatpak run uk.codecrafter.Meridian

# Uninstall and remove all build artefacts
./cleanup_flatpak.sh
```

### macOS — DMG

```bash
# Build (requires macOS with Xcode command-line tools)
python builddmg.py

# The DMG will be written to dist/Meridian-<version>.dmg
# Open it, drag Meridian.app to Applications, then launch from Spotlight or Launchpad.
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for Python version requirements, dev tooling, and how to run the test suite.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full project structure and design.

## Sample Feeds

A `feeds_export.json` file is included in the repository with a curated set of RSS, Atom, and MFEED subscriptions ready to import.

To load them:

1. Launch Meridian
2. Open **File > Import Feeds...**
3. Select `feeds_export.json` from the repository root

All feeds will be added and begin polling immediately.

## Features

- Subscribe to RSS, Atom, podcast, and YouTube feeds
- Feed discovery by topic: search for candidate feeds via feedsearch.dev, preview results, subscribe individually or in bulk
- Per-feed filter expressions (MMSP Appendix A ABNF); filter dialog shows existing terms as toggleable rows
- Background polling with conditional GET and rate-limit backoff
- Bulk feed management with select-all checkboxes
- Import / export subscriptions as JSON
- Catppuccin Mocha / Latte theme toggle; preference persists across restarts
- Full-text `content:encoded` rendering for article feeds
- Full keyboard navigation throughout: every control reachable and operable without a mouse; Enter and Space activate focused items; Left/Right navigate between buttons and dialog footer actions; amber focus ring on all focusable controls; Escape closes open drawers and dialogs

## License

LGPL-3.0. See [ARCHITECTURE.md](ARCHITECTURE.md) for third-party licence notes.
