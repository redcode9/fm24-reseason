# Development

Python tools use only the standard library and target Python 3.10+.

```sh
python3 -B -m unittest discover -s tests/public -v
python3 -B scripts/check_publication.py
python3 -B scripts/check_publication.py --staged
python3 -B scripts/build_release.py
```

The build packages only explicit entries in `publication.json`. It never recursively archives the workspace. Private research, downloaded files, snapshots, old releases, and saves can remain locally without being tracked. The default-deny `.gitignore` is a first boundary; the index checker also catches files force-added outside the allowlist and changed index blobs.

A first-publication scan covered the complete staged history and the release archive. All future changes must pass the same checks. Do not force-add an excluded file or weaken the data boundary to make a check pass.

`toolkit/reference.json` is the frozen compatibility template. `toolkit/release_tools.py` and the supplied module retain the tested gameplay implementation. The public wrapper prepares a private user cache from exact, user-supplied FMFs; it does not publish those data files.

To build a developer module on an Apple Silicon Mac with Xcode command-line tools:

```sh
sh scripts/build_module.sh
```

The rebuild is written to ignored `build/` and is not automatically used. Toolchain differences can change hashes. A rebuild requires its own review and game qualification before becoming a release binary. Never replace the pinned binary without updating provenance, compatibility metadata, and tests.

The released tools are a public preview. Game-data verification from the reference installation and synthetic tooling tests are distinct from a user's first complete installation test.

Cache FMFs must remain outside the entire FM24 user-data tree. FM24 opened duplicate archives placed in the old nested cache during actual startup. The cache-location and legacy-migration tests enforce this boundary; relocating complete verified legacy trees preserves their bytes and the active editor-data selection.

The 0.2.0 reference has six canonical custom module identities in `own_fmfs`, with 53 external Basic dependencies and 59 active FMFs. `filename_aliases` maps the six identities to readable installed basenames. Both resolvers refuse duplicate copies, and launch requires a complete naming convention. Cache payload paths and receipts use the canonical identities, not extra active copies.

The six-module layout is a dataset change, not a filename migration. Honours, awards, profiles, and player histories are combined within their respective modules; identity corrections and the Italy rules replacement remain single modules. The old 51-file selection must not remain active alongside the replacements. The public organizer does not construct the merged data or update existing saves. The 53 external Basic files remain separate because a safe merger of their country rules has not been established.

New module archives contain readable DBC resource titles already, so their reference entries do not need `filename_updates`. The organizer can rename canonical outer filenames while preserving archive bytes. It stages and verifies backups outside FM24, uses exclusive creation for destinations, and rolls back ordinary failures. The legacy write installer refuses alias-enabled manifests rather than creating another canonical set.

For compatibility with older metadata-patch catalogues, the tools still support a complete pinned `filename_updates` table. Those patches replace only the final archive-directory trailer, preserving the preceding payload bytes; the private cache normalizes it back to the canonical pin. The existing synthetic tests retain coverage of bounds, modified payloads, incomplete tables, backups, and rollback. No runtime Zstandard dependency is required.

The FMF directory layout was checked against the [gilet manifest parser](https://github.com/fifteen15-labs/gilet/blob/716bfc80fdabc6ab88be4e4908d9738ffc346b69/crates/fm-save/src/manifest.rs). No third-party parser or compression code is included in the public runtime. Optional precomputed patch tables contain only archive-directory trailers and hashes.
