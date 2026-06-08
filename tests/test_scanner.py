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


def test_package_with_main_creates_submenu(tmp_path: Path) -> None:
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "__main__.py").write_text("")
    (pkg / "helper.py").write_text("")
    scanner = ScriptScanner()
    tree = scanner.scan(tmp_path)
    assert len(tree) == 1
    node = tree[0]
    assert node.path.name == "mypkg"
    assert node.run_module == "mypkg"
    assert len(node.children) == 1
    assert node.children[0].path.name == "helper.py"


def test_package_without_main_keeps_children(tmp_path: Path) -> None:
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "util.py").write_text("")
    scanner = ScriptScanner()
    tree = scanner.scan(tmp_path)
    assert len(tree) == 1
    node = tree[0]
    assert node.run_module is None
    assert len(node.children) == 1
    assert node.children[0].path.name == "util.py"


def test_package_skips_init_py_and_underscore(tmp_path: Path) -> None:
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "__main__.py").write_text("")
    (pkg / "_internal.py").write_text("")
    (pkg / "_private.py").write_text("")
    scanner = ScriptScanner()
    tree = scanner.scan(tmp_path)
    assert len(tree) == 1
    node = tree[0]
    assert node.run_module == "mypkg"
    assert node.children == []


def test_package_with_only_init_and_main(tmp_path: Path) -> None:
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "__main__.py").write_text("")
    scanner = ScriptScanner()
    tree = scanner.scan(tmp_path)
    assert len(tree) == 1
    node = tree[0]
    assert node.run_module == "mypkg"
    assert node.children == []


def test_library_package_skips_underscore_files(tmp_path: Path) -> None:
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "_internal.py").write_text("")
    (pkg / "util.py").write_text("")
    scanner = ScriptScanner()
    tree = scanner.scan(tmp_path)
    assert len(tree) == 1
    node = tree[0]
    assert node.run_module is None
    assert len(node.children) == 1
    assert node.children[0].path.name == "util.py"


def test_package_with_only_init_skipped(tmp_path: Path) -> None:
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    scanner = ScriptScanner()
    tree = scanner.scan(tmp_path)
    assert tree == []


def test_nested_package_detection(tmp_path: Path) -> None:
    pkg = tmp_path / "outer"
    pkg.mkdir()
    sub = pkg / "inner"
    sub.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "__main__.py").write_text("")
    (sub / "__init__.py").write_text("")
    (sub / "__main__.py").write_text("")
    (sub / "leaf.py").write_text("")
    scanner = ScriptScanner()
    tree = scanner.scan(tmp_path)
    assert len(tree) == 1
    outer = tree[0]
    assert outer.run_module == "outer"
    assert len(outer.children) == 1
    inner = outer.children[0]
    assert inner.path.name == "inner"
    assert inner.run_module == "inner"
    assert len(inner.children) == 1
    assert inner.children[0].path.name == "leaf.py"


def test_underscore_file_at_root_shown(tmp_path: Path) -> None:
    (tmp_path / "_helper.py").write_text("")
    (tmp_path / "normal.py").write_text("")
    scanner = ScriptScanner()
    tree = scanner.scan(tmp_path)
    assert len(tree) == 2
    names = {n.path.name for n in tree}
    assert "_helper.py" in names
    assert "normal.py" in names


def test_mixed_package_and_regular(tmp_path: Path) -> None:
    (tmp_path / "standalone.py").write_text("")
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "__main__.py").write_text("")
    (pkg / "tool.py").write_text("")
    d = tmp_path / "scripts"
    d.mkdir()
    (d / "run.py").write_text("")
    scanner = ScriptScanner()
    tree = scanner.scan(tmp_path)
    names = sorted(n.path.name for n in tree)
    assert names == ["pkg", "scripts", "standalone.py"]
    pkg_node = next(n for n in tree if n.path.name == "pkg")
    assert pkg_node.run_module == "pkg"
    assert len(pkg_node.children) == 1
    assert pkg_node.children[0].path.name == "tool.py"
    scripts_node = next(n for n in tree if n.path.name == "scripts")
    assert scripts_node.run_module is None
    assert len(scripts_node.children) == 1
    assert scripts_node.children[0].path.name == "run.py"
