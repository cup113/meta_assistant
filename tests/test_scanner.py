from __future__ import annotations

from pathlib import Path

from meta_assistant._scanner import PY_EXTS, ScriptScanner


def test_empty_directory(tmp_path: Path) -> None:
    scanner = ScriptScanner()
    tree = scanner.scan(tmp_path)
    assert tree == []


def test_ignores_nonexistent_directory(tmp_path: Path) -> None:
    scanner = ScriptScanner()
    tree = scanner.scan(tmp_path / "nonexistent")
    assert tree == []


def test_ignores_ignored_directory(tmp_path: Path) -> None:
    (tmp_path / "node_modules").mkdir()
    scanner = ScriptScanner(ignore_dirs={"node_modules"})
    tree = scanner.scan(tmp_path)
    assert tree == []


def test_ignores_pycache(tmp_path: Path) -> None:
    (tmp_path / "__pycache__").mkdir()
    scanner = ScriptScanner(ignore_dirs={"__pycache__"})
    tree = scanner.scan(tmp_path)
    assert tree == []


def test_ignores_are_case_insensitive(tmp_path: Path) -> None:
    (tmp_path / "Node_Modules").mkdir()
    scanner = ScriptScanner(ignore_dirs={"node_modules"})
    tree = scanner.scan(tmp_path)
    assert tree == []


def test_detects_py_script(tmp_path: Path) -> None:
    (tmp_path / "hello.py").write_text("print('hello')")
    scanner = ScriptScanner()
    tree = scanner.scan(tmp_path)
    assert len(tree) == 1
    assert tree[0].path.name == "hello.py"
    assert tree[0].children == []


def test_detects_pyw_script(tmp_path: Path) -> None:
    (tmp_path / "gui.pyw").write_text("")
    scanner = ScriptScanner()
    tree = scanner.scan(tmp_path)
    assert len(tree) == 1
    assert tree[0].path.suffix.lower() == ".pyw"


def test_ignores_non_python_files(tmp_path: Path) -> None:
    (tmp_path / "readme.md").write_text("# hi")
    (tmp_path / "stuff.txt").write_text("data")
    scanner = ScriptScanner()
    tree = scanner.scan(tmp_path)
    assert tree == []


def test_recursive_scan(tmp_path: Path) -> None:
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "inner.py").write_text("")
    scanner = ScriptScanner()
    tree = scanner.scan(tmp_path)
    assert len(tree) == 1
    assert tree[0].path.name == "sub"
    assert len(tree[0].children) == 1
    assert tree[0].children[0].path.name == "inner.py"


def test_get_all_scripts_flat(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("")
    b_dir = tmp_path / "b"
    b_dir.mkdir()
    (b_dir / "c.py").write_text("")
    scanner = ScriptScanner()
    paths = scanner.get_all_scripts(tmp_path)
    assert len(paths) == 2
    assert all(p.suffix.lower() in PY_EXTS for p in paths)
    assert all(p.is_absolute() for p in paths)


def test_cache_hit_returns_same_tree(tmp_path: Path) -> None:
    (tmp_path / "x.py").write_text("")
    scanner = ScriptScanner()
    first = scanner.scan(tmp_path)
    (tmp_path / "y.py").write_text("")
    cached = scanner.scan(tmp_path)
    assert len(cached) == 1
    assert cached is first


def test_invalidate_clears_cache(tmp_path: Path) -> None:
    (tmp_path / "x.py").write_text("")
    scanner = ScriptScanner()
    scanner.scan(tmp_path)
    (tmp_path / "y.py").write_text("")
    scanner.invalidate()
    tree = scanner.scan(tmp_path)
    assert len(tree) == 2


def test_ignore_dirs_setter_invalidates(tmp_path: Path) -> None:
    (tmp_path / "x.py").write_text("")
    scanner = ScriptScanner()
    scanner.scan(tmp_path)
    (tmp_path / "y.py").write_text("")
    scanner.ignore_dirs = {"__pycache__"}
    tree = scanner.scan(tmp_path)
    assert len(tree) == 2


def test_ignore_dirs_setter_normalizes_casing() -> None:
    scanner = ScriptScanner()
    scanner.ignore_dirs = {"Node_Modules", ".GIT"}
    assert scanner.ignore_dirs == {"node_modules", ".git"}
