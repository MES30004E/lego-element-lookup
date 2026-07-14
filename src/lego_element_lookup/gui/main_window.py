"""Main desktop lookup window."""

from __future__ import annotations

import tkinter as tk
import sys
from pathlib import Path
from tkinter import messagebox, ttk

from PIL import Image, ImageTk, UnidentifiedImageError

from .. import __version__
from ..clipboard import copy
from ..downloader import DownloadCancelled
from ..lookup import Match
from ..relationship_cache import RelationshipCacheState
from ..set_metadata import SetMetadataError
from ..services import ApplicationService, ValidationError
from .set_chooser import SetChooser
from .set_manager import DownloadedSetManager
from .settings_window import SettingsDialog
from .tasks import BackgroundTask
from .widgets import ResultCard
from .responsive import DebouncedBreakpointController, LayoutMode, layout_mode_for_width
from .scrollable import VerticalScrollFrame
from .window_layout import normalise_layout_preset

HEADER_GRID_ROW = 0
DATA_GRID_ROW = 1
FOOTER_GRID_ROW = 2
TOOLBAR_HEADER_ROW = 1
INPUT_HEADER_ROW = 4
CONTENT_GRID_ROW = DATA_GRID_ROW
RESULT_GRID_ROW = 1
BOTTOM_BAR_STICKY = "ew"
MAIN_WINDOW_PADDING = 0
MAIN_WINDOW_MIN_SIZE = (640, 560)
HEADER_THUMBNAIL_SIZES = {
    LayoutMode.WIDE: (72, 48),
    LayoutMode.MEDIUM: (64, 42),
    LayoutMode.NARROW: (52, 36),
}

COMMANDS = ("Lookup", "Change Set", "Update Inventory", "Open Cache", "Settings")


def commands_for_mode(mode: LayoutMode) -> tuple[str, ...]:
    """Return visible command names; narrow mode exposes Cache via overflow."""
    return COMMANDS if mode is not LayoutMode.NARROW else ("Lookup", "Change Set", "Update Inventory", "Settings", "Overflow")

def action_row_columns(width: int) -> int:
    """Return the number of compact command controls visible in one row."""
    return 5


def version_footer_text() -> str:
    return f"v{__version__}"


def status_style_for_message(message: str) -> str:
    value = message.lower()
    if any(word in value for word in ("failed", "error", "invalid", "unavailable", "could not", "was not changed")):
        return "Error.BottomBar.TLabel"
    if any(word in value for word in ("no match", "stale", "warning")):
        return "Warning.BottomBar.TLabel"
    if any(word in value for word in ("copied", "updated", "downloaded", "loaded", "saved", "set changed")):
        return "Success.BottomBar.TLabel"
    if any(word in value for word in ("downloading", "updating", "loading", "matches found")):
        return "Info.BottomBar.TLabel"
    return "BottomBar.TLabel"


class SemanticStatusVar(tk.StringVar):
    def __init__(self, master, value: str) -> None:
        super().__init__(master=master, value=value)
        self.label = None

    def bind_label(self, label) -> None:
        self.label = label
        label.configure(style=status_style_for_message(self.get()))

    def set(self, value) -> None:
        super().set(value)
        if self.label is not None:
            self.label.configure(style=status_style_for_message(str(value)))


