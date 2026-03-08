import json
import logging
import os
import subprocess
import tkinter as tk
from dataclasses import dataclass
from os import startfile
from pathlib import Path
from sys import argv, executable
from tkinter import filedialog
from typing import Any, Callable, Optional

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

PY_EXTS = (".py", ".pyw")


def _noop(*_args: Any, **_kwargs: Any) -> None:
    return None


def _safe_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [s for s in (str(x).strip() for x in value) if s]


@dataclass
class Config:
    target_dir: Path
    ignore_dirs: set[str]
    autostart_script: Optional[str] = None

    @staticmethod
    def default() -> "Config":
        return Config(
            target_dir=DEFAULT_TARGET_DIR,
            ignore_dirs=set(DEFAULT_IGNORE_DIRS),
            autostart_script=None,
        )

    @staticmethod
    def from_json(data: dict[str, Any]) -> "Config":
        target_raw = data.get("target_dir", str(DEFAULT_TARGET_DIR))
        ignore_raw = data.get("ignore_dirs", list(DEFAULT_IGNORE_DIRS))
        autostart_script = data.get("autostart_script")

        target = Path(target_raw) if isinstance(target_raw, str) else DEFAULT_TARGET_DIR
        ignore = {d.lower() for d in _safe_str_list(ignore_raw)}
        return Config(
            target_dir=target,
            ignore_dirs=ignore,
            autostart_script=str(autostart_script)
            if isinstance(autostart_script, str)
            else None,
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "target_dir": str(self.target_dir),
            "ignore_dirs": sorted(self.ignore_dirs),
            "autostart_script": self.autostart_script,
        }


@dataclass
class Stats:
    recent: list[str]

    @staticmethod
    def default() -> "Stats":
        return Stats(recent=[])

    @staticmethod
    def from_json(data: dict[str, Any]) -> "Stats":
        recent_raw = data.get("recent", [])
        recent = (
            [s for s in recent_raw if isinstance(s, str)]
            if isinstance(recent_raw, list)
            else []
        )
        return Stats(recent=recent)

    def to_json(self) -> dict[str, Any]:
        return {"recent": self.recent}


