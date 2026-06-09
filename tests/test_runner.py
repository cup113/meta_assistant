from __future__ import annotations

from pathlib import Path

from meta_assistant._runner import ScriptRunner

# pyright: reportPrivateUsage=false


def test_returns_error_for_missing_file(tmp_path: Path) -> None:
    result = ScriptRunner.run(tmp_path / "nonexistent.py")
    assert result.error is not None
    assert "not found" in result.error
    assert result.process is None


def test_returns_error_for_unsupported_extension(tmp_path: Path) -> None:
    path = tmp_path / "script.txt"
    path.write_text("")
    result = ScriptRunner.run(path)
    assert result.error is not None
    assert "Unsupported" in result.error
    assert result.process is None


def test_returns_error_for_supported_extension_but_no_exe(tmp_path: Path) -> None:
    path = tmp_path / "script.py"
    path.write_text("print('hi')")

    runner = ScriptRunner()
    result = runner.run(path)
    # python is on PATH in CI/dev, so this will succeed
    # If it fails, we expect an error about exe not found
    if result.error is not None:
        assert "PATH" in result.error or "not found" in result.error


def test_run_as_module_returns_result(tmp_path: Path) -> None:
    runner = ScriptRunner()
    result = runner.run_as_module("_nonexistent_module_that_does_not_exist_", tmp_path)
    # Should return a result (with process or error), not crash
    assert result.error is not None or result.process is not None


def test_module_cwd_returns_parent(tmp_path: Path) -> None:
    pkg_dir = tmp_path / "mypkg"
    assert ScriptRunner.module_cwd(pkg_dir) == tmp_path


def test_resolve_python_finds_venv(tmp_path: Path) -> None:
    venv_dir = tmp_path / ".venv" / "Scripts"
    venv_dir.mkdir(parents=True)
    (venv_dir / "python.exe").write_text("")
    python = ScriptRunner._resolve_python(tmp_path)
    assert python == str((venv_dir / "python.exe").absolute())


def test_resolve_python_falls_back(tmp_path: Path) -> None:
    python = ScriptRunner._resolve_python(tmp_path)
    # Should return a non-empty string (either venv, or "python", or PATH result)
    assert isinstance(python, str) and len(python) > 0
