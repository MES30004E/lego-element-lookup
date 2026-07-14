from __future__ import annotations

from lego_element_lookup.gui import about
from lego_element_lookup.gui.about import (
    ABOUT_MIN_SIZE,
    AboutActions,
    PROJECT_URL,
    RELEASES_URL,
    SECURITY_URL,
    clear_about_reference,
    close_dialog,
    copy_diagnostics,
    open_trusted_url,
    show_about,
)
from lego_element_lookup.gui.app import MENU_STRUCTURE, DesktopApplication
from lego_element_lookup.gui.main_window import (
    DATA_GRID_ROW,
    FOOTER_GRID_ROW,
    HEADER_GRID_ROW,
    INPUT_HEADER_ROW,
    RESULT_GRID_ROW,
    TOOLBAR_HEADER_ROW,
    status_style_for_message,
)
from lego_element_lookup.gui.settings_window import SETTINGS_DEFAULT_SIZE, SETTINGS_MIN_SIZE
from lego_element_lookup.gui.theme import DARK, LIGHT, SEMANTIC_STYLES, palette_for


class ClipboardTarget:
    def __init__(self):
        self.value = "old"
        self.updated = False

    def clipboard_clear(self):
        self.value = ""

    def clipboard_append(self, value):
        self.value += value

    def update_idletasks(self):
        self.updated = True


def test_only_data_region_scrolls_and_fixed_shell_order_is_stable():
    assert (HEADER_GRID_ROW, DATA_GRID_ROW, FOOTER_GRID_ROW) == (0, 1, 2)
    assert TOOLBAR_HEADER_ROW < INPUT_HEADER_ROW
    assert RESULT_GRID_ROW == 1


def test_menu_structure_exposes_all_shared_actions():
    assert MENU_STRUCTURE["application"] == ("About LEGO Element Lookup", "Settings…", "Check for Updates…")
    assert MENU_STRUCTURE["file"] == ("Change Set…", "Update Inventory", "Open Cache Folder")
    assert MENU_STRUCTURE["edit"] == ("Copy Part Code", "Focus Element ID")
    assert MENU_STRUCTURE["view"] == ("Auto Layout", "Wide Layout", "Tall Layout", "Compact Layout")
    assert MENU_STRUCTURE["help"] == ("Project Repository", "Security & Support", "Check for Updates")


def test_menu_dispatch_calls_the_same_main_window_methods():
    calls = []
    main = type(
        "Main",
        (),
        {
            name: (lambda method: lambda self: calls.append(method))(name)
            for name in ("_change_set", "_update", "_open_cache", "_copy", "_focus_input", "_settings")
        },
    )()
    owner = type("Application", (), {"_main_window": lambda self: main})()
    for method in ("_change_set", "_update", "_open_cache", "_copy", "_focus_input", "_settings"):
        DesktopApplication._main_action(owner, method)
    assert calls == ["_change_set", "_update", "_open_cache", "_copy", "_focus_input", "_settings"]


def test_about_trusted_links_and_browser_failures_are_handled():
    opened = []
    for url in (PROJECT_URL, SECURITY_URL, RELEASES_URL):
        assert open_trusted_url(url, lambda value, new: opened.append((value, new)) or True)
    assert [value for value, _new in opened] == [PROJECT_URL, SECURITY_URL, RELEASES_URL]
    assert not open_trusted_url(PROJECT_URL, lambda *_args, **_kwargs: False)
    assert not open_trusted_url(PROJECT_URL, lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("no browser")))


def test_about_diagnostics_copy_and_close_actions_work():
    target = ClipboardTarget()
    assert copy_diagnostics(target, "redacted diagnostics")
    assert target.value == "redacted diagnostics" and target.updated
    dialog = type("Dialog", (), {"destroy": lambda self: setattr(self, "closed", True)})()
    assert close_dialog(dialog)
    assert dialog.closed


