from __future__ import annotations

import queue
import tkinter as tk
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


class TkDialogBridge:
    def __init__(self) -> None:
        self._queue: queue.Queue[tuple[Callable[..., Any], queue.Queue[Any]]] = queue.Queue()

    def start(self, root: tk.Tk) -> None:
        self._poll(root)

    def _poll(self, root: tk.Tk) -> None:
        try:
            while True:
                callback, result_queue = self._queue.get_nowait()
                result = callback(root)
                result_queue.put(result)
        except queue.Empty:
            pass
        root.after(100, lambda: self._poll(root))

    def run_dialog(self, callback: Callable[[tk.Tk], T]) -> T:
        result_queue: queue.Queue[T] = queue.Queue()
        self._queue.put((callback, result_queue))  # type: ignore[arg-type]
        return result_queue.get()
