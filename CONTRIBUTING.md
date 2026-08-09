# Contributing to Meridian

Thanks for your interest in Meridian. This document describes how the project is
built, the standards a change has to meet and the design boundaries a change has
to respect. Reading it before you open a pull request will save a round trip.

Meridian is a single-device desktop feed reader built on the
[MMSP](https://ernster.dev/MMSP-Spec/) protocol, written in Python with a
Qt Quick (QML) UI and laid out as a clean-architecture project. The bar for
merging is correctness, layer discipline and a green test suite at 100% coverage.

## Before you start

- For anything beyond a typo or a docs fix, open an issue first and describe the
  change. This lets us agree on scope and on whether it fits Meridian's design
  before you invest time.
- Check the [open issues](https://github.com/oernster/meridian/issues) so you do
  not duplicate work already in flight.
- Keep pull requests focused. One logical change per PR reviews faster and is
  easier to reason about than a mixed bag.

## Development setup

The full setup, Python version policy and tooling list live in
[DEVELOPMENT.md](DEVELOPMENT.md). In short:

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

pip install -r requirements-dev.txt
python -m meridian.main
```

Python 3.11 is the minimum; 3.12+ is recommended.

## Architecture: the layer invariant

Meridian follows a strict dependency direction. This is the single most
important rule in the project and it is non-negotiable:

```
UI -> Application -> Domain <- Infrastructure
```

- **Domain** (`meridian/domain`): stdlib only. No I/O, no framework imports, no
  wall-clock reads. Pure dataclasses and pure services.
- **Application** (`meridian/application`): Domain plus stdlib only. Defines the
  interfaces (ABCs) that Infrastructure implements. Never imports Infrastructure
  or UI.
- **Infrastructure** (`meridian/infrastructure`): implements the Application
  interfaces and owns all I/O (SQLite, HTTP, parsing). Never imported by Domain
  or Application.
- **UI** (`meridian/ui`): a client of Application only, through `AppController`.
  No direct access to Domain entities or to Infrastructure.

Cross-layer data moves as DTOs defined in `application/dto`, never as Domain
entities crossing into the UI. New behaviour belongs in the layer that owns it:
ask "which layer is responsible for this?" before you write it. If you are
unsure, [ARCHITECTURE.md](ARCHITECTURE.md) documents every component and the
reasoning behind the key design decisions.

These boundaries are enforced by AST scanning in
`tests/structural/test_boundaries.py`. A boundary violation is a test failure,
not a style note.

## Coding standards

- **No magic numbers.** Domain-specific values come from data, configuration or
  a named constant at the right layer. `POLL_FLOOR_SECONDS = 300` is the model:
  one named source of truth, no bare literals in logic. The only acceptable
  literals are pure structural constants such as `0`, `1` and `100`.
- **Immutable domain.** Domain entities and value objects are
  `@dataclass(frozen=True, slots=True)` with `from __future__ import
  annotations`. Use `tuple[T, ...]` rather than `list` for collections on a
  frozen dataclass. Mutable state lives in Infrastructure ORM rows; entities are
  re-hydrated into new instances on each read.
- **Dependency injection only.** Wiring happens in one place, `meridian/main.py`
  (the composition root). No module-level singletons, no service locators and no
  containers. Constructors take their dependencies as arguments.
- **Module size.** Modules stay at or under 400 lines; the rule reads the
  QML components and the test tree and the installer, not just the package. A
  file landing in the top 5% of the cap (381 to 399) is one edit from breaking
  it, so the rule is to take it to 350 or below in one go rather than shave a
  line off. The root delivery scripts are exempt by design, being linear
  recipes; the exemption is about length and never about formatting. All of
  this is checked by structural tests.
- **One version string.** The root `VERSION` file is the single source of truth.
  `meridian/version.py` reads it and everything else imports `__version__` from
  there. Do not write a version number into source, into a build script or into
  any markdown file; the `docs/` site carries stamped tokens that
  `stamp_version.py` refreshes.
- **Formatting and linting.** `black` (line length 88) and `flake8` are run as
  part of the test suite over `meridian/`, `installer/`, `tests/` and every
  `*.py` at the repository root, so unformatted or lint-failing code fails the
  build. Run both before you push:

  ```bash
  black meridian installer tests
  flake8 meridian installer tests
  pytest tests/structural/test_boundaries.py
  ```

  The last command is the one that decides: it holds the root delivery scripts
  too, which the first two do not reach.

- **Prose style.** In code comments, docstrings and docs, avoid em dashes and
  avoid the serial comma; prefer a comma, colon, semicolon or parentheses for a
  pause. Keep documentation plain and free of marketing language.

## Tests and coverage

Coverage is gated at 100% (`--cov-fail-under=100`, branch coverage on). A failing
test or a single missed branch is a build failure. Add tests with every change;
new code without tests will not reach 100% and so will not merge.

```bash
pytest                               # full suite with the coverage gate
pytest tests/ui/test_bridge_items.py -v   # a single file
pytest --cov-report=html             # an HTML coverage report
```

The coverage-gated run prints the coverage table last and emits no "N passed"
line, so trust the exit code rather than grepping the output: `0` means all
tests passed and the gate was met.

Put each test at the layer it exercises:

| Layer | Test style | I/O |
|---|---|---|
| domain | pure unit tests | none |
| application | unit tests with the interfaces faked or mocked | none |
| infrastructure | integration tests against a real SQLite tmpdir; `respx` for HTTP | yes (temp) |
| ui | real QApplication from the session `qapp` fixture in `tests/ui/conftest.py`, offscreen platform | none |
| structural | AST and source scans (boundaries, module size, black, flake8) | file reads |

Never mock Qt. The UI tests use a real `QApplication` on the offscreen platform.

## Keyboard navigation

Meridian is fully keyboard operable and every interactive control has to remain
so. If you add or change a control in the QML layer, wire its focus and key
handling to match the rest of the UI: every control reachable by Tab, an
explicit focus ring, Space and Enter to activate, Left and Right to move between
sort chips and dialog footer actions and Escape to close drawers and dialogs. A
Qt Quick Controls `Button` handles Space for you but never Enter, so a bare
`Button` needs its own `Keys.onReturnPressed`. Two in the tree still lack one,
the reader's Mark all read and the transport's play and pause, which is a defect
rather than a pattern to copy. See
the keyboard-navigation notes in [ARCHITECTURE.md](ARCHITECTURE.md) for the
`forceActiveFocus` and `FocusScope` gotchas before you touch the tab chain.

## Design boundaries

Some things are deliberate choices, not gaps. A pull request that crosses one of
these will be declined regardless of code quality, so check here first:

- **Single-device by design.** No cloud sync, no server component and no account
  system. JSON export and import is the migration path between machines. Read
  state is a local client concern and does not transfer.
- **MMSP semantics.** Meridian is a pull-only reference client. There are no
  subscriber push notifications on new items; the scheduler is silent and items
  appear on the next poll tick or user view.
- **Transport policy.** `Feed.__post_init__` accepts `http://` and `https://`
  and rejects every other scheme, so an imported or discovered plain-HTTP feed
  still loads. Everything downstream is stricter and stays that way: the Add
  Subscription field only enables Subscribe for an `https://` URL, `HttpFetcher`
  discards a non-HTTPS redirect target and the parsers drop non-HTTPS media,
  enclosure and transcript URLs.
- **No new heavy dependencies** without discussion. The runtime dependency set
  is intentionally small. Propose additions in an issue first.

## Destructive actions

Any feature that removes user content needs a modal confirmation that names what
is removed and the consequence, both for single and for bulk deletion. The
existing feed-delete and bulk-delete dialogs are the reference. Do not add a
delete path without a confirmation.

## Commit messages and pull requests

- Write commit subjects in the imperative mood and keep them short. Add a body
  only when the "why" is not obvious from the subject.
- Rebase or update your branch on the latest default branch before opening the
  PR. Make sure `pytest` is green locally first.
- In the PR description, say what changed and why, link the issue it closes and
  note anything a reviewer should look at closely.
- Expect review feedback on layer placement, test coverage and the design
  boundaries above. None of those are personal; they are how the project stays
  coherent over time.

## Licence

Meridian is dual-licensed, split by component. The user interface (`meridian/ui`)
is LGPL-3.0-or-later, to align with Qt's licensing; the model (everything else:
`domain`, `application`, `infrastructure`, `main.py`, `version.py`, build scripts
and tests) is Apache-2.0, aligning with the MMSP specification ecosystem. By
contributing you agree that your contribution is provided under whichever of
those two licences covers the files you change. See [LICENSE](LICENSE) for the
component map and the third-party licence notes in
[ARCHITECTURE.md](ARCHITECTURE.md).
