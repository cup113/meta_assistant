# Changelog

## [1.3.3] - 2026-06-09

### Build
- Nuitka: replace fake `--windows-installer=inno` with true `--standalone` + `iscc` two-step flow
- Add `--windows-icon-from-ico=assistant.ico` to set exe icon
- Add `installer.iss` with proper AppId and preprocessor-based versioning

## [1.3.2] - 2026-06-09

### Fixed
- Replace fake `--windows-installer=inno` Nuitka option with correct `--standalone` + Inno Setup (`iscc`) two-step build
- Use `--windows-icon-from-ico` (real Nuitka option) to set exe icon

### Added
- `installer.iss` — Inno Setup script with proper `AppId` (generated via `uuid.uuid4()`), version passed via preprocessor variable
- nuitka-build skill: 4 lessons covering `--windows-installer` nonexistence, ISS version variable distinction, `AppId` UUID requirement, and `--windows-icon-from-ico`

### Removed
- Remove "ignore dir" remove-buttons from settings menu; ignored directories displayed as read-only items

### Build
- Split dev and build dependencies to speed up CI

## [1.3.1] - 2026-06-09

### Fixed
- Fix code style violations (line-break formatting) in scanner and app modules

## [1.3.0] - 2026-06-08

### Added
- Package-aware scanning: `ScriptScanner` now detects Python packages (directories with `__init__.py`), folds those with `__main__.py` into a single "▶ Run" submenu entry with `python -m` support, and filters out `_`-prefixed internal modules for a cleaner menu
- Virtual environment support: `ScriptRunner._resolve_python()` walks up the directory tree to find `.venv`/`venv/Scripts/python.exe`, preferring it over the system Python for launching scripts
- Menu item grouping: package directories are rendered as expandable submenus with a bold "▶ Run Package" default action as the first item

### Fixed
- Fix `python -m` package launch failing with `ModuleNotFoundError` because `cwd` was set to the package directory instead of its parent; extracted `ScriptRunner.module_cwd()` to encapsulate the correct path computation

### Removed
- Remove `⚡ Autostart (N): ...` summary label from Settings menu; the per-script autostart toggle submenu remains functional

## [1.2.1] - 2026-06-08

### Changed
- Rebrand tray icon title, welcome dialog, and log output from "Assistant Launcher" to "Meta Assistant"
- Update README title and add project poster image

## [1.2.0] - 2026-06-08

### Changed
- Rebrand display strings from "Assistant Launcher" to "Meta Assistant" across README, tray icon, and logs
- Refactor single-file `meta_assistant.py` into `meta_assistant/` package with 6 modules
- Extract `ScriptScanner` — directory tree walker with case-insensitive ignore-dir filtering and cache, replacing duplicate traversal in menu building and script listing
- Extract `JsonFile[T]` — generic JSON persistence replacing shallow `JsonStore` + repetitive `from_json`/`to_json`/`default` protocol
- Extract `ScriptRunner` with typed `LaunchResult` — subprocess launch logic separated from stat tracking and orchestration
- Extract `TkDialogBridge` — thread-safe tkinter dialog bridge extracted from main class

### Added
- Test suite (`tests/`) with 23 tests covering scanning, persistence, and runner modules
- Pystray type stubs (`typings/pystray/__init__.pyi`) for pyright strict mode
- `types-Pillow` dependency for pyright type checking
- `pytest` runner to CI and release workflows

### Build
- Update Nuitka build command and pyright include to reference `meta_assistant` package instead of single file

## [1.1.3] - 2026-06-05

### Changed
- Replace `sys.executable` name check with `globals().get("__compiled__")` for exe detection when setting autostart, which is reliable even when the Nuitka-built exe is renamed

## [1.1.2] - 2026-06-04

### Fixed
- Strip `TCL_LIBRARY` and `TK_LIBRARY` from subprocess environment before launching `.pyw` scripts, fixing `version conflict for package "Tcl"` crash when Nuitka-built exe spawns system Python with bundled Tcl libraries

## [1.1.1] - 2026-06-04

### Fixed
- Use `shutil.which()` to resolve `pythonw`/`python` executable paths instead of bare names, preventing launch failures when only venv-wrapped paths are on PATH

## [1.1.0] - 2026-06-04

### Fixed
- Fix `.pyw` script detection for subdirectory scripts by passing `is_pyw` parameter explicitly to `format_name()`

### Added
- Log launch command (pythonw vs python) when launching scripts

## [1.0.5] - 2026-06-04

### Changed
- Use persistent `tkinter` root window with dialog queue pattern to fix thread-safety of file dialogs
- Replace `icon.stop()` direct calls with `_exit_app()` to properly clean up tkinter mainloop
- Replace `icon.run()` with `icon.run_detached()` + `root.mainloop()` to support persistent tkinter root

### Fixed
- Fix pyright `reportPrivateUsage`, `reportUnknownMemberType` errors

## [1.0.4] - 2026-06-04

### Changed
- Rename data folder from `AssistantLauncher` to `MetaAssistant`
- Ensure data directory is created before logging setup to prevent crash on first run

## [1.0.3] - 2026-06-04

### Fixed
- Fix zip archive path to point to `dist/meta_assistant.dist/` instead of `dist/`

## [1.0.2] - 2026-06-04

### Fixed
- Use `Compress-Archive` instead of `zip` on Windows runner

## [1.0.1] - 2026-06-04

### Changed
- Split CI and release workflows to avoid duplicate runs
- Release workflow now uses `permissions: contents: write` to fix 403 error

### Fixed
- Nuitka build failure in CI: added `--assume-yes-for-downloads` for Dependency Walker

## [1.0.0] - 2026-06-04

### Added
- CI workflow for linting, type checking, and Nuitka build
- Multiple autostart script support with backward compatibility
- First-run guide dialog
- Build script for Windows development

### Changed
- Refactored to dataclasses and improved type safety
