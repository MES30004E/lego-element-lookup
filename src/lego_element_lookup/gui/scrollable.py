"""Single-region vertical scrolling for the desktop main window."""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk

NO_HORIZONTAL_SCROLLBAR = True
SCROLL_INCREMENT_PX = 8
MACOS_MAX_WHEEL_UNITS = 3


def scroll_required(content_height: int, viewport_height: int) -> bool:
    return viewport_height > 1 and content_height > viewport_height + 1


def normalise_wheel_event(delta: int = 0, number: int | None = None, platform: str | None = None) -> int:
    """Return signed Tk scroll units for macOS, Windows, and X11 wheel events."""
    if number == 4:
        return -1
    if number == 5:
        return 1
    if not delta:
        return 0
    system = sys.platform if platform is None else platform
    if system == "win32":
        units = abs(delta) // 120 or 1
        return -units if delta > 0 else units
    # macOS trackpads commonly send small deltas; preserve a bounded magnitude.
    if system == "darwin":
        units = min(MACOS_MAX_WHEEL_UNITS, max(1, abs(int(delta))))
        return -units if delta > 0 else units
    return -1 if delta > 0 else 1


def platform_scroll_multiplier(platform: str | None = None) -> int:
    """Keep precise macOS input small while retaining conventional wheel speed elsewhere."""
    return 1 if (sys.platform if platform is None else platform) == "darwin" else 3


class VerticalScrollFrame(ttk.Frame):
    """A canvas-backed inner frame with an on-demand vertical scrollbar."""

    def __init__(self, master) -> None:
        super().__init__(master)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        background = self.winfo_toplevel().cget("background")
        self.canvas = tk.Canvas(
            self,
            borderwidth=0,
            highlightthickness=0,
            background=background,
            takefocus=True,
            yscrollincrement=SCROLL_INCREMENT_PX,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.inner = ttk.Frame(self.canvas)
        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.is_scrollable = False
        self.inner.bind("<Configure>", self._content_configured, add="+")
        self.canvas.bind("<Configure>", self._canvas_configured, add="+")
        self.canvas.bind("<Prior>", lambda _event: self._keyboard_scroll(-1, "pages"))
        self.canvas.bind("<Next>", lambda _event: self._keyboard_scroll(1, "pages"))
        self.canvas.bind("<Up>", lambda _event: self._keyboard_scroll(-1, "units"))
        self.canvas.bind("<Down>", lambda _event: self._keyboard_scroll(1, "units"))
        self.canvas.bind("<Home>", lambda _event: self._move_to(0.0))
        self.canvas.bind("<End>", lambda _event: self._move_to(1.0))
        top = self.winfo_toplevel()
        self._top = top
        self._wheel_bindings = [
            ("<MouseWheel>", top.bind("<MouseWheel>", self._wheel, add="+")),
            ("<Button-4>", top.bind("<Button-4>", self._wheel, add="+")),
            ("<Button-5>", top.bind("<Button-5>", self._wheel, add="+")),
        ]

    def _content_configured(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.after_idle(self._update_scrollbar)

    def _canvas_configured(self, event) -> None:
        self.canvas.itemconfigure(self.window_id, width=max(1, event.width))
        self.after_idle(self._update_scrollbar)

    def _update_scrollbar(self) -> None:
        if not self.winfo_exists():
            return
        required = scroll_required(self.inner.winfo_reqheight(), self.canvas.winfo_height())
        if required and not self.is_scrollable:
            self.scrollbar.grid(row=0, column=1, sticky="ns")
        elif not required and self.is_scrollable:
            self.scrollbar.grid_remove()
            self.canvas.yview_moveto(0.0)
        self.is_scrollable = required

    def _contains(self, widget) -> bool:
        while widget is not None:
            if widget is self:
                return True
            widget = getattr(widget, "master", None)
        return False

    def _wheel(self, event):
        if not self.is_scrollable or not self._contains(getattr(event, "widget", None)):
            return None
        units = normalise_wheel_event(
            int(getattr(event, "delta", 0) or 0),
            getattr(event, "num", None),
        )
        if units:
            self.canvas.yview_scroll(units * platform_scroll_multiplier(), "units")
            return "break"
        return None

    def _keyboard_scroll(self, amount: int, mode: str):
        if self.is_scrollable:
            self.canvas.yview_scroll(amount, mode)
        return "break"

    def _move_to(self, fraction: float):
        if self.is_scrollable:
            self.canvas.yview_moveto(fraction)
        return "break"

    def preserve_position(self) -> None:
        fraction = self.canvas.yview()[0]
        self.after_idle(lambda: self.canvas.yview_moveto(fraction) if self.winfo_exists() else None)

    def ensure_visible(self, widget) -> None:
        """Reveal a newly selected result only when it is outside the viewport."""
        if not widget.winfo_exists():
            return
        self.update_idletasks()
        self._update_scrollbar()
        if not self.is_scrollable:
            return
        content_height = max(1, self.inner.winfo_reqheight())
        viewport_height = self.canvas.winfo_height()
        widget_top = widget.winfo_rooty() - self.inner.winfo_rooty()
        widget_bottom = widget_top + widget.winfo_height()
        viewport_top = self.canvas.canvasy(0)
        viewport_bottom = viewport_top + viewport_height
        if widget.winfo_height() >= viewport_height:
            # For a result taller than the viewport, keep its beginning visible and
            # let the user read down naturally instead of jumping to the bottom.
            if widget_top < viewport_top or widget_top >= viewport_bottom:
                self.canvas.yview_moveto(max(0.0, widget_top / content_height))
            return
        if widget_top < viewport_top:
            self.canvas.yview_moveto(max(0.0, widget_top / content_height))
        elif widget_bottom > viewport_bottom:
            target = max(0, widget_bottom - viewport_height)
            self.canvas.yview_moveto(min(1.0, target / content_height))

    def refresh_colours(self) -> None:
        self.canvas.configure(background=self.winfo_toplevel().cget("background"))

    def destroy(self) -> None:
        for sequence, function_id in self._wheel_bindings:
            if function_id:
                self._top.unbind(sequence, function_id)
        super().destroy()
