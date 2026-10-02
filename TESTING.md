# Testing

How Meridian is tested: running the suite, reading what it says, what the gate holds, the rules a run by hand has to follow and how a new test or guard is written. The rules themselves are in [ARCHITECTURE.md](ARCHITECTURE.md), each invariant linked to the test that enforces it. This file is how to work with those tests, not a second copy of what they assert.

## Before the first run

Two things a fresh machine needs, each of which fails quietly rather than loudly when missing:

- **The dev requirements, all of them.** `pip install -r requirements-dev.txt`. The MMSP conformance test skips itself when `jsonschema` cannot be imported, so an environment missing it passes with one test fewer and says so only in the skip count.
- **MMSP-Spec beside this repository**, for the same test. `tests/infrastructure/test_mmsp_conformance.py` reads the published feed schema from a sibling `MMSP-Spec` checkout and skips when there is none.

## Running the suite

From the repository root, in PowerShell:

```powershell
.\venv\Scripts\python.exe -m pytest
$LASTEXITCODE
```

**No window appears.** `tests/conftest.py` forces `QT_QPA_PLATFORM=offscreen` before any test module imports Qt, overriding whatever the shell holds, so a bare run stays off the desktop. `tests/ui/test_offscreen_platform.py` fails if that line is ever lost or moved below a Qt import; it was proved by removing the line and running under `QT_QPA_PLATFORM=minimal`.

That one command is the whole gate. `pyproject.toml` adds the coverage measurement and its floor to every run; `black` and `flake8` run inside the suite as assertions (`tests/structural/test_boundaries.py`), so a formatting or lint failure is a test failure. There is no separate gate script.

**A full run takes about thirty seconds.** 822 tests are collected: 297 interface, 219 infrastructure, 125 installer and version at the top of `tests/`, 90 application, 64 domain and 27 structural. A `WebEngineView` coming up on the offscreen platform prints Chromium GPU errors to the console; they are noise, not failures.

**Read the exit code, never the last line.** The suite is coverage gated, so it prints the coverage table last and no line of passed and failed; a coverage row such as `errors.py` also reads like a result to anybody searching the text. `0` means every test passed and the floor was met. Anything else means read the failures above the table. For a count without running anything, `python -m pytest --co -q --no-cov` ends with one.

## What the gate holds

| Scope | Floor | Why this scope |
|---|---|---|
| `meridian` (domain, application, infrastructure and the UI bridge) | 100% branch | Everything the application decides. The bridge is in the gate as well, which most of the portfolio does not do |
| `installer/ops` | 100% branch | Everything the setup program does to the machine, kept free of Qt so it can be gated |
| `installer/ui/_operation_dispatch.py` | 100% branch | The one Qt-free part of the installer window: which operation a button starts |
| The rest of `installer/ui` | none | The PySide6 installer window itself. What it decides was lifted into the two scopes above; what is left is widgets |
| `meridian/main.py` | none | The composition root; wiring, no decisions |
| Root delivery scripts | none | Linear build recipes. Held to `black` and `flake8`, never to coverage |

Inside the gated scopes, four installer functions and two branches carry `# pragma: no cover`: each function would do something real to the developer's machine and each branch is reached only by a system already broken. With `main.py` they are the seven omissions [ARCHITECTURE.md](ARCHITECTURE.md) lists with their reasons. The rule is that the caller of each is covered and asserts what it hands over.

## Running part of it

The coverage floor applies to every run, so a partial run needs `--no-cov` or it fails on coverage alone:

```powershell
.\venv\Scripts\python.exe -m pytest tests/ui/test_help_menu.py --no-cov -q
.\venv\Scripts\python.exe -m pytest tests/infrastructure --no-cov -q
.\venv\Scripts\python.exe -m pytest -k update --no-cov -q
.\venv\Scripts\python.exe -m pytest tests/structural/test_boundaries.py --no-cov -q
```

The last is the one to run after formatting: it holds the root delivery scripts, which `black meridian installer tests` does not reach. `pytest --cov-report=html` writes a browsable coverage report.

## Where the tests live

`tests/` mirrors the package, one directory a layer:

| Directory | What it tests | Against |
|---|---|---|
| `domain/` | entities, value objects, the filter evaluator | values built in the test |
| `application/` | the services and the update decision | the interfaces stood in for with `unittest.mock`; the update decision uses a small hand-written fake (`FakeSource`) |
| `infrastructure/` | the repositories, parsers, fetcher, scheduler, discovery client and the GitHub adapter | a real SQLite file in a temporary folder; HTTP through `respx`, which answers the request inside the process, except redirects: those go through each fetcher's production client over an `httpx.MockTransport` (`redirect_transport.py`), because a bare client never follows a redirect and so cannot show what production does with one |
| `ui/` | the bridge, the models and the real `main.qml` | a real `QApplication`; the window is built against hand-written stub controllers |
| `test_installer_*.py` | the setup program's operations | real files in a temporary folder, with the registry and processes stood in for |
| `structural/` | the rules no single test can see | the source tree itself |

