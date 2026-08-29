"""Single source of truth for the resources every delivery script bundles.

`meridian/main.py` reads two licence texts at startup and injects them as the
`uiLicenceText` and `modelLicenceText` context properties. `_read_text`
degrades to "Licence text unavailable." rather than raising, so a delivery
script that omits a licence produces a build that starts cleanly and renders
that line in both licence dialogs instead of a licence.

The list lived in three hand-maintained copies (`buildexe.py`, `builddmg.py`
and `build_flatpak.sh`) and the macOS one had drifted to a single entry, so
every DMG shipped with both dialogs empty. The two Python scripts now read
this module; `tests/structural/test_delivery_resources.py` holds the shell
script and `meridian/main.py` to the same list, so no copy can drift again
without a test failing.

The header artwork joined it for the same reason from the other direction.
`create_icons.py` derives the marks and `HeaderBar.qml` sources them, so the
names had two homes and neither could see the other. They live here now, where
a structural test can hold the generator, the QML and the wheel's package-data
to one list without importing Pillow to do it.

This module deliberately states what is bundled, never how. Each script keeps
its own argument spelling, which genuinely differs between PyInstaller
invocations and a Flatpak manifest.
"""

from __future__ import annotations

# Every licence text shipped with the application. LICENSE is the map that
# says which licence covers which directory; LICENSE-GPL-3.0.txt is present
# because the LGPL text incorporates it by reference.
LICENCE_FILES: tuple[str, ...] = (
    "LICENSE",
    "LICENSE-LGPL-3.0.txt",
    "LICENSE-APACHE-2.0.txt",
    "LICENSE-GPL-3.0.txt",
)

# Where the header masters live and where their renders are written, both
# relative to the repository root. The render directory sits inside the QML
# tree because all three delivery scripts already bundle `meridian/ui/qml`
# whole; the wheel reaches it through the package-data glob in pyproject.toml.
ART_MASTER_DIR = "assets"
ART_RENDER_DIR = "meridian/ui/qml/art"

# The height the header draws its marks at, plus the factor the render is
# multiplied by so they stay crisp under display scaling. The buttons carry no
# words, so the mark is the whole control and is sized to be read as one.
# TrayButton.qml's iconSize default must match; a structural test says so.
ART_DRAW_PX = 54
ART_SUPERSAMPLE = 4

# Every mark the header asks for, named as both master and render. A name here
# with no master fails the generator; a name in HeaderBar.qml that is not here
# fails the structural test.
ART_NAMES: tuple[str, ...] = (
    "import",
    "export",
    "search",
    "manage",
    "ui-licence",
    "model-licence",
    "help",
    "specification",
    "dark-mode",
    "light-mode",
)

# The donate mark. Its master sits at the repository root rather than in
# `assets/` because that is where it was delivered; everything downstream of
# the crop is identical to the header's, so it rides the same render step.
DONATE_NAME = "donate"
DONATE_MASTER = "donate.png"

# Every destination the donate render is written to. The site cannot import
# anything from the application, so it necessarily holds its own copy of the
# picture; writing both from one render in one loop is what stops the two
# drifting into different artwork under the same name.
DONATE_OUTPUTS: tuple[str, ...] = (
    "meridian/ui/qml/art/donate.png",
    "docs/donate.png",
)

# The footer mark as a fraction of the header's, which is ClearBudget's rule
# taken whole: the band at the foot is subordinate to the one at the top, so
# two matching bands would weigh the window down at both ends. Expressed
# against ART_DRAW_PX rather than as a second pixel number, so retuning the
# header carries the footer with it and the two cannot drift.
FOOTER_NUMERATOR = 2
FOOTER_DENOMINATOR = 3
DONATE_DRAW_PX = ART_DRAW_PX * FOOTER_NUMERATOR // FOOTER_DENOMINATOR