class MainWindow(ttk.Frame):
    def __init__(self, master, service: ApplicationService, on_layout_preset=None, on_layout_selected=None) -> None:
        super().__init__(master)
        self.service = service
        self.on_layout_preset = on_layout_preset
        self.on_layout_selected = on_layout_selected
        self._applied_layout_preset = service.settings.preferences.window_layout_preset
        self.current_match: Match | None = None
        self.current_candidate_id = None
        self.matches: list[Match] = []
        self.selection_token = 0
        self.set_preview_token = 0
        self.task = None
        self.preview_task = None
        self.relationship_task = None
        self.set_preview_task = None
        self._set_image: ImageTk.PhotoImage | None = None
        self._set_source_image: Image.Image | None = None
        self._set_preview_path = None
        self._set_image_variants: dict[tuple[int, int], ImageTk.PhotoImage] = {}
        self._identity_image: ImageTk.PhotoImage | None = None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(DATA_GRID_ROW, weight=1)

        self.header = ttk.Frame(self, padding=(20, 14, 20, 10), style="AppHeader.TFrame")
        self.header.grid(row=HEADER_GRID_ROW, column=0, sticky="ew")
        self.header.columnconfigure(0, weight=1)

        self.identity_row = ttk.Frame(self.header, style="AppHeader.TFrame")
        self.identity_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.identity_icon = ttk.Label(self.identity_row, style="AppHeader.TLabel")
        self.identity_icon.pack(side="left", padx=(0, 8))
        self.heading = ttk.Label(self.identity_row, text="LEGO Element Lookup", style="Identity.TLabel")
        self.heading.pack(side="left")
        self._load_identity_icon()

        self.command_bar = ttk.Frame(self.header, padding=(0, 2), style="CommandBar.TFrame")
        self.command_bar.grid(row=TOOLBAR_HEADER_ROW, column=0, sticky="ew", pady=(0, 8))
        self.command_buttons = {
            "Lookup": ttk.Button(self.command_bar, text="Lookup", command=self._focus_input, style="CommandButton.TButton"),
            "Change Set": ttk.Button(self.command_bar, text="Change Set", command=self._change_set, style="CommandButton.TButton"),
            "Update Inventory": ttk.Button(self.command_bar, text="Update Inventory", command=self._update, style="Primary.CommandButton.TButton"),
            "Open Cache": ttk.Button(self.command_bar, text="Open Cache", command=self._open_cache, style="CommandButton.TButton"),
            "Settings": ttk.Button(self.command_bar, text="Settings", command=self._settings, style="CommandButton.TButton"),
        }
        self.command_separators = (
            ttk.Separator(self.command_bar, orient="vertical", style="CommandSeparator.TSeparator"),
            ttk.Separator(self.command_bar, orient="vertical", style="CommandSeparator.TSeparator"),
        )
        self.layout_separator = ttk.Separator(self.command_bar, orient="vertical", style="CommandSeparator.TSeparator")
        self.layout_var = tk.StringVar(value=service.settings.preferences.window_layout_preset.title())
        self.layout_button = ttk.Menubutton(self.command_bar, text="Layout", style="CommandOverflow.TMenubutton")
        self.layout_menu = tk.Menu(self.layout_button, tearoff=False)
        for preset in ("auto", "wide", "tall", "compact"):
            self.layout_menu.add_radiobutton(
                label=preset.title(),
                value=preset.title(),
                variable=self.layout_var,
                command=lambda value=preset: self._select_layout(value),
            )
        self.layout_button.configure(menu=self.layout_menu)
        self.overflow_button = ttk.Menubutton(self.command_bar, text="⋯", style="CommandOverflow.TMenubutton")
        self.overflow_menu = tk.Menu(self.overflow_button, tearoff=False)
        self.overflow_menu.add_command(label="Open Cache Folder", command=self._open_cache)
        self.overflow_menu.add_separator()
        self.overflow_layout_menu = tk.Menu(self.overflow_menu, tearoff=False)
        for preset in ("auto", "wide", "tall", "compact"):
            self.overflow_layout_menu.add_radiobutton(
                label=preset.title(),
                value=preset.title(),
                variable=self.layout_var,
                command=lambda value=preset: self._select_layout(value),
            )
        self.overflow_menu.add_cascade(label="Layout", menu=self.overflow_layout_menu)
        self.overflow_button.configure(menu=self.overflow_menu)

        self.set_row = ttk.Frame(self.header, padding=(7, 5), style="CurrentSet.TFrame", cursor="hand2")
        self.set_row.grid(row=2, column=0, sticky="ew", pady=(0, 9))
        self.set_row.columnconfigure(1, weight=1)
        self.set_preview = ttk.Label(self.set_row, text="No set preview", width=11, anchor="center", style="CurrentSet.TLabel", cursor="hand2")
        self.set_label = ttk.Label(
            self.set_row,
            text=f"{service.settings.default_set}",
            justify="left",
            anchor="w",
            wraplength=720,
            style="CurrentSet.TLabel",
            cursor="hand2",
        )
        for widget in (self.set_row, self.set_preview, self.set_label):
            widget.bind("<Button-1>", lambda _event: self._change_set(), add="+")

        self.input_area = ttk.Frame(self.header, style="AppHeader.TFrame")
        self.input_area.grid(row=3, column=0, sticky="ew")
        self.input_area.columnconfigure(0, weight=1)
        ttk.Label(self.input_area, text="Element ID", style="AppHeader.TLabel").grid(row=0, column=0, sticky="w")
        self.element_var = tk.StringVar()
        self.element_entry = ttk.Entry(self.input_area, textvariable=self.element_var, font=("TkDefaultFont", 18))
        self.element_entry.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.element_entry.bind("<Return>", self._lookup)
        self.element_entry.bind("<FocusIn>", self._lookup_focus_changed, add="+")
        self.element_entry.bind("<FocusOut>", self._lookup_focus_changed, add="+")

        self.scroll_area = VerticalScrollFrame(self)
        self.scroll_area.grid(row=DATA_GRID_ROW, column=0, sticky="nsew")
        self.scroll_area.inner.columnconfigure(0, weight=1)
        self.content = ttk.Frame(self.scroll_area.inner, padding=(20, 4, 20, 8))
        self.content.grid(row=0, column=0, sticky="nsew")
        self.content.columnconfigure(0, weight=1)
        self.match_choice = tk.StringVar()
        self.match_selector = ttk.Combobox(self.content, textvariable=self.match_choice, state="readonly")
        self.match_selector.bind("<<ComboboxSelected>>", self._match_selected)
        self.message = SemanticStatusVar(self, "Ready — enter an element ID and press Enter.")
        self.result = ResultCard(self.content, copy_command=self._copy)
        self.result.grid(row=RESULT_GRID_ROW, column=0, sticky="nsew")
        self.copy_button = self.result.copy_button
        self.bottom_bar = ttk.Frame(self, style="BottomBar.TFrame")
        self.bottom_bar.grid(row=FOOTER_GRID_ROW, column=0, sticky=BOTTOM_BAR_STICKY)
        self.bottom_bar.columnconfigure(0, weight=1)
        ttk.Separator(self.bottom_bar, orient="horizontal").grid(row=0, column=0, columnspan=2, sticky="ew")
        self.status_label = ttk.Label(
            self.bottom_bar,
            textvariable=self.message,
            anchor="w",
            justify="left",
            wraplength=700,
            style="BottomBar.TLabel",
        )
        self.status_label.grid(row=1, column=0, sticky="ew")
        self.message.bind_label(self.status_label)
        self.version_label = ttk.Label(self.bottom_bar, text=version_footer_text(), anchor="e", style="BottomBar.TLabel")
        self.version_label.grid(row=1, column=1, sticky="e")
        # The first responsive pass references header, result, toolbar, and footer
        # widgets, so it must start only after the complete shell exists.
        self._responsive = DebouncedBreakpointController(self, self._apply_responsive_layout)
        self._responsive.apply_now(820)
        self.bind("<Configure>", self._resize_actions, add="+")
        self.element_entry.focus_set()
        self._refresh_set_header()

    def _load_identity_icon(self) -> None:
        """Decode the existing app icon once and retain the Tk image in memory."""
        roots = [Path(getattr(sys, "_MEIPASS", ""))] if getattr(sys, "_MEIPASS", None) else []
        roots.append(Path(__file__).resolve().parents[3])
        for root in roots:
            candidate = root / "assets" / "icon.png"
            try:
                with Image.open(candidate) as source:
                    image = source.convert("RGBA")
                image.thumbnail((28, 28), Image.Resampling.LANCZOS)
                self._identity_image = ImageTk.PhotoImage(image)
                self.identity_icon.configure(image=self._identity_image)
                return
            except (OSError, UnidentifiedImageError):
                continue
        self.identity_icon.configure(text="")

    def _resize_actions(self, event) -> None:
        if event.widget is self:
            self._responsive.request(event.width)

    def _lookup_focus_changed(self, _event=None) -> None:
        active = self.focus_get() is self.element_entry
        self.command_buttons["Lookup"].configure(
            style="Active.CommandButton.TButton" if active else "CommandButton.TButton"
        )

    def _apply_responsive_layout(self, mode: LayoutMode) -> None:
        self.scroll_area.preserve_position()
        padding = {
            LayoutMode.WIDE: (20, 14, 20, 0),
            LayoutMode.MEDIUM: (14, 12, 14, 0),
            LayoutMode.NARROW: (10, 10, 10, 0),
        }[mode]
        self.header.configure(padding=(padding[0], padding[1], padding[2], 8))
        self.content.configure(padding=(padding[0], 4, padding[2], 8))
        self.status_label.configure(wraplength={LayoutMode.WIDE: 1080, LayoutMode.MEDIUM: 700, LayoutMode.NARROW: 500}[mode])
        self.set_preview.configure(width={LayoutMode.WIDE: 11, LayoutMode.MEDIUM: 10, LayoutMode.NARROW: 8}[mode])
        self.set_preview.grid_forget()
        self.set_label.grid_forget()
        if mode is LayoutMode.NARROW:
            self.set_row.columnconfigure(0, weight=1)
            self.set_row.columnconfigure(1, weight=0)
            self.set_preview.grid(row=0, column=0, sticky="w")
            self.set_label.grid(row=1, column=0, sticky="ew", pady=(4, 0))
            self.set_label.configure(wraplength=560)
        else:
            self.set_row.columnconfigure(0, weight=0)
            self.set_row.columnconfigure(1, weight=1)
            self.set_preview.grid(row=0, column=0, sticky="w", padx=(0, 10))
            self.set_label.grid(row=0, column=1, sticky="ew")
            self.set_label.configure(wraplength=820 if mode is LayoutMode.WIDE else 620)
        self.set_row.grid_configure(pady=(0, 9))
        self.element_entry.grid_configure(pady=(4, 0))
        self.result.set_layout(mode)
        self._layout_commands(mode)
        self._render_set_preview()

    def _layout_commands(self, mode: LayoutMode) -> None:
        for widget in (
            *self.command_buttons.values(),
            *self.command_separators,
            self.layout_separator,
            self.layout_button,
            self.overflow_button,
        ):
            widget.grid_forget()
        visible = tuple(name for name in commands_for_mode(mode) if name != "Overflow")
        gap = 6 if mode is LayoutMode.WIDE else 3
        column = 0
        for index, name in enumerate(visible):
            self.command_buttons[name].grid(row=0, column=column, sticky="w", padx=(0, gap))
            column += 1
            group_break = name in {"Change Set", "Open Cache"}
            if mode is LayoutMode.NARROW:
                group_break = name in {"Change Set", "Update Inventory"}
            if group_break:
                separator = self.command_separators[0 if name == "Change Set" else 1]
                separator.grid(row=0, column=column, sticky="ns", padx=(3, 6))
                column += 1
        if mode is LayoutMode.NARROW:
            self.overflow_button.grid(row=0, column=column, sticky="w")
        else:
            self.layout_separator.grid(row=0, column=column, sticky="ns", padx=(3, 6))
            self.layout_button.grid(row=0, column=column + 1, sticky="w")

    def _select_layout(self, preset: str) -> None:
        selected = normalise_layout_preset(preset)
        self.layout_var.set(selected.title())
        if self.on_layout_selected:
            self.on_layout_selected(selected)
        self._applied_layout_preset = selected

    def set_layout_preset(self, preset: str) -> None:
        """Synchronise the compact Layout control after Settings/menu changes."""
        self.layout_var.set(normalise_layout_preset(preset).title())

    def _lookup(self, _event=None) -> None:
        try:
            matches = self.service.lookup(self.element_var.get())
        except Exception as exc:
            self.message.set(str(exc))
            self._focus_input()
            return
        if not matches:
            self.message.set(f"No match found in set {self.service.settings.default_set}.")
            self._focus_input()
            return
        self.matches = matches
        if len(matches) == 1:
            self.match_selector.grid_forget()
            self._select_match(matches[0], auto_copy=True)
            return
        self.current_match = None
        self.current_candidate_id = None
        self.copy_button.configure(state="disabled")
        self.match_selector.configure(values=[self._candidate_label(match) for match in matches])
        self.match_choice.set("")
        self.match_selector.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.message.set(f"{len(matches)} matches found — choose a part.")
        self.match_selector.focus_set()
        self.after_idle(lambda: self.scroll_area.ensure_visible(self.match_selector))

    @staticmethod
    def _candidate_label(match: Match) -> str:
        quantities = [f"quantity {match.quantity}"] if match.quantity else []
        if match.spare_quantity:
            quantities.append(f"spares {match.spare_quantity}")
        return f"{match.part_code} — {match.colour_name} — {', '.join(quantities) or 'quantity unknown'}"

    def _match_selected(self, _event=None) -> None:
        index = self.match_selector.current()
        if 0 <= index < len(self.matches):
            self._select_match(self.matches[index], auto_copy=True)

    def _select_match(self, match: Match, *, auto_copy: bool) -> None:
        self.selection_token += 1
        self.current_match = match
        self.current_candidate_id = match.candidate_id
        self.result.show_match(match, self.service.settings.preferences)
        self._load_preview(match, self.selection_token)
        self._show_related_designs(match)
        self.copy_button.configure(state="normal")
        self.after_idle(lambda: self.scroll_area.ensure_visible(self.result))
        if auto_copy and self.service.settings.preferences.auto_copy:
            self._copy()
        if self.service.settings.preferences.refocus_input:
            self._focus_input()

    def _load_preview(self, match: Match, token: int) -> None:
        cached = self.service.cached_preview(match)
        if cached:
            self.result.show_preview(cached)
            return
        prefs = self.service.settings.preferences
        if not prefs.previews_enabled:
            self.result.show_preview_status("Preview disabled in Settings")
            return
        if not match.part_img_url:
            self.result.show_preview_status("No preview available")
            return
        if not prefs.auto_download_previews:
            self.result.show_preview_status("Preview not cached")
            return
        self.result.show_preview_status("Loading preview…")
        requested_match = match
        self.preview_task = BackgroundTask(
            self,
            lambda: self.service.fetch_preview(requested_match),
            lambda path: self._preview_loaded(requested_match, token, path),
            lambda error: self._preview_failed(requested_match, token, error),
        )
        self.preview_task.start()

    def _preview_loaded(self, match: Match, token: int, path) -> None:
        if token == self.selection_token and self.current_candidate_id == match.candidate_id:
            self.result.show_preview(path)

    def _preview_failed(self, match: Match, token: int, error: Exception) -> None:
        if token == self.selection_token and self.current_candidate_id == match.candidate_id:
            self.result.show_preview_status(str(error) or "No preview available")

    def _show_related_designs(self, match: Match) -> None:
        cache = self.service.relationship_cache_state()
        if cache.index:
            self.result.show_related_designs(
                cache.index.related_designs(match.part_code),
                self._copy_related_design,
                stale=cache.state is RelationshipCacheState.STALE,
                refresh=self._refresh_relationship_data,
            )
        else:
            self.result.show_relationship_cache_state(cache.state, self._refresh_relationship_data)

    def _copy_related_design(self, code: str) -> None:
        try:
            self.clipboard_clear()
            self.clipboard_append(code)
            self.update_idletasks()
            self.message.set(f"Design code {code} copied to clipboard.")
        except tk.TclError:
            success, message = copy(code)
            self.message.set(message if success else message)

    def _refresh_relationship_data(self) -> None:
        self.message.set("Downloading related-design data…")

        def progress(page, count):
            if self.relationship_task:
                self.relationship_task.report((page, count))

        self.relationship_task = BackgroundTask(
            self,
            lambda: self.service.refresh_relationship_data(
                progress=progress,
                cancelled=lambda: bool(self.relationship_task and self.relationship_task.cancelled.is_set()),
            ),
            self._relationship_downloaded,
            self._relationship_failed,
            lambda value: self.message.set("Downloading related-design data…" if value[0] == 0 else "Related-design data updated."),
        )
        self.relationship_task.start()

    def _relationship_downloaded(self, _metadata) -> None:
        self.message.set("Related-design data updated.")
        if self.current_match:
            self._show_related_designs(self.current_match)

    def _relationship_failed(self, error: Exception) -> None:
        self.message.set(str(error) or "Related-design data is unavailable offline.")
        if self.current_match:
            self._show_related_designs(self.current_match)

    def _copy(self) -> None:
        if not self.current_match:
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(self.current_match.part_code)
            self.update_idletasks()
            if self.service.settings.preferences.show_copied_confirmation:
                self.message.set("Part code copied to clipboard.")
        except tk.TclError:
            success, message = copy(self.current_match.part_code)
            self.message.set(message)

    def _focus_input(self) -> None:
        self.element_entry.focus_set()
        self.element_entry.selection_range(0, tk.END)

    def _change_set(self) -> None:
        SetChooser(
            self,
            self.service.downloaded_sets(),
            self.service.settings.default_set,
            self.service.cached_set_preview,
            self._apply_set_choice,
            self._manage_downloaded_sets,
        )

    def _manage_downloaded_sets(self, refresh_chooser=None) -> None:
        def changed(removed: tuple[str, ...]) -> None:
            self._sets_removed(removed)
            if refresh_chooser:
                refresh_chooser(self.service.downloaded_sets())

        DownloadedSetManager(self, self.service, changed)

    def _sets_removed(self, removed: tuple[str, ...]) -> None:
        if removed:
            self.message.set(f"Removed downloaded set{'s' if len(removed) != 1 else ''}: {', '.join(removed)}.")
        self._refresh_set_header()

    def _apply_set_choice(self, value: str, download: bool = False) -> None:
        try:
            selected = self.service.validate_set_num(value)
        except ValidationError as exc:
            messagebox.showerror("Change set", str(exc), parent=self)
            return
        if download:
            self._download_new_set(selected)
            return
        cached = self.service.change_set(selected)
        self._refresh_set_header()
        if cached:
            self.service.load_inventory(force=True)
            self.message.set("Set changed. Cached inventory loaded.")
        elif messagebox.askyesno("Download inventory", "No cached inventory exists for this set. Download it now?", parent=self):
            self._update()

    def _download_new_set(self, set_num: str) -> None:
        self.message.set(f"Downloading set {set_num}…")

        def progress(page, count):
            if self.task:
                self.task.report((page, count))

        self.task = BackgroundTask(
            self,
            lambda: self.service.download(set_num=set_num, progress=progress),
            lambda count: self._new_set_downloaded(set_num, count),
            lambda error: self._new_set_failed(set_num, error),
            lambda value: self.message.set(f"Downloading {set_num}: page {value[0]} — {value[1]} entries…"),
        )
        self.task.start()

    def _new_set_downloaded(self, set_num: str, count: int) -> None:
        self.service.change_set(set_num)
        self.service.load_inventory(force=True)
        self._refresh_set_header()
        self.message.set(f"Set {set_num} downloaded and selected: {count} entries.")

    def _new_set_failed(self, set_num: str, error: Exception) -> None:
        if not isinstance(error, DownloadCancelled):
            messagebox.showerror("Download set", str(error), parent=self)
        self.message.set(f"Set {set_num} was not changed. {error}")

    def _update(self) -> None:
        self.message.set("Updating inventory…")

        def progress(page, count):
            if self.task:
                self.task.report((page, count))

        self.task = BackgroundTask(
            self,
            lambda: self.service.download(progress=progress),
            self._updated,
            self._update_failed,
            lambda value: self.message.set(f"Downloading page {value[0]} — {value[1]} entries…"),
        )
        self.task.start()

    def _updated(self, count: int) -> None:
        self.service.load_inventory(force=True)
        self.message.set(f"Inventory updated: {count} entries.")
        self._refresh_set_header()

    def _update_failed(self, exc: Exception) -> None:
        if not isinstance(exc, DownloadCancelled):
            messagebox.showerror("Inventory update", str(exc), parent=self)
        self.message.set(str(exc))

    def _settings(self) -> None:
        SettingsDialog(self, self.service, self._settings_saved)

    def _settings_saved(self) -> None:
        from .theme import apply_theme
        apply_theme(self.winfo_toplevel(), self.service.settings.preferences.theme, self.service.settings.preferences.density)
        self.scroll_area.refresh_colours()
        selected_preset = self.service.settings.preferences.window_layout_preset
        if self.on_layout_preset and selected_preset != self._applied_layout_preset:
            self.on_layout_preset()
        self._applied_layout_preset = selected_preset
        self._refresh_set_header()
        self.message.set("Settings saved.")

    def _open_cache(self) -> None:
        try:
            self.service.open_cache_folder()
        except Exception as exc:
            messagebox.showerror("Cache folder", str(exc), parent=self)

    def _refresh_set_header(self) -> None:
        self.set_preview_token += 1
        token = self.set_preview_token
        set_num = self.service.settings.default_set
        metadata = self.service.set_metadata(set_num)
        label = f"Set {set_num}" + (f" — {metadata.name}" if metadata else "")
        self.set_label.configure(text=label)
        cached = self.service.cached_set_preview(set_num)
        if cached:
            self._show_set_preview(cached)
            return
        self._set_image = None
        self._set_source_image = None
        self._set_preview_path = None
        self._set_image_variants.clear()
        self.set_preview.configure(image="", text="No set preview")
        if not metadata or not metadata.image_url:
            return
        self.set_preview_task = BackgroundTask(
            self,
            lambda: self.service.fetch_set_preview(set_num),
            lambda path: self._set_preview_loaded(set_num, token, path),
            lambda error: self._set_preview_failed(set_num, token, error),
        )
        self.set_preview_task.start()

    def _show_set_preview(self, path) -> None:
        try:
            resolved = Path(path).resolve()
            if resolved != self._set_preview_path or self._set_source_image is None:
                with Image.open(resolved) as source:
                    self._set_source_image = source.convert("RGBA")
                self._set_preview_path = resolved
                self._set_image_variants.clear()
        except (OSError, UnidentifiedImageError):
            self._set_image = None
            self._set_source_image = None
            self._set_preview_path = None
            self._set_image_variants.clear()
            self.set_preview.configure(image="", text="No set preview")
            return
        self._render_set_preview()

    def _render_set_preview(self) -> None:
        if self._set_source_image is None:
            return
        mode = self._responsive.current or LayoutMode.MEDIUM
        size = HEADER_THUMBNAIL_SIZES[mode]
        variant = self._set_image_variants.get(size)
        if variant is None:
            image = self._set_source_image.copy()
            image.thumbnail(size, Image.Resampling.LANCZOS)
            variant = ImageTk.PhotoImage(image)
            self._set_image_variants[size] = variant
        self._set_image = variant
        self.set_preview.configure(image=variant, text="")

    def _set_preview_loaded(self, set_num: str, token: int, path) -> None:
        if token == self.set_preview_token and set_num == self.service.settings.default_set:
            self._show_set_preview(path)

    def _set_preview_failed(self, set_num: str, token: int, _error: Exception) -> None:
        if token == self.set_preview_token and set_num == self.service.settings.default_set:
            self.set_preview.configure(image="", text="Set preview offline")

    def destroy(self) -> None:
        if hasattr(self, "_responsive"):
            self._responsive.stop()
        super().destroy()
