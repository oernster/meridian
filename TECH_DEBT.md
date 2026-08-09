# Meridian: Technical Debt

A standing reference to the project's outstanding technical debt. It records what is still open, weighs whether each item is worth doing and gives the rationale. Every item is a behaviour-preserving internal concern: nothing here proposes reverting a feature or changing any UI or UX behaviour. Scope is the whole repository (the `meridian` package, the QML front end, the bespoke installer and the delivery scripts) read against `ARCHITECTURE.md` and `tests/structural/test_boundaries.py`.

---

## 1. Three QML files carry 2664 lines between them

The Python side of this repository is held to an unusually strong standard: a 100% branch-coverage gate over the `meridian` package and `installer/ops`, with three named omissions, plus AST layer-boundary tests, a 400-line cap with its danger band and an in-suite `black` and `flake8` run. That is stricter than most of the portfolio.

The size cap now reads `.qml`, so these three are carried explicitly in `_LEGACY_OVER_LIMIT` in `tests/structural/test_boundaries.py` and nothing new can join them. Coverage still measures Python only, so the QML remains unmeasured by it.

**The split now has a safety net it did not have.** `tests/ui/test_qml_compiles.py` compiles every QML file and fails on a syntax error, a property assigned on a type that has none or an unresolvable component: exactly what a careless extraction introduces; none of it visible before launch otherwise. All three were mutation-checked. `qmllint` was considered and rejected as a gate: it reports unqualified-access warnings by the hundred across this front end, which is inherent to one driven by context properties rather than a defect; it exits 0 regardless, so it cannot fail a build even where the report is fair.

**Two things a split has to know, both learned the expensive way.**

An extracted component still resolves the ids of the file that created it, because the instance's context chains to its creation context. That is why `ToastBar.qml` reads `theme` while declaring no such property. It means an outer-scope read survives extraction silently, invisible until the component is used somewhere else, so a new component declares what it needs and its test builds it with no caller in scope and asserts the engine raised no warnings.

The keyboard focus ring is the part that breaks quietly. Wiring by id inside one file becomes a signal the composition has to connect; a missed connection compiles, leaves every component correct on its own and simply strands the user at whichever end the ring broke. Nothing short of real key events through a real window shows it, because the handlers are `Keys.onTabPressed` on whichever item holds focus. `tests/ui/test_discovery_focus_ring.py` is the worked example.

| File | Lines |
|---|---|
| `meridian/ui/qml/main.qml` | 991 |
| `meridian/ui/qml/SubscriptionManager.qml` | 857 |
| `meridian/ui/qml/FeedReader.qml` | 816 |

Three files, the smallest 816 lines and the largest 991, carrying the keyboard focus wiring, the subscription management and the reader state machine. This is where the application's user-facing behaviour actually lives; it is the least constrained code in the repository.

Two things close this. They are independent:

- Split the three along the seams QML already gives (component extraction into sibling `.qml` files, which is the idiomatic decomposition and needs no new concepts). Each one that lands under the cap leaves the allowlist; the staleness test fails if it is left behind. The discovery panel is the pattern to copy: state and wiring in the composing file, each half naming nothing outside itself.
- Push the decision-shaped parts of those files down through the bridge into `meridian/application`, where the coverage gate can see them. The `test_bridge_*` modules show the bridge is already testable; the QML above it is doing more than presentation.

This is the only item in the file. `tests/infrastructure/parser/test_atom_parser.py` sits at exactly 400, within the cap but with no room left: whoever edits it next should take it to 350 or below rather than shave a line off.

---

## Looks like debt, not worth touching

- `builddmg.py` at 530 lines and the other delivery scripts (`buildexe.py`, `buildinstaller.py`, `build_flatpak.sh`, `cleanup_flatpak.sh`, `create_icons.py`, `create_splash.py`). These are linear recipes and are exempt from the module cap by design. Do not raise length against them. **The exemption is about length only:** every root script is now held to `black` and `flake8` by the in-suite assertions, which is what stopped `builddmg.py` drifting unnoticed.
- The three root `.spec` files (`Meridian.spec`, `MeridianDebug.spec`, `MeridianSetup.spec`) are PyInstaller artefacts and are untracked. Nothing to do.
- The fifteen tracked PNG sizes plus the `.ico`. Each is emitted by `create_icons.py` from a single master and consumed by a named packaging path. The single-master rule working, not asset sprawl.
- `installer/ui/_header_fit.py` and `_main_window_actions.py` carrying leading underscores at module level. Unconventional for a package, clear in intent (private to the installer UI) and harmless.
- The `asyncio_mode = "auto"` pytest setting. It hides explicit markers; removing it would mean annotating every async test for no behavioural gain.

## Not debt (do not "fix" these)

These look like candidates but are correct as they stand; changing them would regress or add cost for nothing.

- **Coverage configured in `pyproject.toml` rather than a `.coveragerc`.** Both work and `pyproject` is arguably the better home. This was carried as an item only because it made cross-project comparison harder and because the installer coverage work needed the `source` list edited; that work is done, so nothing practical turned on it. Ruled not debt on 2026-08-09. Do not reopen it as a consistency point.
- **The 100% gate covering the UI bridge.** Most projects here omit the UI layer wholesale. Meridian covers its bridge, which is why the `test_bridge_*` modules add up to as much as they do. This is the strength of the repository, not an excess.
- **`black --check` and `flake8` run as in-suite assertions** in `tests/structural/test_boundaries.py`, over the whole Python surface: `meridian/`, `installer/`, `tests/` and every root delivery script. It looks like the test suite doing a linter's job. It is what makes formatting non-optional without depending on a hook or a CI step; the narrower `meridian/`-only version is precisely how one delivery script drifted for long enough to become a tracked item.
- **`Feed.__post_init__` accepting `http://` as well as `https://`.** It looks like a hole in the transport policy. It is not: an imported or discovered feed can legitimately be plain HTTP; every layer that matters is already strict. The Add Subscription field only enables Subscribe for `https://`, redirects are followed to HTTPS targets only and the parsers drop non-HTTPS media. Tightening the entity would break import of existing reading lists for no security gain.
- **The Apache-2.0 model and LGPL-3.0 UI split**, with four licence files at root. `LICENSE` is the map, `LICENSE-APACHE-2.0.txt` covers domain, application, infrastructure and the scripts, `LICENSE-LGPL-3.0.txt` covers the Qt front end and `LICENSE-GPL-3.0.txt` is present because the LGPL text incorporates it by reference. All four are load-bearing. The Apache choice on the model side is deliberate, aligning with the MMSP ecosystem this application is the reference implementation for.
- **The five separate parser modules** (`rss`, `atom`, `mfeed`, `podcast`, `platform`) with one test module each. One source type per parser is the specification's own shape; consolidating them would destroy the mapping.
- **The three coverage omissions.** `meridian/main.py` is the composition root, where nothing is a decision. `shortcuts.create_shortcut` and `uninstall_ops._schedule_delete_after_exit` are a COM call writing into the running user's own profile and a detached PowerShell holding a real deletion; exercising either is a side effect on the developer's machine rather than a test. Every caller of all three is covered.
- **The separate `installer/ops` and `installer/ui` packages.** The decomposition that made the installer testable at all: `ops/` is free of Qt, which is what let it join the coverage gate; it is the shape the rest of the portfolio's installers should adopt.
