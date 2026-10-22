# Changelog

## 0.2.0 — 2026-10-22

- Consolidated the local reference dataset from 51 custom FMFs into six functional modules: competition honours, player identities, individual awards, Italy/Serie D, player profiles, and player histories. All 27 history parts become one file; all 13 profile parts become another.
- The compatible selection is now 59 files: six custom modules plus 53 unchanged external Basic dependencies. Safe consolidation of the external country rules has not been established.
- Rebuilt the modules through the native FM24 Editor with complete source/export comparisons. Preserved operation order and values; assigned unique change-record tracking IDs within merged modules. Retained Italy's advanced rules through native Load/Save As.
- Removed the old archive-directory rename patches from the new selection. Native archives already contain readable names. Added explicit retirement metadata for the previous split modules.
- Made setup and launcher counts derive from the manifest, and added regression checks for native modules, readable aliases, and rejection of leftover split files.
- Updated the module catalogue and upgrade instructions. Data coverage gaps remain documented separately from consolidation checks.
- Passed 99 automated tests and an actual career with all 59 files enabled. Rechecked creation, one day, and normal restart without the initialization module: all source history/profile operations remain applied; 18 award editions and 179 competition-history/control rows are retained. Runtime profile differences remain disclosed in the coverage notes.

The public toolkit still contains **zero FMFs**. Consolidation does not change redistribution rights or complete missing worldwide data.

## 0.1.4 — 2026-10-21

- Added readable English names for the 51 custom FMFs, labeled by purpose and numbered to preserve their previous alphabetical order. Sortitoutsi filenames retain their original names.
- Added an optional Organize Editor Data command with exact-content checks, staged originals outside FM24, exclusive new destinations or atomic replacements, and rollback on ordinary failures. Original game files, saves, and Basic FMFs are preserved.
- Updated the embedded archive-directory names that FM24 displays. Precomputed metadata patches preserve all database-member payload bytes; whole-archive hashes change. Private cache preparation restores the canonical trailer in memory for the existing payload pins.
- Setup, preparation, and both launch modes accept original or readable names. Duplicate copies and partly renamed sets block launch. Canonical identities and existing ownership receipts remain valid.
- Published the complete filename mapping and updated manual instructions. Database-member payloads, the native module, and the 104-file selection are unchanged.
- Passed 96 automated tests and actual FM24 startup. The new-career editor-data list displayed the readable names and 104 enabled files out of 104. All 153 stored member payloads remained identical; a new career with the relabeled archives has not yet been qualified.

## 0.1.3 — 2026-10-21

- Moved private FMF caches outside the entire FM24 user-data tree. FM24 was observed opening unintended FMF copies from the previous nested location during startup.
- Added migration that validates complete legacy caches and preserves them outside FM24 with the game closed. Unknown or changed contents are refused; active editor data and saves are preserved.
- Preserved completed, verified installer transactions outside FM24 as well, including their backup FMFs. Ownership receipts and logs stay in place; unfinished transactions are refused.
- Read-only checks now report legacy caches before startup. Added regression coverage for relocation, preservation, unsafe paths, and refusal conditions.
- Replaced the temporary Steam-start workaround with the cache correction. The native gameplay module and compatible database selection are unchanged.
- Verified three actual New Career command launches to the main menu on the reference Mac, including a confirmed normal quit and restart, with the module loaded and no cache or transaction FMFs open. All 104 active FMF hashes were unchanged; 75 automated tests passed.

## 0.1.2 — 2026-10-21

- Added a manual installation guide listing file types, exact destinations, and the boundary between editor data and original game resource archives.
- Documented recovery from the observed language/XML startup errors by launching normally from Steam before retrying the launcher. The underlying cause remains unconfirmed.
- Checked actual main-menu startup after recovery with the initialization module enabled and without it. This was a startup check, not a new-career data qualification.
- No gameplay module, launcher behavior, compatible database selection, or original game file was changed by this documentation update.

## 0.1.1 — 2026-10-21

- New Career and Continue Career now check and prepare the private cache automatically before launching; separate setup commands are optional.
- Automatic preparation refuses to run while FM24 is open or the process check fails. Dry runs remain read-only and require a prepared cache.
- Explained the launcher, native module, retention helper, Mac-only support, and one-time save/restart handover.
- Gameplay module, data compatibility, and the exclusion of all FMFs are unchanged.

## 0.1.0 — 2026-10-21

First public tooling preview of ReSeason for Football Manager 2024, season 2026/27.

- Original branding and an English guide focused on databases and data.
- Setup checking, private-local preparation, and manual career launch tools.
- The original exact-build initialization module and source.
- Official database download links and precise compatibility metadata.
- A readable Included / In progress coverage table and known limitations.
- Noncommercial licensing scoped to original project work.
- Explicit publication allowlists, index scanning, tests, and release checksums.

No FMFs, original game databases, third-party mod archives, or saves are distributed.
End-user installation testing and a rights-cleared data release remain in progress.
