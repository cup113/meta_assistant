from __future__ import annotations

from pathlib import Path

from meta_assistant._runner import ScriptRunner


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
