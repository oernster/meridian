"""Generate multi-size PNGs and ICO from meridian.png."""

from pathlib import Path
from PIL import Image

# Covers 100/125/150/175/200% DPI for all Windows shell icon slots.
_PNG_SIZES = [16, 20, 24, 28, 32, 40, 48, 56, 64, 72, 96, 128, 256, 512]
_ICO_SIZES = [16, 20, 24, 28, 32, 40, 48, 56, 64, 72, 96, 128, 256]


def main() -> int:
    root = Path(__file__).parent
    src = root / "meridian.png"

    if not src.exists():
        print(f"ERROR: {src} not found")
        return 1

    base = Image.open(src).convert("RGBA")

    resized: dict[int, Image.Image] = {}

    print("Generating PNGs...")
    for size in _PNG_SIZES:
        img = base.resize((size, size), Image.LANCZOS)
        out = root / f"meridian_{size}.png"
        img.save(out, "PNG")
        resized[size] = img
        print(f"  [OK] {out.name}")

    ico_path = root / "meridian.ico"
    base.save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in _ICO_SIZES],
    )
    print(f"  [OK] {ico_path.name}")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
