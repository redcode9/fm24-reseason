"""Check the explicit public surface before committing, uploading, or packaging."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "publication.json"
SENSITIVE = (
    rb"/Users/(?!YOURNAME(?:/|$)|USERNAME(?:/|$))[A-Za-z0-9_.-]+/",
    rb"gh[pousr]_[A-Za-z0-9]{20,}",
    rb"github_pat_[A-Za-z0-9_]{40,}",
    rb"sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,}",
    rb"-----BEGIN [A-Z ]*PRIVATE KEY-----",
)
FORBIDDEN_SUFFIXES = {".fm", ".fmf", ".dat", ".cmt", ".sqlite", ".db", ".rar", ".torrent", ".log", ".pyc", ".pem", ".key"}


def file_digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest() if hasattr(hashlib, "file_digest") else hashlib.sha256(handle.read()).hexdigest()


def safe_relative(name: str) -> bool:
    p = PurePosixPath(name)
    return bool(name) and not p.is_absolute() and "\\" not in name and all(x not in {"", ".", ".."} for x in name.split("/"))


def check(root: Path, manifest: dict, staged: bool = False) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    paths = manifest.get("public_files", [])
    if not isinstance(paths, list) or not paths or len(paths) != len(set(paths)):
        return ["Invalid or duplicate publication allowlist."]
    for name in paths:
        if not isinstance(name, str) or not safe_relative(name):
            errors.append("Unsafe allowlist path.")
            continue
        p = root / name
        parts = PurePosixPath(name).parts
        if any((root.joinpath(*parts[:i])).is_symlink() for i in range(1, len(parts) + 1)):
            errors.append(f"Symlink refused: {name}")
            continue
        if not p.is_file():
            errors.append(f"Missing public file: {name}")
            continue
        if p.suffix.lower() in FORBIDDEN_SUFFIXES or any(x in {".env", "__pycache__", ".DS_Store", "node_modules"} for x in p.parts):
            errors.append(f"Private artifact type refused: {name}")
        if p.stat().st_size > 10 * 1024 * 1024:
            errors.append(f"Unexpected large tracked file: {name}")
        content = p.read_bytes()
        if any(re.search(pattern, content) for pattern in SENSITIVE):
            errors.append(f"Potential private path or credential in {name}; matched value withheld.")
        if name in manifest.get("pinned_files", {}) and file_digest(p) != manifest["pinned_files"][name]:
            errors.append(f"Pinned public payload changed: {name}")
    if not set(manifest.get("pinned_files", {})).issubset(paths):
        errors.append("Pinned file outside allowlist.")
    if staged:
        run = subprocess.run(["git", "ls-files", "--stage", "-z"], cwd=root, capture_output=True, check=True)
        tracked = set()
        for row in run.stdout.split(b"\0"):
            if not row:
                continue
            metadata, raw_name = row.split(b"\t", 1)
            mode, oid, _ = metadata.split()
            name = raw_name.decode("utf-8")
            tracked.add(name)
            if mode not in {b"100644", b"100755"}:
                errors.append(f"Non-regular tracked entry refused: {name}")
            if name not in paths:
                errors.append(f"Tracked file outside publication allowlist: {name}")
                continue
            indexed = subprocess.run(["git", "cat-file", "blob", oid.decode()], cwd=root, capture_output=True, check=True).stdout
            if indexed != (root / name).read_bytes():
                errors.append(f"Index differs from reviewed file: {name}")
        if tracked != set(paths):
            errors.append("Git index does not exactly match the public allowlist.")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true", help="Also inspect every actual Git index blob.")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    errors = check(ROOT, manifest, args.staged)
    for item in errors:
        print(item, file=sys.stderr)
    if errors:
        return 1
    print(f"Publication check passed: {len(manifest['public_files'])} explicitly approved files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
