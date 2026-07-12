"""Reusable Tk widgets."""

from __future__ import annotations

import re
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from PIL import Image, ImageTk, UnidentifiedImageError

from ..lookup import Match

RGB_PATTERN = re.compile(r"#?([0-9a-fA-F]{6})\Z")
PREVIEW_SIZE = (300, 220)


class ResultCard(ttk.LabelFrame):
    def __init__(self, master) -> None:
        super().__init__(master, text="Part result", padding=18)
        self.columnconfigure(0, minsize=320)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self._preview_image: ImageTk.PhotoImage | None = None

        preview_frame = ttk.Frame(self, padding=(4, 4, 20, 4))
        preview_frame.grid(row=0, column=0, rowspan=7, sticky="nsew")
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        self.preview = ttk.Label(
            preview_frame,
            text="No preview available",
            anchor="center",
            justify="center",
            relief="solid",
            padding=12,
        )
        self.preview.grid(sticky="nsew")

        self.part_name = ttk.Label(self, text="No part selected", font=("TkDefaultFont", 17, "bold"), wraplength=430)
        self.part_name.grid(row=0, column=1, sticky="nw", pady=(2, 12))

        code_row = ttk.Frame(self)
        code_row.grid(row=1, column=1, sticky="ew", pady=(0, 12))
        ttk.Label(code_row, text="Part code", font=("TkDefaultFont", 9)).pack(anchor="w")
        self.part_code = ttk.Label(code_row, text="—", font=("TkDefaultFont", 15, "bold"))
        self.part_code.pack(anchor="w")

        colour_row = ttk.Frame(self)
        colour_row.grid(row=2, column=1, sticky="ew", pady=5)
        ttk.Label(colour_row, text="Colour:").pack(side="left")
        self.colour_name = ttk.Label(colour_row, text="—", font=("TkDefaultFont", 11, "bold"))
        self.colour_name.pack(side="left", padx=(6, 10))
        self.swatch = tk.Label(colour_row, text="      ", relief="solid", borderwidth=1)
        self.swatch.pack(side="left")
        self.hex_label = ttk.Label(colour_row, text="Unknown")
        self.hex_label.pack(side="left", padx=(8, 0))

        inventory_row = ttk.Frame(self)
        inventory_row.grid(row=3, column=1, sticky="ew", pady=5)
        ttk.Label(inventory_row, text="Inventory:").pack(side="left")
        self.inventory = ttk.Label(inventory_row, text="—")
        self.inventory.pack(side="left", padx=(6, 0))

        self.colour_code = ttk.Label(self, text="LEGO colour code: —", font=("TkDefaultFont", 9))
        self.colour_code.grid(row=4, column=1, sticky="w", pady=(12, 0))

    def show_match(self, match: Match) -> None:
        self.part_code.configure(text=match.part_code)
        self.colour_code.configure(text=f"LEGO colour code: {match.colour_code}")
        self.part_name.configure(text=match.part_name)
        self.colour_name.configure(text=match.colour_name)
        inventory = []
        if match.quantity:
            inventory.append(f"quantity {match.quantity}")
        if match.spare_quantity:
            inventory.append(f"spares {match.spare_quantity}")
        self.inventory.configure(text=", ".join(inventory) or "Unknown")
        parsed = RGB_PATTERN.fullmatch(str(match.rgb or "").strip())
        if parsed:
            hex_code = f"#{parsed.group(1).upper()}"
            self.swatch.configure(background=hex_code)
            self.hex_label.configure(text=hex_code)
        else:
            self.swatch.configure(background=self.winfo_toplevel().cget("background"))
            self.hex_label.configure(text=str(match.rgb or "Unknown"))

    def show_preview_status(self, message: str) -> None:
        self._preview_image = None
        self.preview.configure(image="", text=message)

    def show_preview(self, path: Path) -> bool:
        """Decode and display a cached preview on Tk's main thread."""
        try:
            with Image.open(path) as source:
                image = source.convert("RGBA")
            image.thumbnail(PREVIEW_SIZE, Image.Resampling.LANCZOS)
        except (OSError, UnidentifiedImageError):
            self.show_preview_status("No preview available")
            return False
        self._preview_image = ImageTk.PhotoImage(image)
        self.preview.configure(image=self._preview_image, text="")
        return True