## Writing a test

- **Qt is never mocked.** `tests/ui/conftest.py` provides one session `qapp` fixture; a second `QApplication` aborts the process, so no suite builds its own.
- **The window.** `tests/ui/window_stub.py` loads the real `main.qml` with `load_main_window(controller, update_controller, link_controller)`. `StubController`, `StubUpdateController` and `StubLinkController` carry exactly the surface the QML reaches for and record every call, so a test asserts which call reached the controller. Keep a Python reference to any stub handed to QML; one the garbage collector takes leaves QML calling nothing.
- **Keys, not inspection.** Focus and keyboard behaviour are driven with `QTest.keyClick` through the real window, because every handover is a signal the composing file connects and a missed connection compiles cleanly. `tests/ui/test_help_menu.py` is the nearest example to copy.
- **Cross-thread delivery is proved, not assumed.** `tests/ui/test_update_bridge.py` connects a probe to the controller's internal signal after the controller's own slot, so spinning until the probe fires guarantees the slot ran first. A test waits on that delivery, never on the service call the worker makes before it; ending a test early is how the old update bridge crashed. The same file proves the worker holds no reference to the controller: dropping it mid-check frees it at once.
- **Lists that recycle.** A test about anything a delegate does needs a list long enough to recycle its delegates and should assert that it is recycling before asserting anything else (`tests/ui/test_subscription_selection.py`, two hundred feeds).
- **No real network, browser or database.** HTTP goes through `respx`; the browser opener is injected into `ExternalLinkController`, with `QDesktopServices.openUrl` patched where the update bridge calls it; the session database is a temporary file from `tests/conftest.py`, never `~/.meridian/meridian.db`.

## Guards

A structural test checks the source tree rather than behaviour, so a rule holds for code nobody has written yet. The suite in `tests/structural/`:

| Guard | Holds |
|---|---|
| `test_boundaries.py` | layer direction by AST scan, the 400-line cap and the danger band below it, `black` and `flake8` over every Python file |
| `test_delivery_resources.py` | every delivery script bundles the same licence texts |
| `test_guide_marks.py` | every button on either band has a line in the Guide and every mark the Guide names exists |
| `test_tray_art.py` | the marks, their generator and the package data name the same files; the site's donate mark is byte-identical to the application's |
| `test_donation_address.py` | the payment address is Meridian's own, is `https://`, appears once in the package and nowhere in the QML |

`tests/ui/test_qml_compiles.py` belongs with them in spirit: the coverage gate reads Python only, so compiling every QML file is what catches a broken component.

**A guard is not trusted until it has been seen to fail.** Prove a new one by planting the violation it exists to catch, reading the failure, then restoring the tree in a `finally` block so an interrupted proof cannot leave the plant behind. A test written for a defect is run before the fix, where it has to fail for the reason named, not merely fail.

## What only a real machine settles

The suite never starts the application, never opens a browser, never reaches the network and never touches the registry. Everything below is therefore outside what a green run proves; check it by hand before a release it could affect.

| Check | Why the suite cannot |
|---|---|
| The update prompt against the live GitHub releases API | The adapter is tested against `respx`, never the real endpoint |
| The update check inside the Flatpak | Only an installed bundle shows whether the sandbox grants the network |
| Each packaged build starts: Windows setup, macOS DMG, Linux Flatpak | The suite runs from source; bundling, `VERSION` resolution and the licence texts in a frozen build are only real once built |
| The installer's shortcut, deferred uninstall delete, launch on finish and window to front | The four installer functions excluded from coverage, because running them acts on the machine |
| Installer tooltips over an inactive window | The offscreen platform does not model window activation faithfully |
| Audio and video playback, the YouTube embed | Need a real audio device and a real network; the embed is Google's player |
| Feed discovery and the topic suggestions | Feedly and Wikipedia are live services; the tests use recorded or stubbed answers |
| The donate and specification buttons open the browser | The opener is injected in tests; only a desktop proves the hand-off |
| The focus ring paints where focus is | The tests assert which item holds focus, not what is drawn |

See also [README.md](README.md), [ARCHITECTURE.md](ARCHITECTURE.md) and [DEVELOPMENT.md](DEVELOPMENT.md).
