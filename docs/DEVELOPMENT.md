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

Canonical identities in `own_fmfs`, ownership receipts, and private cache payloads stay stable. `filename_aliases` maps these identities to readable installed basenames; both resolvers refuse duplicate copies, and launch requires a complete naming convention. FM24 displays embedded DBC resource names, so a filesystem rename alone is insufficient. The organizer replaces only the final archive-directory trailer using precomputed, pinned metadata patches; the complete preceding payload region remains verbatim. Before applying, it stages and verifies originals and updated archives outside FM24, uses exclusive creation for new names or atomic replacement for an exact existing alias, and rolls back ordinary failures. The private cache normalizes the trailer back to the original canonical pin. No runtime Zstandard dependency is required. Numeric prefixes preserve the previous alphabetical order. The legacy write installer refuses alias-enabled manifests rather than creating another canonical set.

The FMF directory layout was checked against the [gilet manifest parser](https://github.com/fifteen15-labs/gilet/blob/716bfc80fdabc6ab88be4e4908d9738ffc346b69/crates/fm-save/src/manifest.rs). No third-party parser or compression code is included in the public runtime. The precomputed patch table contains only archive-directory trailers and hashes.
