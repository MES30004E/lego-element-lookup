"""Desktop application entry point."""

from __future__ import annotations

import argparse
import sys
import tkinter as tk
from dataclasses import replace
from tkinter import messagebox, ttk

from .. import __version__
from ..config import save_settings
from ..services import ApplicationService
from .main_window import MAIN_WINDOW_MIN_SIZE, MainWindow
from .about import PROJECT_URL, RELEASES_URL, SECURITY_URL, open_trusted_url, show_about
from .theme import SystemThemeMonitor, apply_theme, detect_system_theme
from .wizard import SetupWizard
from .window_layout import MIN_WINDOW_SIZE, valid_saved_geometry, window_size_for, with_layout_preset, with_saved_geometry

GEOMETRY_SAVE_DEBOUNCE_MS = 500
MENU_STRUCTURE = {
    "application": ("About LEGO Element Lookup", "Settings…", "Check for Updates…"),
    "file": ("Change Set…", "Update Inventory", "Open Cache Folder"),
    "edit": ("Copy Part Code", "Focus Element ID"),
    "view": ("Auto Layout", "Wide Layout", "Tall Layout", "Compact Layout"),
    "help": ("Project Repository", "Security & Support", "Check for Updates"),
}


class DesktopApplication:
    def __init__(self, root: tk.Tk, service: ApplicationService | None = None) -> None:
        self.root = root
        self.service = service or ApplicationService()
        self._geometry_after_id = None
        self._pending_geometry: tuple[int, int] | None = None
        self._last_window_size: tuple[int, int] | None = None
        self._preset_resize_active = False
        root.title("LEGO Element Lookup")
        preferences = self.service.settings.preferences
        initial_appearance = detect_system_theme() if preferences.theme == "system" else None
        apply_theme(root, preferences.theme, preferences.density, system_appearance=initial_appearance)
        self.theme_monitor = SystemThemeMonitor(
            root,
            lambda: self.service.settings.preferences.theme,
            self._system_appearance_changed,
            initial_appearance=initial_appearance,
        )
        self.theme_monitor.start()
        root.resizable(True, True)
        root.minsize(*MAIN_WINDOW_MIN_SIZE)
        self._apply_selected_preset()
        root.bind("<Configure>", self._root_configured, add="+")
        self._build_menu()
        root.protocol("WM_DELETE_WINDOW", self._quit)
        self.container = ttk.Frame(root)
        self.container.pack(fill="both", expand=True)
        self._show_wizard() if self.service.setup_required else self._show_main()

    def _clear(self) -> None:
        for child in self.container.winfo_children():
            child.destroy()

    def _show_wizard(self) -> None:
        self._clear()
        wizard = SetupWizard(self.container, self.service, self._show_main)
        wizard.pack(fill="both", expand=True)

    def _show_main(self) -> None:
        self._clear()
        window = MainWindow(
            self.container,
            self.service,
            self._apply_selected_preset,
            self._select_layout_preset,
        )
        window.pack(fill="both", expand=True)

    def _apply_selected_preset(self) -> None:
        if self._geometry_after_id is not None:
            self.root.after_cancel(self._geometry_after_id)
            self._geometry_after_id = None
        # Preserve a valid manual size as Auto's future restore point before a
        # fixed preset replaces the current geometry.
        self._save_pending_geometry()
        requested_width, requested_height = window_size_for(self.service.settings.preferences)
        screen_width = max(MIN_WINDOW_SIZE[0], self.root.winfo_screenwidth() - 80)
        screen_height = max(MIN_WINDOW_SIZE[1], self.root.winfo_screenheight() - 80)
        size = (min(requested_width, screen_width), min(requested_height, screen_height))
        self._preset_resize_active = True
        self._last_window_size = size
        self.root.geometry(f"{size[0]}x{size[1]}")
        self.root.after_idle(lambda: setattr(self, "_preset_resize_active", False))
        if hasattr(self, "container"):
            window = self._main_window()
            if window:
                window.set_layout_preset(self.service.settings.preferences.window_layout_preset)

    def _select_layout_preset(self, preset: str) -> None:
        """Persist and apply one preset for command bar, native menu, and Settings."""
        preferences = with_layout_preset(self.service.settings.preferences, preset)
        if preferences != self.service.settings.preferences:
            self.service.settings = replace(self.service.settings, preferences=preferences)
            save_settings(self.service.settings, self.service.settings_path)
        self._apply_selected_preset()

    def _root_configured(self, event) -> None:
        if event.widget is not self.root:
            return
        size = (int(event.width), int(event.height))
        if self._preset_resize_active:
            self._last_window_size = size
            return
        if size == self._last_window_size or valid_saved_geometry(*size) is None:
            return
        self._last_window_size = size
        self._pending_geometry = size
        if self._geometry_after_id is not None:
            self.root.after_cancel(self._geometry_after_id)
        self._geometry_after_id = self.root.after(GEOMETRY_SAVE_DEBOUNCE_MS, self._save_pending_geometry)

    def _save_pending_geometry(self) -> None:
        self._geometry_after_id = None
        if self._pending_geometry is None:
            return
        width, height = self._pending_geometry
        self._pending_geometry = None
        preferences = with_saved_geometry(self.service.settings.preferences, width, height)
        if preferences == self.service.settings.preferences:
            return
        self.service.settings = replace(self.service.settings, preferences=preferences)
        save_settings(self.service.settings, self.service.settings_path)

    def _open_settings(self) -> None:
        window = self._main_window()
        if window:
            window._settings()

    def _main_window(self) -> MainWindow | None:
        children = self.container.winfo_children()
        return children[0] if children and isinstance(children[0], MainWindow) else None

    def _main_action(self, method: str) -> None:
        window = self._main_window()
        if window:
            getattr(window, method)()

    def _open_help_url(self, url: str, title: str) -> None:
        if not open_trusted_url(url):
            messagebox.showinfo(title, f"Open {url} in your browser.", parent=self.root)

    def _build_menu(self) -> None:
        menu = tk.Menu(self.root)
        app_options = {"tearoff": False}
        if sys.platform == "darwin":
            app_options["name"] = "apple"
        app_menu = tk.Menu(menu, **app_options)
        app_menu.add_command(label="About LEGO Element Lookup", command=lambda: show_about(self.root))
        app_menu.add_separator()
        app_menu.add_command(label="Settings…", accelerator="Command+," if sys.platform == "darwin" else "Ctrl+,", command=self._open_settings)
        app_menu.add_command(label="Check for Updates…", command=lambda: self._open_help_url(RELEASES_URL, "Check for updates"))
        if sys.platform != "darwin":
            app_menu.add_separator()
            app_menu.add_command(label="Quit", command=self._quit)
        menu.add_cascade(label="LEGO Element Lookup", menu=app_menu)

        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="Change Set…", command=lambda: self._main_action("_change_set"))
        file_menu.add_command(label="Update Inventory", command=lambda: self._main_action("_update"))
        file_menu.add_separator()
        file_menu.add_command(label="Open Cache Folder", command=lambda: self._main_action("_open_cache"))
        menu.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menu, tearoff=False)
        edit_menu.add_command(label="Copy Part Code", command=lambda: self._main_action("_copy"))
        edit_menu.add_command(label="Focus Element ID", command=lambda: self._main_action("_focus_input"))
        menu.add_cascade(label="Edit", menu=edit_menu)

        view_menu = tk.Menu(menu, tearoff=False)
        for preset in ("auto", "wide", "tall", "compact"):
            view_menu.add_command(
                label=f"{preset.title()} Layout",
                command=lambda value=preset: self._select_layout_preset(value),
            )
        menu.add_cascade(label="View", menu=view_menu)

        help_menu = tk.Menu(menu, tearoff=False, name="help" if sys.platform == "darwin" else None)
        help_menu.add_command(label="Project Repository", command=lambda: self._open_help_url(PROJECT_URL, "Project repository"))
        help_menu.add_command(label="Security & Support", command=lambda: self._open_help_url(SECURITY_URL, "Security & support"))
        help_menu.add_separator()
        help_menu.add_command(label="Check for Updates", command=lambda: self._open_help_url(RELEASES_URL, "Check for updates"))
        menu.add_cascade(label="Help", menu=help_menu)
        self.root.configure(menu=menu)
        shortcut = "<Command-comma>" if sys.platform == "darwin" else "<Control-comma>"
        self.root.bind_all(shortcut, lambda _event: self._open_settings() or "break", add="+")

    def _quit(self) -> None:
        if self._geometry_after_id is not None:
            self.root.after_cancel(self._geometry_after_id)
            self._geometry_after_id = None
        self._save_pending_geometry()
        self.theme_monitor.stop()
        self.service.clear_session_key()
        self.root.destroy()

    def _system_appearance_changed(self, appearance: str) -> None:
        preferences = self.service.settings.preferences
        if preferences.theme == "system":
            apply_theme(self.root, "system", preferences.density, system_appearance=appearance)


def _report_callback_exception(root: tk.Tk, exc_type, exc_value, traceback) -> None:
    messagebox.showerror(
        "LEGO Element Lookup",
        "An unexpected error occurred. No API key or request details were written to the screen.",
        parent=root,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--smoke-test", action="store_true")
    args, _ = parser.parse_known_args(sys.argv[1:] if argv is None else argv)
    if args.smoke_test:
        print(f"LEGO Element Lookup {__version__}")
        return 0
    root = tk.Tk()
    root.report_callback_exception = lambda *values: _report_callback_exception(root, *values)
    DesktopApplication(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
