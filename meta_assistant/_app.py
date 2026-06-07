from __future__ import annotations

import logging
import os
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from os import startfile
from pathlib import Path
from sys import argv
from tkinter import filedialog
from typing import Any, cast
from winreg import (
    HKEY_CURRENT_USER,
    KEY_SET_VALUE,
    REG_SZ,
    CloseKey,
    OpenKey,
    SetValueEx,
)

from PIL import Image
from pystray import Icon, Menu, MenuItem

from meta_assistant._dialog_bridge import TkDialogBridge
from meta_assistant._persist import JsonFile
from meta_assistant._runner import ScriptRunner
from meta_assistant._scanner import PY_EXTS, ScriptNode, ScriptScanner

__version__ = "1.2.0"

APP_NAME = "MetaAssistant"
APP_EXE_PATH = Path(argv[0]).absolute()
DEFAULT_TARGET_DIR = Path.cwd()
DEFAULT_IGNORE_DIRS: set[str] = {
    "node_modules",
    "__pycache__",
    "venv",
    ".git",
    ".venv",
    "dist",
    "build",
    "site-packages",
}
MAX_RECENT = 10

APP_DATA_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / APP_NAME
CONFIG_FILE = APP_DATA_DIR / "config.json"
STATS_FILE = APP_DATA_DIR / "assistant_stats.json"
LOG_FILE = APP_DATA_DIR / "assistant.log"
ICON_FILE = APP_DATA_DIR / "assistant.ico"
EXE_ICON_FILE = APP_EXE_PATH.parent / "assistant.ico"


def _noop(*_args: Any, **_kwargs: Any) -> None: ...


def _safe_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in cast("list[object]", value):
        s = str(item).strip()
        if s:
            result.append(s)
    return result


@dataclass
class Config:
    target_dir: Path
    ignore_dirs: set[str]
    autostart_scripts: list[str]

    @staticmethod
    def default() -> Config:
        return Config(
            target_dir=DEFAULT_TARGET_DIR,
            ignore_dirs=set(DEFAULT_IGNORE_DIRS),
            autostart_scripts=[],
        )

    @staticmethod
    def from_json(data: dict[str, Any]) -> Config:
        target_raw = data.get("target_dir", str(DEFAULT_TARGET_DIR))
        ignore_raw = data.get("ignore_dirs", list(DEFAULT_IGNORE_DIRS))

        target = Path(target_raw) if isinstance(target_raw, str) else DEFAULT_TARGET_DIR
        ignore = set(_safe_str_list(ignore_raw))

        autostart_list: list[str] = []
        autostart_raw = data.get("autostart_scripts")
        if isinstance(autostart_raw, list):
            autostart_list = _safe_str_list(autostart_raw)
        elif isinstance(autostart_raw, str) and autostart_raw:
            autostart_list = [autostart_raw]
        else:
            legacy = data.get("autostart_script")
            if isinstance(legacy, str) and legacy:
                autostart_list = [legacy]

        return Config(
            target_dir=target,
            ignore_dirs=ignore,
            autostart_scripts=autostart_list,
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "target_dir": str(self.target_dir),
            "ignore_dirs": sorted(self.ignore_dirs),
            "autostart_scripts": self.autostart_scripts,
        }


@dataclass
class Stats:
    recent: list[str]

    @staticmethod
    def default() -> Stats:
        return Stats(recent=[])

    @staticmethod
    def from_json(data: dict[str, Any]) -> Stats:
        recent_raw = data.get("recent", [])
        if not isinstance(recent_raw, list):
            return Stats(recent=[])
        recent: list[str] = []
        for item in cast("list[object]", recent_raw):
            if isinstance(item, str):
                recent.append(item)
        return Stats(recent=recent)

    def to_json(self) -> dict[str, Any]:
        return {"recent": self.recent}


