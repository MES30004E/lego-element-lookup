"""Small platform-native clipboard adapter."""

from __future__ import annotations

import shutil
import subprocess
import sys
from typing import Callable


def clipboard_command(platform: str | None = None, which: Callable[[str], str | None] = shutil.which) -> list[str] | None:
    system = sys.platform if platform is None else platform
    if system == "darwin":
        return ["pbcopy"]
    if system == "win32":
        return ["clip"]
    for command in ("wl-copy", "xclip", "xsel"):
        if which(command):
            if command == "xclip":
                return ["xclip", "-selection", "clipboard"]
            if command == "xsel":
                return ["xsel", "--clipboard", "--input"]
            return [command]
    return None


def copy(text: str, platform: str | None = None) -> tuple[bool, str]:
    command = clipboard_command(platform)
    if command is None:
        return False, "Clipboard unavailable. On Linux, install wl-clipboard, xclip, or xsel."
    try:
        subprocess.run(command, input=text, text=True, check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError):
        return False, "Could not copy the part code to the clipboard."
    return True, "Part code copied to clipboard."