def test_actual_about_button_callbacks_open_copy_close_and_report_feedback():
    class View(ClipboardTarget):
        def __init__(self):
            super().__init__()
            self.feedback = []
            self.closed = False

        def set_feedback(self, message, role):
            self.feedback.append((message, role))

        def destroy(self):
            self.closed = True

    opened = []
    view = View()
    actions = AboutActions(view, lambda url, new: opened.append((url, new)) or True)
    for name in ("repository", "security", "updates", "copy", "close"):
        assert callable(getattr(actions, name))
    assert actions.repository() and actions.security() and actions.updates()
    assert [url for url, _new in opened] == [PROJECT_URL, SECURITY_URL, RELEASES_URL]
    assert actions.copy() and "LEGO Element Lookup" in view.value
    assert view.feedback[-1] == ("Diagnostics copied to clipboard.", "success")
    assert actions.close() and view.closed


def test_actual_about_callback_surfaces_browser_failure():
    class View(ClipboardTarget):
        def set_feedback(self, message, role): self.feedback = (message, role)
    view = View()
    actions = AboutActions(view, lambda *_args, **_kwargs: False)
    assert not actions.repository()
    assert view.feedback[1] == "error" and PROJECT_URL in view.feedback[0]


def test_about_reuses_and_focuses_existing_dialog(monkeypatch):
    class Existing:
        def __init__(self):
            self.calls = []

        def winfo_exists(self): return True
        def deiconify(self): self.calls.append("deiconify")
        def lift(self): self.calls.append("lift")
        def focus_force(self): self.calls.append("focus")

    existing = Existing()
    monkeypatch.setattr(about, "_about_dialog", existing)
    monkeypatch.setattr(about, "AboutDialog", lambda master: (_ for _ in ()).throw(AssertionError("created twice")))
    assert show_about(object()) is existing
    assert existing.calls == ["deiconify", "lift", "focus"]


def test_about_close_clears_singleton_and_reopen_creates_new_dialog(monkeypatch):
    created = []

    class Dialog:
        def __init__(self, master):
            self.master = master
            self.bound = None
            self.closed = False
            created.append(self)
        def bind(self, sequence, callback, add=None): self.bound = callback
        def winfo_exists(self): return not self.closed
        def destroy(self):
            self.closed = True
            clear_about_reference(self)

    monkeypatch.setattr(about, "_about_dialog", None)
    monkeypatch.setattr(about, "AboutDialog", Dialog)
    first = show_about(object())
    assert AboutActions(first).close()
    second = show_about(object())
    assert second is not first and len(created) == 2


def test_light_and_system_light_share_complete_semantic_surfaces():
    assert palette_for("system", "light") is LIGHT
    assert palette_for("system", "dark") is DARK
    assert {
        "Toolbar.TFrame", "Primary.Toolbar.TButton", "Danger.TButton",
        "Success.BottomBar.TLabel", "Info.BottomBar.TLabel",
        "Warning.BottomBar.TLabel", "Error.BottomBar.TLabel",
    } <= set(SEMANTIC_STYLES)
    for palette in (LIGHT, DARK):
        assert len({palette.success, palette.focus, palette.warning, palette.error, palette.surface}) == 5


def test_status_messages_select_restrained_semantic_roles():
    assert status_style_for_message("Part code copied to clipboard.") == "Success.BottomBar.TLabel"
    assert status_style_for_message("Downloading inventory…") == "Info.BottomBar.TLabel"
    assert status_style_for_message("No match found") == "Warning.BottomBar.TLabel"
    assert status_style_for_message("Download failed") == "Error.BottomBar.TLabel"


def test_declared_dialog_sizes_allow_wrapped_content():
    assert ABOUT_MIN_SIZE >= (540, 390)
    assert SETTINGS_MIN_SIZE >= (720, 600)
    assert SETTINGS_DEFAULT_SIZE[0] >= SETTINGS_MIN_SIZE[0]
    assert SETTINGS_DEFAULT_SIZE[1] >= SETTINGS_MIN_SIZE[1]
