# <img width="128" height="128" alt="meridian-icon" src="https://github.com/user-attachments/assets/11d9d338-774b-47e7-88d1-918d9b89313b" /> Meridian

A desktop feed reader and subscription manager built on the [MMSP](https://github.com/MMSP-Spec) protocol. Supports RSS, Atom, podcast feeds, and YouTube channels with a native Qt Quick UI.

<img width="1265" height="827" alt="meridian" src="https://github.com/user-attachments/assets/54ff3fbb-5abc-445b-a2ee-808829ec214e" />

## Quick Start

```bash
# 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

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

See [DEVELOPMENT.md](DEVELOPMENT.md) for Python version requirements, dev tooling, and how to run the test suite.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full project structure and design.

## Features

- Subscribe to RSS, Atom, podcast, and YouTube feeds
- Per-feed filter expressions (MMSP Appendix A ABNF)
- Background polling with conditional GET and rate-limit backoff
- Bulk feed management with select-all checkboxes
- Import / export subscriptions as JSON
- Catppuccin Mocha / Latte theme toggle
- Full-text `content:encoded` rendering for article feeds

## License

Apache-2.0. See [ARCHITECTURE.md](ARCHITECTURE.md) for third-party licence notes.
