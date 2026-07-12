"""Generate centred LEGO-brick icons for every desktop platform."""

from __future__ import annotations

from pathlib import Path

from lego_element_lookup.icon_generation import SIZES, draw_icon

ROOT = Path(__file__).resolve().parent
def main() -> None:
    images = [draw_icon(size) for size in SIZES]
    images[-1].save(ROOT / "icon.png")
    images[-1].save(ROOT / "icon.ico", sizes=[(size, size) for size in SIZES if size <= 256])
    images[-1].save(ROOT / "icon.icns", append_images=images[:-1])


if __name__ == "__main__":
    main()
