# Changelog

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
