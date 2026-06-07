from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class JsonFile(Generic[T]):
    def __init__(
        self,
        path: Path,
        *,
        default: Callable[[], T],
        deserialize: Callable[[dict[str, Any]], T],
        serialize: Callable[[T], dict[str, Any]],
    ) -> None:
        self._path = path
        self._default = default
        self._deserialize = deserialize
        self._serialize = serialize

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> T:
        try:
            raw = self._path.read_text(encoding="utf-8")
            data: dict[str, Any] = json.loads(raw)
        except FileNotFoundError:
            logging.warning("Missing JSON file: %s", self._path)
            return self._default()
        except json.JSONDecodeError:
            logging.exception("Invalid JSON in file: %s", self._path)
            return self._default()
        except OSError:
            logging.exception("Failed reading JSON file: %s", self._path)
            return self._default()
        return self._deserialize(data)

    def save(self, value: T) -> None:
        data = self._serialize(value)
        try:
            self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError:
            logging.exception("Failed writing JSON file: %s", self._path)
