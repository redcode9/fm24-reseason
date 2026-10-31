# Changelog

## 1.0.1 — 2026-10-31

- Fixed the 2026/27 player development: attributes left blank in FM24 were read as zero, so young players gained too much and some declining veterans gained attributes instead of losing them. Current and potential ability are unchanged.

## 1.0.0 — 2026-10-31

First public release.

- Six data modules for the 2026/27 season: competition honours, player identities, individual awards, Italy and Serie D, player profiles, player histories.
- Player careers: about 850,000 club seasons added for over 300,000 players, up to 2025/26.
- Player profiles developed to the 2026/27 start from 2025/26 minutes, league level and form (about 40,000 players).
- Engine module for Apple Silicon Macs (Steam FM24 24.4.2): imports the 2023 to 2026 award winners, moves the award calendar to 2026 and treats finished tournaments as finished.
- Installers for Mac (`Install.command`) and Windows (`Install.bat`): copy the modules, switch off the sortitoutsi Italy file and check the setup.
- `New Career.command` starts FM24 with the engine module on Mac.
