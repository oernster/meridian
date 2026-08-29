"""The marks, the generator and the wheel must name the same files.

The window has two icon bands: the header at the top and the tray at the foot.
Both source their marks by a relative URL. QML resolves that at run time and an
unresolvable source is not an error: the Image simply draws nothing, so a
missing render leaves an empty box where a control was. Nothing else in this
suite would see it, because the QML compile check stops short of instantiating
anything and the coverage gate reads Python only.

Ways the set can come apart, one test each: a mark sourced in the QML that was
never derived, a render absent from the tree, a render at a height the
generator would not have produced, a wheel that carries the QML without the
artwork beside it. The last is Linux only, so it fails nowhere a developer
would notice.

`build_resources` is the single source of truth for the names and the two drawn
sizes. It is deliberately free of Pillow so this file can read it; the renders'
own dimensions come from the PNG header rather than an image library for the
same reason.
"""

from __future__ import annotations

import importlib.util
import re
import struct
from pathlib import Path
from types import ModuleType

_ROOT = Path(__file__).parent.parent.parent
_QML_DIR = _ROOT / "meridian" / "ui" / "qml"
_HEADER_QML = _QML_DIR / "HeaderBar.qml"
_TRAY_QML = _QML_DIR / "BottomTray.qml"
_BUTTON_QML = _QML_DIR / "TrayButton.qml"

# The eight-byte signature every PNG opens with, then a length and a type.
# Width and height are the first two fields of the IHDR chunk that follows.
_PNG_IHDR_OFFSET = 16
_PNG_IHDR_LENGTH = 8


