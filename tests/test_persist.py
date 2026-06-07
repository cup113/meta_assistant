from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from meta_assistant._persist import JsonFile


@dataclass
class DummyModel:
    name: str
    count: int

    @staticmethod
    def default() -> DummyModel:
        return DummyModel(name="default", count=0)

    @staticmethod
    def from_json(data: dict[str, Any]) -> DummyModel:
        return DummyModel(
            name=str(data.get("name", "default")),
            count=int(data.get("count", 0)),
        )

    def to_json(self) -> dict[str, Any]:
        return {"name": self.name, "count": self.count}


def test_load_returns_default_when_file_missing(tmp_path: Path) -> None:
    store = JsonFile(
        tmp_path / "nonexistent.json",
        default=DummyModel.default,
        deserialize=DummyModel.from_json,
        serialize=DummyModel.to_json,
    )
    value = store.load()
    assert value.name == "default"
    assert value.count == 0


def test_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    store = JsonFile(
        path,
        default=DummyModel.default,
        deserialize=DummyModel.from_json,
        serialize=DummyModel.to_json,
    )
    store.save(DummyModel(name="hello", count=42))
    value = store.load()
    assert value.name == "hello"
    assert value.count == 42


def test_load_returns_default_on_corrupt_json(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.json"
    path.write_text("not valid json", encoding="utf-8")
    store = JsonFile(
        path,
        default=DummyModel.default,
        deserialize=DummyModel.from_json,
        serialize=DummyModel.to_json,
    )
    value = store.load()
    assert value.name == "default"


def test_load_returns_default_on_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "empty.json"
    path.write_text("", encoding="utf-8")
    store = JsonFile(
        path,
        default=DummyModel.default,
        deserialize=DummyModel.from_json,
        serialize=DummyModel.to_json,
    )
    value = store.load()
    assert value.name == "default"


def test_writes_indented_json(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    store = JsonFile(
        path,
        default=DummyModel.default,
        deserialize=DummyModel.from_json,
        serialize=DummyModel.to_json,
    )
    store.save(DummyModel(name="a", count=1))
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw == {"name": "a", "count": 1}


def test_path_property(tmp_path: Path) -> None:
    path = tmp_path / "test.json"
    store = JsonFile(
        path,
        default=DummyModel.default,
        deserialize=DummyModel.from_json,
        serialize=DummyModel.to_json,
    )
    assert store.path == path
