# Meridian: Technical Debt

A standing reference to the project's outstanding technical debt. It records what is still open, weighs whether each item is worth doing and gives the rationale. Every item is a behaviour-preserving internal concern: nothing here proposes reverting a feature or changing any UI or UX behaviour. Scope is the whole repository (the `meridian` package, the QML front end, the bespoke installer and the delivery scripts) read against `ARCHITECTURE.md` and `tests/structural/test_boundaries.py`.

---

## 1. Roughly 3700 lines of QML sit outside every gate in the project

The Python side of this repository is held to an unusually strong standard: a 100% branch-coverage gate over the whole `meridian` package with only `main.py` omitted, plus AST layer-boundary tests, a 400-line cap, and `black` and `flake8` run as in-suite assertions. That is stricter than most of the portfolio.

None of it reaches the QML.

| File | Lines |
|---|---|
| `meridian/ui/qml/FeedDiscovery.qml` | 1072 |
| `meridian/ui/qml/main.qml` | 991 |
| `meridian/ui/qml/SubscriptionManager.qml` | 857 |
| `meridian/ui/qml/FeedReader.qml` | 816 |

`test_all_source_files_under_400_lines()` walks `_SRC.rglob("*.py")`, so `.qml` is invisible to it; coverage measures Python, so the QML is invisible there too. Four files, each two to two and a half times the module cap, carrying the keyboard focus wiring, the discovery flow, the delete confirmations and the reader state machine. This is where the application's user-facing behaviour actually lives, and it is the least constrained code in the repository.

Two things close this, and they are independent:

- Extend the size test to `.qml` and split the four files along the seams QML already gives (component extraction into sibling `.qml` files, which is the idiomatic decomposition and needs no new concepts).
- Push the decision-shaped parts of those files down through the bridge into `meridian/application`, where the coverage gate can see them. `test_bridge.py` shows the bridge is already testable; the QML above it is doing more than presentation.

This is the single largest item in the file and everything else here is smaller.

## 2. The version is a literal in `meridian/version.py`, with no `VERSION` file

`meridian/version.py` declares `__version__: str = "2.4.0"` directly, and eight other modules import it (`installer/app.py`, `installer/build_payload.py`, `installer/ops/install_ops.py`, `installer/ops/repair_ops.py`, `builddmg.py`, `create_splash.py` and others).

The single-import discipline is good: there is one literal, not nine. But the literal is in a Python module rather than in a `VERSION` file, `pyproject.toml` does not read it, there is no `stamp_version.py` and the markdown and the `docs/` site carry no stamped tokens. A release bump is therefore a source edit plus a manual sweep of anything that quotes the number in prose.

The fix is the established pattern: `VERSION` at root as the only real string, `version.py` reading it with a `0.0.0-dev` fallback, `pyproject.toml` made dynamic, and a `stamp_version.py` writing delimited tokens into the markdown and `docs/`. Every consumer above keeps importing `meridian.version` unchanged.

`version.py` also hardcodes `APP_COPYRIGHT = "© 2026 Oliver Ernster"`. A year baked into application identity goes stale on a fixed date for no benefit; drop the year.

## 3. The installer is 2812 lines with no tests and thirty unexplained broad handlers

`installer/` is better structured than most bespoke installers here: `ops/` (install, uninstall, repair, shortcuts, running-app detection) is genuinely separated from `ui/`, and no module is over 400 lines. The decomposition is already done, which is what makes the rest surprising.

`[tool.coverage.run] source = ["meridian"]` means none of it is measured, and there are no installer tests. Around thirty `except Exception` blocks across `install_ops.py`, `shortcuts.py`, `repair_ops.py`, `uninstall_ops.py`, `_main_window_actions.py` and `_header_fit.py` carry no `# noqa` and no comment.

The exposure is concrete: `install_ops.py` writes the HKCU uninstall key, `shortcuts.py` creates Start Menu and Desktop entries and `uninstall_ops.py` removes files from a user's machine. Every one of those is a swallowed exception away from leaving a half-installed application with no visible error. Because `ops/` is already pure of Qt, bringing it into the coverage source and testing it against a temporary directory and a fake registry writer is a contained piece of work with a high return.

The broad handlers should each get one line saying what is being degraded and why, exactly as `installer/app.py` and the build scripts do elsewhere in the portfolio.

## 4. Test modules are outside the size cap and one is 1029 lines

The structural test scopes itself to `meridian/`, so the test tree is unmeasured. `tests/ui/test_bridge.py` is 1029 lines and `tests/infrastructure/parser/test_atom_parser.py` is exactly 400.

The bridge test is doing valuable work (it is why the QML bridge is covered at all), so this is not a suggestion to shrink it by deleting assertions. It wants splitting by the bridge surface it exercises: subscription operations, item operations, discovery and settings. The rule in this portfolio applies to test files exactly as to source, and the cap should be extended over `tests/` at the same time as item 1 extends it over `.qml`.

