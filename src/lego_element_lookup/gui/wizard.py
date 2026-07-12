"""First-run setup wizard."""

from __future__ import annotations

import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ..config import cache_dir
from ..services import ApplicationService, ValidationError
from .tasks import BackgroundTask


class SetupWizard(ttk.Frame):
    def __init__(self, master, service: ApplicationService, on_complete) -> None:
        super().__init__(master, padding=24)
        self.service = service
        self.on_complete = on_complete
        self.page = 0
        self.task = None
        self.api_key = tk.StringVar(value="")
        self.set_num = tk.StringVar(value=service.settings.default_set)
        self.cache_path = tk.StringVar(value=str(service.cache_directory))
        self.remember = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.pages = [self._welcome(), self._account(), self._storage(), self._download(), self._complete()]
        self.buttons = ttk.Frame(self)
        self.buttons.grid(row=1, column=0, sticky="ew", pady=(20, 0))
        self.back = ttk.Button(self.buttons, text="Back", command=self._back)
        self.back.pack(side="left")
        self.next = ttk.Button(self.buttons, text="Next", command=self._next)
        self.next.pack(side="right")
        self.cancel = ttk.Button(self.buttons, text="Cancel download", command=self._cancel_download)
        self._show_page(0)

    def _page(self) -> ttk.Frame:
        frame = ttk.Frame(self)
        frame.columnconfigure(0, weight=1)
        return frame

    def _welcome(self):
        frame = self._page()
        ttk.Label(frame, text="Welcome to LEGO Element Lookup", font=("TkDefaultFont", 18, "bold")).grid(sticky="w")
        ttk.Label(frame, text="Set up a Rebrickable account once, then look up cached LEGO parts offline.", wraplength=560).grid(sticky="w", pady=16)
        ttk.Button(frame, text="How to get a Rebrickable API key", command=lambda: webbrowser.open("https://rebrickable.com/api/" )).grid(sticky="w")
        return frame

    def _account(self):
        frame = self._page()
        ttk.Label(frame, text="Rebrickable account and set", font=("TkDefaultFont", 16, "bold")).grid(sticky="w")
        ttk.Label(frame, text="API key").grid(sticky="w", pady=(18, 4))
        entry_row = ttk.Frame(frame)
        entry_row.grid(sticky="ew")
        entry_row.columnconfigure(0, weight=1)
        self.key_entry = ttk.Entry(entry_row, textvariable=self.api_key, show="•")
        self.key_entry.grid(row=0, column=0, sticky="ew")
        ttk.Checkbutton(entry_row, text="Show", command=lambda: self.key_entry.configure(show="" if self.key_entry.cget("show") else "•")).grid(row=0, column=1, padx=8)
        ttk.Checkbutton(frame, text="Remember securely in the operating system keychain", variable=self.remember).grid(sticky="w", pady=8)
        ttk.Label(frame, text="Default LEGO set number").grid(sticky="w", pady=(12, 4))
        ttk.Entry(frame, textvariable=self.set_num).grid(sticky="ew")
        return frame

    def _storage(self):
        frame = self._page()
        ttk.Label(frame, text="Inventory storage", font=("TkDefaultFont", 16, "bold")).grid(sticky="w")
        ttk.Label(frame, text="Cache folder").grid(sticky="w", pady=(18, 4))
        row = ttk.Frame(frame)
        row.grid(sticky="ew")
        row.columnconfigure(0, weight=1)
        ttk.Entry(row, textvariable=self.cache_path).grid(row=0, column=0, sticky="ew")
        ttk.Button(row, text="Browse…", command=self._browse).grid(row=0, column=1, padx=8)
        ttk.Button(frame, text="Use default", command=lambda: self.cache_path.set(str(cache_dir()))).grid(sticky="w", pady=8)
        return frame

    def _download(self):
        frame = self._page()
        ttk.Label(frame, text="Test and download", font=("TkDefaultFont", 16, "bold")).grid(sticky="w")
        ttk.Label(frame, textvariable=self.status, wraplength=560).grid(sticky="w", pady=18)
        self.progress = ttk.Progressbar(frame, mode="indeterminate")
        self.progress.grid(sticky="ew")
        return frame

    def _complete(self):
        frame = self._page()
        ttk.Label(frame, text="Setup complete", font=("TkDefaultFont", 16, "bold")).grid(sticky="w")
        ttk.Label(frame, text="Your inventory is ready. Normal lookups now work offline.").grid(sticky="w", pady=18)
        return frame

    def _show_page(self, page: int) -> None:
        for frame in self.pages:
            frame.grid_forget()
        self.page = page
        self.pages[page].grid(row=0, column=0, sticky="nsew")
        self.back.configure(state="disabled" if page == 0 else "normal")
        self.next.configure(text="Open application" if page == 4 else "Next")
        if page == 3:
            self._start_download()

    def _next(self) -> None:
        try:
            if self.page == 1:
                if not self.api_key.get().strip():
                    raise ValidationError("Enter your Rebrickable API key.")
                self.service.validate_set_num(self.set_num.get())
            if self.page == 2:
                from ..config import validate_cache_directory
                validate_cache_directory(Path(self.cache_path.get()))
        except Exception as exc:
            messagebox.showerror("Setup", str(exc), parent=self)
            return
        if self.page == 4:
            self.on_complete()
        elif self.page != 3:
            self._show_page(self.page + 1)

    def _back(self) -> None:
        if self.page > 0 and self.page != 3:
            self._show_page(self.page - 1)

    def _browse(self) -> None:
        selected = filedialog.askdirectory(parent=self, initialdir=self.cache_path.get())
        if selected:
            self.cache_path.set(selected)

    def _start_download(self) -> None:
        self.status.set("Testing the connection…")
        self.progress.start(12)
        self.next.configure(state="disabled")
        self.back.configure(state="disabled")
        self.cancel.pack(side="right", padx=8)
        selected_cache = Path(self.cache_path.get())
        default_cache = cache_dir()
        api_key = self.api_key.get().strip()
        set_num = self.set_num.get().strip()
        remember_key = self.remember.get()

        def progress(page, count):
            if self.task:
                self.task.report((page, count))

        def work():
            self.service.test_connection(api_key, set_num)
            count = self.service.download(
                set_num=set_num, api_key=api_key, cache_directory=selected_cache, progress=progress,
                cancelled=lambda: bool(self.task and self.task.cancelled.is_set()),
            )
            self.service.configure(
                api_key=api_key, set_num=set_num,
                cache_directory=None if selected_cache == default_cache else selected_cache,
                remember_key=remember_key,
            )
            return count

        self.task = BackgroundTask(
            self,
            work,
            self._downloaded,
            self._download_failed,
            lambda value: self.status.set(f"Downloading page {value[0]} — {value[1]} entries…"),
        )
        self.task.start()

    def _downloaded(self, count: int) -> None:
        self.progress.stop()
        self.cancel.pack_forget()
        self.status.set(f"Downloaded and validated {count} inventory entries.")
        self.next.configure(state="normal")
        self._show_page(4)

    def _download_failed(self, exc: Exception) -> None:
        self.progress.stop()
        self.cancel.pack_forget()
        self.status.set(str(exc))
        self.back.configure(state="normal")
        messagebox.showerror("Setup could not be completed", str(exc), parent=self)
        self._show_page(2)

    def _cancel_download(self) -> None:
        if self.task:
            self.task.cancel()
            self.status.set("Cancelling after the current request…")
