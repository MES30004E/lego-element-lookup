from __future__ import annotations

from types import MethodType

from lego_element_lookup.gui.main_window import DATA_GRID_ROW, FOOTER_GRID_ROW, HEADER_GRID_ROW, INPUT_HEADER_ROW, MAIN_WINDOW_MIN_SIZE, TOOLBAR_HEADER_ROW, MainWindow, action_row_columns, commands_for_mode
from lego_element_lookup.gui.responsive import (
    NARROW_BREAKPOINT,
    RESIZE_DEBOUNCE_MS,
    WIDE_BREAKPOINT,
    DebouncedBreakpointController,
    LayoutMode,
    layout_mode_for_width,
)
from lego_element_lookup.gui.settings_window import SETTINGS_MIN_SIZE
from lego_element_lookup.gui.widgets import PART_NAME_WRAP, PREVIEW_SIZES, result_grid_positions


class FakeAfterOwner:
    def __init__(self):
        self.next_id = 0
        self.scheduled = {}
        self.cancelled = []

    def after(self, delay, callback):
        self.next_id += 1
        self.scheduled[self.next_id] = (delay, callback)
        return self.next_id

    def after_cancel(self, after_id):
        self.cancelled.append(after_id)
        self.scheduled.pop(after_id, None)


class FakeWidget:
    def __init__(self):
        self.config = {}
        self.grid_calls = []

    def configure(self, **values):
        self.config.update(values)

    def grid_forget(self):
        self.grid_calls.append(("forget", {}))

    def grid(self, **values):
        self.grid_calls.append(("grid", values))

    def grid_configure(self, **values):
        self.grid_calls.append(("configure", values))

    def columnconfigure(self, *_args, **_kwargs):
        pass


class FakeResult(FakeWidget):
    def __init__(self):
        super().__init__()
        self.preview_state = "cached"
        self.modes = []

    def set_layout(self, mode):
        self.modes.append(mode)


class FakeScrollArea:
    def __init__(self):
        self.preserved = 0

    def preserve_position(self):
        self.preserved += 1


def test_breakpoint_selection_contract():
    assert layout_mode_for_width(WIDE_BREAKPOINT) is LayoutMode.WIDE
    assert layout_mode_for_width(WIDE_BREAKPOINT - 1) is LayoutMode.MEDIUM
    assert layout_mode_for_width(NARROW_BREAKPOINT) is LayoutMode.MEDIUM
    assert layout_mode_for_width(NARROW_BREAKPOINT - 1) is LayoutMode.NARROW


def test_wide_medium_narrow_transitions_only_rebuild_on_mode_change():
    owner = FakeAfterOwner()
    applied = []
    controller = DebouncedBreakpointController(owner, applied.append)
    assert controller.apply_now(1100)
    assert controller.apply_now(900)
    assert not controller.apply_now(800)
    assert controller.apply_now(700)
    assert applied == [LayoutMode.WIDE, LayoutMode.MEDIUM, LayoutMode.NARROW]
    assert controller.transition_count == 3


def test_resize_requests_are_debounced():
    owner = FakeAfterOwner()
    applied = []
    controller = DebouncedBreakpointController(owner, applied.append)
    controller.request(1001)
    first = controller.after_id
    controller.request(990)
    second = controller.after_id
    controller.request(750)
    assert first in owner.cancelled and second in owner.cancelled
    delay, callback = owner.scheduled[controller.after_id]
    assert delay == RESIZE_DEBOUNCE_MS
    callback()
    assert applied == [LayoutMode.NARROW]


def test_actual_main_layout_preserves_match_selection_preview_and_long_set_name():
    owner = type("ResponsiveMain", (), {})()
    for name in ("header", "content", "status_label", "set_preview", "set_label", "set_row", "element_entry"):
        setattr(owner, name, FakeWidget())
    owner.result = FakeResult()
    owner.scroll_area = FakeScrollArea()
    owner.command_buttons = {name: FakeWidget() for name in ("Lookup", "Change Set", "Update Inventory", "Open Cache", "Settings")}
    owner.command_separators = (FakeWidget(), FakeWidget())
    owner.layout_separator = FakeWidget()
    owner.layout_button = FakeWidget()
    owner.overflow_button = FakeWidget()
    owner.current_match = object()
    owner.current_candidate_id = "candidate-2"
    owner.matches = [object(), object()]
    owner.match_choice = "candidate-2"
    owner._layout_commands = MethodType(MainWindow._layout_commands, owner)
    owner._render_set_preview = lambda: None
    owner.set_label.config["text"] = "Set 12345-1 — A very long set name that must wrap without widening the window"
    state = (owner.current_match, owner.current_candidate_id, owner.matches, owner.match_choice, owner.result.preview_state)
    MainWindow._apply_responsive_layout(owner, LayoutMode.WIDE)
    MainWindow._apply_responsive_layout(owner, LayoutMode.MEDIUM)
    MainWindow._apply_responsive_layout(owner, LayoutMode.NARROW)
    assert state == (owner.current_match, owner.current_candidate_id, owner.matches, owner.match_choice, owner.result.preview_state)
    assert owner.result.modes == [LayoutMode.WIDE, LayoutMode.MEDIUM, LayoutMode.NARROW]
    assert owner.scroll_area.preserved == 3
    positions = [owner.command_buttons[name].grid_calls[-1][1] for name in ("Lookup", "Change Set", "Update Inventory", "Settings")]
    assert [(item["row"], item["column"]) for item in positions] == [(0, 0), (0, 1), (0, 3), (0, 5)]
    assert all(item["sticky"] == "w" for item in positions)
    assert owner.overflow_button.grid_calls[-1][0] == "grid"
    assert owner.set_label.config["wraplength"] == 560
    assert owner.set_label.config["text"].startswith("Set 12345-1")


def test_narrow_result_stacks_preview_and_wraps_long_names():
    narrow = result_grid_positions(LayoutMode.NARROW)
    wide = result_grid_positions(LayoutMode.WIDE)
    assert narrow["preview"][0] < narrow["part_name"][0]
    assert narrow["preview"][1] == narrow["part_name"][1] == 0
    assert wide["preview"][0] == wide["part_name"][0]
    assert PART_NAME_WRAP[LayoutMode.NARROW] <= MAIN_WINDOW_MIN_SIZE[0] - 100
    assert PREVIEW_SIZES[LayoutMode.WIDE][0] > PREVIEW_SIZES[LayoutMode.MEDIUM][0] > PREVIEW_SIZES[LayoutMode.NARROW][0]


def test_all_actions_remain_reachable_in_narrow_layout():
    assert action_row_columns(700) == 5
    assert commands_for_mode(LayoutMode.NARROW) == ("Lookup", "Change Set", "Update Inventory", "Settings", "Overflow")
    assert commands_for_mode(LayoutMode.MEDIUM) == ("Lookup", "Change Set", "Update Inventory", "Open Cache", "Settings")


def test_minimum_sizes_and_bottom_bar_contract():
    assert MAIN_WINDOW_MIN_SIZE == (640, 560)
    assert SETTINGS_MIN_SIZE == (720, 600)
    assert (HEADER_GRID_ROW, DATA_GRID_ROW, FOOTER_GRID_ROW) == (0, 1, 2)
    assert TOOLBAR_HEADER_ROW < INPUT_HEADER_ROW
