"""Generate splash screen PNG with app name, version, and author."""

import importlib.util
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

_version_path = Path(__file__).parent / "meridian" / "version.py"
_spec = importlib.util.spec_from_file_location("meridian.version", _version_path)
_version_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_version_mod)

__version__: str = _version_mod.__version__
APP_NAME: str = _version_mod.APP_NAME
APP_AUTHOR: str = _version_mod.APP_AUTHOR


def main() -> int:
    root = Path(__file__).parent
    logo_src = root / "meridian.png"

    W, H = 600, 300
    BG = (22, 24, 39, 255)
    ACCENT = (127, 176, 255, 255)
    WHITE = (229, 231, 235, 255)
    MUTED = (156, 163, 175, 255)

    img = Image.new("RGBA", (W, H), color=BG)
    draw = ImageDraw.Draw(img)

    logo_size = 100
    if logo_src.exists():
        logo_full = Image.open(logo_src).convert("RGBA")
        backed = Image.new("RGBA", logo_full.size, BG)
        backed.alpha_composite(logo_full)
        logo_rgb = backed.resize((logo_size, logo_size), Image.LANCZOS).convert("RGB")
        logo_mask = logo_full.split()[3].resize((logo_size, logo_size), Image.LANCZOS)
        logo_x = (W - logo_size) // 2
        logo_y = 30
        img.paste(logo_rgb, (logo_x, logo_y), logo_mask)

    def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
        for name in (
            ["segoeuib.ttf", "segoeui.ttf"] if bold else ["segoeui.ttf", "segoeuib.ttf"]
        ) + ["arial.ttf", "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]:
            try:
                return ImageFont.truetype(name, size)
            except Exception:
                continue
        return ImageFont.load_default()

    def _center_text(text: str, y: int, font, color) -> None:
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        draw.text(((W - w) // 2, y), text, font=font, fill=color)

    y = logo_size + 44
    _center_text(APP_NAME, y, _font(38, bold=True), ACCENT)

    y += 52
    _center_text(f"v{__version__}", y, _font(18), MUTED)

    y += 32
    _center_text(f"by {APP_AUTHOR}", y, _font(15), WHITE)

    corner_radius = 18
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [(0, 0), (W - 1, H - 1)], radius=corner_radius, fill=255
    )
    img_out = img.convert("RGBA")
    img_out.putalpha(mask)

    out = root / "meridian_splash.png"
    img_out.save(out, "PNG")
    print(f"[OK] {out.name}  ({W}x{H})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
