# Coverage and work in progress

Two separate things are tracked here: the tools actually published in v0.1.2, and the data selection tested during development. This distinction matters when deciding whether you can reproduce the setup.

## Published in v0.1.2

- Original setup checker and private-local-cache preparation tools.
- Manual initial-career and normal-continuation launchers.
- Automatic checks and private-cache preparation in both real launch commands.
- Original native initialization module and its source.
- A pinned compatibility manifest and official author download links.
- English instructions, licensing notices, tests, and the original project logo.

The public archive includes **zero FMFs**. The original game, database dumps, research extracts, third-party mods, saves, and private development material are excluded.

## Reference data tested locally

| Feature | Measured coverage | Remaining work |
| --- | --- | --- |
| Data selection | 104 files: 53 external Basic + 51 custom | Public redistribution/rebuild permissions and version availability |
| Past individual awards | 18 editions / 48 places | Other worldwide awards |
| Competition honours | 113 added editions + 11 protected controls | Worldwide competition coverage and full old-season tables/results |
| Additional international honours | Six corrected editions; 49 prior rows preserved | Other competitions and known future hosts/calendars |
| Player career histories | 213,592 imported season/club rows | Complete recent and worldwide coverage |
| Updated player profiles | 39,830 reference targets | Full 2025/26 performance review and remaining runtime differences |
| Italian Serie D | Nine groups / 162 clubs | Coppa Italia Serie D, Scudetto poule, and broader league coverage |
| Retirement changes | None | A tested approach for individual players |

Past awards and honours passed career creation, one day of play, and a normal restart without the initialization module. All 179 checked competition-history/control rows remained identical. This does not mean every competition in the world was checked.

The six additional corrected editions are Club World Cup 2023/2025, Gold Cup 2025, OFC Nations Cup 2024, and CONCACAF Nations League 2024/2025. The 49 preserved rows include Gold Cup 2023 and CONCACAF Nations League 2023.

## Player-history gaps

A row means one player's stint at one club in one season, not a whole player career. The 2025/26 season remains incomplete. In Serie A, the added 2025/26 selection contains 131 rows for 129 people across 15 clubs; it does not complete every squad.

The cold-restart reader resolves 90,900 added target rows. Another 122,692 cannot be associated with a loaded identity by the current reader, so their runtime presence is unverified. This is not evidence that they were deleted. Among resolved people, 649,081 pre-existing rows remained unchanged. Later retention remains unverified for 23 player IDs / 36 target rows.

Full past match reports, minutes, assists, ratings, and league tables are not reconstructed by this history patch.

## Profile limitations

All 1,892,488 expected profile-change targets are present in the saved change data. Actual game values still have 361 differences at creation and 352 after the first day and restart. These include five differing current-ability values initially; four remain readable and different, while one case becomes unverified by the current reader. The cause is unresolved.

The 33 closely reviewed editorial profiles pass their known-field checks in each stage. Potential ability matches in exposed cases and is not below current ability. No arbitrary attribute or potential-ability increases were used to hide differences. This is not a verified full-profile equivalence claim or an official FM27 prediction.

## League and long-term limitations

The same 162 Serie D club IDs appear in all three checkpoints. Full-season samples were checked for Asti in the preceding data selection and Fiorenzuola in the current one: 34 fixtures, 17 opponents, home and away. This is not a census of all 2,754 fixtures. Some historical club lineages and nominal date/time differences remain unresolved.

Previous base-module simulations exercised future awards and tournaments over longer periods. They are separate evidence, not a new multi-season simulation of this public tooling package. Some future hosts/calendars remain incorrect.

## Next priorities

1. Establish permissions or rebuild a publicly distributable dataset from usable sources.
2. Complete 2025/26 histories and missing earlier seasons, with source links.
3. Review profiles against recent performances and investigate runtime differences.
4. Complete league rules, historical competitions, and future calendars.
5. Test the public installation path with end users and expand platform support only after testing.
