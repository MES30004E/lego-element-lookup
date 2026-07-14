"""Small, explicit ttk theme and density layer shared by desktop windows."""
from __future__ import annotations

from dataclasses import dataclass
import os
import queue
import subprocess
import sys
import threading
from tkinter import ttk


@dataclass(frozen=True)
class Palette:
    window: str; surface: str; surface_border: str; text: str; muted_text: str
    focus: str; selection: str; button: str; warning: str; error: str; success: str; preview_border: str


LIGHT = Palette("#EEF1F4", "#FFFFFF", "#C8CED6", "#18202A", "#586574", "#0069B4", "#DCEEFF", "#F3F5F7", "#985000", "#B42318", "#177245", "#AEB7C2")
DARK = Palette("#191C20", "#262A30", "#48505A", "#F3F5F7", "#B7C0CB", "#79BCFF", "#294D70", "#353A41", "#FFB86B", "#FF938D", "#7DDBA0", "#66717E")
SEMANTIC_STYLES = (
    "Surface.TFrame", "Surface.TLabel", "Surface.TCheckbutton", "Footer.TFrame",
    "Status.TFrame", "Status.TLabel", "Version.TLabel", "Muted.TLabel",
    "Title.TLabel", "Heading.TLabel", "BottomBar.TFrame", "BottomBar.TLabel",
    "Toolbar.TFrame", "Toolbar.TButton", "Diagnostics.TLabel",
    "Primary.Toolbar.TButton", "Danger.TButton", "Success.Surface.TLabel",
    "Info.Surface.TLabel", "Warning.Surface.TLabel", "Error.Surface.TLabel",
    "Success.BottomBar.TLabel", "Info.BottomBar.TLabel", "Warning.BottomBar.TLabel",
    "Error.BottomBar.TLabel", "AppHeader.TFrame", "AppHeader.TLabel", "Identity.TLabel",
    "CommandBar.TFrame", "Navigation.TButton", "Active.Navigation.TButton",
    "Primary.Navigation.TButton", "Navigation.TMenubutton", "CurrentSet.TFrame",
    "CurrentSet.TLabel", "ResultCard.TFrame", "Compact.TButton", "Attribution.TLabel",
    "Muted.Surface.TLabel", "CommandButton.TButton", "Active.CommandButton.TButton",
    "Primary.CommandButton.TButton", "CommandOverflow.TMenubutton", "CommandSeparator.TSeparator",
)

def detect_system_theme(
    platform: str | None = None,
    *,
    runner=subprocess.run,
    env: dict[str, str] | None = None,
) -> str:
    """Resolve the OS appearance once at launch, falling back safely to Light."""
    system = sys.platform if platform is None else platform
    values = os.environ if env is None else env
    try:
        if system == "darwin":
            result = runner(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True, text=True, timeout=2, check=False,
            )
            return "dark" if result.returncode == 0 and "dark" in result.stdout.lower() else "light"
        if system == "win32":
            import winreg
            path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
                return "light" if int(winreg.QueryValueEx(key, "AppsUseLightTheme")[0]) else "dark"
        gtk_theme = values.get("GTK_THEME", "").lower()
        if "dark" in gtk_theme:
            return "dark"
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return "light"


def system_theme() -> str:
    return detect_system_theme()

def palette_for(choice: str, system_appearance: str | None = None) -> Palette:
    resolved = system_appearance or (system_theme() if choice == "system" else "light")
    return DARK if choice == "dark" or (choice == "system" and resolved == "dark") else LIGHT

