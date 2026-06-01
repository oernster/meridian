"""Generate splash screen PNG with app name, version, and author."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from meridian.version import __version__, APP_NAME, APP_AUTHOR


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
        logo = (
            Image.open(logo_src)
            .convert("RGBA")
            .resize((logo_size, logo_size), Image.LANCZOS)
        )
        logo_x = (W - logo_size) // 2
        logo_y = 30
        img.paste(logo, (logo_x, logo_y), logo)

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

    out = root / "meridian_splash.png"
    img.convert("RGB").save(out, "PNG")
    print(f"[OK] {out.name}  ({W}x{H})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
