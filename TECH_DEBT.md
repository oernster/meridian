# Meridian: Technical Debt

A standing reference to the project's outstanding technical debt. It records what is still open, weighs whether each item is worth doing and gives the rationale. Every item is a behaviour-preserving internal concern: nothing here proposes reverting a feature or changing any UI or UX behaviour. Scope is the whole repository (the `meridian` package, the QML front end, the bespoke installer and the delivery scripts) read against `ARCHITECTURE.md` and `tests/structural/test_boundaries.py`.

---

## 1. Four QML files carry 3736 lines between them

The Python side of this repository is held to an unusually strong standard: a 100% branch-coverage gate over the `meridian` package and `installer/ops`, with three named omissions, plus AST layer-boundary tests, a 400-line cap with its danger band and an in-suite `black` and `flake8` run. That is stricter than most of the portfolio.

The size cap now reads `.qml`, so these four are carried explicitly in `_LEGACY_OVER_LIMIT` in `tests/structural/test_boundaries.py` and no fifth can join them. Coverage still measures Python only, so the QML remains unmeasured.

| File | Lines |
|---|---|
| `meridian/ui/qml/FeedDiscovery.qml` | 1072 |
| `meridian/ui/qml/main.qml` | 991 |
| `meridian/ui/qml/SubscriptionManager.qml` | 857 |
| `meridian/ui/qml/FeedReader.qml` | 816 |

Four files, each two to two and three-quarter times the module cap, carrying the keyboard focus wiring, the discovery flow, the delete confirmations and the reader state machine. This is where the application's user-facing behaviour actually lives; it is the least constrained code in the repository.

Two things close this. They are independent:

- Split the four along the seams QML already gives (component extraction into sibling `.qml` files, which is the idiomatic decomposition and needs no new concepts). Each one that lands under the cap leaves the allowlist, and the staleness test fails if it is left behind.
- Push the decision-shaped parts of those files down through the bridge into `meridian/application`, where the coverage gate can see them. `test_bridge.py` shows the bridge is already testable; the QML above it is doing more than presentation.

This is the single largest item in the file and everything else here is smaller.

## 2. `tests/ui/test_bridge.py` is 1029 lines

The size cap now reads the test tree as well as the package, so this file is carried in `_LEGACY_OVER_LIMIT` alongside the four QML files. `tests/infrastructure/parser/test_atom_parser.py` sits at exactly 400, within the cap but with no room left: whoever edits it next should take it to 350 or below rather than shave a line off.

The bridge test is doing valuable work (it is why the QML bridge is covered at all), so this is not a suggestion to shrink it by deleting assertions. It wants splitting by the bridge surface it exercises: subscription operations, item operations, discovery and settings.

## 3. There is no `.coveragerc`, so the coverage configuration lives in two idioms

Coverage is configured entirely inside `pyproject.toml` (`[tool.coverage.run]`, `[tool.coverage.report]`) while the rest of the portfolio uses a `.coveragerc` beside it. Both work and `pyproject` is arguably the better home.

It had a second reason: the installer coverage work needed the `source` list edited, and whoever did that should know there was no `.coveragerc` to look for. That work is done, so only the cross-project comparison argument remains, which was never worth changing on its own.

**Recommendation: move this to "Not debt".** With its practical driver spent, what is left is a preference for one working idiom over another working idiom. Awaiting a decision rather than being deleted, since an item that vanishes without a ruling is a discrepancy.

## 4. The reference implementation never runs the specification's conformance suite

Meridian is publicly billed as the reference implementation of MMSP. It implements the protocol independently in `meridian/infrastructure/fetching/parser/mfeed_parser.py`, depends on nothing from the MMSP-Spec repository and shares no test with it.

So the normative rules are expressed twice; nothing checks that the two agree. Meridian's parser could drift from the specification it is the reference for; both repositories would stay green. `http_fetcher.py` also hardcodes `_USER_AGENT = "MMSP/1.0"`, a copy of the protocol version that lives nowhere near the specification that defines it.

This is ranked below the QML item because closing it depends on the specification repository; that repository is deliberately not a package: MMSP-Spec publishes the spec text, the JSON Schemas and a conformance suite while declaring no build system or distribution metadata by design. So the validators cannot simply be imported from PyPI.

