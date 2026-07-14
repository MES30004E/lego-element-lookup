"""About and safe manual update-link support."""
from __future__ import annotations

import platform
import sys
import tkinter as tk
import webbrowser
from tkinter import ttk

from .. import __version__

PROJECT_URL = "https://github.com/MES30004E/lego-element-lookup"
RELEASES_URL = f"{PROJECT_URL}/releases"
SECURITY_URL = f"{PROJECT_URL}/security"
LICENCE_NAME = "MIT License"
ABOUT_MIN_SIZE = (540, 390)
_about_dialog = None


def diagnostics_text() -> str:
    """Return useful runtime facts without secrets, headers, paths, or cache content."""
    return "\n".join((
        f"LEGO Element Lookup {__version__}",
        f"Python {platform.python_version()}",
        f"Runtime: {platform.python_implementation()}",
        f"Platform: {sys.platform}",
        f"Architecture: {platform.machine() or 'unknown'}",
    ))


def open_trusted_url(url: str, opener=webbrowser.open) -> bool:
    if url not in {PROJECT_URL, RELEASES_URL, SECURITY_URL}:
        raise ValueError("The requested link is not trusted.")
    try:
        return bool(opener(url, new=2))
    except Exception:
        return False


def check_for_updates(opener=webbrowser.open) -> bool:
    """Open Releases only; this function never downloads or replaces files."""
    return open_trusted_url(RELEASES_URL, opener)


def copy_diagnostics(target, text: str | None = None) -> bool:
    """Copy redacted diagnostics using Tk's cross-platform clipboard."""
    try:
        target.clipboard_clear()
        target.clipboard_append(diagnostics_text() if text is None else text)
        target.update_idletasks()
        return True
    except tk.TclError:
        return False


def close_dialog(dialog) -> bool:
    try:
        dialog.destroy()
        return True
    except tk.TclError:
        return False


def clear_about_reference(dialog) -> None:
    global _about_dialog
    if _about_dialog is dialog:
        _about_dialog = None


class AboutActions:
    """Retained, testable callbacks bound directly to About buttons."""

    def __init__(self, view, opener=None) -> None:
        self.view = view
        self.opener = opener

    def _open(self, url: str, title: str) -> bool:
        opened = open_trusted_url(url, self.opener or webbrowser.open)
        if opened:
            self.view.set_feedback(f"Opened {title.lower()} in your browser.", "success")
        else:
            self.view.set_feedback(f"Could not open the browser. Visit {url}", "error")
        return opened

    def repository(self) -> bool:
        return self._open(PROJECT_URL, "Project repository")

    def security(self) -> bool:
        return self._open(SECURITY_URL, "Security & support")

    def updates(self) -> bool:
        return self._open(RELEASES_URL, "Releases")

    def copy(self) -> bool:
        copied = copy_diagnostics(self.view)
        self.view.set_feedback(
            "Diagnostics copied to clipboard." if copied else "Diagnostics could not be copied to the clipboard.",
            "success" if copied else "error",
        )
        return copied

    def close(self) -> bool:
        return close_dialog(self.view)


def show_about(master):
    """Open or focus the application's single About window."""
    global _about_dialog
    try:
        if _about_dialog is not None and _about_dialog.winfo_exists():
            _about_dialog.deiconify()
            _about_dialog.lift()
            _about_dialog.focus_force()
            return _about_dialog
    except tk.TclError:
        _about_dialog = None
    dialog = AboutDialog(master)
    _about_dialog = dialog

    def cleared(event) -> None:
        if event.widget is dialog:
            clear_about_reference(dialog)

    dialog.bind("<Destroy>", cleared, add="+")
    return dialog


