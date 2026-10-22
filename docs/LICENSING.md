# Licensing and attribution

## Original ReSeason work

Original code, documentation, and original artwork are offered under **PolyForm Noncommercial License 1.0.0**. See [LICENSE](../LICENSE) and [NOTICE](../NOTICE). This is source-available software with use restrictions, not OSI-approved open-source software.

The license permits noncommercial use, modification, and redistribution subject to its terms. Commercial use of rights owned by redcode9 requires a separate written license. Contact the maintainer through the [GitHub profile](https://github.com/redcode9) to discuss permissions; a request is not a granted license.

Only the maintainer can offer additional permissions for the original rights they own. This does not grant anyone, including the maintainer, permission to monetize SEGA material, third-party databases, other authors' mods, or facts that cannot be owned. Any additional permissions and applicable publisher terms remain necessary.

## External rights

Football Manager and its software, databases, content, names, and trademarks remain subject to the rights and terms of Sports Interactive, SEGA, and their licensors. ReSeason is independent and not endorsed by them.

The official FM24 terms include a separate modding schedule and commercial-use restrictions. An original project license cannot waive those terms or supply a missing permission.

- [Official FM24 EULA](https://policy.sega.com/fm24-eula-end-user-license-agreement)
- [Official SEGA Europe EULA](https://privacy.sega.com/en/sega-europe-end-user-license-agreement)
- [PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0)

Sortitoutsi, FMScout, M.C, FusionDB/Cizzu, and other mod authors retain their respective rights. Links are provided in [Downloads](DOWNLOADS.md), rather than copies of their packages. A publicly downloadable or renamed file is not automatically cleared for redistribution.

## Why the dataset is not bundled

The development selection contains SI-demo-derived profile/history data and Italy rules derived from external mods. Redistribution/relicensing permission is not established for the complete set. All six custom FMF modules and the optional competition-name file are therefore excluded from Git and release assets, along with original game/demo files and third-party downloads. Consolidating the former 51 custom files does not change their provenance or grant redistribution permission.

The compatibility manifest contains filenames, hashes, counts, and technical identifiers only. Its legacy `own_fmfs` field means installer-managed entries, not a claim to copyright in their contents. The legacy list of package paths is a reference template, not a declaration that those files are included in this release.

Private-local preparation checks and copies files already supplied by the user. It neither distributes those files nor creates a permission to obtain or use them contrary to their original terms.

## Provenance of published tools

The Python runtime, launcher, C module, and arm64 bridge were created in this project. The previously named upstream launcher was a local development script, not unidentified external code. No research decoder, game executable, game database, or native game function body is bundled. The runtime uses Python's standard library; the native library links the system library on macOS.

The project logo was generated from an original prompt using OpenAI image generation. Its prompt and provenance note are in [assets/LOGO.md](../assets/LOGO.md). It contains no official game or club logo.

The earlier local prototype carried a provisional MIT notice. It is not distributed in this release. This publication does not purport to revoke any permissions already granted under an earlier license.

No license makes a zero-risk legal guarantee. These publication boundaries avoid making a rights claim over the withheld data.
