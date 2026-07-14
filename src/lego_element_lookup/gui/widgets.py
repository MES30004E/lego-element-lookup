"""Reusable Tk widgets."""

from __future__ import annotations

import re
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from PIL import Image, ImageTk, UnidentifiedImageError

from ..lookup import Match
from ..relationship_cache import RelationshipCacheState
from ..relationships import RelatedDesigns, RelationshipType
from ..services import RELATED_DESIGN_LABELS
from .responsive import LayoutMode

RGB_PATTERN = re.compile(r"#?([0-9a-fA-F]{6})\Z")
PREVIEW_SIZES = {
    LayoutMode.WIDE: (300, 220),
    LayoutMode.MEDIUM: (250, 185),
    LayoutMode.NARROW: (210, 155),
}
PART_NAME_WRAP = {
    LayoutMode.WIDE: 520,
    LayoutMode.MEDIUM: 400,
    LayoutMode.NARROW: 520,
}


def result_grid_positions(mode: LayoutMode) -> dict[str, tuple[int, int]]:
    """Expose the stable result-card layout contract for tests and maintenance."""
    if mode is LayoutMode.NARROW:
        return {"preview": (0, 0), "part_name": (1, 0), "related": (6, 0)}
    return {"preview": (0, 0), "part_name": (0, 1), "related": (5, 1)}


