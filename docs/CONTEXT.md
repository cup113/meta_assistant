# Meta Assistant — Domain Context

## Glossary

### Version (__version__)
Single source-of-truth string in `meta_assistant.py`. Bumped manually per release. Displayed in Settings menu and startup log. Follows semver (`0.y.z` for initial development).

### First-run
Detected when `CONFIG_FILE` does not exist in `%APPDATA%/MetaAssistant/`. On first run, the tray menu shows a welcome guide with a "Choose Target Directory..." prompt instead of scanning a default directory. The guide is dismissed once the user selects a directory or triggers a refresh.

### Ignore dirs
Directory names excluded from script scanning. Stored with original casing in config.json; matching against filesystem entries is case-insensitive (Windows convention). The menu displays the original-cased names.

### Display formatting
File/directory names in the tray menu use `.title()` (each word capitalised) for readability. Internal identifiers (ignore dirs, config) retain their original casing.

### run_module
A string field on `ScriptNode` (e.g. `"mypkg"`) that marks a directory as a runnable Python package. When present, the tray menu renders the node as a submenu with a bold "▶ Run" first item that executes `python -m <run_module>` via `ScriptRunner.run_as_module()`. Set automatically when the scanner finds a package directory containing `__main__.py`.

### Package-Aware Scanning
The `ScriptScanner` recognizes Python packages by the presence of `__init__.py`. Package directories are treated as atomic units: their `__main__.py` becomes the run entry point, and `_`-prefixed modules are hidden from the menu to reduce noise. Non-package directories continue to display all `.py`/`.pyw` files recursively.

### Venv Discovery
`ScriptRunner._resolve_python()` walks upward from the script directory looking for `.venv`/`venv/Scripts/python.exe`. The first match is used as the Python interpreter for launching scripts, falling back to the system `python` from PATH. This ensures GitHub-cloned projects with local virtual environments work out of the box.

## Decisions

- **Why keep casing in ignore dirs?** Windows paths are case-insensitive, so lowercasing on read was unnecessary and lost the user's original formatting in the menu display. Case-insensitive comparison at lookup time is functionally equivalent and preserves aesthetics.
- **Why filter `_`-prefixed files only inside packages?** In Python convention, `_`-prefix signals internal/private modules within a package. At the project root, a `_setup.py` or `_helper.py` may be intentionally user-facing. The filter is scoped to package directories only.
- **Why fold packages with `__main__.py` but not without?** `__main__.py` is the Python-standard entry point for `python -m`. A package without it is a library — not directly runnable — so we show its non-`_` modules as individual items rather than hiding them behind a package wrapper.
