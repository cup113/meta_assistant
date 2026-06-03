# Assistant Launcher — Domain Context

## Glossary

### Version (__version__)
Single source-of-truth string in `meta_assistant.py`. Bumped manually per release. Displayed in Settings menu and startup log. Follows semver (`0.y.z` for initial development).

### First-run
Detected when `CONFIG_FILE` does not exist in `%APPDATA%/AssistantLauncher/`. On first run, the tray menu shows a welcome guide with a "Choose Target Directory..." prompt instead of scanning a default directory. The guide is dismissed once the user selects a directory or triggers a refresh.

### Ignore dirs
Directory names excluded from script scanning. Stored with original casing in config.json; matching against filesystem entries is case-insensitive (Windows convention). The menu displays the original-cased names.

### Display formatting
File/directory names in the tray menu use `.title()` (each word capitalised) for readability. Internal identifiers (ignore dirs, config) retain their original casing.

## Decisions

- **Why keep casing in ignore dirs?** Windows paths are case-insensitive, so lowercasing on read was unnecessary and lost the user's original formatting in the menu display. Case-insensitive comparison at lookup time is functionally equivalent and preserves aesthetics.
