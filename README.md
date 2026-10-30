<p align="center"><img src="assets/logo.png" width="420" alt="ReSeason"></p>

# ReSeason

**The 2026/27 season, played in Football Manager 2024.**

For a lot of us FM24 is still the best Football Manager: a match engine we trust, a game that runs well, and years of community content behind it. The only thing it's missing is the present. ReSeason brings it up to date. You start your career in August 2026, with current squads and a football world that remembers the last two years: who won what, who got the Ballon d'Or, where every player has been.

It's the season FM27 would cover, on the FM24 you already own.

## What you get

- **A career that starts in August 2026**, built on the free sortitoutsi 2026 start update (squads, transfers, contracts, new players).
- **Recent honours**: 113 competition editions from 2024 to 2026 added to club and national team histories, including the 2026 World Cup.
- **Real award winners**: Ballon d'Or, Kopa and Yashin trophies (2024, 2025), FIFA The Best and Best Goalkeeper (2023 to 2025), Golden Boy (2023 to 2025) and UEFA Player of the Season (2024 to 2026), each with its podium.
- **Player careers**: over 200,000 season-by-season club entries, so history pages show where players actually played.
- **Updated profiles** for about 40,000 players.
- **Serie D**: all nine groups and 162 clubs, fully playable.

On Mac, a small engine module also fixes what FM24 gets wrong when a career starts years after its original database: without it the game throws away the recent award winners, leaves awards like the Ballon d'Or on their old 2023/24 calendar, and doesn't know that tournaments like the 2026 World Cup are already over.

## What you need

- **Football Manager 2024 on Steam**, updated to the final patch (24.4.2).
- **The [sortitoutsi FM24 Data Update](https://sortitoutsi.net/football-manager-data-update/fm24-transfer-update), 2026 start edition.** It's free. ReSeason was tested with the 17 October 2026 version; the installer tells you if yours is different. Newer versions should work but haven't been tested.
- **A Mac with Apple Silicon, or a Windows PC.**

> **Windows:** the engine module is Mac only for now. You get all the data, but the 2023 to 2026 award winners won't appear in the award histories and the big individual awards may run on the wrong dates in your first season.

## Install

### Mac

1. Install the sortitoutsi update as explained on its page.
2. Download `ReSeason-x.y.z.zip` from [Releases](https://github.com/redcode9/fm24-reseason/releases) and unzip it anywhere.
3. Open **Install.command**. The first time, macOS may refuse to open it: right-click it, choose Open, then Open again.

### Windows

1. Install the sortitoutsi update as explained on its page.
2. Download `ReSeason-x.y.z.zip` from [Releases](https://github.com/redcode9/fm24-reseason/releases) and unzip it anywhere.
3. Double-click **Install.bat**. If SmartScreen appears, click More info, then Run anyway.

The installer copies the six ReSeason files into your editor data folder, switches off the sortitoutsi Italy file (ReSeason replaces it) and checks that every file is the right one. You can run it again at any time.

## Start your career

1. **Mac:** open **New Career.command**. **Windows:** start FM24 from Steam.
2. Create a new career and make sure every ReSeason and sortitoutsi file is ticked in the editor data list.
3. Go to Advanced Setup and pick the August 2026 start. To play in Serie D, load Italy down to Serie D.
4. **Mac only:** play one day, save and quit. That's it: from now on start FM24 from Steam as usual and load that save.

Old saves aren't affected. ReSeason needs a new career.

## Known gaps

- Player careers for 2025/26 are still incomplete, Serie A included.
- Honours are updated for the main competitions, not every competition in the world.
- Coppa Italia Serie D and the Serie D title playoff aren't set up yet.
- Ratings come from the sortitoutsi update and the profile updates. There are no FM27-style re-ratings.
- No faces, kits or logos. Keep using your usual graphics packs.

Spotted a wrong winner or a missing season? [Open an issue](https://github.com/redcode9/fm24-reseason/issues) with the player or competition and the season.

## For developers

- `mac/` holds the engine module source. It hooks a few functions of the Steam 24.4.2 Mac build and does nothing on any other build. `mac/build.sh` rebuilds it.
- `release.sh 1.0.0` builds the release zip from the current commit plus the six modules in `data/`.

## Credits

Built on the [sortitoutsi](https://sortitoutsi.net) FM24 data update. The Italy rules start from [M.C's 2026/27 league updates](https://sortitoutsi.net/content/76916/202627-league-updates-fm24-fm26).

ReSeason is a fan project, not affiliated with or endorsed by Sports Interactive or SEGA. Football Manager is a trademark of Sports Interactive.

## License

[PolyForm Noncommercial 1.0.0](LICENSE): free to use, change and share, not for commercial use.
