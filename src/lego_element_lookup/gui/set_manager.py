"""Safe management of downloaded inventory caches."""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from PIL import Image, ImageTk, UnidentifiedImageError

from ..services import SetRemovalError


def set_manager_label(set_num: str, name: str, active_set: str) -> str:
    return f"{set_num} — {name}" + ("   Active" if set_num == active_set else "")


class DownloadedSetManager(tk.Toplevel):
    def __init__(self, master, service, on_changed=None) -> None:
        super().__init__(master)
        self.service = service
        self.on_changed = on_changed
        self.title("Downloaded sets")
        self.geometry("680x420")
        self.minsize(540, 320)
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.body = ttk.Frame(self, padding=18, style="Surface.TFrame")
        self.body.grid(sticky="nsew")
        self.body.columnconfigure(0, weight=1)
        self.body.rowconfigure(1, weight=1)
        ttk.Label(self.body, text="Downloaded sets", style="Heading.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.list_frame = ttk.Frame(self.body, style="Surface.TFrame")
        self.list_frame.grid(row=1, column=0, sticky="nsew")
        self.list_frame.columnconfigure(2, weight=1)
        self.delete_assets = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self.body,
            text="Also delete cached set metadata and thumbnail",
            variable=self.delete_assets,
            style="Surface.TCheckbutton",
        ).grid(row=2, column=0, sticky="w", pady=(12, 4))
        ttk.Label(
            self.body,
            text="Removing a downloaded set always deletes its inventory cache. Shared part previews, related-design data and credentials are kept.",
            style="Muted.TLabel",
            wraplength=620,
        ).grid(row=3, column=0, sticky="ew", pady=(0, 12))
        buttons = ttk.Frame(self.body, style="Surface.TFrame")
        buttons.grid(row=4, column=0, sticky="e")
        self.remove_button = ttk.Button(buttons, text="Remove selected", command=self._remove, style="Danger.TButton", width=16)
        self.remove_button.pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Close", command=self.destroy, width=10).pack(side="left")
        self._variables: dict[str, tk.BooleanVar] = {}
        self._images: list[ImageTk.PhotoImage] = []
        self._refresh()

    def _refresh(self) -> None:
        for child in self.list_frame.winfo_children():
            child.destroy()
        self._variables.clear()
        self._images.clear()
        sets = self.service.downloaded_sets()
        if not sets:
            ttk.Label(self.list_frame, text="No downloaded sets are available.", style="Muted.TLabel").grid(sticky="w", pady=12)
            self.remove_button.configure(state="disabled")
            return
        self.remove_button.configure(state="normal")
        for row, item in enumerate(sets):
            variable = tk.BooleanVar(value=False)
            self._variables[item.set_num] = variable
            active = item.set_num == self.service.settings.default_set
            ttk.Checkbutton(self.list_frame, variable=variable, style="Surface.TCheckbutton").grid(row=row, column=0, sticky="w", pady=5)
            image = self._thumbnail(item.set_num)
            thumbnail = ttk.Label(self.list_frame, style="Surface.TLabel", width=7, anchor="center")
            thumbnail.grid(row=row, column=1, sticky="w", padx=(4, 10), pady=5)
            if image:
                self._images.append(image)
                thumbnail.configure(image=image)
            label = set_manager_label(item.set_num, item.name, self.service.settings.default_set)
            ttk.Label(self.list_frame, text=label, style="Surface.TLabel", wraplength=500).grid(row=row, column=2, sticky="w", pady=5)

    def _thumbnail(self, set_num: str) -> ImageTk.PhotoImage | None:
        path = self.service.cached_set_preview(set_num)
        if not path:
            return None
        try:
            with Image.open(Path(path)) as source:
                image = source.convert("RGBA")
            image.thumbnail((52, 38), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(image)
        except (OSError, UnidentifiedImageError, tk.TclError):
            return None

    def _remove(self) -> None:
        selected = [set_num for set_num, variable in self._variables.items() if variable.get()]
        if not selected:
            messagebox.showinfo("Downloaded sets", "Select one or more downloaded sets to remove.", parent=self)
            return
        if self.service.settings.default_set in selected:
            messagebox.showerror("Downloaded sets", "Switch to another downloaded set before removing the active set.", parent=self)
            return
        names = ", ".join(selected)
        if not messagebox.askyesno(
            "Remove downloaded sets",
            f"Remove the cached inventory for {names}? This cannot be undone.",
            parent=self,
        ):
            return
        try:
            removed = self.service.remove_downloaded_sets(selected, delete_set_assets=self.delete_assets.get())
        except SetRemovalError as exc:
            messagebox.showerror("Downloaded sets", str(exc), parent=self)
            return
        self._refresh()
        if self.on_changed:
            self.on_changed(removed)
