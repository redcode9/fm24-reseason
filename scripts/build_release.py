"""Build the public tooling preview from the exact publication allowlist."""
from pathlib import Path
import hashlib
import json
import sys
import zipfile

from check_publication import ROOT, check

VERSION = "0.1.2"


def main() -> int:
    manifest = json.loads((ROOT / "publication.json").read_text())
    errors = check(ROOT, manifest)
    if errors:
        raise ValueError("Publication checks failed: " + "; ".join(errors))
    out = ROOT / "dist"
    out.mkdir(exist_ok=True)
    name = f"ReSeason-v{VERSION}-Mac-toolkit"
    archive = out / (name + ".zip")
    if archive.exists():
        raise ValueError("Release archive already exists; preserve or move it before rebuilding.")
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in sorted(manifest["public_files"]):
            source = ROOT / path
            item = zipfile.ZipInfo(name + "/" + path, date_time=(2026, 10, 21, 0, 0, 0))
            item.create_system = 3
            executable = path.endswith((".command", ".sh"))
            item.external_attr = (0o100755 if executable else 0o100644) << 16
            item.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(item, source.read_bytes())
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError("Archive CRC check failed.")
        if len(z.namelist()) != len(manifest["public_files"]):
            raise ValueError("Archive file count differs from allowlist.")
        for path in manifest["public_files"]:
            if z.read(name + "/" + path) != (ROOT / path).read_bytes():
                raise ValueError("Archive content mismatch: " + path)
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    (out / "SHA256SUMS.txt").write_text(checksum + "  " + archive.name + "\n")
    print(json.dumps({"archive": archive.name, "bytes": archive.stat().st_size, "sha256": checksum, "files": len(manifest["public_files"]), "FMF_files_included": 0}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        print("Build stopped: " + str(error), file=sys.stderr)
        raise SystemExit(1)
