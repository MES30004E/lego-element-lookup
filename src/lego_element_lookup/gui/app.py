"""Desktop application entry point."""

from __future__ import annotations

import argparse
import sys
import tkinter as tk
from tkinter import messagebox, ttk

from .. import __version__
from ..services import ApplicationService
from .main_window import MainWindow
from .wizard import SetupWizard


class DesktopApplication:
    def __init__(self, root: tk.Tk, service: ApplicationService | None = None) -> None:
        self.root = root
        self.service = service or ApplicationService()
        root.title("LEGO Element Lookup")
        root.minsize(820, 560)
        self.container = ttk.Frame(root)
        self.container.pack(fill="both", expand=True)
        self._show_wizard() if self.service.setup_required else self._show_main()

    def _clear(self) -> None:
        for child in self.container.winfo_children():
            child.destroy()

    def _show_wizard(self) -> None:
        self._clear()
        wizard = SetupWizard(self.container, self.service, self._show_main)
        wizard.pack(fill="both", expand=True)

    def _show_main(self) -> None:
        self._clear()
        window = MainWindow(self.container, self.service)
        window.pack(fill="both", expand=True)


def _report_callback_exception(root: tk.Tk, exc_type, exc_value, traceback) -> None:
    messagebox.showerror(
        "LEGO Element Lookup",
        "An unexpected error occurred. No API key or request details were written to the screen.",
        parent=root,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--smoke-test", action="store_true")
    args, _ = parser.parse_known_args(sys.argv[1:] if argv is None else argv)
    if args.smoke_test:
        print(f"LEGO Element Lookup {__version__}")
        return 0
    root = tk.Tk()
    root.report_callback_exception = lambda *values: _report_callback_exception(root, *values)
    DesktopApplication(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
