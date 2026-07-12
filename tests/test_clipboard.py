import subprocess

from lego_element_lookup import clipboard


def test_clipboard_commands_by_operating_system():
    none = lambda _name: None
    assert clipboard.clipboard_command("darwin", none) == ["pbcopy"]
    assert clipboard.clipboard_command("win32", none) == ["clip"]
    assert clipboard.clipboard_command("linux", lambda name: f"/bin/{name}" if name == "wl-copy" else None) == ["wl-copy"]
    assert clipboard.clipboard_command("linux", lambda name: f"/bin/{name}" if name == "xclip" else None) == ["xclip", "-selection", "clipboard"]
    assert clipboard.clipboard_command("linux", none) is None


def test_clipboard_failure_is_friendly(monkeypatch):
    monkeypatch.setattr(clipboard, "clipboard_command", lambda platform=None: ["pbcopy"])
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("no clipboard")))
    success, message = clipboard.copy("35480")
    assert success is False
    assert "Could not copy" in message