The realistic route is therefore to consume the specification's artefacts rather than its code: point `tests/infrastructure/parser/test_mfeed_parser.py` at the published JSON Schemas and validate this parser's output against them; take the protocol version from the same place rather than from the `_USER_AGENT` literal here. That keeps the dependency one-directional (implementation depends on spec, never the reverse), which is the correct shape for a reference implementation.

Until then this is a known, deliberate gap, not an oversight. It is recorded so the phrase "reference implementation" is never read as "verified against the spec".

## 5. `builddmg.py` fails `black --check`

`python -m black --check builddmg.py` exits 1 with "would reformat builddmg.py". The script also carries twelve `flake8` violations: four `E221` multiple-spaces-before-operator, which black fixes, and four `E501` long lines, which it does not.

This is drift rather than a deliberate exemption, which was settled by measurement on 2026-08-09: `buildexe.py`, `buildinstaller.py`, `create_icons.py`, `create_splash.py`, the whole of `installer/` and the whole of `tests/` all pass black cleanly. `builddmg.py` is the only file in the repository outside `meridian/` that does not, and it already failed before the licence work touched it.

The "Looks like debt" note below covers `builddmg.py` for its 530 lines, which is the module-cap exemption. That exemption is about length and says nothing about formatting; a delivery script being exempt from being split is not a reason for it to be unformatted.

Closing it is a black run plus a manual pass over the four long lines. The durable half is extending `test_black_compliance`, which currently checks `meridian/` only, to the delivery scripts as well, so the same drift cannot recur silently.

---

## Looks like debt, not worth touching

- `builddmg.py` at 530 lines and the other delivery scripts (`buildexe.py`, `buildinstaller.py`, `build_flatpak.sh`, `cleanup_flatpak.sh`, `create_icons.py`, `create_splash.py`). These are linear recipes and are exempt from the module cap by design. Do not raise length against them.
- The three root `.spec` files (`Meridian.spec`, `MeridianDebug.spec`, `MeridianSetup.spec`) are PyInstaller artefacts and are untracked. Nothing to do.
- The fifteen tracked PNG sizes plus the `.ico`. Each is emitted by `create_icons.py` from a single master and consumed by a named packaging path. The single-master rule working, not asset sprawl.
- `installer/ui/_header_fit.py` and `_main_window_actions.py` carrying leading underscores at module level. Unconventional for a package, clear in intent (private to the installer UI) and harmless.
- The `asyncio_mode = "auto"` pytest setting. It hides explicit markers; removing it would mean annotating every async test for no behavioural gain.

## Not debt (do not "fix" these)

These look like candidates but are correct as they stand; changing them would regress or add cost for nothing.

- **The 100% gate covering the UI bridge.** Most projects here omit the UI layer wholesale. Meridian covers its bridge and that is why `test_bridge.py` is large. This is the strength of the repository, not an excess.
- **`black --check` and `flake8` run as in-suite assertions** in `tests/structural/test_boundaries.py`. It looks like the test suite doing a linter's job. It is what makes formatting non-optional without depending on a hook or a CI step.
- **`Feed.__post_init__` accepting `http://` as well as `https://`.** It looks like a hole in the transport policy. It is not: an imported or discovered feed can legitimately be plain HTTP; every layer that matters is already strict. The Add Subscription field only enables Subscribe for `https://`, redirects are followed to HTTPS targets only and the parsers drop non-HTTPS media. Tightening the entity would break import of existing reading lists for no security gain.
- **The Apache-2.0 model and LGPL-3.0 UI split**, with four licence files at root. `LICENSE` is the map, `LICENSE-APACHE-2.0.txt` covers domain, application, infrastructure and the scripts, `LICENSE-LGPL-3.0.txt` covers the Qt front end and `LICENSE-GPL-3.0.txt` is present because the LGPL text incorporates it by reference. All four are load-bearing. The Apache choice on the model side is deliberate, aligning with the MMSP ecosystem this application is the reference implementation for.
- **The five separate parser modules** (`rss`, `atom`, `mfeed`, `podcast`, `platform`) with one test module each. One source type per parser is the specification's own shape; consolidating them would destroy the mapping.
- **`meridian/main.py` being the only coverage omission.** Composition root. Nothing there is a decision.
- **The separate `installer/ops` and `installer/ui` packages.** The decomposition that made the installer testable at all: `ops/` is free of Qt, which is what let it join the coverage gate, and it is the shape the rest of the portfolio's installers should adopt.
