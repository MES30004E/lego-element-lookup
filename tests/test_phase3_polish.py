from __future__ import annotations

from lego_element_lookup import __version__
from lego_element_lookup.config import Preferences
from lego_element_lookup.gui.about import RELEASES_URL, check_for_updates, diagnostics_text, open_trusted_url
from lego_element_lookup.gui.main_window import BOTTOM_BAR_STICKY, CONTENT_GRID_ROW, FOOTER_GRID_ROW, MAIN_WINDOW_PADDING, action_row_columns, version_footer_text
from lego_element_lookup.gui.set_chooser import choose_set_value
from lego_element_lookup.gui.settings_window import DirtyState, FOOTER_ACTIONS, SETTINGS_MIN_SIZE, SETTINGS_TAB_LABELS
from lego_element_lookup.gui.theme import DARK, LIGHT, SEMANTIC_STYLES, SystemThemeMonitor, detect_system_theme, palette_for


def test_settings_layout_contract_is_large_and_labels_are_compact():
    assert SETTINGS_TAB_LABELS == ("General", "Lookup", "Images & cache", "Data", "Account & security")
    assert SETTINGS_MIN_SIZE[0] >= 680 and SETTINGS_MIN_SIZE[1] >= 500
    assert FOOTER_ACTIONS == ("Restore defaults", "About", "Cancel", "Apply", "Save")


def test_action_row_layout_is_responsive():
    assert action_row_columns(1100) == 5
    assert action_row_columns(900) == 5
    assert action_row_columns(700) == 5


def test_about_version_and_diagnostics_are_safe():
    diagnostics = diagnostics_text()
    assert __version__ in diagnostics
    assert "API" not in diagnostics and "Authorization" not in diagnostics
    assert "/Users/" not in diagnostics and "cache" not in diagnostics.lower()


def test_update_check_opens_only_trusted_releases_page():
    opened = []
    assert check_for_updates(lambda url, new: opened.append((url, new)) or True)
    assert opened == [(RELEASES_URL, 2)]
    try:
        open_trusted_url("https://example.invalid/release", lambda *_args, **_kwargs: True)
    except ValueError:
        pass
    else:
        raise AssertionError("untrusted update URL was accepted")


def test_update_preferences_are_safe_placeholders():
    preferences = Preferences()
    assert preferences.update_channel == "stable"
    assert preferences.automatic_update_checks is False


def test_theme_roles_are_complete_for_light_and_dark():
    expected = set(LIGHT.__dataclass_fields__)
    assert expected == set(DARK.__dataclass_fields__)
    assert expected == {"window", "surface", "surface_border", "text", "muted_text", "focus", "selection", "button", "warning", "error", "success", "preview_border"}


def test_settings_dirty_state_apply_contract():
    state = DirtyState()
    assert not state.dirty
    state.changed(); assert state.dirty
    state.applied(); assert not state.dirty


def test_version_footer_uses_package_version():
    assert version_footer_text() == f"v{__version__}"
    assert "Status.TLabel" in SEMANTIC_STYLES and "Version.TLabel" in SEMANTIC_STYLES


def test_dark_palette_has_distinct_selected_surface_and_readable_muted_text():
    assert DARK.surface != DARK.window
    assert DARK.selection != DARK.button
    assert DARK.muted_text != DARK.surface


def test_typed_set_takes_precedence_over_downloaded_selection():
    labels = {"76344-1 — Iron Man": "76344-1"}
    assert choose_set_value("76344-1 — Iron Man", " 10305-1 ", labels) == ("10305-1", True)
    assert choose_set_value("76344-1 — Iron Man", "", labels) == ("76344-1", False)


def test_system_theme_resolves_mocked_macos_appearance():
    result = type("Result", (), {"returncode": 0, "stdout": "Dark\n"})()
    assert detect_system_theme("darwin", runner=lambda *args, **kwargs: result) == "dark"
    light = type("Result", (), {"returncode": 1, "stdout": ""})()
    assert detect_system_theme("darwin", runner=lambda *args, **kwargs: light) == "light"
    assert palette_for("light") is LIGHT and palette_for("dark") is DARK


def test_footer_contract_is_pinned_below_expanding_content():
    assert FOOTER_GRID_ROW > CONTENT_GRID_ROW
    assert BOTTOM_BAR_STICKY == "ew" and MAIN_WINDOW_PADDING == 0
    assert "BottomBar.TFrame" in SEMANTIC_STYLES and "BottomBar.TLabel" in SEMANTIC_STYLES
    assert version_footer_text() == f"v{__version__}"


def test_dirty_state_compares_draft_to_last_applied_snapshot():
    state = DirtyState(); state.compare(("dark",), ("light",)); assert state.dirty
    state.compare(("light",), ("light",)); assert not state.dirty


class ThemeOwner:
    def __init__(self): self.cancelled = []
    def after(self, delay, callback): return (delay, callback)
    def after_cancel(self, value): self.cancelled.append(value)


def test_live_system_theme_transitions_only_apply_changes():
    choice = {"value": "system"}; applied = []
    monitor = SystemThemeMonitor(ThemeOwner(), lambda: choice["value"], applied.append, initial_appearance="light")
    monitor._stopped = False
    monitor._accept("light"); assert applied == []
    monitor._accept("dark"); assert applied == ["dark"]
    monitor._accept("dark"); assert applied == ["dark"]
    monitor._accept("light"); assert applied == ["dark", "light"]
    assert choice["value"] == "system"


def test_manual_theme_ignores_system_changes_and_monitor_stops():
    owner = ThemeOwner(); choice = {"value": "light"}; applied = []
    monitor = SystemThemeMonitor(owner, lambda: choice["value"], applied.append, initial_appearance="light")
    monitor.start(); monitor._accept("dark")
    assert applied == []
    choice["value"] = "dark"; monitor._accept("light")
    assert applied == []
    monitor.stop()
    assert not monitor.running and owner.cancelled
