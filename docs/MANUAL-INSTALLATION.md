# Manual database installation

**The public ZIP contains no FMFs. The 51 custom FMFs are not publicly distributed. Basic alone is not enough.** You must already have legitimate copies of the exact 51 custom files and 53 active Basic files. Original download links are in [Downloads](DOWNLOADS.md); those downloads do not supply the complete custom selection.

Manual placement of the data files is possible. **Copying files alone does not replace the runtime initialization needed for the reference awards and honours fixes.** The complete supported workflow requires Steam FM24 **24.4.2 (2081827)**, database **24.3.0**, and an Apple Silicon Mac.

## Find your folders

The **FM user-data folder** contains `editor data` and your saves. It is separate from the Steam game folder.

- macOS default: `~/Library/Application Support/Sports Interactive/Football Manager 2024/`
- Windows usual location: `%USERPROFILE%\Documents\Sports Interactive\Football Manager 2024\`

Use the actual user-data location configured in FM24 if you changed it or redirected Documents. The public Mac CLI accepts `--user-data` for this location.

The **Steam game folder** contains the installed game. On macOS its default is `~/Library/Application Support/Steam/steamapps/common/Football Manager 2024/`. Use the location of your actual Steam library; the CLI accepts `--steam-game` for an alternative location.

## What goes where

| File | Destination or role |
| --- | --- |
| 53 Basic `.fmf` files | `<FM user-data>/editor data/`, with their exact names and contents. |
| 51 custom `.fmf` files | The same `<FM user-data>/editor data/` folder. These are supplied privately by the user, not by the public ZIP. |
| `FM24_History_Ahron_Retention.ddt` | `<Steam game>/data/database/db/2430/edt/permanent/FM24_History_Ahron_Retention.ddt`. This is the separate one-line retention helper. |
| `libfm24_awards_init_international6_bounded_v2.dylib` | Keep it in `toolkit/engine_fix/` inside the extracted package. The launcher uses a verified copy in its private cache and loads it into the Mac game process in memory during initialization. It does not belong in `editor data` and does not replace the game executable. |
| `.command` and `.py` files | Launcher and checker scaffolding. Keep them in their package locations, with the accompanying folders. They are not database files to copy into `editor data`. |

The exact FMF names and SHA-256 hashes are in [`toolkit/reference.json`](../toolkit/reference.json): `own_fmfs` lists the 51 custom files and `external_basic` lists the 53 active Basic files. `files` records the custom payload sizes. Matching names alone are insufficient.

Keep backup FMFs and toolkit caches outside the entire FM24 user-data folder. FM24 was observed reading private copies in a nested `ReSeason` folder and old installer transaction backups during startup. Since 0.1.3, the launcher uses the sibling `<parent of FM user-data>/ReSeason FM24 cache/` and relocates only verified legacy caches and completed, hash-bound project transactions there with the game closed. Unknown or unfinished contents are preserved in place and cause refusal.

The reference catalogue also records the original 54-file Basic set. Its original Italy file, `sortitoutsi.net FM24 Data Update - Italy (2026 Start).fmf`, is replaced by `FM24_2026_27_Italy_SerieD.fmf`. **Do not keep both in the active editor-data selection.** The supported selection is exactly 104 FMFs; extra FMFs, including original Basic Italy, cause the public checker to refuse it.

## Place the data with FM24 closed

1. Check the exact names and hashes against the reference before copying your legitimately held FMFs into `editor data`. Keep existing exact matches. Stop if a file with the same name has different contents; do not overwrite it. If other mods are present, use a separate configured user-data folder for this selection and leave your existing files intact.
2. Check the DDT destination in the table. If the helper is missing, copy `toolkit/payload/extra_data/FM24_History_Ahron_Retention.ddt` into that existing `2430/edt/permanent/` folder. Keep an existing exact match; stop if it differs. The public wrapper does not install this helper automatically.
3. Keep the extracted toolkit intact. On the supported Mac, `Check Setup.command` checks the FMFs and executable; launching also checks the installed DDT. Follow [Installation](INSTALLATION.md) for the initialization and continuation procedure.

The DDT contains exactly this one line, followed by one LF newline, with no extra commands or text:

```text
"RETAIN_PLAYERS" "71046777"
```

Its size is **28 bytes** and its SHA-256 is:

```text
c905f925e6432036beb2e2cc4ab82f8e12292c4a40a916a0351d29d6b965ed76
```

Copy the supplied DDT rather than recreating it with an editor that may change its encoding or line endings. It retains one referenced player; it does not perform award initialization.

This procedure does not require copying original game databases, database dumps, or `.dat` files. Leave the installed executable and native database files intact. The public package does not supply third-party FMF contents or grant permission to redistribute your private copies; see [Licensing](LICENSING.md).

FM24 itself also has core resource archives ending in `.fmf`, such as `data/shared.fmf` and `data/sitoolkit.fmf`. Those are different from editor-data mods: this procedure does not move or replace them. Optional real-name fixes from other authors can use `.lnc`, `.edt`, or `.dbc` files; they are separate from this release and require their authors' own instructions.

## Initialization and platform limits

For a new career on the supported Mac, **New Career.command** uses the runtime initialization module. Choose database 24.3.0, all 104 compatible files, and **Original** mode as described in [Installation](INSTALLATION.md). The documented handover is to advance one day, save under a new name, quit, and reopen with **Continue Career.command**, which launches without the module. Existing careers are not upgraded by copying FMFs.

You can also run `python3 scripts/reseason.py new` from the extracted package folder instead of opening the `.command` file. This runs the same checks and initialization; it does not bypass them. For missing-language or XML errors, use the [startup recovery instructions](INSTALLATION.md#if-fm24-reports-missing-language-data-or-an-xml-parsing-error).

On Windows, manually placing legitimately held FMFs in the configured user-data folder is possible, but this release includes **no compatible Windows initialization module or launcher**. The Mac `.dylib` and `.command` files do not provide the Windows runtime fixes. Data placement alone is not a complete equivalent of the reference setup, and full Windows support is not claimed.
