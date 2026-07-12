"""Transactional settings and set-selection dialogs."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ..config import Settings, cache_dir, save_settings, validate_cache_directory
from ..services import ApplicationService


class SettingsDialog(tk.Toplevel):
    def __init__(self, master, service: ApplicationService, on_saved) -> None:
        super().__init__(master)
        self.service = service
        self.on_saved = on_saved
        self.title("Settings")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        frame = ttk.Frame(self, padding=20)
        frame.grid(sticky="nsew")
        ttk.Label(frame, text="Default set").grid(row=0, column=0, sticky="w")
        self.set_var = tk.StringVar(value=service.settings.default_set)
        ttk.Entry(frame, textvariable=self.set_var, width=24).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 12))
        ttk.Label(frame, text="Cache folder").grid(row=2, column=0, sticky="w")
        self.cache_var = tk.StringVar(value=str(service.cache_directory))
        ttk.Entry(frame, textvariable=self.cache_var, width=52).grid(row=3, column=0, sticky="ew", pady=(4, 12))
        ttk.Button(frame, text="Browse…", command=self._browse).grid(row=3, column=1, padx=(8, 0), pady=(4, 12))
        ttk.Button(frame, text="Use default", command=lambda: self.cache_var.set(str(cache_dir()))).grid(row=4, column=0, sticky="w")
        buttons = ttk.Frame(frame)
        buttons.grid(row=5, column=0, columnspan=2, sticky="e", pady=(20, 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="left", padx=4)
        ttk.Button(buttons, text="Save", command=self._save).pack(side="left", padx=4)

    def _browse(self) -> None:
        selected = filedialog.askdirectory(parent=self, initialdir=self.cache_var.get())
        if selected:
            self.cache_var.set(selected)

    def _save(self) -> None:
        try:
            selected_set = self.service.validate_set_num(self.set_var.get())
            selected_cache = validate_cache_directory(Path(self.cache_var.get()))
            custom_cache = None if selected_cache == cache_dir() else selected_cache
            settings = Settings(None, selected_set, custom_cache, self.service.settings.setup_complete)
            save_settings(settings, self.service.settings_path)
            self.service.settings = settings
            self.service._inventory = None
        except Exception as exc:
            messagebox.showerror("Settings", str(exc), parent=self)
            return
        self.destroy()
        self.on_saved()
