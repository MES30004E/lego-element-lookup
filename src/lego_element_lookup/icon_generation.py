"""Reusable drawing helpers for LEGO Element Lookup application icons."""

from __future__ import annotations

from PIL import Image, ImageDraw

SIZES = (16, 32, 48, 64, 128, 256, 512)


def stud_centres(size: int) -> tuple[tuple[int, int], ...]:
    """Return a symmetric 2×2 stud grid centred on the canvas."""
    centre = size // 2
    offset = round(size * 0.16)
    return tuple((centre + dx, centre + dy) for dy in (-offset, offset) for dx in (-offset, offset))


def draw_icon(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), "#F4C430")
    draw = ImageDraw.Draw(image)
    margin = max(1, round(size * 0.085))
    outline = max(1, size // 32)
    brick = (margin, margin, size - margin - 1, size - margin - 1)
    draw.rounded_rectangle(brick, radius=round(size * 0.13), fill="#D71920", outline="#8B1015", width=outline)
    highlight_y = margin + round(size * 0.06)
    draw.line(
        (margin + round(size * 0.12), highlight_y, size - margin - round(size * 0.12), highlight_y),
        fill="#ED454B",
        width=max(1, size // 48),
    )
    stud_radius = max(1, round(size * 0.105))
    for x, y in stud_centres(size):
        bounds = (x - stud_radius, y - stud_radius, x + stud_radius, y + stud_radius)
        draw.ellipse(bounds, fill="#F04A50", outline="#9C1117", width=max(1, size // 64))
        shine = max(1, stud_radius // 3)
        draw.ellipse((x - shine, y - shine, x, y), fill="#F76B70")
    return image
