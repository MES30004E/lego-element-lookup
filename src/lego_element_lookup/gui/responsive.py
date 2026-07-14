"""Small breakpoint controller shared by responsive desktop windows."""

from __future__ import annotations

from enum import Enum
from typing import Callable

WIDE_BREAKPOINT = 1000
NARROW_BREAKPOINT = 760
RESIZE_DEBOUNCE_MS = 90


class LayoutMode(str, Enum):
    WIDE = "wide"
    MEDIUM = "medium"
    NARROW = "narrow"


def layout_mode_for_width(width: int) -> LayoutMode:
    if width >= WIDE_BREAKPOINT:
        return LayoutMode.WIDE
    if width >= NARROW_BREAKPOINT:
        return LayoutMode.MEDIUM
    return LayoutMode.NARROW


class DebouncedBreakpointController:
    """Debounce Configure events and notify only when the breakpoint changes."""

    def __init__(self, owner, callback: Callable[[LayoutMode], None]) -> None:
        self.owner = owner
        self.callback = callback
        self.current: LayoutMode | None = None
        self.pending_width = 0
        self.after_id = None
        self.transition_count = 0

    def request(self, width: int) -> None:
        self.pending_width = width
        if self.after_id is not None:
            self.owner.after_cancel(self.after_id)
        self.after_id = self.owner.after(RESIZE_DEBOUNCE_MS, self.flush)

    def flush(self) -> bool:
        self.after_id = None
        mode = layout_mode_for_width(self.pending_width)
        if mode is self.current:
            return False
        self.current = mode
        self.transition_count += 1
        self.callback(mode)
        return True

    def apply_now(self, width: int) -> bool:
        self.pending_width = width
        if self.after_id is not None:
            self.owner.after_cancel(self.after_id)
            self.after_id = None
        return self.flush()

    def stop(self) -> None:
        if self.after_id is not None:
            self.owner.after_cancel(self.after_id)
            self.after_id = None
