"""Transactional, resizable tabbed desktop settings."""
from __future__ import annotations

import tkinter as tk
from dataclasses import replace
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .. import __version__
from ..config import Preferences, cache_dir, save_settings, validate_cache_directory
from .about import show_about
from .responsive import DebouncedBreakpointController, LayoutMode
from .set_manager import DownloadedSetManager
from .theme import SystemThemeMonitor, apply_theme
from .window_layout import with_layout_preset

SETTINGS_TAB_LABELS = ("General", "Lookup", "Images & cache", "Data", "Account & security")
SETTINGS_DEFAULT_SIZE = (860, 680)
SETTINGS_MIN_SIZE = (720, 600)
FOOTER_ACTIONS = ("Restore defaults", "About", "Cancel", "Apply", "Save")


class DirtyState:
    def __init__(self) -> None:
        self.dirty = False

    def changed(self) -> None:
        self.dirty = True

    def applied(self) -> None:
        self.dirty = False

    def compare(self, draft, applied) -> None:
        self.dirty = draft != applied


def ask_unsaved_changes(parent) -> str:
    """Return save, discard, or cancel using an explicit three-button dialog."""
    result = {"value": "cancel"}
    dialog = tk.Toplevel(parent)
    dialog.title("Unsaved changes")
    dialog.transient(parent)
    dialog.grab_set()
    dialog.resizable(False, False)
    frame = ttk.Frame(dialog, padding=20, style="Surface.TFrame")
    frame.grid(sticky="nsew")
    ttk.Label(frame, text="Save changes before closing?", style="Surface.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 18))
    def choose(value):
        result["value"] = value
        dialog.destroy()
    ttk.Button(frame, text="Discard", command=lambda: choose("discard"), width=11).grid(row=1, column=0, padx=(0, 8))
    ttk.Button(frame, text="Cancel", command=lambda: choose("cancel"), width=11).grid(row=1, column=1, padx=(0, 8))
    ttk.Button(frame, text="Save", command=lambda: choose("save"), width=11).grid(row=1, column=2)
    dialog.protocol("WM_DELETE_WINDOW", lambda: choose("cancel"))
    parent.wait_window(dialog)
    return result["value"]


class SettingsDialog(tk.Toplevel):
    def __init__(self, master, service, on_saved) -> None:
        super().__init__(master)
        self.service, self.on_saved = service, on_saved
        self.dirty_state = DirtyState()
        self.title("Settings")
        self.geometry(f"{SETTINGS_DEFAULT_SIZE[0]}x{SETTINGS_DEFAULT_SIZE[1]}")
        self.minsize(*SETTINGS_MIN_SIZE)
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        p = service.settings.preferences
        self.set_var = tk.StringVar(value=service.settings.default_set)
        self.cache_var = tk.StringVar(value=str(service.cache_directory))
        self.theme = tk.StringVar(value=p.theme)
        self.density = tk.StringVar(value=p.density)
        self.window_layout = tk.StringVar(value=p.window_layout_preset.title())
        self.preview_size = tk.StringVar(value=p.preview_size)
        self.eviction = tk.StringVar(value=p.preview_cache_eviction)
        self.limit = tk.StringVar(value=str(p.preview_cache_limit_mb))
        self.update_channel = tk.StringVar(value=p.update_channel)
        flag_names = (
            "auto_copy", "show_copied_confirmation", "refocus_input",
            "show_lego_colour_code", "show_inventory_quantity", "previews_enabled",
            "auto_download_previews", "set_thumbnails_enabled", "auto_cache_set_thumbnails",
            "automatic_update_checks",
        )
        self.flags = {key: tk.BooleanVar(value=getattr(p, key)) for key in flag_names}

        self.body = ttk.Frame(self, padding=(20, 18, 20, 0))
        self.body.grid(row=0, column=0, sticky="nsew")
        self.body.columnconfigure(0, weight=1)
        self.body.rowconfigure(0, weight=1)
        self.notebook = ttk.Notebook(self.body)
        self.notebook.grid(row=0, column=0, sticky="nsew")
        self.tab_frames = []
        self._general(self.notebook)
        self._lookup(self.notebook)
        self._images(self.notebook)
        self._data(self.notebook)
        self._account(self.notebook)

        self.footer = ttk.Frame(self, padding=(20, 12, 20, 16), style="Footer.TFrame")
        self.footer.grid(row=1, column=0, sticky="ew")
        self.restore_button = ttk.Button(self.footer, text="Restore defaults", command=self._defaults, width=16)
        self.about_button = ttk.Button(self.footer, text="About", command=lambda: show_about(self), width=10)
        self.version_label = ttk.Label(self.footer, text=f"Version {__version__}", style="Muted.TLabel")
        self.cancel_button = ttk.Button(self.footer, text="Cancel", command=self._request_close, width=11)
        self.apply_button = ttk.Button(self.footer, text="Apply", command=self._apply, width=11, state="disabled")
        self.save_button = ttk.Button(self.footer, text="Save", command=self._save, width=11)
        self._responsive = DebouncedBreakpointController(self, self._apply_responsive_layout)
        self._responsive.apply_now(SETTINGS_DEFAULT_SIZE[0])
        self.bind("<Configure>", self._queue_responsive_layout, add="+")
        self.protocol("WM_DELETE_WINDOW", self._request_close)
        self.bind("<Escape>", lambda _event: self._request_close())
        self._applied_draft = self._draft_values()
        self._install_dirty_tracking()
        self.theme_monitor = SystemThemeMonitor(
            self,
            self.theme.get,
            self._system_preview_changed,
        )
        self.theme_monitor.start()

    def _tab(self, notebook, title):
        frame = ttk.Frame(notebook, padding=20, style="Surface.TFrame")
        notebook.add(frame, text=title)
        frame.columnconfigure(0, weight=1)
        self.tab_frames.append(frame)
        return frame

    def _queue_responsive_layout(self, event) -> None:
        if event.widget is self:
            self._responsive.request(event.width)

    def _apply_responsive_layout(self, mode: LayoutMode) -> None:
        narrow = mode is LayoutMode.NARROW
        self.body.configure(padding=(12, 12, 12, 0) if narrow else (20, 18, 20, 0))
        self.footer.configure(padding=(12, 8, 12, 12) if narrow else (20, 12, 20, 16))
        for frame in self.tab_frames:
            frame.configure(padding=12 if narrow else 20)
        for widget in (self.restore_button, self.about_button, self.version_label, self.cancel_button, self.apply_button, self.save_button):
            widget.grid_forget()
        for column in range(6):
            self.footer.columnconfigure(column, weight=0)
        if narrow:
            self.footer.columnconfigure(2, weight=1)
            self.restore_button.grid(row=0, column=0, padx=(0, 8), pady=(0, 8))
            self.about_button.grid(row=0, column=1, pady=(0, 8))
            self.version_label.grid(row=0, column=2, sticky="e", padx=(12, 0), pady=(0, 8))
            self.cancel_button.grid(row=1, column=3, padx=(0, 8))
            self.apply_button.grid(row=1, column=4, padx=(0, 8))
            self.save_button.grid(row=1, column=5)
        else:
            self.footer.columnconfigure(2, weight=1)
            self.restore_button.grid(row=0, column=0, padx=(0, 8))
            self.about_button.grid(row=0, column=1)
            self.version_label.grid(row=0, column=2, padx=16)
            self.cancel_button.grid(row=0, column=3, padx=(0, 8))
            self.apply_button.grid(row=0, column=4, padx=(0, 8))
            self.save_button.grid(row=0, column=5)

    @staticmethod
    def _choice(frame, row, label, variable, values):
        ttk.Label(frame, text=label, style="Surface.TLabel").grid(row=row, column=0, sticky="w")
        widget = ttk.Combobox(frame, textvariable=variable, values=values, state="readonly", width=28)
        widget.grid(row=row + 1, column=0, sticky="ew", pady=(4, 14))
        return widget

    def _general(self, notebook):
        frame = self._tab(notebook, SETTINGS_TAB_LABELS[0])
        ttk.Label(frame, text="Default set", style="Surface.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.set_var).grid(row=1, column=0, sticky="ew", pady=(4, 14))
        self._choice(frame, 2, "Window layout", self.window_layout, ("Auto", "Wide", "Tall", "Compact"))
        ttk.Label(
            frame,
            text="Choose a starting window layout. You can still resize the window manually.",
            wraplength=620,
            style="Muted.TLabel",
        ).grid(row=4, column=0, sticky="ew", pady=(0, 14))
        self._choice(frame, 5, "Theme", self.theme, ("system", "light", "dark"))
        self._choice(frame, 7, "Density", self.density, ("comfortable", "compact"))
        ttk.Label(frame, text="Theme changes are previewed. Choose Apply or Save to keep them.", wraplength=640, style="Muted.TLabel").grid(row=9, column=0, sticky="ew", pady=(0, 14))
        ttk.Label(frame, text="Inventory cache folder", style="Surface.TLabel").grid(row=10, column=0, sticky="w")
        cache_row = ttk.Frame(frame, style="Surface.TFrame")
        cache_row.grid(row=11, column=0, sticky="ew", pady=(4, 0))
        cache_row.columnconfigure(0, weight=1)
        ttk.Entry(cache_row, textvariable=self.cache_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(cache_row, text="Browse…", command=self._browse_cache, width=11).grid(row=0, column=1, padx=(8, 0))

    def _lookup(self, notebook):
        frame = self._tab(notebook, SETTINGS_TAB_LABELS[1])
        options = (
            ("auto_copy", "Automatically copy part code"),
            ("show_copied_confirmation", "Show copied confirmation"),
            ("refocus_input", "Refocus and select input after lookup"),
            ("show_lego_colour_code", "Show LEGO colour code"),
            ("show_inventory_quantity", "Show inventory quantity"),
        )
        for row, (key, label) in enumerate(options):
            ttk.Checkbutton(frame, text=label, variable=self.flags[key], style="Surface.TCheckbutton").grid(row=row, column=0, sticky="w", pady=5)

    def _images(self, notebook):
        frame = self._tab(notebook, SETTINGS_TAB_LABELS[2])
        options = (
            ("previews_enabled", "Show part previews"),
            ("auto_download_previews", "Download previews when needed"),
            ("set_thumbnails_enabled", "Show set thumbnails"),
            ("auto_cache_set_thumbnails", "Cache set thumbnails"),
        )
        for row, (key, label) in enumerate(options):
            ttk.Checkbutton(frame, text=label, variable=self.flags[key], style="Surface.TCheckbutton").grid(row=row, column=0, sticky="w", pady=4)
        self._choice(frame, 4, "Preview size", self.preview_size, ("small", "medium", "large"))
        ttk.Label(frame, text="Preview cache limit (MB)", style="Surface.TLabel").grid(row=6, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.limit).grid(row=7, column=0, sticky="ew", pady=(4, 10))
        self._choice(frame, 8, "When the limit is reached", self.eviction, ("oldest", "never"))
        ttk.Button(frame, text="Clear preview cache", command=self._clear, width=20, style="Danger.TButton").grid(row=10, column=0, sticky="w")

    def _data(self, notebook):
        frame = self._tab(notebook, SETTINGS_TAB_LABELS[3])
        ttk.Label(frame, text="Manage downloaded inventory caches and their optional per-set presentation data.", wraplength=620, style="Surface.TLabel").grid(sticky="w")
        ttk.Button(frame, text="Manage downloaded sets…", command=self._manage_downloaded_sets, width=24).grid(sticky="w", pady=(14, 0))
        ttk.Button(frame, text="Open cache folder", command=self.service.open_cache_folder, width=20).grid(sticky="w", pady=(10, 0))

    def _account(self, notebook):
        frame = self._tab(notebook, SETTINGS_TAB_LABELS[4])
        ttk.Label(frame, text="API keys are stored in the operating-system keychain or used only for this session. They are never saved in preferences.", wraplength=620, justify="left", style="Surface.TLabel").grid(sticky="ew")
        ttk.Separator(frame).grid(sticky="ew", pady=18)
        ttk.Label(frame, text="Update preferences", style="Heading.TLabel").grid(sticky="w")
        self._choice(frame, 3, "Update channel (reserved for a later updater)", self.update_channel, ("stable", "beta"))
        ttk.Checkbutton(frame, text="Automatically check in the background (not active yet)", variable=self.flags["automatic_update_checks"], state="disabled", style="Surface.TCheckbutton").grid(row=5, column=0, sticky="ew")
        ttk.Label(frame, text="Use About → Check for updates to open the trusted GitHub Releases page. No files are downloaded or installed.", wraplength=620, style="Muted.TLabel").grid(row=6, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(frame, text="Stable releases are intended to keep a consistent application identity. Unsigned or ad-hoc development rebuilds may ask for Keychain permission again because their code identity can change; Always Allow is not guaranteed to carry across rebuilds.", wraplength=620, style="Muted.TLabel").grid(row=7, column=0, sticky="ew", pady=(14, 0))

    def _manage_downloaded_sets(self):
        DownloadedSetManager(self, self.service, lambda _removed: self.on_saved())

    def _install_dirty_tracking(self):
        variables = [self.set_var, self.cache_var, self.theme, self.density, self.window_layout, self.preview_size, self.eviction, self.limit, self.update_channel, *self.flags.values()]
        for variable in variables:
            variable.trace_add("write", self._mark_dirty)
        self.theme.trace_add("write", self._preview_theme)
        self.density.trace_add("write", self._preview_theme)

    def _draft_values(self):
        return (
            self.set_var.get(), self.cache_var.get(), self.theme.get(), self.density.get(), self.window_layout.get(),
            self.preview_size.get(), self.eviction.get(), self.limit.get(), self.update_channel.get(),
            *(variable.get() for variable in self.flags.values()),
        )

    def _mark_dirty(self, *_args):
        self.dirty_state.compare(self._draft_values(), self._applied_draft)
        self.apply_button.configure(state="normal" if self.dirty_state.dirty else "disabled")

    def _preview_theme(self, *_args):
        choice = self.theme.get()
        if choice == "system":
            appearance = self.theme_monitor.last_appearance if hasattr(self, "theme_monitor") else None
            if appearance:
                apply_theme(self.winfo_toplevel(), choice, self.density.get(), system_appearance=appearance)
        else:
            apply_theme(self.winfo_toplevel(), choice, self.density.get())

    def _system_preview_changed(self, appearance: str) -> None:
        if self.theme.get() == "system":
            apply_theme(self.winfo_toplevel(), "system", self.density.get(), system_appearance=appearance)

    def _browse_cache(self):
        selected = filedialog.askdirectory(parent=self, initialdir=self.cache_var.get())
        if selected:
            self.cache_var.set(selected)

    def _clear(self):
        self.service.clear_preview_cache()
        messagebox.showinfo("Settings", "Preview cache cleared.", parent=self)

    def _defaults(self):
        p = Preferences()
        self.theme.set(p.theme); self.density.set(p.density)
        self.window_layout.set(p.window_layout_preset.title())
        self.preview_size.set(p.preview_size); self.eviction.set(p.preview_cache_eviction)
        self.limit.set(str(p.preview_cache_limit_mb)); self.update_channel.set(p.update_channel)
        for key, variable in self.flags.items():
            variable.set(getattr(p, key))

    def _draft_settings(self):
        selected = self.service.validate_set_num(self.set_var.get())
        directory = validate_cache_directory(Path(self.cache_var.get()))
        custom = None if directory == cache_dir() else directory
        limit = int(self.limit.get())
        if not 0 <= limit <= 10_000:
            raise ValueError("Preview cache limit must be between 0 and 10000 MB.")
        preferences = replace(
            self.service.settings.preferences,
            theme=self.theme.get(), density=self.density.get(), preview_size=self.preview_size.get(),
            preview_cache_limit_mb=limit, preview_cache_eviction=self.eviction.get(),
            update_channel=self.update_channel.get(),
            **{key: variable.get() for key, variable in self.flags.items()},
        )
        preferences = with_layout_preset(preferences, self.window_layout.get().lower())
        return replace(self.service.settings, default_set=selected, cache_directory=custom, preferences=preferences)

    def _persist(self, *, close: bool) -> bool:
        try:
            settings = self._draft_settings()
            save_settings(settings, self.service.settings_path)
            self.service.settings = settings
            self.service._inventory = None
        except Exception as exc:
            messagebox.showerror("Settings", str(exc), parent=self)
            return False
        self.dirty_state.applied()
        self._applied_draft = self._draft_values()
        self.apply_button.configure(state="disabled")
        self.on_saved()
        if close:
            self.destroy()
        return True

    def _apply(self):
        self._persist(close=False)

    def _save(self):
        self._persist(close=True)

    def _request_close(self):
        if not self.dirty_state.dirty:
            self.destroy()
            return
        decision = ask_unsaved_changes(self)
        if decision == "save":
            self._persist(close=True)
        elif decision == "discard":
            preferences = self.service.settings.preferences
            apply_theme(self.winfo_toplevel(), preferences.theme, preferences.density)
            self.destroy()

    def destroy(self):
        if hasattr(self, "_responsive"):
            self._responsive.stop()
        if hasattr(self, "theme_monitor"):
            self.theme_monitor.stop()
        super().destroy()