def apply_theme(root, choice: str = "system", density: str = "comfortable", *, system_appearance: str | None = None) -> Palette:
    palette = palette_for(choice, system_appearance)
    style = ttk.Style(root)
    try: style.theme_use("clam")
    except Exception: pass
    pad = 6 if density == "compact" else 10
    style.configure(".", background=palette.window, foreground=palette.text, font=("TkDefaultFont", 11))
    style.configure("TFrame", background=palette.window)
    style.configure("TLabel", background=palette.window, foreground=palette.text)
    style.configure("Surface.TFrame", background=palette.surface)
    style.configure("Surface.TLabel", background=palette.surface, foreground=palette.text)
    style.configure("Muted.Surface.TLabel", background=palette.surface, foreground=palette.muted_text)
    style.configure("Surface.TCheckbutton", background=palette.surface, foreground=palette.text)
    style.map("Surface.TCheckbutton", foreground=[("disabled", palette.muted_text)], background=[("active", palette.surface), ("disabled", palette.surface)])
    style.configure("Footer.TFrame", background=palette.surface)
    style.configure("AppHeader.TFrame", background=palette.window)
    style.configure("AppHeader.TLabel", background=palette.window, foreground=palette.text)
    style.configure("Identity.TLabel", background=palette.window, foreground=palette.text, font=("TkDefaultFont", 16, "bold"))
    style.configure("CommandBar.TFrame", background=palette.window)
    style.configure("CurrentSet.TFrame", background=palette.surface)
    style.configure("CurrentSet.TLabel", background=palette.surface, foreground=palette.text)
    style.configure("ResultCard.TFrame", background=palette.surface)
    style.configure("Attribution.TLabel", background=palette.surface, foreground=palette.focus)
    style.configure("Toolbar.TFrame", background=palette.button)
    style.configure("BottomBar.TFrame", background=palette.button)
    style.configure("BottomBar.TLabel", background=palette.button, foreground=palette.muted_text, padding=(pad, max(3, pad // 3)))
    for role, colour in (("Success", palette.success), ("Info", palette.focus), ("Warning", palette.warning), ("Error", palette.error)):
        style.configure(f"{role}.BottomBar.TLabel", background=palette.button, foreground=colour, padding=(pad, max(3, pad // 3)))
        style.configure(f"{role}.Surface.TLabel", background=palette.surface, foreground=colour)
    style.configure("Status.TFrame", background=palette.surface, borderwidth=1, relief="solid")
    style.configure("Status.TLabel", background=palette.surface, foreground=palette.muted_text, padding=(pad, max(4, pad // 2)))
    style.configure("Version.TLabel", background=palette.surface, foreground=palette.muted_text, padding=(pad, max(4, pad // 2)))
    style.configure("Muted.TLabel", background=palette.surface, foreground=palette.muted_text)
    style.configure("Title.TLabel", background=palette.surface, foreground=palette.text, font=("TkDefaultFont", 18, "bold"))
    style.configure("Heading.TLabel", background=palette.surface, foreground=palette.text, font=("TkDefaultFont", 11, "bold"))
    style.configure("Diagnostics.TLabel", background=palette.button, foreground=palette.text, bordercolor=palette.surface_border, borderwidth=1, relief="solid")
    style.configure("TLabelframe", background=palette.surface, bordercolor=palette.surface_border, borderwidth=1, relief="solid")
    style.configure("TLabelframe.Label", background=palette.surface, foreground=palette.text)
    style.configure("TButton", padding=(pad, max(3, pad // 2)), background=palette.button)
    style.configure("Toolbar.TButton", padding=(pad, max(3, pad // 2)), background=palette.button)
    style.configure("Primary.Toolbar.TButton", padding=(pad, max(3, pad // 2)), background=palette.selection, foreground=palette.text)
    style.configure("Danger.TButton", padding=(pad, max(3, pad // 2)), foreground=palette.error, background=palette.button)
    nav_pad = (10 if density == "compact" else 12, 4 if density == "compact" else 5)
    style.configure("Navigation.TButton", padding=nav_pad, background=palette.window, foreground=palette.text, borderwidth=0, relief="flat")
    style.configure("Active.Navigation.TButton", padding=nav_pad, background=palette.selection, foreground=palette.focus, borderwidth=0, relief="flat")
    style.configure("Primary.Navigation.TButton", padding=nav_pad, background=palette.selection, foreground=palette.focus, borderwidth=0, relief="flat")
    style.configure("Navigation.TMenubutton", padding=nav_pad, background=palette.window, foreground=palette.text, borderwidth=0, relief="flat")
    style.configure("Compact.TButton", padding=(8, 3), background=palette.button)
    command_pad = (7, 3) if density == "compact" else (9, 4)
    command_common = {
        "padding": command_pad,
        "borderwidth": 1,
        "relief": "raised",
        "background": palette.button,
        "foreground": palette.text,
        "bordercolor": palette.surface_border,
        "lightcolor": palette.surface_border,
        "darkcolor": palette.surface_border,
        "focusthickness": 1,
        "focuscolor": palette.focus,
    }
    style.configure("CommandButton.TButton", **command_common)
    style.configure(
        "Active.CommandButton.TButton",
        **{**command_common, "background": palette.selection, "foreground": palette.focus, "bordercolor": palette.focus},
    )
    style.configure(
        "Primary.CommandButton.TButton",
        **{**command_common, "background": palette.selection, "foreground": palette.focus, "bordercolor": palette.focus},
    )
    style.configure("CommandOverflow.TMenubutton", **command_common)
    style.configure("CommandSeparator.TSeparator", background=palette.surface_border)
    button_map = {
        "foreground": [("disabled", palette.muted_text)],
        "background": [("active", palette.selection), ("pressed", palette.selection), ("disabled", palette.button)],
        "bordercolor": [("focus", palette.focus), ("disabled", palette.surface_border)],
        "lightcolor": [("focus", palette.focus)],
        "darkcolor": [("focus", palette.focus)],
    }
    style.map("TButton", **button_map)
    style.map("Toolbar.TButton", **button_map)
    style.map("Primary.Toolbar.TButton", **button_map)
    style.map("Danger.TButton", **button_map)
    navigation_map = {
        "foreground": [("disabled", palette.muted_text), ("active", palette.text)],
        "background": [("active", palette.selection), ("pressed", palette.selection), ("disabled", palette.window)],
        "bordercolor": [("focus", palette.focus)],
    }
    style.map("Navigation.TButton", **navigation_map)
    style.map("Navigation.TMenubutton", **navigation_map)
    style.map(
        "Active.Navigation.TButton",
        foreground=[("disabled", palette.muted_text), ("active", palette.focus)],
        background=[("active", palette.selection), ("pressed", palette.selection), ("disabled", palette.window)],
        bordercolor=[("focus", palette.focus)],
    )
    style.map(
        "Primary.Navigation.TButton",
        foreground=[("disabled", palette.muted_text), ("active", palette.text)],
        background=[("active", palette.focus), ("pressed", palette.focus), ("disabled", palette.window)],
        bordercolor=[("focus", palette.focus)],
    )
    style.map("Compact.TButton", **button_map)
    command_map = {
        "foreground": [("disabled", palette.muted_text), ("active", palette.text)],
        "background": [
            ("disabled", palette.window),
            ("pressed", palette.selection),
            ("active", palette.selection),
        ],
        "bordercolor": [
            ("disabled", palette.surface_border),
            ("focus", palette.focus),
            ("active", palette.focus),
        ],
        "relief": [("pressed", "sunken"), ("active", "raised")],
    }
    style.map("CommandButton.TButton", **command_map)
    style.map("CommandOverflow.TMenubutton", **command_map)
    style.map(
        "Active.CommandButton.TButton",
        foreground=[("disabled", palette.muted_text), ("active", palette.focus)],
        background=[("disabled", palette.window), ("pressed", palette.button), ("active", palette.selection)],
        bordercolor=[("disabled", palette.surface_border), ("focus", palette.focus), ("active", palette.focus)],
        relief=[("pressed", "sunken"), ("active", "raised")],
    )
    style.map(
        "Primary.CommandButton.TButton",
        foreground=[("disabled", palette.muted_text), ("active", palette.text)],
        background=[("disabled", palette.window), ("pressed", palette.focus), ("active", palette.selection)],
        bordercolor=[("disabled", palette.surface_border), ("focus", palette.focus), ("active", palette.focus)],
        relief=[("pressed", "sunken"), ("active", "raised")],
    )
    style.configure("TCheckbutton", background=palette.window, foreground=palette.text)
    style.map("TCheckbutton", foreground=[("disabled", palette.muted_text)], background=[("active", palette.window), ("disabled", palette.window)], indicatorcolor=[("selected", palette.focus), ("disabled", palette.surface_border)])
    style.map("Surface.TCheckbutton", indicatorcolor=[("selected", palette.focus), ("disabled", palette.surface_border)], bordercolor=[("focus", palette.focus)])
    style.configure("TEntry", fieldbackground=palette.surface, foreground=palette.text, padding=pad)
    style.configure("TCombobox", fieldbackground=palette.surface, foreground=palette.text, padding=pad)
    style.configure("TNotebook", background=palette.window, bordercolor=palette.surface_border)
    style.configure("TNotebook.Tab", padding=(max(12, pad + 5), pad), background=palette.button, foreground=palette.text)
    style.map("TNotebook.Tab", background=[("selected", palette.surface), ("active", palette.selection)], foreground=[("selected", palette.text), ("disabled", palette.muted_text)], bordercolor=[("selected", palette.focus), ("focus", palette.focus)])
    style.map("TEntry", bordercolor=[("focus", palette.focus)], lightcolor=[("focus", palette.focus)])
    style.map("TCombobox", bordercolor=[("focus", palette.focus)], fieldbackground=[("readonly", palette.surface), ("disabled", palette.window)], foreground=[("readonly", palette.text), ("disabled", palette.muted_text)], arrowcolor=[("readonly", palette.text), ("disabled", palette.muted_text)])
    style.configure("TSeparator", background=palette.surface_border)
    root.option_add("*TCombobox*Listbox.background", palette.surface)
    root.option_add("*TCombobox*Listbox.foreground", palette.text)
    root.option_add("*TCombobox*Listbox.selectBackground", palette.selection)
    root.option_add("*TCombobox*Listbox.selectForeground", palette.text)
    root.configure(background=palette.window)
    return palette


class SystemThemeMonitor:
    """Bounded live System-theme monitor; detector work never runs on Tk's thread."""
    def __init__(
        self,
        owner,
        preference,
        on_change,
        *,
        detector=detect_system_theme,
        interval_ms: int = 1500,
        initial_appearance: str | None = None,
    ) -> None:
        self.owner = owner
        self.preference = preference
        self.on_change = on_change
        self.detector = detector
        self.interval_ms = interval_ms
        self.last_appearance = initial_appearance
        self._results: queue.Queue[str] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._after_id = None
        self._stopped = True

    @property
    def running(self) -> bool:
        return not self._stopped

    def start(self) -> None:
        if not self._stopped:
            return
        self._stopped = False
        self._after_id = self.owner.after(0, self._tick)

    def _tick(self) -> None:
        if self._stopped:
            return
        self._drain_results()
        if self.preference() == "system" and not (self._worker and self._worker.is_alive()):
            self._worker = threading.Thread(target=self._detect, daemon=True, name="lego-theme-monitor")
            self._worker.start()
        self._after_id = self.owner.after(self.interval_ms, self._tick)

    def _detect(self) -> None:
        try:
            value = self.detector()
        except Exception:
            value = "light"
        self._results.put(value if value in {"light", "dark"} else "light")

    def _drain_results(self) -> None:
        latest = None
        while True:
            try:
                latest = self._results.get_nowait()
            except queue.Empty:
                break
        if latest is not None:
            self._accept(latest)

    def _accept(self, appearance: str) -> None:
        if self._stopped or self.preference() != "system" or appearance == self.last_appearance:
            return
        self.last_appearance = appearance
        self.on_change(appearance)

    def stop(self) -> None:
        self._stopped = True
        if self._after_id is not None:
            try:
                self.owner.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = None
