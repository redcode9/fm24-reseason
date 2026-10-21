# Editor-data filenames

The complete reference selection is still **104 FMFs: 53 Basic files and 51 custom files**. Organizing names does not merge files or change database-member payloads.

The 51 custom files use `ReSeason 2026-27 - NN - description.fmf`. The two-digit number preserves the previous alphabetical order among the 51 custom archives; it is not a version or a player count. `Part` identifies separate pieces of one category, all of which remain selected. The 53 Sortitoutsi filenames retain the author's original names.

FM24 displays the DBC resource names embedded inside each FMF archive. Renaming only the outer file does not update this list. The organizer updates the archive's final directory metadata as well; all stored database, details, and image payload bytes remain identical. The full archive hash changes, so both original and updated hashes are pinned in the reference catalogue.

With FM24 fully closed, open **Organize Editor Data.command** once, or run `python3 -B scripts/reseason.py organize`. It verifies the exact installed files and game build, stages complete original backups and updated archives outside FM24, and then applies the names. Occupied destinations, unknown contents, duplicate original/readable copies, symlinks, or an open game cause refusal. Existing readable outer filenames are supported and their exact archive metadata is updated in place. Running the organizer again makes no changes.

Backups and the receipt are stored outside the FM24 folder under `ReSeason FM24 cache/renamed-files-<id>/`. Ordinary failures trigger rollback. If interrupted at the filesystem level, preserve that folder and contact the maintainer before changing files further.

Setup checks, preparation, New Career, and Continue Career support the original dataset or the updated names. A partly renamed set blocks launch until organizing finishes. Legacy ownership receipts and private cache payloads retain canonical identities; private preparation reverses only the directory-metadata patch to verify the original archive pin. These are not additional active FMFs. The legacy write installer is disabled for manifests with aliases to prevent creating a second set. Use the public manual placement guide and organizer instead.

The mapping is stored as `filename_aliases` and the pinned, reversible archive-directory patches as `filename_updates` in `toolkit/reference.json`. Patches contain directory metadata, not database-member payloads, and need no additional compression package at runtime. When installing manually, do not keep both filenames for one row; run the organizer to update the internal titles too. Renaming does not grant permission to redistribute the FMFs.

