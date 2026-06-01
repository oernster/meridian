"""Generate multi-size PNGs and ICO from meridian.png."""

from pathlib import Path
from PIL import Image


def main() -> int:
    root = Path(__file__).parent
    src = root / "meridian.png"

    if not src.exists():
        print(f"ERROR: {src} not found")
        return 1

    base = Image.open(src).convert("RGBA")

    sizes = [16, 32, 48, 64, 128, 256, 512]
    resized: dict[int, Image.Image] = {}

    print("Generating PNGs...")
    for size in sizes:
        img = base.resize((size, size), Image.LANCZOS)
        out = root / f"meridian_{size}.png"
        img.save(out, "PNG")
        resized[size] = img
        print(f"  [OK] {out.name}")

    ico_imgs = [resized[s] for s in [16, 32, 48, 64, 128, 256] if s in resized]
    ico_path = root / "meridian.ico"
    ico_imgs[0].save(
        ico_path,
        format="ICO",
        sizes=[(img.width, img.height) for img in ico_imgs],
        append_images=ico_imgs[1:],
    )
    print(f"  [OK] {ico_path.name}")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
