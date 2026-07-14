from __future__ import annotations

import json

from lego_element_lookup.config import Preferences, Settings, load_settings, save_settings
from lego_element_lookup.gui.main_window import CONTENT_GRID_ROW, FOOTER_GRID_ROW, HEADER_GRID_ROW, INPUT_HEADER_ROW, TOOLBAR_HEADER_ROW
from lego_element_lookup.gui.main_window import MainWindow
from lego_element_lookup.gui.responsive import NARROW_BREAKPOINT, WIDE_BREAKPOINT, LayoutMode, layout_mode_for_width
from lego_element_lookup.gui.scrollable import NO_HORIZONTAL_SCROLLBAR, SCROLL_INCREMENT_PX, normalise_wheel_event, platform_scroll_multiplier, scroll_required
from lego_element_lookup.gui.window_layout import (
    DEFAULT_AUTO_SIZE,
    PRESET_SIZES,
    window_size_for,
    with_layout_preset,
    with_saved_geometry,
)


def test_scroll_contract_keeps_footer_fixed_and_uses_no_horizontal_bar():
    assert scroll_required(1200, 700)
    assert not scroll_required(700, 700)
    assert HEADER_GRID_ROW < CONTENT_GRID_ROW < FOOTER_GRID_ROW
    assert TOOLBAR_HEADER_ROW < INPUT_HEADER_ROW
    assert NO_HORIZONTAL_SCROLLBAR


def test_wheel_events_are_normalised_for_supported_platforms():
    assert normalise_wheel_event(delta=1, platform="darwin") == -1
    assert normalise_wheel_event(delta=-3, platform="darwin") == 3
    assert normalise_wheel_event(delta=-99, platform="darwin") == 3
    assert normalise_wheel_event(delta=120, platform="win32") == -1
    assert normalise_wheel_event(delta=-240, platform="win32") == 2
    assert normalise_wheel_event(number=4, platform="linux") == -1
    assert normalise_wheel_event(number=5, platform="linux") == 1
    assert SCROLL_INCREMENT_PX == 8
    assert platform_scroll_multiplier("darwin") == 1
    assert platform_scroll_multiplier("win32") == 3


def test_layout_preset_sizes_and_breakpoint_intent():
    assert Preferences().window_layout_preset == "auto"
    assert PRESET_SIZES["wide"] == (1280, 760)
    assert PRESET_SIZES["tall"] == (740, 1000)
    assert PRESET_SIZES["compact"] == (760, 720)
    assert layout_mode_for_width(PRESET_SIZES["wide"][0]) is LayoutMode.WIDE
    assert layout_mode_for_width(PRESET_SIZES["tall"][0]) is LayoutMode.NARROW
    assert layout_mode_for_width(PRESET_SIZES["compact"][0]) is LayoutMode.MEDIUM
    assert PRESET_SIZES["tall"][0] < NARROW_BREAKPOINT < WIDE_BREAKPOINT
    assert scroll_required(1300, PRESET_SIZES["tall"][1] - 80)


def test_fixed_presets_and_auto_geometry_are_selected_safely():
    assert window_size_for(Preferences()) == DEFAULT_AUTO_SIZE
    for preset, size in PRESET_SIZES.items():
        assert window_size_for(Preferences(window_layout_preset=preset)) == size
    saved = Preferences(last_window_width=1110, last_window_height=810)
    assert window_size_for(saved) == (1110, 810)
    assert window_size_for(Preferences(last_window_width=100, last_window_height=50)) == DEFAULT_AUTO_SIZE


def test_manual_geometry_does_not_mutate_selected_preset():
    original = Preferences(window_layout_preset="wide")
    resized = with_saved_geometry(original, 1040, 840)
    assert resized.window_layout_preset == "wide"
    assert (resized.last_window_width, resized.last_window_height) == (1040, 840)
    assert with_saved_geometry(original, 100, 100) is original


def test_layout_draft_is_transactional_and_invalid_values_fall_back():
    applied = Preferences(window_layout_preset="wide")
    draft = with_layout_preset(applied, "tall")
    assert applied.window_layout_preset == "wide"
    assert draft.window_layout_preset == "tall"
    assert with_layout_preset(applied, "enormous").window_layout_preset == "auto"


def test_layout_preset_and_auto_geometry_persist(tmp_path):
    path = tmp_path / "config.json"
    settings = Settings(
        api_key=None,
        default_set="76344-1",
        preferences=Preferences(
            window_layout_preset="tall",
            last_window_width=1080,
            last_window_height=820,
        ),
    )
    save_settings(settings, path)
    loaded = load_settings(path, env={})
    assert loaded.preferences.window_layout_preset == "tall"
    assert loaded.preferences.last_window_width == 1080
    assert loaded.preferences.last_window_height == 820

    data = json.loads(path.read_text())
    data["preferences"]["window_layout_preset"] = "invalid"
    data["preferences"]["last_window_width"] = 1
    data["preferences"]["last_window_height"] = 99_999
    path.write_text(json.dumps(data))
    invalid = load_settings(path, env={})
    assert invalid.preferences.window_layout_preset == "auto"
    assert window_size_for(invalid.preferences) == DEFAULT_AUTO_SIZE


def test_settings_apply_resizes_only_when_applied_preset_changes(monkeypatch):
    monkeypatch.setattr("lego_element_lookup.gui.theme.apply_theme", lambda *args, **kwargs: None)
    callbacks: list[str] = []
    owner = type("SettingsHost", (), {})()
    owner.service = type(
        "Service",
        (),
        {"settings": Settings(api_key=None, default_set="76344-1", preferences=Preferences(window_layout_preset="wide"))},
    )()
    owner._applied_layout_preset = "auto"
    owner.on_layout_preset = lambda: callbacks.append("resize")
    owner.winfo_toplevel = lambda: owner
    owner.scroll_area = type("Scroll", (), {"refresh_colours": lambda self: None})()
    owner._refresh_set_header = lambda: None
    owner.message = type("Message", (), {"set": lambda self, value: None})()

    MainWindow._settings_saved(owner)
    assert callbacks == ["resize"]
    assert owner._applied_layout_preset == "wide"

    MainWindow._settings_saved(owner)
    assert callbacks == ["resize"]
