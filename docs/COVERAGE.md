# Coverage and work in progress

Two separate things are tracked here: the tools published in v0.2.0, and the data selection tested during development. This distinction matters when deciding whether you can reproduce the setup.

## Published in v0.2.0

- Original setup checker and private-local-cache preparation tools.
- Manual initial-career and normal-continuation launchers.
- Automatic checks and private-cache preparation in both real launch commands.
- Original native initialization module and its source.
- A pinned compatibility manifest and official author download links.
- English instructions, licensing notices, tests, and the original project logo.

The public archive includes **zero FMFs**. The original game, database dumps, research extracts, third-party mods, saves, and private development material are excluded.

The six-module layout replaces the former 51 custom FMFs. It combines four honours files, five award files, 13 profile files, and 27 player-history files; identities and Italy rules remain one module each. The 53 external Basic files remain separate because a safe merger of their country rules has not been established.

The six-module selection was checked in an actual new career on 22 October 2026, at the 10 August 2026 start, after one day, and after a normal restart without the initialization module. Native Editor exports preserve all 3,199,722 source operations, including Italy's advanced rules. The measured coverage below remains partial; consolidation does not fill missing data.

## Reference data tested locally

| Feature | Measured coverage | Remaining work |
| --- | --- | --- |
| Data selection | 59 files: 53 external Basic + six custom modules; new career and restart checked | Public redistribution/rebuild permissions and version availability |
| Past individual awards | 18 editions / 48 places | Other worldwide awards |
| Competition honours | 113 added editions + 11 protected controls | Worldwide competition coverage and full old-season tables/results |
| Additional international honours | Six corrected editions; 49 prior rows preserved | Other competitions and known future hosts/calendars |
| Player career histories | 213,592 imported season/club rows | Complete recent and worldwide coverage |
| Updated player profiles | 39,830 reference targets | Full 2025/26 performance review and remaining runtime differences |
| Italian Serie D | Nine groups / 162 clubs | Coppa Italia Serie D, Scudetto poule, and broader league coverage |
| Real-life player retirements | Sample checked at creation and after restart: 15 people have no player component; two retain one | Worldwide audit and further checks on Hummels and Mertens |
| Delaying future retirements | Not implemented | A separate, tested approach for individual players |

Past awards and honours passed career creation, one day of play, and a normal restart without the initialization module. All 179 checked competition-history/control rows remained identical. This does not mean every competition in the world was checked.

The six additional corrected editions are Club World Cup 2023/2025, Gold Cup 2025, OFC Nations Cup 2024, and CONCACAF Nations League 2024/2025. The 49 preserved rows include Gold Cup 2023 and CONCACAF Nations League 2023.

## Player-history gaps

A row means one player's stint at one club in one season, not a whole player career. The 2025/26 season remains incomplete. In Serie A, the added 2025/26 selection contains 131 rows for 129 people across 15 clubs; it does not complete every squad.

The cold-restart reader resolves 90,902 added target rows. Another 122,690 cannot be associated with a loaded identity by the current reader, so their runtime presence is unverified. This is not evidence that they were deleted. Among resolved people, 649,184 past rows remained unchanged, without lost rows or extra copies. Later retention remains unverified for 21 player IDs / 34 target rows. All 213,592 source rows and their 1,297,431 operations are present in saved change data in all three checkpoints.

Full past match reports, minutes, assists, ratings, and league tables are not reconstructed by this history patch.

## Profile limitations

All 1,892,488 expected profile-change targets are present in the saved change data. The global and recovered cohorts have 365 runtime field differences at creation and 364 after the first day and restart. These include four differing current-ability values. In the separately reviewed 33-player cohort, one bravery value is 17 instead of 18 in all three checkpoints; the other known-field checks pass. Including that case gives 366 differences initially and 365 after the first day and restart. The causes remain unresolved.

Potential ability matches in exposed cases and is not below current ability. No arbitrary attribute or potential-ability increases were used to hide differences. The preceding split-file career had different runtime mismatches despite identical applied source targets; the new counts are reported separately, without attributing the change to a proven cause. This is not a verified full-profile equivalence claim or an official FM27 prediction.

## Player retirements

Some real-life retirements are already reflected in the installed database. Updating player attributes does not by itself check or correct retirement status. There is no completed worldwide audit.

On 22 October 2026, a sample of 17 former players was checked in the actual 59-file career, both at the 10 August 2026 start and after saving and reopening on 11 August. The observations matched at both stages:

| Result | Players |
| --- | --- |
| Non-player records, without a player component | Iniesta, Busquets, Jordi Alba, Thiago Alcântara, Pepe, Bonucci, Varane, Jesús Navas, Pepe Reina, Rakitić, Jonny Evans, Vertonghen and Joe Hart |
| Converted to type 5, without a player component | Toni Kroos and Marcelo |
| Still have a player/non-player record and player attributes; need further review | Mats Hummels and Dries Mertens |

Hummels had already ended his career in 2025, as documented by [Borussia Dortmund](https://www.bvb.de/de/de/aktuelles/news/news.html/2025/8/10/Das-Schoenste-das-mir-passieren-konnte-Mats-Hummels-ein-letztes-Mal-in-Schwarzgelb.html). Mertens' retirement announcement is covered by [Sky Sport](https://sport.sky.it/calcio/giocatori-ritirati-2025). Their records need an in-game check of playing eligibility and retirement state before either case can be called correct or confirmed as still playable. A player component alone does not settle that question.

Four controls—Ronaldo, Messi, Szczęsny and Griezmann—retain player records. These controls check the database state; they are not a worldwide verification of current contracts or retirement announcements.

This is a selected sample, not a global retirement audit. A former player remaining visible in histories or available as staff is expected. International retirement must also be kept separate from retirement from club football. Any corrections must respect the chosen career start date and later returns from retirement.

## League and long-term limitations

In the preceding split-file selection, the same 162 Serie D club IDs appeared in all three checkpoints. Full-season samples for Asti and Fiorenzuola had 34 fixtures, 17 opponents, home and away. The consolidated Italy module preserves the complete native rules and loads Serie D in the new career; a new full fixture census was not performed. Some historical club lineages and nominal date/time differences remain unresolved.

Previous base-module simulations exercised future awards and tournaments over longer periods. They are separate evidence, not a new multi-season simulation of this public tooling package. Some future hosts/calendars remain incorrect.

## Next priorities

1. Establish permissions or rebuild a publicly distributable dataset from usable sources.
2. Complete 2025/26 histories and missing earlier seasons, with source links.
3. Audit real-life retirements worldwide, resolve the two sample cases, and review squads and profiles against recent performances.
4. Complete league rules, historical competitions, and future calendars.
5. Test the public installation path with end users and expand platform support only after testing.
