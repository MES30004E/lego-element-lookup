from __future__ import annotations

import tkinter as tk
from types import SimpleNamespace
from tkinter import ttk

import pytest

from lego_element_lookup import __version__
from lego_element_lookup.config import Settings
from lego_element_lookup.gui import about
from lego_element_lookup.gui.about import AboutDialog, PROJECT_URL, RELEASES_URL, SECURITY_URL
from lego_element_lookup.gui.main_window import COMMANDS, MainWindow
from lego_element_lookup.gui.responsive import LayoutMode
from lego_element_lookup.gui.theme import SEMANTIC_STYLES, apply_theme, palette_for
from lego_element_lookup.lookup import Match
from lego_element_lookup.relationship_cache import RelationshipCacheState


class ShellService:
    def __init__(self, tmp_path):
        self.settings = Settings(None, "76344-1", tmp_path, True)
        self.settings_path = tmp_path / "config.json"
        self.cache_directory = tmp_path

    def set_metadata(self, _set_num):
        return None

    def cached_set_preview(self, _set_num):
        return None

    def cached_preview(self, _match):
        return None

    def relationship_cache_state(self):
        return SimpleNamespace(state=RelationshipCacheState.NOT_DOWNLOADED, index=None)


def tk_root_or_skip():
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk display is unavailable: {exc}")
    root.withdraw()
    return root


def test_shell_hierarchy_copy_placement_and_permanent_version(tmp_path):
    root = tk_root_or_skip()
    try:
        window = MainWindow(root, ShellService(tmp_path))
        assert int(window.header.grid_info()["row"]) == 0
        assert int(window.command_bar.grid_info()["row"]) < int(window.input_area.grid_info()["row"])
        assert not hasattr(window, "action_frame")
        assert window.scroll_area.master is window
        assert int(window.scroll_area.grid_info()["row"]) == 1
        assert int(window.bottom_bar.grid_info()["row"]) == 2
        assert window.version_label.cget("text") == f"v{__version__}"
        assert window.version_label.master is window.bottom_bar
        assert window.copy_button.master is window.result.code_row
        assert str(window.copy_button.cget("state")) == "disabled"
        window.focus_get = lambda: window.element_entry
        window._lookup_focus_changed()
        assert window.command_buttons["Lookup"].cget("style") == "Active.CommandButton.TButton"
        window.focus_get = lambda: None
        window._lookup_focus_changed()
        assert window.command_buttons["Lookup"].cget("style") == "CommandButton.TButton"
    finally:
        root.destroy()


def test_command_bar_invokes_the_shared_main_window_methods(tmp_path, monkeypatch):
    calls = []
    methods = {
        "Lookup": "_focus_input",
        "Change Set": "_change_set",
        "Update Inventory": "_update",
        "Open Cache": "_open_cache",
        "Settings": "_settings",
    }
    for method in methods.values():
        monkeypatch.setattr(MainWindow, method, lambda self, name=method: calls.append(name))
    root = tk_root_or_skip()
    try:
        window = MainWindow(root, ShellService(tmp_path))
        for command in COMMANDS:
            assert window.command_buttons[command].cget("text") == command
            window.command_buttons[command].invoke()
        assert calls == list(methods.values())
        assert window.command_buttons["Update Inventory"].cget("style") == "Primary.CommandButton.TButton"
    finally:
        root.destroy()


def test_result_copy_enables_on_selection_and_updates_status(tmp_path):
    root = tk_root_or_skip()
    try:
        window = MainWindow(root, ShellService(tmp_path))
        copied = []
        window.clipboard_clear = lambda: copied.clear()
        window.clipboard_append = copied.append
        window.update_idletasks = lambda: None
        match = Match("7202", "154", "A long LEGO part name", "Dark Red", rgb="720E0F", quantity=2)
        window._select_match(match, auto_copy=False)
        assert str(window.copy_button.cget("state")) == "normal"
        window.copy_button.invoke()
        assert copied == ["7202"]
        assert window.message.get() == "Part code copied to clipboard."
    finally:
        root.destroy()