| Original filename | Readable filename |
| --- | --- |
| `FM24_2026_27_Albi_Domestici_2024_2025.fmf` | `ReSeason 2026-27 - 01 - Competition honours - Domestic - 2024-2025.fmf` |
| `FM24_2026_27_Albi_Int6.fmf` | `ReSeason 2026-27 - 02 - Competition honours - International additions - 2023-2025.fmf` |
| `FM24_2026_27_Coppe_Internazionali_2024_2026.fmf` | `ReSeason 2026-27 - 03 - Competition honours - International cups - 2024-2026.fmf` |
| `FM24_2026_27_Correzioni_Anagrafiche.fmf` | `ReSeason 2026-27 - 04 - Player identity corrections.fmf` |
| `FM24_2026_27_GoldenBoy_2025.fmf` | `ReSeason 2026-27 - 05 - Individual awards - Golden Boy - 2025.fmf` |
| `FM24_2026_27_Italy_SerieD.fmf` | `ReSeason 2026-27 - 06 - League rules - Italy including Serie D.fmf` |
| `FM24_2026_27_Kopa_Yashin_2024_2025.fmf` | `ReSeason 2026-27 - 07 - Individual awards - Kopa and Yashin - 2024-2025.fmf` |
| `FM24_2026_27_Mondiale_2026.fmf` | `ReSeason 2026-27 - 08 - Competition honours - World Cup - 2026.fmf` |
| `FM24_2026_27_Pallone_dOro_e_TheBest_2023_2025.fmf` | `ReSeason 2026-27 - 09 - Individual awards - Ballon d'Or and The Best - 2023-2025.fmf` |
| `FM24_2026_27_Premi_aggiuntivi.fmf` | `ReSeason 2026-27 - 10 - Individual awards - Additional awards.fmf` |
| `FM24_2026_27_Scheda_Declan_Rice.fmf` | `ReSeason 2026-27 - 11 - Player profiles - Declan Rice.fmf` |
| `FM24_2026_27_Schede_Globali_01.fmf` | `ReSeason 2026-27 - 12 - Player profiles - Global - Part 01.fmf` |
| `FM24_2026_27_Schede_Globali_02.fmf` | `ReSeason 2026-27 - 13 - Player profiles - Global - Part 02.fmf` |
| `FM24_2026_27_Schede_Globali_03.fmf` | `ReSeason 2026-27 - 14 - Player profiles - Global - Part 03.fmf` |
| `FM24_2026_27_Schede_Globali_04.fmf` | `ReSeason 2026-27 - 15 - Player profiles - Global - Part 04.fmf` |
| `FM24_2026_27_Schede_Globali_05.fmf` | `ReSeason 2026-27 - 16 - Player profiles - Global - Part 05.fmf` |
| `FM24_2026_27_Schede_Globali_06.fmf` | `ReSeason 2026-27 - 17 - Player profiles - Global - Part 06.fmf` |
| `FM24_2026_27_Schede_Globali_07.fmf` | `ReSeason 2026-27 - 18 - Player profiles - Global - Part 07.fmf` |
| `FM24_2026_27_Schede_Globali_08.fmf` | `ReSeason 2026-27 - 19 - Player profiles - Global - Part 08.fmf` |
| `FM24_2026_27_Schede_Globali_09.fmf` | `ReSeason 2026-27 - 20 - Player profiles - Global - Part 09.fmf` |
| `FM24_2026_27_Schede_Globali_Recuperate_973.fmf` | `ReSeason 2026-27 - 21 - Player profiles - Additional players.fmf` |
| `FM24_2026_27_Schede_prioritarie_13.fmf` | `ReSeason 2026-27 - 22 - Player profiles - Targeted updates - Part 01.fmf` |
| `FM24_2026_27_Schede_prioritarie_19.fmf` | `ReSeason 2026-27 - 23 - Player profiles - Targeted updates - Part 02.fmf` |
| `FM24_2026_27_Storici_2Bundesliga_2025_26.fmf` | `ReSeason 2026-27 - 24 - Player histories - Bundesliga 2 - 2025-26.fmf` |
| `FM24_2026_27_Storici_3_giocatori.fmf` | `ReSeason 2026-27 - 25 - Player histories - Ronaldo Haaland and Lautaro.fmf` |
| `FM24_2026_27_Storici_Bundesliga_2025_26.fmf` | `ReSeason 2026-27 - 26 - Player histories - Bundesliga - 2025-26.fmf` |
| `FM24_2026_27_Storici_EPL_191.fmf` | `ReSeason 2026-27 - 27 - Player histories - Premier League - Part 01.fmf` |
| `FM24_2026_27_Storici_EPL_Integrativi_107.fmf` | `ReSeason 2026-27 - 28 - Player histories - Premier League - Part 02.fmf` |
| `FM24_2026_27_Storici_EPL_Integrativi_74.fmf` | `ReSeason 2026-27 - 29 - Player histories - Premier League - Part 03.fmf` |
| `FM24_2026_27_Storici_ITA_ENG_1047.fmf` | `ReSeason 2026-27 - 30 - Player histories - Italy and England.fmf` |
| `FM24_2026_27_Storici_LaLiga_2025_26.fmf` | `ReSeason 2026-27 - 31 - Player histories - La Liga - 2025-26.fmf` |
| `FM24_2026_27_Storici_Ligue1_2025_26.fmf` | `ReSeason 2026-27 - 32 - Player histories - Ligue 1 - 2025-26 - Part 01.fmf` |
| `FM24_2026_27_Storici_Ligue1_2025_26_Integrativi_73.fmf` | `ReSeason 2026-27 - 33 - Player histories - Ligue 1 - 2025-26 - Part 02.fmf` |
| `FM24_2026_27_Storici_Ligue2_2025_26_Integrativi_24.fmf` | `ReSeason 2026-27 - 34 - Player histories - Ligue 2 - 2025-26.fmf` |
| `FM24_2026_27_Storici_Mondiali_01.fmf` | `ReSeason 2026-27 - 35 - Player histories - Global - Part 01.fmf` |
| `FM24_2026_27_Storici_Mondiali_02.fmf` | `ReSeason 2026-27 - 36 - Player histories - Global - Part 02.fmf` |
| `FM24_2026_27_Storici_Mondiali_03.fmf` | `ReSeason 2026-27 - 37 - Player histories - Global - Part 03.fmf` |
| `FM24_2026_27_Storici_Mondiali_04.fmf` | `ReSeason 2026-27 - 38 - Player histories - Global - Part 04.fmf` |
| `FM24_2026_27_Storici_Mondiali_05.fmf` | `ReSeason 2026-27 - 39 - Player histories - Global - Part 05.fmf` |
| `FM24_2026_27_Storici_Mondiali_06.fmf` | `ReSeason 2026-27 - 40 - Player histories - Global - Part 06.fmf` |
| `FM24_2026_27_Storici_Mondiali_07.fmf` | `ReSeason 2026-27 - 41 - Player histories - Global - Part 07.fmf` |
| `FM24_2026_27_Storici_Mondiali_08.fmf` | `ReSeason 2026-27 - 42 - Player histories - Global - Part 08.fmf` |
| `FM24_2026_27_Storici_Mondiali_09.fmf` | `ReSeason 2026-27 - 43 - Player histories - Global - Part 09.fmf` |
| `FM24_2026_27_Storici_Mondiali_Traiettoria2_01.fmf` | `ReSeason 2026-27 - 44 - Player histories - Global additions - Part 01.fmf` |
| `FM24_2026_27_Storici_Mondiali_Traiettoria3_01.fmf` | `ReSeason 2026-27 - 45 - Player histories - Global additions - Part 02.fmf` |
| `FM24_2026_27_Storici_Mondiali_Traiettoria3_02.fmf` | `ReSeason 2026-27 - 46 - Player histories - Global additions - Part 03.fmf` |
| `FM24_2026_27_Storici_Mondiali_Traiettoria3_03.fmf` | `ReSeason 2026-27 - 47 - Player histories - Global additions - Part 04.fmf` |
| `FM24_2026_27_Storici_Mondiali_Traiettoria3_04.fmf` | `ReSeason 2026-27 - 48 - Player histories - Global additions - Part 05.fmf` |
| `FM24_2026_27_Storici_Primari_Integrativi.fmf` | `ReSeason 2026-27 - 49 - Player histories - Additional seasons.fmf` |
| `FM24_2026_27_Storici_Segunda_2025_26.fmf` | `ReSeason 2026-27 - 50 - Player histories - La Liga 2 - 2025-26.fmf` |
| `FM24_2026_27_TheBest_Portieri_2023_2025.fmf` | `ReSeason 2026-27 - 51 - Individual awards - The Best Goalkeeper - 2023-2025.fmf` |