class JsonStore:
    def __init__(self) -> None:
        self._ensure_storage()

    @staticmethod
    def _ensure_storage() -> None:
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def read(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            logging.warning("Missing JSON file: %s", path)
        except json.JSONDecodeError:
            logging.exception("Invalid JSON in file: %s", path)
        except OSError:
            logging.exception("Failed reading JSON file: %s", path)
        return fallback.copy()

    @staticmethod
    def write(path: Path, payload: dict[str, Any]) -> None:
        try:
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError:
            logging.exception("Failed writing JSON file: %s", path)


class MetaAssistantApp:
    def __init__(self) -> None:
        self._setup_logging()
        self._store = JsonStore()
        self.config = self._load_config()
        self.stats = self._load_stats()
        # 目录缓存
        self._cached_dir_menu: Optional[list[MenuItem]] = None
        self._cached_script_paths: Optional[list[Path]] = None

    def _setup_logging(self) -> None:
        logging.basicConfig(
            filename=LOG_FILE,
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
        )

    def _load_config(self) -> Config:
        if not CONFIG_FILE.exists():
            JsonStore.write(CONFIG_FILE, Config.default().to_json())
        data = JsonStore.read(CONFIG_FILE, Config.default().to_json())
        return Config.from_json(data)

    def _save_config(self) -> None:
        JsonStore.write(CONFIG_FILE, self.config.to_json())

    def _load_stats(self) -> Stats:
        if not STATS_FILE.exists():
            JsonStore.write(STATS_FILE, Stats.default().to_json())
        data = JsonStore.read(STATS_FILE, Stats.default().to_json())
        return Stats.from_json(data)

    def _save_stats(self) -> None:
        JsonStore.write(STATS_FILE, self.stats.to_json())

    def refresh_state(self, icon: Any = None) -> None:
        self.config = self._load_config()
        self.stats = self._load_stats()
        # 清空缓存强制重建
        self._cached_dir_menu = None
        self._cached_script_paths = None
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
        cwd = str(p.parent)

        try:
            if p.suffix.lower() == ".pyw":
                subprocess.Popen(["pythonw", path_str], cwd=cwd)
            else:
                subprocess.Popen(
                    ["cmd", "/k", "python", path_str],
                    cwd=cwd,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
        except FileNotFoundError:
            logging.exception(
                "Python executable not found while launching: %s", path_str
            )
        except OSError:
            logging.exception("Failed launching script: %s", path_str)

    def _make_launch_callback(self, path_str: str) -> Callable[[Any, MenuItem], None]:
        return lambda _icon, _item: self.launch(path_str)

    def _make_remove_ignore_callback(
        self, dir_name: str
    ) -> Callable[[Any, MenuItem], None]:
        return lambda icon, _item: self.remove_ignore_dir(icon, dir_name)

    def _make_set_autostart_callback(
        self, path_str: str
    ) -> Callable[[Any, MenuItem], None]:
        return lambda icon, _item: self._set_autostart_script(icon, path_str)

    def _set_autostart_script(self, icon: Any, path_str: str) -> None:
        self.config.autostart_script = path_str
        self._save_config()
        self.refresh_state(icon)

    def clear_autostart_script(self, icon: Any, _item: MenuItem) -> None:
        self.config.autostart_script = None
        self._save_config()
        self.refresh_state(icon)

    @staticmethod
    def format_name(stem: str, is_dir: bool = False) -> str:
        name = stem.replace("_", " ").replace("-", " ").capitalize()
        icon = "📁" if is_dir else ("⚡" if stem.lower().endswith(".pyw") else "🐍")
        return f"{icon} {name}"

    def build_menu_recursive(self, directory: Path) -> list[MenuItem]:
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
                    if entry.name.lower() in self.config.ignore_dirs:
                        continue
                    submenu_items = self.build_menu_recursive(entry)
                    if submenu_items:
                        items.append(
                            MenuItem(
                                self.format_name(entry.name, is_dir=True),
                                Menu(*submenu_items),
                            )
                        )
                elif entry.suffix.lower() in PY_EXTS:
                    display = self.format_name(entry.stem)
                    abs_path = str(entry.absolute())
                    items.append(
                        MenuItem(
                            display,
                            self._make_launch_callback(abs_path),
                        )
                    )
        except OSError:
            logging.exception("Failed building recursive menu for: %s", directory)
        return items

    def get_all_scripts(self) -> list[Path]:
        if self._cached_script_paths is not None:
            return self._cached_script_paths
        paths: list[Path] = []

        def scan(dir: Path) -> None:
            try:
                for entry in dir.iterdir():
                    if entry.is_dir():
                        if entry.name.lower() in self.config.ignore_dirs:
                            continue
                        scan(entry)
                    elif entry.suffix.lower() in PY_EXTS:
                        paths.append(entry.absolute())
            except OSError:
                logging.exception("Failed scanning scripts: %s", dir)

        if self.config.target_dir.exists() and self.config.target_dir.is_dir():
            scan(self.config.target_dir)
        self._cached_script_paths = paths
        return paths

    def build_autostart_menu(self) -> list[MenuItem]:
        items: list[MenuItem] = []
        items.append(MenuItem("❌ Cancel Autostart", self.clear_autostart_script))
        items.append(Menu.SEPARATOR)

        scripts = self.stats.recent
        if not scripts:
            items.append(MenuItem("No scripts found", _noop, enabled=False))
            return items

        for script in scripts:
            p = Path(script)
            label = f"{self.format_name(p.stem)} ({p.parent.name})"
            items.append(
                MenuItem(
                    label,
                    self._make_set_autostart_callback(str(script)),
                    checked=lambda item, s=str(script): (
                        self.config.autostart_script == s
                    ),
                )
            )
        return items

    def build_recent_menu(self) -> list[MenuItem]:
        recent_items: list[MenuItem] = []
        for p_str in self.stats.recent:
            p = Path(p_str)
            label = (
                f"{self.format_name(p.stem)} ({p.parent.name})"
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

    def _with_tk_dialog(self, callback: Callable[[tk.Tk], Any]) -> Any:
        root: Optional[tk.Tk] = None
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

    def choose_target_dir(self, icon: Any, _item: MenuItem) -> None:
        def _ask(_root: tk.Tk) -> str:
            return filedialog.askdirectory(
                title="Select Assistant Target Directory",
                initialdir=str(self.config.target_dir)
                if self.config.target_dir.exists()
                else str(Path.home()),
            )

        selected = self._with_tk_dialog(_ask)
        if selected:
            self.config.target_dir = Path(selected)
            self._save_config()
            self.refresh_state(icon)

    def remove_ignore_dir(self, icon: Any, dir_name: str) -> None:
        if dir_name in self.config.ignore_dirs:
            self.config.ignore_dirs.remove(dir_name)
            self._save_config()
            self.refresh_state(icon)

    def refresh_menu(self, icon: Any, _item: MenuItem) -> None:
        self.refresh_state(icon)

    def open_root(self, _icon: Any, _item: MenuItem) -> None:
        try:
            if self.config.target_dir.exists():
                startfile(self.config.target_dir)
            else:
                logging.warning(
                    "Target directory does not exist: %s", self.config.target_dir
                )
        except OSError:
            logging.exception(
                "Failed to open target directory: %s", self.config.target_dir
            )

    def open_config_file(self, _icon: Any, _item: MenuItem) -> None:
        try:
            if not CONFIG_FILE.exists():
                self._save_config()
            startfile(CONFIG_FILE)
        except OSError:
            logging.exception("Failed to open config file: %s", CONFIG_FILE)

    def set_autostart(self, _icon: Any = None, _item: Any = None) -> None:
        if Path(executable).name.lower() in ("python.exe", "pythonw.exe"):
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
            MenuItem(f"➖ {name}", self._make_remove_ignore_callback(name))
            for name in sorted(self.config.ignore_dirs)
        ]
        if not ignore_items:
            ignore_items.append(MenuItem("No ignored folders", _noop, enabled=False))

        return [
            MenuItem(
                f"📍 Current Target: {self.config.target_dir}", _noop, enabled=False
            ),
            MenuItem(
                f"⚡ Autostart Script: {Path(self.config.autostart_script).name if self.config.autostart_script else 'None'}",
                _noop,
                enabled=False,
            ),
            MenuItem("📂 Choose Target Directory...", self.choose_target_dir),
            MenuItem("📄 Open Config File", self.open_config_file),
            MenuItem("🔄 Reload Config", self.refresh_menu),
            MenuItem("🚀 Enable Startup on Boot", self.set_autostart),
            MenuItem("🛑 Ignored Folders", Menu(*ignore_items)),
        ]

    def build_main_menu(self) -> list[MenuItem]:
        items: list[MenuItem] = []

        if self.config.target_dir.exists() and self.config.target_dir.is_dir():
            # 使用缓存目录结构，避免每次读文件系统
            if self._cached_dir_menu is None:
                self._cached_dir_menu = self.build_menu_recursive(
                    self.config.target_dir
                )
            items.extend(self._cached_dir_menu)
        else:
            items.append(MenuItem("Target directory not found", _noop, enabled=False))

        items.append(Menu.SEPARATOR)
        items.append(MenuItem("🕘 Recent", Menu(*self.build_recent_menu())))
        # 新增与Recent平行的脚本自启动设置菜单
        items.append(MenuItem("🚀 Set Autostart", Menu(*self.build_autostart_menu())))
        items.append(MenuItem("⚙️ Settings", Menu(*self.build_settings_menu())))
        items.append(MenuItem("🔄 Refresh", self.refresh_menu))
        items.append(MenuItem("📂 Open Root", self.open_root))
        items.append(MenuItem("❌ Exit", lambda icon, _item: icon.stop()))
        return items

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
        # 启动时自动运行配置的自启动脚本
        if self.config.autostart_script:
            logging.info(f"Autostarting script: {self.config.autostart_script}")
            self.launch(self.config.autostart_script)

        icon = Icon(
            APP_NAME,
            self.load_icon_image(),
            title="Assistant Launcher",
            menu=Menu(lambda: self.build_main_menu()),
        )
        icon.run()  # pyright: ignore[reportUnknownMemberType]


if __name__ == "__main__":
    MetaAssistantApp().run()
