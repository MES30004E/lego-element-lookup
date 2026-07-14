"""Reusable drawing helpers for LEGO Element Lookup application icons."""

from __future__ import annotations

from PIL import Image, ImageDraw

SIZES = (16, 32, 48, 64, 128, 256, 512, 1024)


def tile_bounds(size: int) -> tuple[int, int, int, int]:
    """Return the centred rounded-tile bounds with equal outer breathing room."""
    margin = max(1, round(size * 0.06))
    return margin, margin, size - margin - 1, size - margin - 1


def brick_bounds(size: int) -> tuple[int, int, int, int]:
    """Return a centred, compact 2×2 brick face within the application tile."""
    horizontal = round(size * 0.16)
    vertical = round(size * 0.185)
    return horizontal, vertical, size - horizontal - 1, size - vertical - 1


def stud_centres(size: int) -> tuple[tuple[int, int], ...]:
    """Return a symmetric 2×2 stud grid centred on the canvas."""
    centre = size // 2
    offset = round(size * 0.16)
    return tuple((centre + dx, centre + dy) for dy in (-offset, offset) for dx in (-offset, offset))


def draw_icon(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    tile = tile_bounds(size)
    tile_outline = max(1, size // 96)
    draw.rounded_rectangle(
        tile,
        radius=max(2, round(size * 0.205)),
        fill="#F4C430",
        outline="#D6A91D",
        width=tile_outline,
    )
    brick = brick_bounds(size)
    outline = max(1, size // 42)
    draw.rounded_rectangle(brick, radius=max(2, round(size * 0.105)), fill="#D71920", outline="#8B1015", width=outline)
    highlight_y = brick[1] + round(size * 0.055)
    draw.line(
        (brick[0] + round(size * 0.09), highlight_y, brick[2] - round(size * 0.09), highlight_y),
        fill="#ED454B",
        width=max(1, size // 48),
    )
    stud_radius = max(1, round(size * 0.092))
    for x, y in stud_centres(size):
        bounds = (x - stud_radius, y - stud_radius, x + stud_radius, y + stud_radius)
        draw.ellipse(bounds, fill="#F04A50", outline="#9C1117", width=max(1, size // 64))
        shine = max(1, stud_radius // 3)
        draw.ellipse((x - shine, y - shine, x, y), fill="#F76B70")
    return image
