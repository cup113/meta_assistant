from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

PY_EXTS: tuple[str, ...] = (".py", ".pyw")


@dataclass
class ScriptNode:
    path: Path
    children: list[ScriptNode] = field(default_factory=lambda: cast("list[ScriptNode]", []))


class ScriptScanner:
    def __init__(self, ignore_dirs: set[str] | None = None) -> None:
        self._ignore_dirs_lower: set[str] = {d.lower() for d in (ignore_dirs or set())}
        self._cached_tree: list[ScriptNode] | None = None
        self._cached_root: Path | None = None

    def invalidate(self) -> None:
        self._cached_tree = None
        self._cached_root = None

    @property
    def ignore_dirs(self) -> set[str]:
        return self._ignore_dirs_lower

    @ignore_dirs.setter
    def ignore_dirs(self, value: set[str]) -> None:
        self._ignore_dirs_lower = {d.lower() for d in value}
        self.invalidate()

    def scan(self, root: Path) -> list[ScriptNode]:
        if self._cached_tree is not None and self._cached_root == root:
            return self._cached_tree
        tree = self._build_tree(root)
        self._cached_tree = tree
        self._cached_root = root
        return tree

    def get_all_scripts(self, root: Path) -> list[Path]:
        return list(self._flatten(self.scan(root)))

    def _build_tree(self, directory: Path) -> list[ScriptNode]:
        nodes: list[ScriptNode] = []
        try:
            if not directory.exists() or not directory.is_dir():
                return nodes

            entries = sorted(
                list(directory.iterdir()),
                key=lambda x: (not x.is_dir(), x.name.lower()),
            )

            for entry in entries:
                if entry.is_dir():
                    if entry.name.lower() in self._ignore_dirs_lower:
                        continue
                    children = self._build_tree(entry)
                    if children:
                        nodes.append(ScriptNode(path=entry, children=children))
                elif entry.suffix.lower() in PY_EXTS:
                    nodes.append(ScriptNode(path=entry))
        except OSError:
            logging.exception("Failed building script tree for: %s", directory)
        return nodes

    @staticmethod
    def _flatten(nodes: list[ScriptNode]) -> list[Path]:
        paths: list[Path] = []
        for node in nodes:
            if node.children:
                paths.extend(ScriptScanner._flatten(node.children))
            else:
                paths.append(node.path.absolute())
        return paths