class ResultCard(ttk.Frame):
    def __init__(self, master, copy_command=None) -> None:
        super().__init__(master, padding=18, style="ResultCard.TFrame")
        self.layout_mode = LayoutMode.MEDIUM
        self._preview_image: ImageTk.PhotoImage | None = None
        self._preview_source: Image.Image | None = None
        self._preview_path: Path | None = None
        self._preview_variants: dict[tuple[int, int], ImageTk.PhotoImage] = {}
        self._related_button_groups: list[tuple[ttk.Frame, list[ttk.Button]]] = []

        self.preview_frame = ttk.Frame(self, padding=(4, 4, 20, 4), style="Surface.TFrame")
        self.preview_frame.columnconfigure(0, weight=1)
        self.preview_frame.rowconfigure(0, weight=1)
        self.preview = ttk.Label(
            self.preview_frame,
            text="No preview available",
            anchor="center",
            justify="center",
            relief="solid",
            padding=12,
            style="Surface.TLabel",
        )
        self.preview.grid(sticky="nsew")

        self.part_name = ttk.Label(
            self,
            text="No part selected",
            font=("TkDefaultFont", 17, "bold"),
            wraplength=430,
            justify="left",
            style="Surface.TLabel",
        )
        self.code_row = ttk.Frame(self, style="Surface.TFrame")
        self.code_row.columnconfigure(0, weight=1)
        ttk.Label(self.code_row, text="Part code", font=("TkDefaultFont", 9), style="Muted.Surface.TLabel").grid(row=0, column=0, sticky="w")
        self.part_code = ttk.Label(self.code_row, text="—", font=("TkDefaultFont", 15, "bold"), style="Surface.TLabel")
        self.part_code.grid(row=1, column=0, sticky="w")
        self.copy_button = ttk.Button(
            self.code_row,
            text="Copy",
            command=copy_command,
            state="disabled",
            style="Compact.TButton",
        )
        self.copy_button.grid(row=1, column=1, sticky="e", padx=(10, 0))

        self.colour_row = ttk.Frame(self, style="Surface.TFrame")
        ttk.Label(self.colour_row, text="Colour:", style="Surface.TLabel").pack(side="left")
        self.colour_name = ttk.Label(self.colour_row, text="—", font=("TkDefaultFont", 11, "bold"), style="Surface.TLabel")
        self.colour_name.pack(side="left", padx=(6, 10))
        self.swatch = tk.Label(self.colour_row, text="      ", relief="solid", borderwidth=1)
        self.swatch.pack(side="left")
        self.hex_label = ttk.Label(self.colour_row, text="Unknown", style="Surface.TLabel")
        self.hex_label.pack(side="left", padx=(8, 0))

        self.inventory_row = ttk.Frame(self, style="Surface.TFrame")
        ttk.Label(self.inventory_row, text="Inventory:", style="Surface.TLabel").pack(side="left")
        self.inventory = ttk.Label(self.inventory_row, text="—", style="Surface.TLabel")
        self.inventory.pack(side="left", padx=(6, 0))

        self.colour_code = ttk.Label(self, text="LEGO colour code: —", font=("TkDefaultFont", 9), style="Surface.TLabel")
        self.related = ttk.Frame(self, style="Surface.TFrame")
        self.related.columnconfigure(0, weight=1)
        self.related_title = ttk.Label(self.related, text="Related designs", font=("TkDefaultFont", 10, "bold"), style="Surface.TLabel")
        self.related_title.grid(row=0, column=0, sticky="w")
        self.related_content = ttk.Frame(self.related, style="Surface.TFrame")
        self.related_content.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.set_layout(self.layout_mode, force=True)

    def set_layout(self, mode: LayoutMode, *, force: bool = False) -> bool:
        """Re-grid existing widgets without replacing result or preview state."""
        if not force and mode is self.layout_mode:
            return False
        self.layout_mode = mode
        widgets = (
            self.preview_frame,
            self.part_name,
            self.code_row,
            self.colour_row,
            self.inventory_row,
            self.colour_code,
            self.related,
        )
        for widget in widgets:
            widget.grid_forget()
        for column in (0, 1):
            self.columnconfigure(column, weight=0, minsize=0)
        if mode is LayoutMode.NARROW:
            self.configure(padding=10)
            self.columnconfigure(0, weight=1)
            self.preview_frame.configure(padding=(4, 2, 4, 10))
            self.preview_frame.grid(row=0, column=0, sticky="nsew")
            detail_column, start_row = 0, 1
        else:
            self.configure(padding=18 if mode is LayoutMode.WIDE else 13)
            self.columnconfigure(0, minsize=320 if mode is LayoutMode.WIDE else 270)
            self.columnconfigure(1, weight=1)
            right_gap = 20 if mode is LayoutMode.WIDE else 12
            self.preview_frame.configure(padding=(4, 4, right_gap, 4))
            self.preview_frame.grid(row=0, column=0, rowspan=6, sticky="nsew")
            detail_column, start_row = 1, 0
        positions = result_grid_positions(mode)
        assert positions["preview"] == (0, 0)
        assert positions["part_name"] == (start_row, detail_column)
        self.part_name.configure(
            wraplength=PART_NAME_WRAP[mode],
            font=("TkDefaultFont", 15 if mode is LayoutMode.NARROW else 17, "bold"),
        )
        self.part_name.grid(row=start_row, column=detail_column, sticky="nw", pady=(2, 10))
        self.code_row.grid(row=start_row + 1, column=detail_column, sticky="ew", pady=(0, 9))
        self.colour_row.grid(row=start_row + 2, column=detail_column, sticky="ew", pady=4)
        self.inventory_row.grid(row=start_row + 3, column=detail_column, sticky="ew", pady=4)
        self.colour_code.grid(row=start_row + 4, column=detail_column, sticky="w", pady=(9, 0))
        self.related.grid(row=start_row + 5, column=detail_column, sticky="ew", pady=(12, 0))
        self._layout_related_buttons()
        self._render_preview()
        return True

    def show_match(self, match: Match, preferences=None) -> None:
        self.part_code.configure(text=match.part_code)
        self.colour_code.configure(text=f"LEGO colour code: {match.colour_code}" if preferences is None or preferences.show_lego_colour_code else "")
        self.part_name.configure(text=match.part_name)
        self.colour_name.configure(text=match.colour_name)
        inventory = []
        if match.quantity:
            inventory.append(f"quantity {match.quantity}")
        if match.spare_quantity:
            inventory.append(f"spares {match.spare_quantity}")
        self.inventory.configure(text=(", ".join(inventory) or "Unknown") if preferences is None or preferences.show_inventory_quantity else "Hidden in Settings")
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
        self._preview_source = None
        self._preview_path = None
        self._preview_variants.clear()
        self.preview.configure(image="", text=message)

    def show_preview(self, path: Path) -> bool:
        """Decode once on Tk's main thread and reuse high-quality in-memory variants."""
        try:
            resolved = Path(path).resolve()
            if resolved != self._preview_path or self._preview_source is None:
                with Image.open(resolved) as source:
                    self._preview_source = source.convert("RGBA")
                self._preview_path = resolved
                self._preview_variants.clear()
        except (OSError, UnidentifiedImageError):
            self.show_preview_status("No preview available")
            return False
        self._render_preview()
        return True

    def _render_preview(self) -> None:
        if self._preview_source is None:
            return
        size = PREVIEW_SIZES[self.layout_mode]
        variant = self._preview_variants.get(size)
        if variant is None:
            image = self._preview_source.copy()
            image.thumbnail(size, Image.Resampling.LANCZOS)
            variant = ImageTk.PhotoImage(image)
            self._preview_variants[size] = variant
        self._preview_image = variant
        self.preview.configure(image=variant, text="")

    def clear_related_designs(self) -> None:
        self._related_button_groups.clear()
        for child in self.related_content.winfo_children():
            child.destroy()

    def show_related_designs(self, designs: RelatedDesigns, copy_code, *, stale: bool = False, refresh=None) -> None:
        self.clear_related_designs()
        grouped = {}
        for relationship_type in RelationshipType:
            related = designs.for_type(relationship_type)
            if related:
                grouped.setdefault(RELATED_DESIGN_LABELS[relationship_type], []).extend(related)
        row = 0
        for label, related in grouped.items():
            ttk.Label(self.related_content, text=f"{label}:", style="Surface.TLabel").grid(row=row, column=0, sticky="nw", padx=(0, 8))
            buttons_frame = ttk.Frame(self.related_content, style="Surface.TFrame")
            buttons_frame.grid(row=row, column=1, sticky="w")
            buttons = [
                ttk.Button(buttons_frame, text=item.part_num, command=lambda code=item.part_num: copy_code(code))
                for item in sorted({item.part_num: item for item in related}.values(), key=lambda item: item.part_num)
            ]
            self._related_button_groups.append((buttons_frame, buttons))
            row += 1
        if row:
            ttk.Label(
                self.related_content,
                text="Related by Rebrickable catalogue data; verify compatibility.",
                font=("TkDefaultFont", 9),
                wraplength=430,
                style="Attribution.TLabel",
            ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(6, 0))
            if stale and refresh:
                ttk.Label(self.related_content, text="Related-design data may be stale.", style="Surface.TLabel").grid(
                    row=row + 1, column=0, columnspan=2, sticky="w", pady=(5, 0)
                )
                ttk.Button(self.related_content, text="Refresh related-design data", command=refresh).grid(
                    row=row + 2, column=0, columnspan=2, sticky="w", pady=(3, 0)
                )
        else:
            ttk.Label(self.related_content, text="No direct related designs recorded.", style="Surface.TLabel").grid(sticky="w")
        self._layout_related_buttons()

    def _layout_related_buttons(self) -> None:
        columns = 3 if self.layout_mode is LayoutMode.NARROW else 5
        for frame, buttons in self._related_button_groups:
            for button in buttons:
                button.grid_forget()
            for index, button in enumerate(buttons):
                button.grid(row=index // columns, column=index % columns, sticky="w", padx=(0, 4), pady=(0, 4))

    def show_relationship_cache_state(self, state: RelationshipCacheState, refresh) -> None:
        self.clear_related_designs()
        if state is RelationshipCacheState.NOT_DOWNLOADED:
            ttk.Label(self.related_content, text="Related-design data is optional and not downloaded.", style="Surface.TLabel").grid(row=0, column=0, sticky="w")
            ttk.Button(self.related_content, text="Download related-design data", command=refresh).grid(row=1, column=0, sticky="w", pady=(5, 0))
        elif state is RelationshipCacheState.STALE:
            ttk.Label(self.related_content, text="Related-design data may be stale.", style="Surface.TLabel").grid(row=0, column=0, sticky="w")
            ttk.Button(self.related_content, text="Refresh related-design data", command=refresh).grid(row=1, column=0, sticky="w", pady=(5, 0))
        else:
            ttk.Label(self.related_content, text="Related-design data is unavailable offline.", style="Surface.TLabel").grid(sticky="w")
