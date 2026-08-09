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
