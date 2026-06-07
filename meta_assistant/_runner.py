from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

PY_EXTS: tuple[str, ...] = (".py", ".pyw")


@dataclass
class LaunchResult:
    process: subprocess.Popen[bytes] | None = None
    error: str | None = None


class ScriptRunner:
    @staticmethod
    def run(path: Path) -> LaunchResult:
        p = path.absolute()
        if not p.exists():
            return LaunchResult(error=f"File not found: {p}")
        if p.suffix.lower() not in PY_EXTS:
            return LaunchResult(error=f"Unsupported extension: {p.suffix}")

        is_pyw = p.suffix.lower() == ".pyw"
        exe_name = "pythonw" if is_pyw else "python"
        exe_path = shutil.which(exe_name)
        if exe_path is None:
            return LaunchResult(error=f"{exe_name} not found on PATH")

        logging.info("Launching: %s %s (cwd=%s)", exe_path, str(p), str(p.parent))

        env = os.environ.copy()
        env.pop("TCL_LIBRARY", None)
        env.pop("TK_LIBRARY", None)

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