def test_command_bar_breakpoints_keep_one_row_without_cache_clipping(tmp_path):
    root = tk_root_or_skip()
    try:
        window = MainWindow(root, ShellService(tmp_path))
        for mode in (LayoutMode.WIDE, LayoutMode.MEDIUM):
            window._apply_responsive_layout(mode)
            assert all(window.command_buttons[name].winfo_manager() == "grid" for name in COMMANDS)
            assert window.layout_button.winfo_manager() == "grid"
            assert window.overflow_button.winfo_manager() == ""
        window._apply_responsive_layout(LayoutMode.NARROW)
        assert window.command_buttons["Open Cache"].winfo_manager() == ""
        assert window.layout_button.winfo_manager() == ""
        assert window.overflow_button.winfo_manager() == "grid"
        visible = ("Lookup", "Change Set", "Update Inventory", "Settings")
        assert [int(window.command_buttons[name].grid_info()["row"]) for name in visible] == [0, 0, 0, 0]
        root.update_idletasks()
        assert window.command_bar.winfo_reqwidth() <= 640
    finally:
        root.destroy()


def test_about_real_buttons_and_settings_grab_handoff(tmp_path, monkeypatch):
    root = tk_root_or_skip()
    settings = None
    dialog = None
    try:
        settings = tk.Toplevel(root)
        settings.withdraw()
        settings.grab_set()
        dialog = AboutDialog(settings)
        dialog.withdraw()
        opened = []
        dialog.actions.opener = lambda url, new: opened.append((url, new)) or True
        monkeypatch.setattr(about, "copy_diagnostics", lambda _target: True)
        dialog.repository_button.invoke()
        dialog.security_button.invoke()
        dialog.update_button.invoke()
        dialog.copy_button.invoke()
        assert [url for url, _new in opened] == [PROJECT_URL, SECURITY_URL, RELEASES_URL]
        assert "copied" in dialog.feedback.get().lower()
        assert dialog.grab_current() is dialog
        dialog.close_button.invoke()
        assert not dialog.winfo_exists()
        assert settings.grab_current() is settings
        dialog = None
    finally:
        if dialog is not None and dialog.winfo_exists():
            dialog.destroy()
        if settings is not None and settings.winfo_exists():
            settings.destroy()
        root.destroy()


def test_navigation_and_semantic_theme_roles_are_declared():
    assert {
        "CommandButton.TButton",
        "Active.CommandButton.TButton",
        "Primary.CommandButton.TButton",
        "CommandOverflow.TMenubutton",
        "CurrentSet.TFrame",
        "ResultCard.TFrame",
        "Attribution.TLabel",
        "Success.BottomBar.TLabel",
        "Info.BottomBar.TLabel",
        "Warning.BottomBar.TLabel",
        "Error.BottomBar.TLabel",
        "Danger.TButton",
    } <= set(SEMANTIC_STYLES)


@pytest.mark.parametrize(
    ("choice", "appearance"),
    (("light", None), ("dark", None), ("system", "light"), ("system", "dark")),
)
def test_navigation_semantic_styles_apply_in_every_appearance(choice, appearance):
    root = tk_root_or_skip()
    try:
        palette = apply_theme(root, choice, system_appearance=appearance)
        assert palette is palette_for(choice, appearance)
        style = ttk.Style(root)
        for name in (
            "CommandButton.TButton",
            "Active.CommandButton.TButton",
            "Primary.CommandButton.TButton",
            "CurrentSet.TFrame",
            "ResultCard.TFrame",
            "Attribution.TLabel",
            "Success.BottomBar.TLabel",
            "Error.BottomBar.TLabel",
        ):
            assert style.configure(name)
        assert style.lookup("CommandButton.TButton", "foreground") == palette.text
        assert style.lookup("Active.CommandButton.TButton", "foreground") == palette.focus
        assert style.lookup("CommandButton.TButton", "borderwidth") == 1
    finally:
        root.destroy()
