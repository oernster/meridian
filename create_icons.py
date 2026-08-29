"""Generate the application icon set and the header artwork from their masters.

Two unrelated derivations share this script because both read a committed
master PNG and write a committed derivative; a repository with two icon
generators reliably grows one that nothing runs.

The application icon is square by nature, so it is resized to a square. The
header marks are not: they are pictures drawn at a button's height, so a square
canvas would spend most of its width on nothing. They are cropped to the tight
box of their non-transparent pixels, then scaled by height alone.
"""

from pathlib import Path

from PIL import Image

from build_resources import (
    ART_DRAW_PX,
    ART_MASTER_DIR,
    ART_NAMES,
    ART_RENDER_DIR,
    ART_SUPERSAMPLE,
    DONATE_DRAW_PX,
    DONATE_MASTER,
    DONATE_OUTPUTS,
)

# Covers 100/125/150/175/200% DPI for all Windows shell icon slots.
_PNG_SIZES = [16, 20, 24, 28, 32, 40, 48, 56, 64, 72, 96, 128, 256, 512]
_ICO_SIZES = [16, 20, 24, 28, 32, 40, 48, 56, 64, 72, 96, 128, 256]


def crop_to_artwork(image: Image.Image) -> Image.Image:
    """The tight box of the image's non-transparent pixels."""
    box = image.getbbox()
    return image if box is None else image.crop(box)


def scale_to_height(image: Image.Image, height: int) -> Image.Image:
    """Resize to `height`, keeping the aspect ratio."""
    width = max(1, round(image.width * height / image.height))
    return image.resize((width, height), Image.LANCZOS)


def _generate_app_icon(root: Path) -> int:
    src = root / "meridian.png"
    if not src.exists():
        print(f"ERROR: {src} not found")
        return 1

    base = Image.open(src).convert("RGBA")

    print("Generating PNGs...")
    for size in _PNG_SIZES:
        img = base.resize((size, size), Image.LANCZOS)
        out = root / f"meridian_{size}.png"
        img.save(out, "PNG")
        print(f"  [OK] {out.name}")

    ico_path = root / "meridian.ico"
    base.save(ico_path, format="ICO", sizes=[(s, s) for s in _ICO_SIZES])
    print(f"  [OK] {ico_path.name}")
    return 0


def _render_mark(
    master_path: Path, outputs: list[Path], draw_px: int, root: Path
) -> None:
    """Crop one master to its artwork and write it to every destination.

    One render, written in a loop, because a mark that appears in two places
    drifts the moment the two are produced separately.
    """
    master = Image.open(master_path).convert("RGBA")
    mark = scale_to_height(crop_to_artwork(master), draw_px * ART_SUPERSAMPLE)
    for out in outputs:
        out.parent.mkdir(parents=True, exist_ok=True)
        mark.save(out, "PNG")
        print(f"  [OK] {out.relative_to(root)} ({mark.width}x{mark.height})")


def _generate_header_art(root: Path) -> int:
    masters = root / ART_MASTER_DIR
    renders = root / ART_RENDER_DIR

    missing = [name for name in ART_NAMES if not (masters / f"{name}.png").is_file()]
    if not (root / DONATE_MASTER).is_file():
        missing.append(DONATE_MASTER)
    if missing:
        print(f"ERROR: masters absent: {', '.join(missing)}")
        return 1

    renders.mkdir(parents=True, exist_ok=True)

    print("Generating header artwork...")
    for name in ART_NAMES:
        _render_mark(
            masters / f"{name}.png", [renders / f"{name}.png"], ART_DRAW_PX, root
        )

    # The footer's mark, two thirds of the header's and from the master where
    # it was delivered rather than from `assets/`. It goes to the site as well
    # as to the application, from this one render.
    print("Generating footer artwork...")
    _render_mark(
        root / DONATE_MASTER,
        [root / out for out in DONATE_OUTPUTS],
        DONATE_DRAW_PX,
        root,
    )
    return 0


def main() -> int:
    root = Path(__file__).parent

    if _generate_app_icon(root) != 0:
        return 1
    if _generate_header_art(root) != 0:
        return 1

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
