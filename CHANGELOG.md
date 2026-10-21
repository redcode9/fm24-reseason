# Changelog

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
