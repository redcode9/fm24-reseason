<p align="center"><img src="assets/reseason-logo.png" width="500" alt="ReSeason: FM24, season 2026/27"></p>

# ReSeason

ReSeason is a mod for playing Football Manager 2024 in the **2026/27 season**.

**Still in development. The complete database pack is not available to download yet.** The [current release](https://github.com/redcode9/fm24-reseason/releases/tag/v0.2.0) contains setup tools, launchers and instructions. It includes **no database files**.

## What works so far

Checked in our local installation:

| Feature | Status |
| --- | --- |
| Start a new career in August 2026 | Tested |
| Past award winners and podiums | Tested for the awards covered |
| Past competition winners | Tested for the competitions covered |
| Player career histories | Partly updated; recent seasons are still incomplete |
| Player attributes, current ability and potential | Partly updated; accuracy checks are ongoing |
| Playable Italian Serie D | All nine groups loaded; cup rules and full schedules need more testing |
| Real-life player retirements | Partly checked; two sampled cases need further review |

## What still needs work

- Complete the missing player histories, especially **2025/26**.
- Finish checking retirements, squads and player ratings for the 2026/27 start.
- Finish league rules, competition histories and future calendars.
- Make the database files available with permission to share them.

Estimated “FM27” ratings have not been added. Faces, kits, logos and skins are outside this project.

See [coverage and known gaps](docs/COVERAGE.md) for the detailed findings.

## Database files

Our setup uses **53 Sortitoutsi Basic files + six ReSeason modules**. The six modules are not publicly available while permission to share them is unresolved. Basic alone does not provide the full setup.

[Original database download pages](docs/DOWNLOADS.md) · [The six ReSeason modules](docs/FILE-NAMES.md)

## Starting a career

Requires **all 59 compatible database files**, an **Apple Silicon Mac**, Steam **FM24 24.4.2**, database **24.3.0**, and **Python 3.10+**. Windows and Intel Macs are not supported.

1. Follow the [installation guide](docs/INSTALLATION.md) to place the database files and required helper file.
2. Close FM24 and open **New Career.command** from the extracted release folder.
3. Create a career with **DB 24.3.0**, all 59 files, **Original** mode and the **August 2026** start.
4. Advance one day, save and quit. From then on, use **Continue Career.command** to play that save.

Existing saves are not updated. [Manual file placement](docs/MANUAL-INSTALLATION.md).

## License

Our code, documentation and artwork use [PolyForm Noncommercial 1.0.0](LICENSE). Commercial use requires permission from the project owner. Third-party files keep their own terms; see [licensing and credits](docs/LICENSING.md).

An independent fan project, unaffiliated with Sports Interactive or SEGA.
