# Changelog

## [0.1.1] - 2026-06-04

### Added
- Automated release workflow on git tag (build → zip → GitHub Release)
- CI workflow for linting, type checking, and Nuitka build

### Fixed
- Nuitka build failure in CI: added `--assume-yes-for-downloads` for Dependency Walker

## [1.0.0] - 2026-06-04

### Changed
- Refactored to dataclasses and improved type safety

## [0.1.0] - 2026-06-04

### Added
- First-run guide dialog
- Multiple autostart script support with backward compatibility
- Build script for Windows development
- Initial project structure
