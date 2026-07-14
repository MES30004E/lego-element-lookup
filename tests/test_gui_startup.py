from __future__ import annotations

import tkinter as tk

import pytest

from lego_element_lookup.config import Settings
from lego_element_lookup.gui.app import DesktopApplication
from lego_element_lookup.gui.main_window import MainWindow
from lego_element_lookup.gui.responsive import LayoutMode, layout_mode_for_width


class StartupService:
    def __init__(self, tmp_path):
        self.settings = Settings(None, "76344-1", tmp_path, True)
        self.settings_path = tmp_path / "config.json"
        self.cache_directory = tmp_path
        self.setup_required = False

    def set_metadata(self, _set_num):
        return None

    def cached_set_preview(self, _set_num):
        return None

    def clear_session_key(self):
        pass


def tk_root_or_skip():
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk display is unavailable: {exc}")
    root.withdraw()
    return root


@pytest.mark.parametrize(
    ("width", "expected"),
    ((1280, LayoutMode.WIDE), (820, LayoutMode.MEDIUM), (700, LayoutMode.NARROW)),
)
def test_clean_main_window_constructs_before_initial_responsive_apply(tmp_path, width, expected):
    root = tk_root_or_skip()
    try:
        window = MainWindow(root, StartupService(tmp_path))
        assert window.status_label.winfo_exists()
        assert window.message.label is window.status_label
        assert window._responsive.apply_now(width) is (layout_mode_for_width(width) is not LayoutMode.MEDIUM)
        assert window._responsive.current is expected
    finally:
        root.destroy()


def test_desktop_startup_path_constructs_main_shell_without_mainloop(tmp_path):
    root = tk_root_or_skip()
    try:
        application = DesktopApplication(root, StartupService(tmp_path))
        root.update_idletasks()
        window = application._main_window()
        assert isinstance(window, MainWindow)
        assert window.status_label.winfo_exists()
        assert window._responsive.current in set(LayoutMode)
    finally:
        root.destroy()
