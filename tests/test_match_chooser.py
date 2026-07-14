from __future__ import annotations

from lego_element_lookup.downloader import DownloadCancelled, DownloadError
from lego_element_lookup.gui import main_window
from lego_element_lookup.gui.main_window import MainWindow
from lego_element_lookup.lookup import Match


class FakeSelector:
    def __init__(self):
        self.values = None
        self.focused = False

    def configure(self, **kwargs):
        self.values = kwargs.get("values", self.values)

    def grid(self, **kwargs):
        self.gridded = True

    def grid_forget(self):
        self.gridded = False

    def focus_set(self):
        self.focused = True

    def current(self):
        return 1


class FakeString:
    def set(self, value):
        self.value = value


def match(code, colour, quantity=1, spares=0):
    return Match(code, "154", "Part " + code, colour, quantity=quantity, spare_quantity=spares)


def test_multiple_matches_do_not_select_or_copy_until_user_choice():
    window = object.__new__(MainWindow)
    selected = []
    window.service = type("Service", (), {"lookup": lambda self, value: [match("a", "Red"), match("b", "Blue", 2, 1)]})()
    window.element_var = type("Element", (), {"get": lambda self: "123"})()
    window.match_selector = FakeSelector()
    window.match_choice = FakeString()
    window.copy_button = type("Button", (), {"configure": lambda self, **kwargs: setattr(self, "state", kwargs["state"])})()
    window.message = FakeString()
    window.current_match = match("old", "Grey")
    window.current_candidate_id = window.current_match.candidate_id
    window._focus_input = lambda: selected.append("focus")
    window._select_match = lambda value, auto_copy: selected.append((value.part_code, auto_copy))
    window.scroll_area = type("ScrollArea", (), {"ensure_visible": lambda self, widget: None})()
    window.after_idle = lambda callback: callback()
    window._lookup()
    assert selected == []
    assert window.copy_button.state == "disabled"
    assert window.match_selector.focused is True
    assert "a — Red" in window.match_selector.values[0]


def test_single_match_preserves_direct_auto_copy_and_stale_callbacks_are_ignored():
    window = object.__new__(MainWindow)
    candidate = match("a", "Red")
    window.service = type("Service", (), {"lookup": lambda self, value: [candidate]})()
    window.element_var = type("Element", (), {"get": lambda self: "123"})()
    window.match_selector = FakeSelector()
    window.match_choice = FakeString()
    window._select_match = lambda value, auto_copy: setattr(window, "selected", (value, auto_copy))
    window._lookup()
    assert window.selected == (candidate, True)

    window.selection_token = 2
    window.current_candidate_id = candidate.candidate_id
    window.result = type("Result", (), {"show_preview": lambda self, path: setattr(self, "path", path)})()
    MainWindow._preview_loaded(window, candidate, 1, "stale.png")
    assert not hasattr(window.result, "path")
    MainWindow._preview_loaded(window, candidate, 2, "current.png")
    assert window.result.path == "current.png"


class ImmediateTask:
    def __init__(self, owner, work, success, error, progress=None):
        self.work, self.success, self.error = work, success, error
    def report(self, value):
        pass
    def start(self):
        try:
            self.success(self.work())
        except Exception as exc:
            self.error(exc)


def test_typed_new_set_downloads_before_activation(monkeypatch):
    events = []
    class Service:
        settings = type("Settings", (), {"default_set": "76344-1"})()
        def download(self, set_num, progress): events.append(("download", set_num)); return 12
        def change_set(self, set_num): self.settings.default_set = set_num; events.append(("activate", set_num)); return True
        def load_inventory(self, force): events.append(("load", force))
    window = object.__new__(MainWindow); window.service = Service(); window.message = FakeString(); window.task = None
    window._refresh_set_header = lambda: events.append(("header", "refresh"))
    monkeypatch.setattr(main_window, "BackgroundTask", ImmediateTask)
    window._download_new_set("10305-1")
    assert events[0] == ("download", "10305-1")
    assert ("activate", "10305-1") in events
    assert window.service.settings.default_set == "10305-1"


def test_failed_or_cancelled_new_set_preserves_active_set(monkeypatch):
    monkeypatch.setattr(main_window.messagebox, "showerror", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "BackgroundTask", ImmediateTask)
    for failure in (DownloadError("network failure"), DownloadCancelled("Download cancelled.")):
        class Service:
            settings = type("Settings", (), {"default_set": "76344-1"})()
            def download(self, set_num, progress): raise failure
            def change_set(self, set_num): raise AssertionError("failed download must not activate")
        window = object.__new__(MainWindow); window.service = Service(); window.message = FakeString(); window.task = None
        window._download_new_set("10305-1")
        assert window.service.settings.default_set == "76344-1"