def _load_build_resources() -> ModuleType:
    """Load the root build module without putting the root on `sys.path`."""
    spec = importlib.util.spec_from_file_location(
        "build_resources", _ROOT / "build_resources.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_RESOURCES = _load_build_resources()
ART_RENDER_DIR: str = _RESOURCES.ART_RENDER_DIR
DONATE_OUTPUTS: tuple[str, ...] = _RESOURCES.DONATE_OUTPUTS
HEADER_DRAW_PX: int = _RESOURCES.ART_DRAW_PX
DONATE_DRAW_PX: int = _RESOURCES.DONATE_DRAW_PX
SUPERSAMPLE: int = _RESOURCES.ART_SUPERSAMPLE

# Every mark the window draws, against the height its render must be. The two
# bands are drawn at different sizes, so one expected height would not do.
EXPECTED_HEIGHT: dict[str, int] = {
    name: HEADER_DRAW_PX * SUPERSAMPLE for name in _RESOURCES.ART_NAMES
}
EXPECTED_HEIGHT[_RESOURCES.DONATE_NAME] = DONATE_DRAW_PX * SUPERSAMPLE


def _png_size(path: Path) -> tuple[int, int]:
    """The pixel dimensions in a PNG's IHDR chunk."""
    header = path.read_bytes()[_PNG_IHDR_OFFSET : _PNG_IHDR_OFFSET + _PNG_IHDR_LENGTH]
    width, height = struct.unpack(">II", header)
    return width, height


def _sourced_marks() -> list[str]:
    """Every mark the two bands ask for."""
    found: list[str] = []
    for qml in (_HEADER_QML, _TRAY_QML):
        found.extend(re.findall(r'"art/([^"]+)\.png"', qml.read_text(encoding="utf-8")))
    return found


def test_the_bands_source_marks_at_all() -> None:
    """A rename must not turn the checks below into a vacuous pass."""
    assert _sourced_marks(), f"no art/*.png sources found under {_QML_DIR.name}"


def test_every_sourced_mark_is_a_known_name() -> None:
    unknown = sorted(set(_sourced_marks()) - set(EXPECTED_HEIGHT))
    assert not unknown, (
        "The QML sources marks the generator never derives:\n"
        + "\n".join(unknown)
        + "\nAdd each to build_resources and rerun create_icons.py."
    )


def test_every_known_name_has_a_render() -> None:
    renders = _ROOT / ART_RENDER_DIR
    missing = [
        name for name in EXPECTED_HEIGHT if not (renders / f"{name}.png").is_file()
    ]
    assert not missing, (
        f"Marks named but absent from {ART_RENDER_DIR}:\n"
        + "\n".join(missing)
        + "\nRun create_icons.py."
    )


def test_every_render_is_the_derived_height() -> None:
    """A render at another height was dropped in rather than generated."""
    renders = _ROOT / ART_RENDER_DIR
    wrong = [
        f"{name}.png is {_png_size(renders / f'{name}.png')[1]}px tall, "
        f"expected {height}"
        for name, height in EXPECTED_HEIGHT.items()
        if (renders / f"{name}.png").is_file()
        and _png_size(renders / f"{name}.png")[1] != height
    ]
    assert not wrong, (
        "Renders the generator would not have produced:\n"
        + "\n".join(wrong)
        + "\nRun create_icons.py rather than scaling a master by hand."
    )


def test_the_wheel_carries_the_artwork() -> None:
    """The Flatpak installs a wheel, so package-data is its only route in."""
    packaging = (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    glob = ART_RENDER_DIR.split("meridian/", 1)[1] + "/*.png"
    assert f'"{glob}"' in packaging, (
        f"pyproject.toml package-data does not carry {glob}.\n"
        "Without it the Flatpak build ships QML whose marks resolve to nothing."
    )


def test_the_about_dialog_takes_the_copyright_from_version() -> None:
    """It carried its own copy of the notice, so the year had two homes.

    `meridian.version.APP_COPYRIGHT` was already declared and read by nothing,
    while AboutDialog.qml spelled the same words out again. A hardcoded notice
    is invisible until someone reads the dialog in a shipped build, which is
    exactly when it is too late to be the year it says.
    """
    about = (_QML_DIR / "AboutDialog.qml").read_text(encoding="utf-8")
    assert (
        "appCopyright" in about
    ), "AboutDialog.qml must read the appCopyright context property."
    assert "Oliver Ernster" not in about, (
        "AboutDialog.qml spells the copyright holder out; read APP_COPYRIGHT "
        "through the appCopyright context property instead."
    )


def test_the_button_draws_marks_at_the_height_they_were_rendered_for() -> None:
    """The supersample only holds if the two numbers agree.

    `ART_DRAW_PX` decides how tall the header's renders are made; `iconSize`
    decides how tall they are drawn. Raise one without the other and the marks
    either go soft or carry four times more pixels than the button will ever
    use, neither of which is visible in a screenshot.
    """
    source = _BUTTON_QML.read_text(encoding="utf-8")
    declared = re.search(r"property int iconSize:\s*(\d+)", source)
    assert declared, "TrayButton.qml declares no iconSize"
    assert int(declared.group(1)) == HEADER_DRAW_PX, (
        f"TrayButton draws marks at {declared.group(1)}px while "
        f"build_resources.ART_DRAW_PX renders them for {HEADER_DRAW_PX}px."
    )


def test_the_foot_takes_the_same_fraction_of_the_header_in_both_places() -> None:
    """The ratio is stated twice because Python renders and QML draws.

    BottomTray derives its mark from the header's at run time; the generator
    derives the render from ART_DRAW_PX at build time. Both must reach the same
    number or the footer's mark is scaled from a render made for another size.
    """
    source = _TRAY_QML.read_text(encoding="utf-8")
    numerator = re.search(r"_footerNumerator:\s*(\d+)", source)
    denominator = re.search(r"_footerDenominator:\s*(\d+)", source)
    assert numerator and denominator, "BottomTray.qml states no footer ratio"
    drawn = HEADER_DRAW_PX * int(numerator.group(1)) // int(denominator.group(1))
    assert drawn == DONATE_DRAW_PX, (
        f"BottomTray would draw the donate mark at {drawn}px while "
        f"build_resources renders it for {DONATE_DRAW_PX}px."
    )


def test_the_site_and_the_application_carry_the_same_donate_mark() -> None:
    """The site cannot import anything, so it holds its own copy of the picture.

    The generator writes both from one render in one loop. Comparing the bytes
    is what makes that hold: two copies produced separately drift into
    different artwork under the same name, which nothing else would notice.
    """
    written = [(_ROOT / out) for out in DONATE_OUTPUTS]
    missing = [str(path) for path in written if not path.is_file()]
    assert not missing, "Donate marks absent: " + ", ".join(missing)

    contents = {path.read_bytes() for path in written}
    assert len(contents) == 1, (
        "The donate mark differs between "
        + " and ".join(DONATE_OUTPUTS)
        + "; run create_icons.py rather than copying one over the other."
    )