class AboutDialog(tk.Toplevel):
    def __init__(self, master) -> None:
        super().__init__(master)
        self.title("About LEGO Element Lookup")
        self.resizable(True, True)
        self.minsize(*ABOUT_MIN_SIZE)
        self.geometry(f"{ABOUT_MIN_SIZE[0]}x{ABOUT_MIN_SIZE[1]}")
        self.transient(master)
        self._previous_grab = self.grab_current()
        self._destroying = False
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        content = ttk.Frame(self, padding=22, style="Surface.TFrame")
        content.grid(sticky="nsew")
        content.columnconfigure(0, weight=1)
        ttk.Label(content, text="LEGO Element Lookup", style="Title.TLabel").grid(sticky="w")
        ttk.Label(content, text=f"Installed version {__version__}", style="Muted.TLabel").grid(sticky="w", pady=(4, 16))
        ttk.Label(
            content,
            text="Offline LEGO element lookup for downloaded set inventories.",
            wraplength=480,
            justify="left",
            style="Surface.TLabel",
        ).grid(sticky="ew", pady=(0, 14))
        links = ttk.Frame(content, style="Surface.TFrame")
        links.grid(sticky="ew")
        self.actions = AboutActions(self)
        self.repository_button = ttk.Button(links, text="Project repository", command=self.actions.repository)
        self.repository_button.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        self.security_button = ttk.Button(links, text="Security & support", command=self.actions.security)
        self.security_button.grid(row=0, column=1, sticky="ew")
        links.columnconfigure(0, weight=1)
        links.columnconfigure(1, weight=1)
        ttk.Label(content, text=LICENCE_NAME, style="Surface.TLabel").grid(sticky="w", pady=(14, 10))
        self.diagnostics_visible = tk.BooleanVar(value=False)
        ttk.Checkbutton(content, text="Show diagnostics", variable=self.diagnostics_visible, command=self._toggle, style="Surface.TCheckbutton").grid(sticky="w")
        self.diagnostics = ttk.Label(
            content,
            text=diagnostics_text(),
            justify="left",
            anchor="nw",
            wraplength=480,
            padding=8,
            style="Diagnostics.TLabel",
        )
        actions = ttk.Frame(content, style="Surface.TFrame")
        actions.grid(sticky="ew", pady=(18, 0))
        self.update_button = ttk.Button(actions, text="Check for updates", command=self.actions.updates)
        self.update_button.grid(row=0, column=0, padx=(0, 8))
        self.copy_button = ttk.Button(actions, text="Copy diagnostics", command=self.actions.copy)
        self.copy_button.grid(row=0, column=1)
        self.close_button = ttk.Button(actions, text="Close", command=self.actions.close)
        self.close_button.grid(row=0, column=3, sticky="e")
        actions.columnconfigure(2, weight=1)
        self.feedback = tk.StringVar(value="")
        self.feedback_label = ttk.Label(content, textvariable=self.feedback, wraplength=480, style="Muted.TLabel")
        self.feedback_label.grid(sticky="ew", pady=(10, 0))
        self.protocol("WM_DELETE_WINDOW", self.actions.close)
        self.grab_set()
        self.focus_set()

    def _toggle(self) -> None:
        if self.diagnostics_visible.get():
            self.diagnostics.grid(sticky="ew", pady=(8, 0))
            self.minsize(ABOUT_MIN_SIZE[0], 500)
            if self.winfo_height() < 500:
                self.geometry(f"{max(self.winfo_width(), ABOUT_MIN_SIZE[0])}x500")
        else:
            self.diagnostics.grid_remove()
            self.minsize(*ABOUT_MIN_SIZE)

    def set_feedback(self, message: str, role: str) -> None:
        self.feedback.set(message)
        self.feedback_label.configure(style="Success.Surface.TLabel" if role == "success" else "Error.Surface.TLabel")

    def destroy(self) -> None:
        if self._destroying:
            return
        self._destroying = True
        previous = self._previous_grab
        try:
            if self.grab_current() is self:
                self.grab_release()
        except tk.TclError:
            pass
        clear_about_reference(self)
        super().destroy()
        try:
            if previous is not None and previous.winfo_exists():
                previous.grab_set()
        except tk.TclError:
            pass
