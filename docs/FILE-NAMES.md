# Six editor-data modules

The reference selection contains **59 FMFs: 53 external Sortitoutsi Basic files and six custom modules**. The six modules replace the former 51 custom files. This combines database changes by function; putting the old files in one ZIP or merely renaming them would not reduce FM24's editor-data list.

| Module | Contains | Former custom files |
| --- | --- | --- |
| 01 — Competition honours | The project's domestic, international, and World Cup honours additions | 4 |
| 02 — Player identities | Player identity corrections | 1 |
| 03 — Individual awards | The project's award editions and podiums | 5 |
| 04 — Italy and Serie D | The Italy rules replacement, including Serie D | 1 |
| 05 — Player profiles | Global and targeted profile updates | 13 |
| 06 — Player histories | All of the project's player-history batches | 27 |

Select all six modules together with the 53 compatible Basic files. The external files retain their original names and attribution. A safe merger of their country rules has not been established; they remain separate. Consolidation does not fill the [remaining data gaps](COVERAGE.md).

## Filenames

Each module has a canonical identity and a readable installed filename. The two-digit prefix identifies its function. The new modules contain readable internal titles already; they do not need the previous release's archive-directory patches.

| Canonical filename | Readable filename |
| --- | --- |
| `FM24_2026_27_01_Competition_Honours.fmf` | `ReSeason 2026-27 - 01 - Competition honours.fmf` |
| `FM24_2026_27_02_Player_Identities.fmf` | `ReSeason 2026-27 - 02 - Player identities.fmf` |
| `FM24_2026_27_03_Individual_Awards.fmf` | `ReSeason 2026-27 - 03 - Individual awards.fmf` |
| `FM24_2026_27_04_Italy_Serie_D.fmf` | `ReSeason 2026-27 - 04 - Italy and Serie D.fmf` |
| `FM24_2026_27_05_Player_Profiles.fmf` | `ReSeason 2026-27 - 05 - Player profiles.fmf` |
| `FM24_2026_27_06_Player_Histories.fmf` | `ReSeason 2026-27 - 06 - Player histories.fmf` |

The exact identities, SHA-256 hashes, and `filename_aliases` mapping are recorded in [`toolkit/reference.json`](../toolkit/reference.json). Keep one copy of each module. A complete set of canonical names or readable names is supported; duplicate copies and partly renamed sets block launch.

With FM24 fully closed, **Organize Editor Data.command** can apply the readable filenames to exact canonical modules. It verifies the data, preserves original copies outside FM24, and leaves the Basic files alone. It does not merge old files into these modules. Running it again after naming is complete makes no changes.

Organizer backups and its receipt are stored outside the entire FM24 user-data folder under `ReSeason FM24 cache/renamed-files-<id>/`. Ordinary failures trigger rollback. If a filesystem interruption occurs, preserve that folder and its receipt before changing files further.

## Replacing the old split selection

With FM24 closed, preserve all 51 former custom files outside the entire FM24 user-data folder. Place the six exact replacement modules in `editor data`, keeping the 53 compatible Basic files. Do not leave old profile, award, honour, or history parts beside their replacement module, even if their filenames differ.

The custom Italy/Serie D module also replaces the original Basic Italy file. Keep that original file out of the active selection. The checker refuses extra FMFs and mismatched contents, so renaming an old part does not make it a valid replacement.

These instructions require legitimately held module files. The public release contains **zero FMFs** and does not provide an automatic merger or a complete public dataset. Renaming or consolidating files does not grant redistribution permission.