## 5. `feeds_export.json` is a personal subscription list committed at repository root

The file is a real export of the author's own feeds, including named YouTube channel subscriptions. It is tracked, at root, in a public repository.

It is presumably there as a worked example of the export format, which is a legitimate need. The debt is that a personal reading list is doing the job: it discloses something with no benefit, it goes stale, and root is the wrong place for it. Replace it with a small neutral sample under an `examples/` directory and reference it from the docs.

## 6. There is no `.coveragerc`, so the coverage configuration lives in two idioms

Coverage is configured entirely inside `pyproject.toml` (`[tool.coverage.run]`, `[tool.coverage.report]`) while the rest of the portfolio uses a `.coveragerc` beside it. Both work and `pyproject` is arguably the better home.

This is recorded only because it makes cross-project comparison harder than it needs to be, and because item 3's fix requires editing the `source` list: whoever does that should know there is no `.coveragerc` to look for. Not worth changing on its own.

## 7. The reference implementation never runs the specification's conformance suite

Meridian is publicly billed as the reference implementation of MMSP. It implements the protocol independently in `meridian/infrastructure/fetching/parser/mfeed_parser.py`, depends on nothing from the MMSP-Spec repository and shares no test with it.

So the normative rules are expressed twice, and nothing checks that the two agree. Meridian's parser could drift from the specification it is the reference for, and both repositories would stay green. `http_fetcher.py` also hardcodes `_USER_AGENT = "MMSP/1.0"`, a copy of the protocol version that lives nowhere near the specification that defines it.

This is ranked below the QML item because closing it depends on the specification repository, and that repository is deliberately not a package: MMSP-Spec publishes the spec text, the JSON Schemas and a conformance suite, and declares no build system or distribution metadata by design. So the validators cannot simply be imported from PyPI.

The realistic route is therefore to consume the specification's artefacts rather than its code: point `tests/infrastructure/parser/test_mfeed_parser.py` at the published JSON Schemas and validate this parser's output against them, and take the protocol version from the same place rather than from the `_USER_AGENT` literal here. That keeps the dependency one-directional (implementation depends on spec, never the reverse), which is the correct shape for a reference implementation.

Until then this is a known, deliberate gap, not an oversight. It is recorded so the phrase "reference implementation" is never read as "verified against the spec".

---

## Looks like debt, not worth touching

- `builddmg.py` at 530 lines and the other delivery scripts (`buildexe.py`, `buildinstaller.py`, `build_flatpak.sh`, `cleanup_flatpak.sh`, `create_icons.py`, `create_splash.py`). These are linear recipes and are exempt from the module cap by design. Do not raise length against them.
- The three root `.spec` files (`Meridian.spec`, `MeridianDebug.spec`, `MeridianSetup.spec`) are PyInstaller artefacts and are untracked. Nothing to do.
- The fifteen tracked PNG sizes plus the `.ico`. Each is emitted by `create_icons.py` from a single master and consumed by a named packaging path. The single-master rule working, not asset sprawl.
- `installer/ui/_header_fit.py` and `_main_window_actions.py` carrying leading underscores at module level. Unconventional for a package, clear in intent (private to the installer UI) and harmless.
- The `asyncio_mode = "auto"` pytest setting. It hides explicit markers, and removing it would mean annotating every async test for no behavioural gain.

## Not debt (do not "fix" these)

These look like candidates but are correct as they stand; changing them would regress or add cost for nothing.

- **The 100% gate covering the UI bridge.** Most projects here omit the UI layer wholesale. Meridian covers its bridge and that is why `test_bridge.py` is large. This is the strength of the repository, not an excess.
- **`black --check` and `flake8` run as in-suite assertions** in `tests/structural/test_boundaries.py`. It looks like the test suite doing a linter's job. It is what makes formatting non-optional without depending on a hook or a CI step.
- **The Apache-2.0 model and LGPL-3.0 UI split**, with four licence files at root. `LICENSE` is the map, `LICENSE-APACHE-2.0.txt` covers domain, application, infrastructure and the scripts, `LICENSE-LGPL-3.0.txt` covers the Qt front end and `LICENSE-GPL-3.0.txt` is present because the LGPL text incorporates it by reference. All four are load-bearing. The Apache choice on the model side is deliberate, aligning with the MMSP ecosystem this application is the reference implementation for.
- **The five separate parser modules** (`rss`, `atom`, `mfeed`, `podcast`, `platform`) with one test module each. One source type per parser is the specification's own shape; consolidating them would destroy the mapping.
- **`meridian/main.py` being the only coverage omission.** Composition root. Nothing there is a decision.
- **The separate `installer/ops` and `installer/ui` packages.** The decomposition item 3 asks the rest of the portfolio's installers to adopt.
