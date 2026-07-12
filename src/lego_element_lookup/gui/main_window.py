"""Main desktop lookup window."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from ..clipboard import copy
from ..downloader import DownloadCancelled
from ..lookup import Match
from ..services import ApplicationService, ValidationError
from .settings_window import SettingsDialog
from .tasks import BackgroundTask
from .widgets import ResultCard


class MainWindow(ttk.Frame):
    def __init__(self, master, service: ApplicationService) -> None:
        super().__init__(master, padding=20)
        self.service = service
        self.current_match: Match | None = None
        self.task = None
        self.preview_task = None
        self.columnconfigure(0, weight=1)
        ttk.Label(self, text="LEGO Element Lookup", font=("TkDefaultFont", 20, "bold")).grid(sticky="w")
        self.set_label = ttk.Label(self, text=f"Set {service.settings.default_set}")
        self.set_label.grid(sticky="w", pady=(2, 16))
        ttk.Label(self, text="Element ID").grid(sticky="w")
        self.element_var = tk.StringVar()
        self.element_entry = ttk.Entry(self, textvariable=self.element_var, font=("TkDefaultFont", 18))
        self.element_entry.grid(sticky="ew", pady=(4, 10))
        self.element_entry.bind("<Return>", self._lookup)
        self.message = tk.StringVar(value="Enter an element ID and press Enter.")
        ttk.Label(self, textvariable=self.message).grid(sticky="w", pady=(0, 10))
        self.result = ResultCard(self)
        self.result.grid(sticky="nsew")
        buttons = ttk.Frame(self)
        buttons.grid(sticky="ew", pady=(14, 0))
        self.copy_button = ttk.Button(buttons, text="Copy part code", command=self._copy, state="disabled")
        self.copy_button.pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="Change set", command=self._change_set).pack(side="left", padx=6)
        ttk.Button(buttons, text="Update inventory", command=self._update).pack(side="left", padx=6)
        ttk.Button(buttons, text="Settings", command=self._settings).pack(side="left", padx=6)
        ttk.Button(buttons, text="Open cache folder", command=self._open_cache).pack(side="left", padx=6)
        self.element_entry.focus_set()

    def _lookup(self, _event=None) -> None:
        try:
            matches = self.service.lookup(self.element_var.get())
        except Exception as exc:
            self.message.set(str(exc))
            self._focus_input()
            return
        if not matches:
            self.message.set(f"No match found in set {self.service.settings.default_set}.")
            self._focus_input()
            return
        self.current_match = matches[0]
        self.result.show_match(self.current_match)
        self._load_preview(self.current_match)
        self.copy_button.configure(state="normal")
        self._copy()
        if len(matches) > 1:
            self.message.set(f"Copied part code. {len(matches)} unique matches found; showing the first.")
        self._focus_input()

    def _load_preview(self, match: Match) -> None:
        cached = self.service.cached_preview(match)
        if cached:
            self.result.show_preview(cached)
            return
        if not match.part_img_url:
            self.result.show_preview_status("No preview available")
            return
        self.result.show_preview_status("Loading preview…")
        requested_match = match
        self.preview_task = BackgroundTask(
            self,
            lambda: self.service.fetch_preview(requested_match),
            lambda path: self._preview_loaded(requested_match, path),
            lambda error: self._preview_failed(requested_match, error),
        )
        self.preview_task.start()

    def _preview_loaded(self, match: Match, path) -> None:
        if self.current_match is match:
            self.result.show_preview(path)

    def _preview_failed(self, match: Match, error: Exception) -> None:
        if self.current_match is match:
            self.result.show_preview_status(str(error) or "No preview available")

    def _copy(self) -> None:
        if not self.current_match:
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(self.current_match.part_code)
            self.update_idletasks()
            self.message.set("Part code copied to clipboard.")
        except tk.TclError:
            success, message = copy(self.current_match.part_code)
            self.message.set(message)

    def _focus_input(self) -> None:
        self.element_entry.focus_set()
        self.element_entry.selection_range(0, tk.END)

    def _change_set(self) -> None:
        value = simpledialog.askstring("Change set", "LEGO set number:", initialvalue=self.service.settings.default_set, parent=self)
        if value is None:
            return
        try:
            cached = self.service.change_set(value)
        except ValidationError as exc:
            messagebox.showerror("Change set", str(exc), parent=self)
            return
        self.set_label.configure(text=f"Set {self.service.settings.default_set}")
        if cached:
            self.service.load_inventory(force=True)
            self.message.set("Set changed. Cached inventory loaded.")
        elif messagebox.askyesno("Download inventory", "No cached inventory exists for this set. Download it now?", parent=self):
            self._update()

    def _update(self) -> None:
        self.message.set("Updating inventory…")

        def progress(page, count):
            if self.task:
                self.task.report((page, count))

        self.task = BackgroundTask(
            self,
            lambda: self.service.download(progress=progress),
            self._updated,
            self._update_failed,
            lambda value: self.message.set(f"Downloading page {value[0]} — {value[1]} entries…"),
        )
        self.task.start()

    def _updated(self, count: int) -> None:
        self.service.load_inventory(force=True)
        self.message.set(f"Inventory updated: {count} entries.")

    def _update_failed(self, exc: Exception) -> None:
        if not isinstance(exc, DownloadCancelled):
            messagebox.showerror("Inventory update", str(exc), parent=self)
        self.message.set(str(exc))

    def _settings(self) -> None:
        SettingsDialog(self, self.service, self._settings_saved)

    def _settings_saved(self) -> None:
        self.set_label.configure(text=f"Set {self.service.settings.default_set}")
        self.message.set("Settings saved.")

    def _open_cache(self) -> None:
        try:
            self.service.open_cache_folder()
        except Exception as exc:
            messagebox.showerror("Cache folder", str(exc), parent=self)
