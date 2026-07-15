from __future__ import annotations

import tkinter as tk
from types import SimpleNamespace

import pytest

from lego_element_lookup.config import Preferences, Settings
from lego_element_lookup.gui.app import DesktopApplication
from lego_element_lookup.gui.main_window import MAIN_WINDOW_MIN_SIZE, MainWindow
from lego_element_lookup.gui.responsive import LayoutMode


class FakeRoot:
    def __init__(self):
        self.geometries = []
        self.cancelled = []
        self.scheduled = []

    def after_cancel(self, value):
        self.cancelled.append(value)

    def after(self, delay, callback):
        self.scheduled.append((delay, callback))
        return len(self.scheduled)

    def after_idle(self, callback):
        callback()

    def winfo_screenwidth(self):
        return 2000

    def winfo_screenheight(self):
        return 1400

    def geometry(self, value):
        self.geometries.append(value)


class ControllerService:
    def __init__(self, tmp_path, preferences=None):
        self.settings = Settings(
            api_key=None,
            default_set="76344-1",
            preferences=preferences or Preferences(),
        )
        self.settings_path = tmp_path / "config.json"


def controller(tmp_path, preferences=None):
    app = object.__new__(DesktopApplication)
    app.root = FakeRoot()
    app.service = ControllerService(tmp_path, preferences)
    app._geometry_after_id = None
    app._pending_geometry = None
    app._last_window_size = None
    app._preset_resize_active = False
    return app


def tk_root_or_skip():
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk display is unavailable: {exc}")
    root.withdraw()
    return root


class ResizeService:
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


def test_root_is_freely_resizable_in_both_axes_without_height_lock(tmp_path):
    root = tk_root_or_skip()
    application = None
    try:
        application = DesktopApplication(root, ResizeService(tmp_path))
        root.update_idletasks()
        assert tuple(bool(value) for value in root.resizable()) == (True, True)
        assert root.minsize() == MAIN_WINDOW_MIN_SIZE == (640, 560)
        assert root.maxsize()[1] > MAIN_WINDOW_MIN_SIZE[1]

        preset = application.service.settings.preferences.window_layout_preset
        application._root_configured(SimpleNamespace(widget=root, width=900, height=640))
        application._save_pending_geometry()
        preferences = application.service.settings.preferences
        assert (preferences.last_window_width, preferences.last_window_height) == (900, 640)
        assert preferences.window_layout_preset == preset

        application._root_configured(SimpleNamespace(widget=root, width=1000, height=640))
        application._save_pending_geometry()
        preferences = application.service.settings.preferences
        assert (preferences.last_window_width, preferences.last_window_height) == (1000, 640)
        assert preferences.window_layout_preset == preset

        application._root_configured(SimpleNamespace(widget=root, width=1000, height=600))
        application._save_pending_geometry()
        preferences = application.service.settings.preferences
        assert (preferences.last_window_width, preferences.last_window_height) == (1000, 600)
        assert preferences.window_layout_preset == preset

        application._select_layout_preset("wide")
        root.update_idletasks()
        application._root_configured(SimpleNamespace(widget=root, width=1040, height=690))
        application._save_pending_geometry()
        preferences = application.service.settings.preferences
        assert (preferences.last_window_width, preferences.last_window_height) == (1040, 690)
        assert preferences.window_layout_preset == "wide"

        window = application._main_window()
        window._responsive.apply_now(900)
        mode = window._responsive.current
        application._root_configured(SimpleNamespace(widget=root, width=900, height=700))
        assert window._responsive.current is mode is LayoutMode.MEDIUM
    finally:
        if application is not None:
            application.theme_monitor.stop()
        root.destroy()


def test_presets_are_one_shot_sizes_and_auto_restores_manual_geometry(tmp_path):
    app = controller(
        tmp_path,
        Preferences(last_window_width=1060, last_window_height=680),
    )
    expected = {
        "wide": "1280x760",
        "tall": "740x1000",
        "compact": "760x720",
    }
    for preset, geometry in expected.items():
        app._select_layout_preset(preset)
        assert app.root.geometries[-1] == geometry
        assert app.service.settings.preferences.window_layout_preset == preset
        assert app._preset_resize_active is False

    app._select_layout_preset("auto")
    assert app.root.geometries[-1] == "1060x680"
    assert app.service.settings.preferences.window_layout_preset == "auto"


def test_manual_height_persistence_does_not_reapply_or_mutate_preset(tmp_path):
    app = controller(tmp_path, Preferences(window_layout_preset="wide"))
    app._last_window_size = (1280, 760)
    app._root_configured(SimpleNamespace(widget=app.root, width=1040, height=650))
    assert app.root.geometries == []
    app._save_pending_geometry()
    preferences = app.service.settings.preferences
    assert (preferences.last_window_width, preferences.last_window_height) == (1040, 650)
    assert preferences.window_layout_preset == "wide"


def test_main_layout_control_uses_application_preset_callback(tmp_path):
    root = tk_root_or_skip()
    try:
        selected = []
        window = MainWindow(root, ResizeService(tmp_path), on_layout_selected=selected.append)
        window._select_layout("tall")
        assert selected == ["tall"]
        assert window.layout_var.get() == "Tall"
        window.set_layout_preset("compact")
        assert window.layout_var.get() == "Compact"
        window._apply_responsive_layout(LayoutMode.WIDE)
        assert window.layout_button.winfo_manager() == "grid"
        window._apply_responsive_layout(LayoutMode.NARROW)
        assert window.layout_button.winfo_manager() == ""
        assert window.overflow_button.winfo_manager() == "grid"
    finally:
        root.destroy()


def test_native_view_menu_dispatches_to_the_same_preset_method(tmp_path):
    root = tk_root_or_skip()
    try:
        selected = []
        app = object.__new__(DesktopApplication)
        app.root = root
        app._select_layout_preset = selected.append
        app._build_menu()
        menu = root.nametowidget(root.cget("menu"))
        view_index = next(
            index
            for index in range(menu.index("end") + 1)
            if menu.type(index) == "cascade" and menu.entrycget(index, "label") == "View"
        )
        view_menu = root.nametowidget(menu.entrycget(view_index, "menu"))
        for index in range(4):
            view_menu.invoke(index)
        assert selected == ["auto", "wide", "tall", "compact"]
    finally:
        root.destroy()
