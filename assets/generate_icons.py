"""Generate reproducible project-owned icons and packaging artwork."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from lego_element_lookup.icon_generation import SIZES, draw_icon

ROOT = Path(__file__).resolve().parent


def _font(size: int, *, bold: bool = False):
    names = ("DejaVuSans-Bold.ttf", "Arial Bold.ttf") if bold else ("DejaVuSans.ttf", "Arial.ttf")
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _background(size: tuple[int, int]) -> Image.Image:
    width, height = size
    image = Image.new("RGB", size, "#F3F5F7")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, width, 112 * height // 450), radius=0, fill="#252A31")
    # Original, abstract brick/stud pattern—no LEGO marks or third-party artwork.
    for x in range(-20, width + 40, 80):
        draw.rounded_rectangle((x, height - 90, x + 52, height - 40), radius=12, outline="#D6A91D", width=3)
        draw.ellipse((x + 14, height - 77, x + 38, height - 53), outline="#D6A91D", width=3)
    draw.text((42, 30), "LEGO Element Lookup", fill="white", font=_font(34, bold=True))
    draw.text((42, 73), "Drag the app to Applications", fill="#F4CA42", font=_font(20))
    draw.text((42, height - 30), "Lightweight offline LEGO element lookup", fill="#525D69", font=_font(17))
    draw.text((width - 410, height - 30), "Unsigned beta: macOS approval may be required", fill="#525D69", font=_font(13))
    arrow_y = height // 2 + 20
    draw.line((width // 2 - 70, arrow_y, width // 2 + 100, arrow_y), fill="#C99400", width=8)
    draw.polygon(((width // 2 + 100, arrow_y), (width // 2 + 70, arrow_y - 20), (width // 2 + 70, arrow_y + 20)), fill="#C99400")
    return image


def _windows_wizard(size: tuple[int, int], *, compact: bool) -> Image.Image:
    width, height = size
    image = Image.new("RGB", size, "#252A31")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width, max(14, height // 14)), fill="#F4CA42")
    icon = draw_icon(min(width - 20, 112 if not compact else 42)).convert("RGBA")
    image.paste(icon, ((width - icon.width) // 2, 28 if not compact else 8), icon)
    if not compact:
        draw.text((16, 168), "LEGO", fill="white", font=_font(18, bold=True))
        draw.text((16, 190), "Element Lookup", fill="white", font=_font(18, bold=True))
        draw.text((16, 224), "Offline element lookup", fill="#D4DAE1", font=_font(12))
    return image


def generate_assets(root: Path = ROOT) -> None:
    images = [draw_icon(size) for size in SIZES]
    root.mkdir(parents=True, exist_ok=True)
    images[-1].save(root / "icon.png")
    images[-1].save(root / "icon.ico", sizes=[(size, size) for size in SIZES if size <= 256])
    images[-1].save(root / "icon.icns", append_images=images[:-1])

    dmg = root / "dmg"; dmg.mkdir(parents=True, exist_ok=True)
    _background((720, 450)).save(dmg / "background.png")
    _background((1440, 900)).save(dmg / "background@2x.png")

    installer = root / "installer" / "windows"; installer.mkdir(parents=True, exist_ok=True)
    _windows_wizard((164, 314), compact=False).save(installer / "wizard-large.bmp")
    _windows_wizard((55, 55), compact=True).save(installer / "wizard-small.bmp")

    icons = root / "linux" / "icons"
    for size in (16, 32, 48, 64, 128, 256, 512):
        target = icons / f"{size}x{size}"; target.mkdir(parents=True, exist_ok=True)
        draw_icon(size).save(target / "io.github.mes30004e.lego-element-lookup.png")


def main() -> None:
    generate_assets()


if __name__ == "__main__":
    main()
