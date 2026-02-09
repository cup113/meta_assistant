import json
import logging
import os
import subprocess
import tkinter as tk
from os import startfile
from pathlib import Path
from sys import argv, executable
from tkinter import filedialog
from winreg import (
    HKEY_CURRENT_USER,
    KEY_SET_VALUE,
    REG_SZ,
    CloseKey,
    OpenKey,
    SetValueEx,
)

from PIL import Image  # pyright: ignore[reportMissingTypeStubs]
from pystray import Icon, Menu, MenuItem  # pyright: ignore[reportMissingTypeStubs]
from typing import Any, TypedDict

# --- Configuration ---
APP_NAME = "AssistantLauncher"
APP_EXE_PATH = Path(argv[0]).absolute()
DEFAULT_TARGET_DIR = Path(r"F:/projects/assistant")
DEFAULT_IGNORE_DIRS = {
    "node_modules",
    "__pycache__",
    "venv",
    ".git",
    ".venv",
    "dist",
    "build",
}
MAX_RECENT = 10

APP_DATA_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / APP_NAME
CONFIG_FILE = APP_DATA_DIR / "config.json"
STATS_FILE = APP_DATA_DIR / "assistant_stats.json"
LOG_FILE = APP_DATA_DIR / "assistant.log"
ICON_FILE = APP_DATA_DIR / "assistant.ico"
EXE_ICON_FILE = APP_EXE_PATH.parent / "assistant.ico"

class Config(TypedDict):
    target_dir: str
    ignore_dirs: list[str]


def _noop(*_args: Any, **_kwargs: Any):
    return None


