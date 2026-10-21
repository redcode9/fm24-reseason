# Installation

## Before downloading

This release is a **database tooling preview**, not a self-contained mod pack.
The public archive contains no FMFs, no original game database, and no game saves.
You need Steam FM24 **24.4.2 (2081827)** on an Apple Silicon Mac and Python **3.10+**.

The reference integration uses a specific 2026-start Sortitoutsi Basic snapshot plus 51 custom files. Those custom files are not available from the public release. A fresh user without them can use the documentation and setup checker, but cannot reproduce the full tested setup yet. **Downloading Basic alone does not supply the 51 custom files.**

Use the [official download pages](DOWNLOADS.md). Compatibility is checked by file contents, not just filenames. A newer daily update, a renamed unrelated FMF, or the FMScout alternative will not silently pass these checks. Do not replace your working data just to bypass a failure.

## If you already have the compatible data

1. Quit FM24 completely.
2. Extract `ReSeason-v0.1.1-Mac-toolkit.zip` and keep the complete folder together. Check the required retention helper below before launching.
3. Open **New Career.command**. It checks the exact data and game build, prepares or verifies its private cache, and launches FM24 with the initialization module. Installed FMFs and saves are preserved.
4. In FM24 choose **Career → Update 24.3.0 → all 104 compatible editor-data files → Original → Advanced Setup**.
5. For the tested configuration, load Italy down to Serie D and the top divisions of France, Germany, England, Portugal, and Spain. Choose **10 August 2026**. No game-setup preset is distributed.
6. Pick your club, create the career, advance one day, and save under a new name.
7. Quit FM24 normally. Reopen with **Continue Career.command** and load that save. This checks and prepares the same installation automatically, then starts without the initialization module.

**Check Setup.command** is an optional read-only diagnostic. **Prepare ReSeason.command** is optional separate cache preparation. You do not need to run either before a real New Career or Continue Career launch.

Do not combine the custom Italy rules with the original Basic Italy rules. They are an explicit replacement, not two layers.

### Required retention helper

The reference setup also uses the supplied one-line player-retention file. With FM24 closed, check for `FM24_History_Ahron_Retention.ddt` under your Steam FM24 game folder at `data/database/db/2430/edt/permanent/`.

If it is missing, copy `toolkit/payload/extra_data/FM24_History_Ahron_Retention.ddt` from this release into that existing folder. If a file with that name already exists, compare its SHA-256 with `toolkit/reference.json`; keep an exact match and stop if it differs. The public wrapper does not install or replace this helper automatically. Check Setup checks the FMFs and executable; the launcher additionally requires the exact installed helper before starting FM24.

The project adds no startup service, scheduled task, browser automation, or automatic downloader.

## Why these files and the first restart exist

- **FMF database files** supply transfers, profiles, histories, and rules. They are loaded when creating the career.
- **New Career.command** is a convenience launcher for checking the installation, preparing its private cache, and enabling the native initialization module.
- **The native `.dylib` module** addresses FM24 behavior that prevented the edited past honours and award schedules from being initialized correctly with the shifted start date. The game saves the resulting state itself; there is no separate save-file patching step.
- **Continue Career.command** launches without that module. It is a convenience tool, not a special save format. The requirement is a normal continuation without the initialization module.
- **The `.ddt` helper** asks the database loader to retain one specific player referenced by the honours data. It does not implement the season update or award corrections.

The save-and-restart handover is performed **once per new career**, not on every play session. Advancing one day is the checkpoint used in the reference tests; an exact one-day delay has not been established as an engine requirement. Saving is necessary to retain the initialized state, and quitting ends the process containing the module. The documented one-day/save/restart path remains the verified procedure; skipping that handover has not been qualified.

## Windows support

This release supports only the pinned Steam FM24 build on an Apple Silicon Mac. The `.command` launchers, `.dylib` module, arm64 code, and game-build checks are Mac-specific. Renaming the files or copying them to Windows does not provide the same fixes. A Windows implementation needs its own native module, launcher, and game verification; none is included or claimed here.

## Terminal commands

From the extracted release directory:

```sh
python3 scripts/reseason.py new
python3 scripts/reseason.py continue
```

Optional diagnostics are `python3 scripts/reseason.py doctor` and `python3 scripts/reseason.py prepare`. For a launch preview, run `prepare` first, then `new --dry-run` or `continue --dry-run`. A dry run never creates a cache or launches FM24.

Use `--help` for alternate Steam or FM24 user-data locations. Default paths are the standard Steam and FM24 locations under your home folder. A missing or mismatched file stops the operation rather than being replaced with an unverified download.

If macOS blocks an unsigned downloaded command, inspect the source and follow macOS's normal file-opening controls. Do not disable system-wide security protections.

## What to test

Start a fresh career and check the start date, club names, several player histories, past award podiums, and Serie D club lists. Save after one day and confirm that these remain after continuing normally. Report gaps with specific player/competition names and seasons. Do not upload your full save to an issue.
