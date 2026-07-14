"""Downloaded-set selection and new-set entry dialog."""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from PIL import Image, ImageTk, UnidentifiedImageError

from ..set_metadata import SetMetadata


def choose_set_value(existing: str, typed: str, labels: dict[str, str]) -> tuple[str, bool]:
    """Return (set number, needs download); a typed value always takes precedence."""
    entered = typed.strip()
    if entered:
        return entered, True
    selected = labels.get(existing, "")
    return selected, False


class SetChooser(tk.Toplevel):
    def __init__(self, master, sets: list[SetMetadata], current_set: str, preview_for, on_choose, on_manage=None) -> None:
        super().__init__(master)
        self.title("Change set"); self.transient(master); self.grab_set(); self.resizable(True, False)
        self.preview_for, self.on_choose, self.on_manage = preview_for, on_choose, on_manage
        self._image: ImageTk.PhotoImage | None = None
        self._labels = {f"{item.set_num} — {item.name}": item.set_num for item in sets}
        frame = ttk.Frame(self, padding=18); frame.grid(sticky="nsew"); frame.columnconfigure(0, weight=1)
        ttk.Label(frame, text="Select a downloaded set", font=("TkDefaultFont", 11, "bold")).grid(sticky="w")
        current_label = next((label for label, value in self._labels.items() if value == current_set), "")
        self.existing = tk.StringVar(value=current_label)
        self.combo = ttk.Combobox(frame, textvariable=self.existing, values=list(self._labels), state="readonly", width=52)
        self.combo.grid(sticky="ew", pady=(5, 10)); self.combo.bind("<<ComboboxSelected>>", self._selected)
        self.preview = ttk.Label(frame, text="No set preview available", anchor="center", padding=8)
        self.preview.grid(sticky="ew", pady=(0, 12))
        ttk.Separator(frame).grid(sticky="ew", pady=(0, 12))
        ttk.Label(frame, text="Or download another set", font=("TkDefaultFont", 10, "bold")).grid(sticky="w")
        self.new_set = tk.StringVar()
        self.entry = ttk.Entry(frame, textvariable=self.new_set, width=28)
        self.entry.grid(sticky="ew", pady=(5, 4))
        ttk.Label(frame, text="Enter a LEGO set number, for example 10334.", style="Muted.TLabel").grid(sticky="w", pady=(0, 14))
        self.error = tk.StringVar()
        ttk.Label(frame, textvariable=self.error).grid(sticky="w")
        buttons = ttk.Frame(frame); buttons.grid(sticky="ew")
        if on_manage:
            ttk.Button(buttons, text="Manage downloaded sets…", command=lambda: on_manage(self._sets_changed), width=24).pack(side="left")
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="left", padx=4)
        ttk.Button(buttons, text="Select", command=self._choose).pack(side="left", padx=4)
        if current_label: self._show_preview(current_set)
        self.entry.focus_set()

    def _sets_changed(self, sets: list[SetMetadata]) -> None:
        self._labels = {f"{item.set_num} — {item.name}": item.set_num for item in sets}
        self.combo.configure(values=list(self._labels))
        if self.existing.get() not in self._labels:
            self.existing.set("")

    def _selected(self, _event=None) -> None:
        set_num = self._labels.get(self.existing.get())
        if set_num: self._show_preview(set_num)

    def _show_preview(self, set_num: str) -> None:
        path = self.preview_for(set_num)
        if not path:
            self._image = None; self.preview.configure(image="", text="No set preview available"); return
        try:
            with Image.open(Path(path)) as source: image = source.convert("RGBA")
            image.thumbnail((180, 100), Image.Resampling.LANCZOS)
        except (OSError, UnidentifiedImageError):
            self._image = None; self.preview.configure(image="", text="No set preview available"); return
        self._image = ImageTk.PhotoImage(image); self.preview.configure(image=self._image, text="")

    def _choose(self) -> None:
        value, download = choose_set_value(self.existing.get(), self.new_set.get(), self._labels)
        if not value:
            self.error.set("Select a downloaded set or enter a set number.")
            return
        self.destroy()
        self.on_choose(value, download)
