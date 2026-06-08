from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

PY_EXTS: tuple[str, ...] = (".py", ".pyw")
VENV_NAMES: tuple[str, ...] = (".venv", "venv")


@dataclass
class LaunchResult:
    process: subprocess.Popen[bytes] | None = None
    error: str | None = None


class ScriptRunner:
    @staticmethod
    def _prepare_env() -> dict[str, str]:
        env = os.environ.copy()
        env.pop("TCL_LIBRARY", None)
        env.pop("TK_LIBRARY", None)
        return env

    @staticmethod
    def _resolve_python(script_dir: Path, is_pyw: bool = False) -> str:
        exe = "pythonw.exe" if is_pyw else "python.exe"
        for parent in [script_dir, *script_dir.parents]:
            for venv_name in VENV_NAMES:
                candidate = parent / venv_name / "Scripts" / exe
                if candidate.exists():
                    logging.info("Using venv python: %s", candidate)
                    return str(candidate.absolute())
        fallback = shutil.which("pythonw" if is_pyw else "python")
        return fallback or ("pythonw" if is_pyw else "python")

    @staticmethod
    def run(path: Path) -> LaunchResult:
        p = path.absolute()
        if not p.exists():
            return LaunchResult(error=f"File not found: {p}")
        if p.suffix.lower() not in PY_EXTS:
            return LaunchResult(error=f"Unsupported extension: {p.suffix}")

        is_pyw = p.suffix.lower() == ".pyw"
        exe_path = ScriptRunner._resolve_python(p.parent, is_pyw=is_pyw)

        logging.info("Launching: %s %s (cwd=%s)", exe_path, str(p), str(p.parent))

        env = ScriptRunner._prepare_env()

        try:
            if is_pyw:
                proc = subprocess.Popen([exe_path, str(p)], cwd=str(p.parent), env=env)
            else:
                proc = subprocess.Popen(
                    ["cmd", "/k", exe_path, str(p)],
                    cwd=str(p.parent),
                    env=env,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
            return LaunchResult(process=proc)
        except FileNotFoundError:
            return LaunchResult(error=f"Python executable not found: {exe_path}")
        except OSError as e:
            return LaunchResult(error=f"Failed launching script: {e}")

    @staticmethod
    def run_as_module(module_name: str, cwd: Path) -> LaunchResult:
        exe_path = ScriptRunner._resolve_python(cwd)
        log_msg = f"{exe_path} -m {module_name} (cwd={cwd})"
        logging.info("Launching module: %s", log_msg)

        env = ScriptRunner._prepare_env()

        try:
            proc = subprocess.Popen(
                ["cmd", "/k", exe_path, "-m", module_name],
                cwd=str(cwd),
                env=env,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            return LaunchResult(process=proc)
        except FileNotFoundError:
            return LaunchResult(error=f"Python executable not found: {exe_path}")
        except OSError as e:
            return LaunchResult(error=f"Failed launching module: {e}")
