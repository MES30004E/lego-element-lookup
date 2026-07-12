"""Run blocking work away from Tk's event loop."""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from typing import Generic, TypeVar

T = TypeVar("T")


class BackgroundTask(Generic[T]):
    def __init__(
        self,
        owner,
        work: Callable[[], T],
        on_success: Callable[[T], None],
        on_error: Callable[[Exception], None],
        on_progress: Callable[[object], None] | None = None,
    ) -> None:
        self.owner = owner
        self.work = work
        self.on_success = on_success
        self.on_error = on_error
        self.on_progress = on_progress
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.cancelled = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        self.thread = threading.Thread(target=self._run, daemon=True, name="lego-lookup-worker")
        self.thread.start()
        self.owner.after(50, self._poll)

    def cancel(self) -> None:
        self.cancelled.set()

    def report(self, value: object) -> None:
        self.events.put(("progress", value))

    def _run(self) -> None:
        try:
            self.events.put(("success", self.work()))
        except Exception as exc:
            self.events.put(("error", exc))

    def _poll(self) -> None:
        try:
            event, value = self.events.get_nowait()
        except queue.Empty:
            self.owner.after(50, self._poll)
            return
        if event == "progress":
            if self.on_progress:
                self.on_progress(value)
            self.owner.after(50, self._poll)
        elif event == "success":
            self.on_success(value)  # type: ignore[arg-type]
        else:
            self.on_error(value if isinstance(value, Exception) else RuntimeError("Background task failed."))
