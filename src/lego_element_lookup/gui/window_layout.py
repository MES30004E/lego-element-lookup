"""Validated desktop window layout presets and geometry persistence helpers."""

from __future__ import annotations

from dataclasses import replace

from ..config import Preferences

AUTO_PRESET = "auto"
WINDOW_LAYOUT_PRESETS = (AUTO_PRESET, "wide", "tall", "compact")
PRESET_SIZES = {
    "wide": (1280, 760),
    # 740 is deliberately below the existing 760 px narrow breakpoint.
    "tall": (740, 1000),
    "compact": (760, 720),
}
DEFAULT_AUTO_SIZE = (900, 720)
MIN_WINDOW_SIZE = (640, 560)
MAX_WINDOW_SIZE = (7680, 4320)


def normalise_layout_preset(value: object) -> str:
    return value if isinstance(value, str) and value in WINDOW_LAYOUT_PRESETS else AUTO_PRESET


def valid_saved_geometry(width: object, height: object) -> tuple[int, int] | None:
    if not isinstance(width, int) or isinstance(width, bool):
        return None
    if not isinstance(height, int) or isinstance(height, bool):
        return None
    if not MIN_WINDOW_SIZE[0] <= width <= MAX_WINDOW_SIZE[0]:
        return None
    if not MIN_WINDOW_SIZE[1] <= height <= MAX_WINDOW_SIZE[1]:
        return None
    return width, height


def window_size_for(preferences: Preferences) -> tuple[int, int]:
    preset = normalise_layout_preset(preferences.window_layout_preset)
    if preset != AUTO_PRESET:
        return PRESET_SIZES[preset]
    return valid_saved_geometry(preferences.last_window_width, preferences.last_window_height) or DEFAULT_AUTO_SIZE


def with_layout_preset(preferences: Preferences, preset: object) -> Preferences:
    """Return a transactional preference copy; callers decide when to persist it."""
    return replace(preferences, window_layout_preset=normalise_layout_preset(preset))


def with_saved_geometry(preferences: Preferences, width: int, height: int) -> Preferences:
    geometry = valid_saved_geometry(width, height)
    if geometry is None:
        return preferences
    return replace(preferences, last_window_width=geometry[0], last_window_height=geometry[1])