class AssistantApp:
    def __init__(self):
        self._setup_storage()
        self._setup_logging()
        self.config: Config = self._load_config()
        self.target_dir = Path(self.config["target_dir"])
        self.ignore_dirs = {d.lower() for d in self.config["ignore_dirs"]}
        self.stats = self._load_stats()

    def _setup_storage(self):
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not CONFIG_FILE.exists():
            self._write_json(
                CONFIG_FILE,
                {
                    "target_dir": str(DEFAULT_TARGET_DIR),
                    "ignore_dirs": sorted(DEFAULT_IGNORE_DIRS),
                },
            )
        if not STATS_FILE.exists():
            self._write_json(STATS_FILE, {"recent": []})

    def _setup_logging(self):
        logging.basicConfig(
            filename=LOG_FILE,
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
        )

    def _read_json(self, file_path: Path, fallback: dict[str, Any]):
        try:
            return json.loads(file_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            logging.warning("Missing JSON file: %s", file_path)
        except json.JSONDecodeError:
            logging.exception("Invalid JSON in file: %s", file_path)
        except OSError:
            logging.exception("Failed reading JSON file: %s", file_path)
        return fallback.copy()

    def _write_json(self, file_path: Path, payload: dict[str, Any]):
        try:
            file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError:
            logging.exception("Failed writing JSON file: %s", file_path)

    def _load_config(self):
        data = self._read_json(
            CONFIG_FILE,
            {
                "target_dir": str(DEFAULT_TARGET_DIR),
                "ignore_dirs": sorted(DEFAULT_IGNORE_DIRS),
            },
        )

        target_dir = data.get("target_dir", str(DEFAULT_TARGET_DIR))
        ignore_dirs = data.get("ignore_dirs", sorted(DEFAULT_IGNORE_DIRS))

        if not isinstance(target_dir, str):
            target_dir = str(DEFAULT_TARGET_DIR)
        if not isinstance(ignore_dirs, list):
            ignore_dirs = sorted(DEFAULT_IGNORE_DIRS)

        cleaned_ignore = [str(x).strip() for x in ignore_dirs if str(x).strip()]
        config: Config = {
            "target_dir": target_dir,
            "ignore_dirs": cleaned_ignore,
        }
        return config

    def _save_config(self):
        self.config = {
            "target_dir": str(self.target_dir),
            "ignore_dirs": sorted(self.ignore_dirs),
        }
        self._write_json(CONFIG_FILE, self.config)

    def _load_stats(self):
        data = self._read_json(STATS_FILE, {"recent": []})
        recent = data.get("recent", [])
        if not isinstance(recent, list):
            recent = []
        return {"recent": [str(x) for x in recent if isinstance(x, str)]}

    def _save_stats(self):
        self._write_json(STATS_FILE, self.stats)

    def refresh_state(self, icon=None):
        self.config = self._load_config()
        self.target_dir = Path(self.config["target_dir"])
        self.ignore_dirs = {d.lower() for d in self.config["ignore_dirs"]}
        self.stats = self._load_stats()
        if icon is not None:
            try:
                icon.update_menu()
            except Exception:
                logging.exception("Failed to update tray menu during refresh.")

    def record_hit(self, file_path: Path):
        try:
            p_str = str(file_path.absolute())
            recent = self.stats.get("recent", [])
            if p_str in recent:
                recent.remove(p_str)
            recent.insert(0, p_str)
            self.stats["recent"] = recent[:MAX_RECENT]
            self._save_stats()
        except OSError:
            logging.exception("Failed to record recent item: %s", file_path)

    def launch(self, path_str: str):
        p = Path(path_str)
        if not p.exists():
            logging.warning("Launch skipped; file not found: %s", path_str)
            return
        if p.suffix.lower() not in (".py", ".pyw"):
            logging.warning("Launch skipped; unsupported extension: %s", path_str)
            return

        self.record_hit(p)
        ext = p.suffix.lower()
        cwd = str(p.parent)

        try:
            if ext == ".pyw":
                subprocess.Popen(["pythonw", path_str], cwd=cwd)
            else:
                subprocess.Popen(
                    ["cmd", "/k", "python", path_str],
                    cwd=cwd,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
        except FileNotFoundError:
            logging.exception("Python executable not found while launching: %s", path_str)
        except OSError:
            logging.exception("Failed launching script: %s", path_str)

    def _make_launch_callback(self, path_str: str):
        """Factory to create pystray-compatible callbacks using closure."""
        return lambda icon, item: self.launch(path_str)

    def _make_remove_ignore_callback(self, dir_name: str):
        """Factory to create pystray-compatible callbacks for removing ignored dirs."""
        return lambda icon, item: self.remove_ignore_dir(icon, dir_name)

    def format_name(self, stem: str, is_dir=False) -> str:
        name = stem.replace("_", " ").upper()
        return f"{'📁 ' if is_dir else ''}{name}"

    def build_menu_recursive(self, directory: Path):
        items: list[MenuItem] = []
        try:
            if not directory.exists() or not directory.is_dir():
                return items

            entries = sorted(
                list(directory.iterdir()),
                key=lambda x: (not x.is_dir(), x.name.lower()),
            )

            for entry in entries:
                if entry.is_dir():
                    if entry.name.lower() in self.ignore_dirs:
                        continue
                    submenu_items = self.build_menu_recursive(entry)
                    if submenu_items:
                        items.append(
                            MenuItem(
                                self.format_name(entry.name, is_dir=True),
                                Menu(*submenu_items),
                            )
                        )
                elif entry.suffix.lower() in (".py", ".pyw"):
                    display = self.format_name(entry.stem)
                    icon_prefix = "⚡ " if entry.suffix.lower() == ".pyw" else "🐍 "
                    abs_path = str(entry.absolute())
                    items.append(
                        MenuItem(
                            f"{icon_prefix}{display}",
                            self._make_launch_callback(abs_path),)
                    )
        except OSError:
            logging.exception("Failed building recursive menu for: %s", directory)
        return items

    def build_recent_menu(self):
        recent_items: list[MenuItem] = []
        for p_str in self.stats.get("recent", []):
            p = Path(p_str)
            label = f"{p.stem} ({p.parent.name})" if p.parent.name else p.stem
            recent_items.append(
                MenuItem(
                    f"🕘 {label}",
                    self._make_launch_callback(p_str),
                    enabled=p.exists(),
                )
            )

        if not recent_items:
            recent_items.append(MenuItem("No recent items", _noop, enabled=False))
        return recent_items

    def _with_tk_dialog(self, callback):
        root = None
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            return callback(root)
        except Exception:
            logging.exception("Dialog operation failed.")
            return None
        finally:
            if root is not None:
                root.destroy()

    def choose_target_dir(self, icon, item):
        def _ask(_root):
            return filedialog.askdirectory(
                title="Select Assistant Target Directory",
                initialdir=str(self.target_dir) if self.target_dir.exists() else str(Path.home()),
            )

        selected = self._with_tk_dialog(_ask)
        if selected:
            self.target_dir = Path(selected)
            self._save_config()
            self.refresh_state(icon)

    def remove_ignore_dir(self, icon, dir_name: str):
        if dir_name in self.ignore_dirs:
            self.ignore_dirs.remove(dir_name)
            self._save_config()
            self.refresh_state(icon)

    def refresh_menu(self, icon, item):
        self.refresh_state(icon)

    def open_root(self, icon, item):
        try:
            if self.target_dir.exists():
                startfile(self.target_dir)
            else:
                logging.warning("Target directory does not exist: %s", self.target_dir)
        except OSError:
            logging.exception("Failed to open target directory: %s", self.target_dir)

    def open_config_file(self, icon, item):
        try:
            if not CONFIG_FILE.exists():
                self._save_config()
            startfile(CONFIG_FILE)
        except OSError:
            logging.exception("Failed to open config file: %s", CONFIG_FILE)

    def build_settings_menu(self):
        ignore_items = [
            MenuItem(f"➖ {name}", self._make_remove_ignore_callback(name))
            for name in sorted(self.ignore_dirs)
        ]
        if not ignore_items:
            ignore_items.append(MenuItem("No ignored folders", _noop, enabled=False))

        return [
            MenuItem(f"📍 Current Target: {self.target_dir}", _noop, enabled=False),
            MenuItem("📂 Choose Target Directory...", self.choose_target_dir),
            MenuItem("📄 Open Config File", self.open_config_file),
            MenuItem("🔄 Reload Config", self.refresh_menu),
            MenuItem("🛑 Ignored Folders", Menu(*ignore_items)),
        ]

    def build_main_menu(self):
        items = []

        if self.target_dir.exists() and self.target_dir.is_dir():
            items.extend(self.build_menu_recursive(self.target_dir))
        else:
            items.append(MenuItem("Target directory not found", _noop, enabled=False))

        items.append(Menu.SEPARATOR)
        items.append(MenuItem("🕘 Recent", Menu(*self.build_recent_menu())))
        items.append(MenuItem("⚙️ Settings", Menu(*self.build_settings_menu())))
        items.append(MenuItem("🔄 Refresh", self.refresh_menu))
        items.append(MenuItem("📂 Open Root", self.open_root))
        items.append(MenuItem("❌ Exit", lambda icon, item: icon.stop()))
        return items

    def load_icon_image(self):
        icon_source = ICON_FILE if ICON_FILE.exists() else EXE_ICON_FILE
        if icon_source.exists():
            try:
                return Image.open(icon_source)
            except OSError:
                logging.exception("Failed loading icon file: %s", icon_source)
                img = Image.new("RGB", (64, 64), (15, 23, 42))
        return img

    def set_autostart(self):
        if Path(executable).name.lower() in ("python.exe", "pythonw.exe"):
            return
        try:
            key = OpenKey(
                HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                KEY_SET_VALUE,
            )
            SetValueEx(key, APP_NAME, 0, REG_SZ, f'"{APP_EXE_PATH}"')
            CloseKey(key)
        except OSError:
            logging.exception("Failed setting autostart registry key.")

    def run(self):
        self.set_autostart()
        icon = Icon(
            APP_NAME,
            self.load_icon_image(),
            title="Assistant Launcher",
            menu=Menu(lambda: self.build_main_menu()),
        )
        icon.run()


if __name__ == "__main__":
    AssistantApp().run()
