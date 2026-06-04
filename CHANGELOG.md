# Changelog

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