class MetaAssistantApp:
    def __init__(self) -> None:
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._setup_logging()
        self._is_first_run = not CONFIG_FILE.exists()

        self._config_store = JsonFile(
            CONFIG_FILE,
            default=Config.default,
            deserialize=Config.from_json,
            serialize=Config.to_json,
        )
        self._stats_store = JsonFile(
            STATS_FILE,
            default=Stats.default,
            deserialize=Stats.from_json,
            serialize=Stats.to_json,
        )

        self.config = self._config_store.load()
        self.stats = self._stats_store.load()
        self._scanner = ScriptScanner(self.config.ignore_dirs)
        self._dialog_bridge = TkDialogBridge()
        self._runner = ScriptRunner()
        self._root: tk.Tk | None = None

    def _setup_logging(self) -> None:
        logging.basicConfig(
            filename=LOG_FILE,
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
        )
        logging.info("Assistant Launcher v%s", __version__)

    def _save_config(self) -> None:
        self._config_store.save(self.config)

    def _save_stats(self) -> None:
        self._stats_store.save(self.stats)

    def refresh_state(self, icon: Any = None) -> None:
        self.config = self._config_store.load()
        self.stats = self._stats_store.load()
        self._scanner.ignore_dirs = self.config.ignore_dirs
        self._is_first_run = False
        if icon is not None:
            try:
                icon.update_menu()
            except Exception:
                logging.exception("Failed to update tray menu during refresh.")

    def record_hit(self, file_path: Path) -> None:
        try:
            p_str = str(file_path.absolute())
            if p_str in self.stats.recent:
                self.stats.recent.remove(p_str)
            self.stats.recent.insert(0, p_str)
            self.stats.recent = self.stats.recent[:MAX_RECENT]
            self._save_stats()
        except OSError:
            logging.exception("Failed to record recent item: %s", file_path)

    def launch(self, path_str: str) -> None:
        p = Path(path_str)
        if not p.exists():
            logging.warning("Launch skipped; file not found: %s", path_str)
            return
        if p.suffix.lower() not in PY_EXTS:
            logging.warning("Launch skipped; unsupported extension: %s", path_str)
            return

        self.record_hit(p)
        result = self._runner.run(p)
        if result.error is not None:
            logging.warning("Launch failed: %s", result.error)

    def _make_launch_callback(self, path_str: str) -> Callable[[Any, MenuItem], None]:
        return lambda _icon, _item: self.launch(path_str)

    def _make_remove_ignore_callback(self, dir_name: str) -> Callable[[Any, MenuItem], None]:
        return lambda icon, _item: self.remove_ignore_dir(icon, dir_name)

    def _make_set_autostart_callback(self, path_str: str) -> Callable[[Any, MenuItem], None]:
        return lambda icon, _item: self._toggle_autostart_script(icon, path_str)

    def _toggle_autostart_script(self, icon: Any, path_str: str) -> None:
        if path_str in self.config.autostart_scripts:
            self.config.autostart_scripts.remove(path_str)
        else:
            self.config.autostart_scripts.append(path_str)
        self._save_config()
        self.refresh_state(icon)

    def clear_autostart_scripts(self, icon: Any, _item: MenuItem) -> None:
        self.config.autostart_scripts.clear()
        self._save_config()
        self.refresh_state(icon)

    @staticmethod
    def format_name(stem: str, is_dir: bool = False, is_pyw: bool = False) -> str:
        name = stem.replace("_", " ").replace("-", " ").title()
        icon = "\U0001f4c1" if is_dir else ("\u26a1" if is_pyw else "\U0001f40d")
        return f"{icon} {name}"

    def _build_menu_from_tree(self, nodes: list[ScriptNode]) -> list[MenuItem]:
        items: list[MenuItem] = []
        for node in nodes:
            if node.children:
                items.append(
                    MenuItem(
                        self.format_name(node.path.name, is_dir=True),
                        Menu(*self._build_menu_from_tree(node.children)),
                    )
                )
            else:
                is_pyw = node.path.suffix.lower() == ".pyw"
                display = self.format_name(node.path.stem, is_pyw=is_pyw)
                items.append(
                    MenuItem(
                        display,
                        self._make_launch_callback(str(node.path.absolute())),
                    )
                )
        return items

    def get_all_scripts(self) -> list[Path]:
        if self.config.target_dir.exists() and self.config.target_dir.is_dir():
            return self._scanner.get_all_scripts(self.config.target_dir)
        return []

    def build_autostart_menu(self) -> list[MenuItem]:
        items: list[MenuItem] = []
        items.append(MenuItem("\u274c Clear Autostart Scripts", self.clear_autostart_scripts))
        items.append(Menu.SEPARATOR)

        scripts = self.stats.recent
        if not scripts:
            items.append(MenuItem("No scripts found", _noop, enabled=False))
            return items

        for script in scripts:
            p = Path(script)
            is_pyw = p.suffix.lower() == ".pyw"
            label = f"{self.format_name(p.stem, is_pyw=is_pyw)} ({p.parent.name})"
            items.append(
                MenuItem(
                    label,
                    self._make_set_autostart_callback(str(script)),
                    checked=lambda _item, s=str(script), _=is_pyw: (
                        s in self.config.autostart_scripts
                    ),
                )
            )
        return items

    def build_recent_menu(self) -> list[MenuItem]:
        recent_items: list[MenuItem] = []
        for p_str in self.stats.recent:
            p = Path(p_str)
            is_pyw = p.suffix.lower() == ".pyw"
            label = (
                f"{self.format_name(p.stem, is_pyw=is_pyw)} ({p.parent.name})"
                if p.parent.name
                else p.stem
            )
            recent_items.append(
                MenuItem(
                    label,
                    self._make_launch_callback(p_str),
                    enabled=p.exists(),
                )
            )

        if not recent_items:
            recent_items.append(MenuItem("No recent items", _noop, enabled=False))
        return recent_items

    def choose_target_dir(self, icon: Any, _item: MenuItem) -> None:
        def _ask(_root: tk.Tk) -> str:
            return filedialog.askdirectory(
                title="Select Assistant Target Directory",
                initialdir=str(self.config.target_dir)
                if self.config.target_dir.exists()
                else str(Path.home()),
            )

        selected = self._dialog_bridge.run_dialog(_ask)
        if selected:
            self.config.target_dir = Path(selected)
            self._is_first_run = False
            self._save_config()
            self.refresh_state(icon)

    def remove_ignore_dir(self, icon: Any, dir_name: str) -> None:
        to_remove = next(
            (d for d in self.config.ignore_dirs if d.lower() == dir_name.lower()),
            None,
        )
        if to_remove is not None:
            self.config.ignore_dirs.remove(to_remove)
            self._save_config()
            self.refresh_state(icon)

    def refresh_menu(self, icon: Any, _item: MenuItem) -> None:
        self.refresh_state(icon)

    def open_root(self, _icon: Any, _item: MenuItem) -> None:
        try:
            if self.config.target_dir.exists():
                startfile(self.config.target_dir)
            else:
                logging.warning("Target directory does not exist: %s", self.config.target_dir)
        except OSError:
            logging.exception("Failed to open target directory: %s", self.config.target_dir)

    def open_config_file(self, _icon: Any, _item: MenuItem) -> None:
        try:
            if not CONFIG_FILE.exists():
                self._save_config()
            startfile(CONFIG_FILE)
        except OSError:
            logging.exception("Failed to open config file: %s", CONFIG_FILE)

    def set_autostart(self, _icon: Any = None, _item: Any = None) -> None:
        if not globals().get("__compiled__", False):
            logging.warning("Skipped setting autostart: running in dev mode")
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
            logging.info("Successfully set startup on boot")
        except OSError:
            logging.exception("Failed setting autostart registry key.")

    def build_settings_menu(self) -> list[MenuItem]:
        ignore_items = [
            MenuItem(f"\u2796 {name}", self._make_remove_ignore_callback(name))
            for name in sorted(self.config.ignore_dirs)
        ]
        if not ignore_items:
            ignore_items.append(MenuItem("No ignored folders", _noop, enabled=False))

        autostart_label = (
            f"\u26a1 Autostart ({len(self.config.autostart_scripts)}): "
            + ", ".join(Path(s).stem for s in self.config.autostart_scripts)
            if self.config.autostart_scripts
            else "None"
        )

        return [
            MenuItem(f"\U0001f4cd Current Target: {self.config.target_dir}", _noop, enabled=False),
            MenuItem(f"\U0001f4cc v{__version__}", _noop, enabled=False),
            MenuItem(autostart_label, _noop, enabled=False),
            MenuItem("\U0001f4c2 Choose Target Directory...", self.choose_target_dir),
            MenuItem("\U0001f4c4 Open Config File", self.open_config_file),
            MenuItem("\U0001f504 Reload Config", self.refresh_menu),
            MenuItem("\U0001f680 Enable Startup on Boot", self.set_autostart),
            MenuItem("\U0001f6d1 Ignored Folders", Menu(*ignore_items)),
        ]

    def build_main_menu(self) -> list[MenuItem]:
        items: list[MenuItem] = []

        if self._is_first_run:
            items.append(MenuItem("\U0001f44b Welcome to Assistant Launcher", _noop, enabled=False))
            items.append(Menu.SEPARATOR)
            items.append(MenuItem("\U0001f4c2 Choose Target Directory...", self.choose_target_dir))
            items.append(MenuItem("\u2699\ufe0f Settings", Menu(*self.build_settings_menu())))
            items.append(Menu.SEPARATOR)
            items.append(MenuItem("\u274c Exit", lambda _icon, _item: self._exit_app()))
            return items

        if self.config.target_dir.exists() and self.config.target_dir.is_dir():
            tree = self._scanner.scan(self.config.target_dir)
            items.extend(self._build_menu_from_tree(tree))
        else:
            items.append(MenuItem("Target directory not found", _noop, enabled=False))

        items.append(Menu.SEPARATOR)
        items.append(MenuItem("\U0001f558 Recent", Menu(*self.build_recent_menu())))
        items.append(MenuItem("\U0001f680 Set Autostart", Menu(*self.build_autostart_menu())))
        items.append(MenuItem("\u2699\ufe0f Settings", Menu(*self.build_settings_menu())))
        items.append(MenuItem("\U0001f504 Refresh", self.refresh_menu))
        items.append(MenuItem("\U0001f4c2 Open Root", self.open_root))
        items.append(MenuItem("\u274c Exit", lambda _icon, _item: self._exit_app()))
        return items

    def _exit_app(self) -> None:
        if self._root is not None:
            self._root.quit()

    def load_icon_image(self) -> Image.Image:
        icon_source = ICON_FILE if ICON_FILE.exists() else EXE_ICON_FILE
        img = Image.new("RGB", (64, 64), (15, 23, 42))
        if icon_source.exists():
            try:
                return Image.open(icon_source)
            except OSError:
                logging.exception("Failed loading icon file: %s", icon_source)
        return img

    def run(self) -> None:
        for script in self.config.autostart_scripts:
            if Path(script).exists():
                logging.info("Autostarting script: %s", script)
                self.launch(script)
            else:
                logging.warning("Autostart script not found, skipping: %s", script)

        self._root = tk.Tk()
        self._root.withdraw()
        self._root.attributes("-topmost", True)  # pyright: ignore[reportUnknownMemberType]

        self._dialog_bridge.start(self._root)

        icon = Icon(
            APP_NAME,
            self.load_icon_image(),
            title="Assistant Launcher",
            menu=Menu(lambda: self.build_main_menu()),
        )
        icon.run_detached()

        self._root.mainloop()
        icon.stop()
