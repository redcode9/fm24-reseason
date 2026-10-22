# Official database downloads

Download files directly from the original authors and follow their terms. Free download access does not automatically grant permission to rehost or relicense a package.

| Database | Original page | Role in ReSeason |
| --- | --- | --- |
| Sortitoutsi Basic Free FM24 Update — 2026 start | [Sortitoutsi FM24 Data Update](https://sortitoutsi.net/football-manager-data-update/fm24-transfer-update) | Base used by the tested local integration. Choose the free 2026-start edition. |
| Season 2026/27 Update for FM24, by Magicomonta | [FMScout author page](https://www.fmscout.com/a-season-2026-27-update-for-fm24.html) | Alternative season database. Not verified as a drop-in replacement for the pinned Sortitoutsi selection. |
| Additional league updates, by M.C | [2026/27 League Updates](https://sortitoutsi.net/content/76916/202627-league-updates-fm24-fm26) | Original author/source of external league rules. Download and licensing remain with the author. |

**Do not install the two season databases together and assume compatibility.** ReSeason's current launcher checks the specific reference selection.

## Exact versions matter

The integration was tested with the **17 October 2026** Basic 2026-start snapshot. Basic is updated regularly, so the latest download may have different hashes. An author's page is a source link, not a guarantee that an older snapshot is still downloadable. ReSeason does not mirror it or bypass account/payment controls.

Expected filenames, sizes, and SHA-256 hashes are recorded in `toolkit/reference.json`. That file is compatibility metadata; it contains no FMF data.

## Custom project files

The six custom modules in the reference setup contain history, award, profile, identity, and honours changes, plus derived Italy/Serie D rules. They consolidate the former 51 custom files and are distinct from the original site downloads above. Their redistribution rights have not all been established, so they remain outside Git and the public release.

There is currently **no public URL for the complete six-module custom selection**. Existing authorized users may supply their own exact local copies. Other users must wait for a distributable dataset or documented compatible rebuild; downloading the 53 external Basic files is not sufficient. The public filename organizer does not build consolidated modules from the old files.

Renaming a file does not change its provenance, terms, or compatibility hash. Author attribution is retained.

This repository focuses on databases and data. Visual packs and skins are outside its scope.
