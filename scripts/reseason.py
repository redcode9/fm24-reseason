"""Public, offline bootstrap. Python 3.10+; never installs or downloads FMFs."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import types
import uuid

sys.dont_write_bytecode = True
ROOT = Path(__file__).absolute().parents[1]
FIRST_USE = ("FIRST USE: YOU CANNOT GET ALL DATA FROM THIS ZIP. The public ZIP does "
             "not provide the custom FMF files. Basic alone is NOT enough. You "
             "must already have legitimate, exact copies of every custom FMF "
             "and active Basic dependency listed in toolkit/reference.json "
             "in your editor data folder.")


def first_use(data):
    """Describe the exact selection only after its sealed manifest is validated."""
    custom, basic = len(data["own_fmfs"]), len(data["external_basic"])
    return ("FIRST USE: YOU CANNOT GET ALL DATA FROM THIS ZIP. The public ZIP does "
            f"not provide the {custom} custom FMF files. Basic alone is NOT enough. You "
            f"must already have legitimate, exact copies of all {custom} custom FMFs "
            f"and the {basic} active Basic dependencies in your editor data folder.")


class Refusal(ValueError):
    """An error safe to show without exposing local paths or backend environment."""


def require(condition, message):
    if not condition:
        raise Refusal(message)


def guarded(path):
    path = Path(path).absolute()
    require(".." not in path.parts, "Path traversal refused.")
    require(not any(p.is_symlink() for p in (path, *path.parents)), "Symlink refused.")
    return path


def relative(name):
    require(isinstance(name, str) and name and not any(c in name for c in "\\:\0"),
            "Invalid relative asset path.")
    require(not PurePosixPath(name).is_absolute() and
            all(p not in {"", ".", ".."} for p in name.split("/")), "Path traversal refused.")
    return name


def sha(content):
    return hashlib.sha256(content).hexdigest()


def pin(name, content):
    return {"path": name, "bytes": len(content), "sha256": sha(content)}


def read(path, expected=None):
    path = guarded(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as handle:
        before = os.fstat(handle.fileno())
        require(stat.S_ISREG(before.st_mode), "Expected a regular file.")
        content = handle.read()
        after = os.fstat(handle.fileno())
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    require(identity(before) == identity(after) == identity(guarded(path).stat()),
            "Source changed while being read; nothing was installed.")
    require(expected is None or (len(content) == expected["bytes"] and sha(content) == expected["sha256"]),
            "File SHA or size mismatch; nothing was installed.")
    return content


def context(root):
    root = guarded(root)
    reference = read(root / "toolkit/reference.json")
    seal = read(root / "toolkit/REFERENCE.sha256").decode().strip()
    require(re.fullmatch("[0-9a-f]{64}", seal) and sha(reference) == seal,
            "Reference SHA mismatch.")
    data = json.loads(reference)
    declared = {relative(r["path"]): r for r in data["files"]}
    selected = {"release_tools.py", "install.py", "launch.py", data["module"]["path"]}
    selected.update(r["payload"] for r in data.get("retention_ddt", []))
    selected.update(n for n in declared if n.startswith("source/") and
                    (Path(n).suffix in {".c", ".inc", ".S"} or
                     n == "source/portable_library_derivation.json"))
    assets = {}
    for name in sorted(selected):
        relative(name)
        assets[name] = (root / "toolkit" / name, read(root / "toolkit" / name, declared[name]))
    # Only public documentation is eligible; never sweep this mixed private workspace.
    documents = {"LICENSE", "NOTICE", "README.md"}
    publication = guarded(root / "publication.json")
    if publication.exists():
        documents.update(n for n in json.loads(read(publication))["public_files"]
                         if relative(n).startswith("docs/") and n.endswith(".md"))
    elif guarded(root / "docs/LICENSING.md").exists():
        documents.add("docs/LICENSING.md")
    for name in sorted(documents):
        assets[name] = (root / name, read(root / name))
    backend = types.ModuleType("reseason_backend")
    backend.__file__ = str(root / "toolkit/release_tools.py")
    exec(compile(assets["release_tools.py"][1], backend.__file__, "exec"), backend.__dict__)
    backend.validate_policy(data)  # Keep sealed legacy draft metadata and policy intact.
    rows = [pin(n, content) for n, (_, content) in sorted(assets.items())]
    rows.extend(declared[r["payload"]] for r in data["own_fmfs"])
    manifest = backend.encoded(dict(data, files=sorted(rows, key=lambda r: r["path"])))
    key = sha(reference + manifest + read(Path(__file__)))
    return backend, data, assets, manifest, key


def installed_status(data, user_data, steam_game, *, allow_mixed=False):
    declared = {r["path"]: r for r in data["files"]}
    complete = True
    updated_titles = 0
    for label, rows in (("Custom FMFs", data["own_fmfs"]), ("Basic FMFs", data["external_basic"])):
        missing = mismatch = 0
        for row in rows:
            path = installed_path(data, user_data, row["name"])
            expected = declared[row["payload"]] if "payload" in row else row
            if not path.exists():
                missing += 1
            elif not path.is_file():
                mismatch += 1
            else:
                raw = read(path)
                update = data.get("filename_updates", {}).get(row["name"])
                updated_titles += bool(update and sha(raw) == update["after_sha256"])
                content = canonical_content(data, row["name"], raw)
                if sha(content) != expected["sha256"] or len(content) != expected["bytes"]:
                    mismatch += 1
        print(f"{label}: {len(rows) - missing - mismatch}/{len(rows)} exact; {missing} missing; {mismatch} mismatched.")
        complete &= not (missing or mismatch)
    if data.get("filename_aliases"):
        readable = sum(installed_path(data, user_data, row["name"]).name != row["name"]
                       for row in data["own_fmfs"])
        print(f"Readable custom filenames: {readable}/{len(data['own_fmfs'])}.")
        require(allow_mixed or readable in {0, len(data["own_fmfs"])},
                "Mixed filename conventions; close FM24 and run organize to finish the complete set.")
    if data.get("filename_updates"):
        print(f"Readable internal archive titles: {updated_titles}/{len(data['own_fmfs'])}.")
        require(allow_mixed or not complete or updated_titles in {0, len(data["own_fmfs"])},
                "Mixed internal archive titles; close FM24 and run organize to finish the complete set.")
    binary = guarded(steam_game / "fm.app/Contents/MacOS/fm")
    game_ok = binary.is_file() and sha(read(binary)) == data["game"]["executable_sha256"]
    print("Supported executable SHA: " + ("match." if game_ok else "missing or mismatched."))
    expected_names = {row["name"] for row in data["own_fmfs"] + data["external_basic"]}
    expected_names.update(data.get("filename_aliases", {}).values())
    editor = guarded(user_data / "editor data")
    extra = sum(p.suffix.casefold() == ".fmf" and p.name not in expected_names
                for p in editor.iterdir()) if editor.is_dir() else 0
    print(f"Extra editor FMFs: {extra}.")
    count = len(data["own_fmfs"]) + len(data["external_basic"])
    require(not extra, f"Extra editor FMFs conflict with the exact {count}-file selection; existing files preserved.")
    return complete and game_ok


def installed_path(data, user_data, name):
    canonical = guarded(user_data / "editor data" / relative(name))
    alias = data.get("filename_aliases", {}).get(name)
    if alias is None:
        return canonical
    readable = guarded(user_data / "editor data" / relative(alias))
    require(not (canonical.exists() and readable.exists()),
            "Both original and readable names exist for one FMF; duplicate copies preserved, launch refused.")
    return readable if readable.exists() else canonical


def canonical_content(data, name, content):
    """Normalize the pinned archive-directory change; database members stay verbatim."""
    update = data.get("filename_updates", {}).get(name)
    if update and sha(content) == update["after_sha256"]:
        offset = update["offset"]
        require(len(content) == update["after_bytes"] and
                content[offset:] == bytes.fromhex(update["after_tail_hex"]), "Filename metadata differs.")
        content = content[:offset] + bytes.fromhex(update["before_tail_hex"])
        require(len(content) == update["before_bytes"] and sha(content) == update["before_sha256"],
                "Filename metadata changed database payload bytes.")
    return content


def payload_content(data, source, expected):
    content = read(source)
    if expected["path"].startswith("payload/editor data/"):
        content = canonical_content(data, Path(expected["path"]).name, content)
    require(len(content) == expected["bytes"] and sha(content) == expected["sha256"],
            "File SHA or size mismatch; nothing was installed.")
    return content


def cache_path(root, user_data, key):
    path = guarded(user_data.parent / "ReSeason FM24 cache" / key)
    require(not path.resolve().is_relative_to(guarded(root).resolve()),
            "Private cache must be outside the project/publication folder.")
    require(not path.resolve().is_relative_to(guarded(user_data).resolve()),
            "Private cache must be outside the FM24 user-data folder.")
    return path


def verify_cache(backend, path, manifest):
    require(path.is_dir(), "Run prepare first; a complete private cache is required.")
    require(path.stat().st_uid == os.getuid() and not path.stat().st_mode & 0o077,
            "Private cache permissions are unsafe; existing cache preserved.")
    require(read(path / "release.json") == manifest, "Private cache manifest differs; existing cache preserved.")
    seal = sha(manifest)
    require(read(path / "RELEASE_MANIFEST.sha256").decode().strip() == seal, "Private cache seal mismatch.")
    expected = {r["path"] for r in json.loads(manifest)["files"]} | {"release.json", "RELEASE_MANIFEST.sha256"}
    actual = set()
    for entry in path.rglob("*"):
        guarded(entry)
        if not entry.is_dir():
            actual.add(entry.relative_to(path).as_posix())
    require(actual == expected, "Private cache has missing or unexpected files; existing cache preserved.")
    backend.package(path, seal)


def directory(path, private=False):
    path = guarded(path)
    if not path.exists():
        path.mkdir(mode=0o700)
    require(path.is_dir() and path.stat().st_uid == os.getuid(), "Unsafe cache/log directory.")
    require(not path.stat().st_mode & (0o077 if private else 0o022), "Unsafe cache/log directory permissions.")


def migrate_legacy(ctx, root, user_data):
    """Preserve verified old caches outside every FM24 resource search path."""
    legacy = guarded(user_data / "ReSeason")
    if not legacy.exists():
        return
    backend, data, assets, _, key = ctx
    require(legacy.is_dir() and legacy.stat().st_uid == os.getuid() and
            not legacy.stat().st_mode & 0o077, "Unknown legacy ReSeason folder; existing files preserved.")
    entries = list(legacy.iterdir())
    require(bool(entries), "Unknown empty legacy ReSeason folder; existing files preserved.")
    allowed = set(assets) | {r["payload"] for r in data["own_fmfs"]}
    reference = {k: v for k, v in data.items() if k not in {"files", "filename_aliases", "filename_updates"}}
    identities = {}
    for entry in entries:
        guarded(entry)
        require(re.fullmatch("[0-9a-f]{64}", entry.name) and entry.is_dir(),
                "Unrecognized legacy cache entry; existing files preserved.")
        raw = read(entry / "release.json")
        previous = json.loads(raw)
        require({k: v for k, v in previous.items() if k not in {"files", "filename_aliases", "filename_updates"}} == reference and
                all(r["path"] in allowed for r in previous["files"]),
                "Unrecognized legacy cache manifest; existing files preserved.")
        verify_cache(backend, entry, raw)
        identities[entry.name] = sha(raw)
    require(subprocess.run(["pgrep", "-x", "fm"], capture_output=True).returncode == 1,
            "FM must be closed before relocating legacy caches; existing files preserved.")
    require(set(p.name for p in guarded(legacy).iterdir()) == set(identities),
            "Legacy cache changed during validation; existing files preserved.")
    for entry in entries:
        require(sha(read(entry / "release.json")) == identities[entry.name],
                "Legacy cache changed during validation; existing files preserved.")
        verify_cache(backend, entry, read(entry / "release.json"))
    parent = cache_path(root, user_data, key).parent
    directory(parent, private=True)
    destination = guarded(parent / ("preserved-legacy-" + str(uuid.uuid4())))
    destination.mkdir(mode=0o700)  # Exclusive new container; never replace an existing archive.
    try:
        legacy.rename(destination / "ReSeason")
    except BaseException:
        destination.rmdir()  # Only our own empty reservation; preserve all source files.
        raise
    print("Previous verified caches preserved outside FM24 user data; active editor data unchanged.")


def migrate_transactions(ctx, root, user_data):
    """Archive completed, hash-bound installer backups outside FM24's scanner."""
    source = guarded(user_data / "FM24-History-Community/transactions")
    if not source.exists():
        return
    require(source.is_dir() and source.stat().st_uid == os.getuid() and
            not source.stat().st_mode & 0o022, "Unrecognized transaction folder; existing files preserved.")
    entries = list(source.iterdir())
    if not entries:
        return
    backend, data, _, _, key = ctx
    names = {r["name"] for r in data["own_fmfs"] + data.get("retire_owned", [])}
    names.update(r["dependency_name"] for r in data.get("basic_replacements", []))
    names.update(r["name"] for r in data.get("retention_ddt", []))
    fingerprints = {}
    for entry in entries:
        guarded(entry)
        require(entry.is_dir() and re.fullmatch("[0-9a-f]{32}", entry.name),
                "Unrecognized installation transaction; existing files preserved.")
        raw = read(entry / "journal.json")
        journal = json.loads(raw)
        require(journal.get("schema") == 1 and journal.get("pack_id") == backend.PACK_ID and
                journal.get("transaction_id") == entry.name and
                journal.get("status") in {"COMMITTED", "ROLLED_BACK"},
                "Unknown or unfinished installation transaction; existing files preserved.")
        actions = {r["name"]: r for r in journal["actions"]}
        require(set(actions) <= names, "Unrecognized transaction action; existing files preserved.")
        for path in entry.rglob("*"):
            guarded(path)
            if path.is_dir():
                continue
            name = path.relative_to(entry).as_posix()
            content = read(path)
            if name not in {"journal.json", "installation_receipt.json", "prior_owned_state.json"}:
                parts = name.split("/")
                require(len(parts) == 2 and parts[0] in {"backup", "stage"} and parts[1] in actions,
                        "Unrecognized transaction file; existing files preserved.")
                expected = actions[parts[1]].get("before_sha256" if parts[0] == "backup" else "after_sha256")
                require(expected and sha(content) == expected,
                        "Transaction backup hash mismatch; existing files preserved.")
            fingerprints[path] = sha(content)
    require(subprocess.run(["pgrep", "-x", "fm"], capture_output=True).returncode == 1,
            "FM must be closed before relocating transaction backups; existing files preserved.")
    require(set(p for p in source.rglob("*") if not p.is_dir()) == set(fingerprints),
            "Transaction contents changed; existing files preserved.")
    for path, expected in fingerprints.items():
        require(sha(read(path)) == expected, "Transaction contents changed; existing files preserved.")
    parent = cache_path(root, user_data, key).parent
    directory(parent, private=True)
    destination = guarded(parent / ("preserved-transactions-" + str(uuid.uuid4())))
    destination.mkdir(mode=0o700)
    try:
        source.rename(destination / "transactions")
    except BaseException:
        destination.rmdir()
        raise
    print("Completed installer transactions and backups preserved outside FM24 user data.")


def prepare(ctx, root, user_data, steam_game):
    migrate_legacy(ctx, root, user_data)
    migrate_transactions(ctx, root, user_data)
    backend, data, assets, manifest, key = ctx
    cache = cache_path(root, user_data, key)
    if cache.exists():
        verify_cache(backend, cache, manifest)
        print("Private cache already complete and verified; no files changed.")
        return
    directory(cache.parent, private=True)
    stage = Path(tempfile.mkdtemp(prefix=".prepare-", dir=cache.parent))
    try:
        sources = dict(assets)
        sources.update((r["payload"], (installed_path(data, user_data, r["name"]), None)) for r in data["own_fmfs"])
        for row in json.loads(manifest)["files"]:
            source, _ = sources[row["path"]]
            destination = guarded(stage / row["path"])
            destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with destination.open("xb") as handle:
                handle.write(payload_content(data, source, row))
        (stage / "release.json").write_bytes(manifest)
        (stage / "RELEASE_MANIFEST.sha256").write_text(sha(manifest) + "\n")
        verify_cache(backend, stage, manifest)
        require(installed_status(data, user_data, steam_game), "Installed data changed during prepare.")
        for row in json.loads(manifest)["files"]:
            payload_content(data, sources[row["path"]][0], row)
        require(context(root)[4] == key, "Public inputs changed during prepare; retry with stable inputs.")
        require(not guarded(cache).exists(), "Cache appeared during prepare; existing files preserved.")
        cache.mkdir(mode=0o700)  # Exclusively reserve a NEW destination; never replace a pre-existing directory.
        stage.rename(cache)
    finally:
        if stage.exists():
            shutil.rmtree(guarded(stage))
    print("Private cache verified and prepared outside FM24 user data. Never publish this cache.")


def organize_filenames(ctx, root, user_data, steam_game):
    """Rename exact custom FMFs only; retain canonical receipt identities."""
    if ctx[1].get("filename_updates"):
        return organize_archive_names(ctx, root, user_data, steam_game)
    backend, data, _, _, key = ctx
    require(bool(data.get("filename_aliases")), "This package has no readable filename catalogue.")
    require(subprocess.run(["pgrep", "-x", "fm"], capture_output=True).returncode == 1,
            "FM must be closed before organizing filenames.")
    migrate_legacy(ctx, root, user_data)
    migrate_transactions(ctx, root, user_data)
    require(installed_status(data, user_data, steam_game, allow_mixed=True), "Installed data changed before organizing filenames.")
    declared = {r["path"]: r for r in data["files"]}
    actions = []
    for row in sorted(data["own_fmfs"], key=lambda r: r["name"]):
        source = installed_path(data, user_data, row["name"])
        destination = guarded(user_data / "editor data" / data["filename_aliases"][row["name"]])
        read(source, declared[row["payload"]])
        if source != destination:
            require(not destination.exists(), "Readable filename is occupied; existing files preserved.")
            actions.append((source, destination, declared[row["payload"]]))
    if not actions:
        print(f"All {len(data['own_fmfs'])} custom FMFs already use readable names; no files changed.")
        return
    parent = cache_path(root, user_data, key).parent
    directory(parent, private=True)
    folder = guarded(parent / ("renamed-files-" + str(uuid.uuid4())))
    folder.mkdir(mode=0o700)
    receipt = {"schema": 1, "status": "PREPARED", "files": [
        {"original": a.name, "readable": b.name, "sha256": expected["sha256"]}
        for a, b, expected in actions]}
    record = folder / "receipt.json"
    record.write_bytes(backend.encoded(receipt))
    record.chmod(0o600)
    linked = []
    try:
        for source, destination, expected in actions:
            read(source, expected)
            # Exclusive creation preserves an occupied destination. Both paths
            # refer to the same inode until the old directory entry is removed.
            os.link(guarded(source), guarded(destination), follow_symlinks=False)
            linked.append((source, destination, expected))
            require(source.samefile(destination), "Filename changed concurrently; organizing stopped.")
            read(destination, expected)
            source.unlink()
        require(installed_status(data, user_data, steam_game), "Installed data changed after organizing filenames.")
        receipt["status"] = "COMPLETED"
        record.write_bytes(backend.encoded(receipt))
    except BaseException:
        receipt["status"] = "ROLLBACK_REQUIRED"
        record.write_bytes(backend.encoded(receipt))
        for source, destination, expected in reversed(linked):
            read(destination, expected)
            if not source.exists():
                os.link(guarded(destination), guarded(source), follow_symlinks=False)
            require(source.samefile(destination), "Concurrent edit preserved; manual filename recovery required.")
            destination.unlink()
        receipt["status"] = "ROLLED_BACK"
        record.write_bytes(backend.encoded(receipt))
        raise
    print(f"Organized {len(actions)} custom FMF filenames; contents, Basic files and canonical receipts unchanged.")


def organize_archive_names(ctx, root, user_data, steam_game):
    """Update only archive-directory names, with complete originals outside FM24."""
    backend, data, _, _, key = ctx
    require(subprocess.run(["pgrep", "-x", "fm"], capture_output=True).returncode == 1,
            "FM must be closed before organizing filenames.")
    migrate_legacy(ctx, root, user_data)
    migrate_transactions(ctx, root, user_data)
    require(installed_status(data, user_data, steam_game, allow_mixed=True), "Installed data changed before organizing filenames.")
    actions = []
    for name, update in data["filename_updates"].items():
        source = installed_path(data, user_data, name)
        destination = guarded(user_data / "editor data" / data["filename_aliases"][name])
        before = read(source)
        original = canonical_content(data, name, before)
        require(sha(original) == update["before_sha256"], "Unknown source archive; existing files preserved.")
        after = original[:update["offset"]] + bytes.fromhex(update["after_tail_hex"])
        require(len(after) == update["after_bytes"] and sha(after) == update["after_sha256"],
                "Filename metadata patch differs from its pin.")
        if source != destination or before != after:
            require(source == destination or not destination.exists(), "Readable filename is occupied.")
            actions.append((name, source, destination, before, after))
    if not actions:
        print(f"All {len(data['own_fmfs'])} custom archives already use readable filenames and internal titles; no files changed.")
        return
    parent = cache_path(root, user_data, key).parent
    directory(parent, private=True)
    folder = guarded(parent / ("renamed-files-" + str(uuid.uuid4())))
    folder.mkdir(mode=0o700)
    (folder / "backup").mkdir(mode=0o700)
    (folder / "stage").mkdir(mode=0o700)
    receipt = {"schema": 2, "status": "PREPARING", "files": [
        {"canonical": name, "original": source.name, "readable": destination.name,
         "before_sha256": sha(before), "after_sha256": sha(after)}
        for name, source, destination, before, after in actions]}
    record = folder / "receipt.json"
    record.write_bytes(backend.encoded(receipt))
    record.chmod(0o600)
    applied = []
    try:
        for name, source, destination, before, after in actions:
            require(read(source) == before, "Source changed before organizing archive names.")
            backup = guarded(folder / "backup" / name)
            with backup.open("xb") as handle:
                handle.write(before)
            backup.chmod(0o600)
            stage = guarded(folder / "stage" / name)
            with stage.open("xb") as handle:
                handle.write(after)
            stage.chmod(stat.S_IMODE(source.stat().st_mode))
        receipt["status"] = "PREPARED"
        record.write_bytes(backend.encoded(receipt))
        require(subprocess.run(["pgrep", "-x", "fm"], capture_output=True).returncode == 1,
                "FM opened before organizing archive names; original files preserved.")
        for action in actions:
            name, source, destination, before, after = action
            require(read(source) == before, "Source changed during archive-name update.")
            stage = guarded(folder / "stage" / name)
            require(read(stage) == after, "Staged archive changed.")
            if source == destination:
                os.replace(stage, guarded(destination))
                applied.append(action)
            else:
                os.link(stage, guarded(destination), follow_symlinks=False)
                applied.append(action)
                source.unlink()
            require(read(destination) == after, "Updated archive differs from the expected bytes.")
        require(installed_status(data, user_data, steam_game), "Installed data changed after organizing archive names.")
        receipt["status"] = "COMPLETED"
        record.write_bytes(backend.encoded(receipt))
    except BaseException:
        receipt["status"] = "ROLLBACK_REQUIRED"
        record.write_bytes(backend.encoded(receipt))
        for name, source, destination, before, after in reversed(applied):
            require(read(destination) == after, "Concurrent archive edit preserved; manual recovery required.")
            if source == destination:
                restore = guarded(folder / "stage" / (name + ".restore"))
                require(read(folder / "backup" / name) == before, "Original backup changed; manual recovery required.")
                with restore.open("xb") as handle:
                    handle.write(before)
                restore.chmod(stat.S_IMODE(destination.stat().st_mode))
                os.replace(restore, destination)
            else:
                if source.exists():
                    require(read(source) == before, "Concurrent source edit preserved; manual recovery required.")
                else:
                    with source.open("xb") as handle:
                        handle.write(before)
                    source.chmod(stat.S_IMODE(destination.stat().st_mode))
                destination.unlink()
        receipt["status"] = "ROLLED_BACK"
        record.write_bytes(backend.encoded(receipt))
        raise
    print(f"Organized {len(actions)} custom archive names and internal titles; database payload bytes unchanged. Originals preserved outside FM24.")


def session_plan(plan, user_data, create=False):
    state = guarded(user_data / "FM24-History-Community")
    logs = guarded(state / "logs")
    command = list(plan["command"])
    environment = dict(plan["environment"])
    # Reject dangerous old outputs too, even though every output will be replaced.
    outputs = [command[i + 1] for i, value in enumerate(command[:-1]) if value in {"--stdout", "--stderr"}]
    if environment.get("FM24_AWARDS_LOG"):
        outputs.append(environment["FM24_AWARDS_LOG"])
    for output in outputs:
        require(guarded(output).parent == logs, "Unexpected backend log destination.")
    session = guarded(logs / str(uuid.uuid4()))
    require(not session.exists(), "Log session already exists; existing files preserved.")
    if environment.get("FM24_AWARDS_LOG"):
        environment["FM24_AWARDS_LOG"] = str(session / "module.log")
    for i, value in enumerate(command[:-1]):
        if value in {"--stdout", "--stderr"}:
            command[i + 1] = str(session / ("stdout.log" if value == "--stdout" else "stderr.log"))
        elif value == "--env" and command[i + 1].startswith("FM24_AWARDS_LOG="):
            command[i + 1] = "FM24_AWARDS_LOG=" + environment["FM24_AWARDS_LOG"]
    if create:
        directory(state)
        directory(logs)
        session.mkdir(mode=0o700)
        names = ["stdout.log", "stderr.log"] + (["module.log"] if environment.get("FM24_AWARDS_LOG") else [])
        for name in names:
            os.close(os.open(guarded(session / name), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600))
    return dict(plan, command=command, environment=environment, logs_directory=str(session))


def main(argv=None, *, root=None):
    parser = argparse.ArgumentParser(description=__doc__, epilog=FIRST_USE)
    parser.add_argument("command", choices=("doctor", "prepare", "organize", "new", "continue", "cold"))
    parser.add_argument("--user-data", type=Path, default=Path.home() / "Library/Application Support/Sports Interactive/Football Manager 2024")
    parser.add_argument("--steam-game", type=Path, default=Path.home() / "Library/Application Support/Steam/steamapps/common/Football Manager 2024")
    parser.add_argument("--dry-run", action="store_true", help="Preview new/continue without launching or writing logs.")
    args = parser.parse_args(argv)
    try:
        require(platform.system() == "Darwin" and platform.machine() == "arm64", "Only macOS arm64 is supported.")
        require(not args.dry_run or args.command in {"new", "continue", "cold"}, "--dry-run applies to launch commands only.")
        root = guarded(root or ROOT)
        user_data, steam_game = guarded(args.user_data.expanduser()), guarded(args.steam_game.expanduser())
        ctx = context(root)
        backend, data, _, manifest, key = ctx
        notice = first_use(data)
        print(notice)
        print("Reference SHA and public toolkit: verified.")
        ready = installed_status(data, user_data, steam_game, allow_mixed=args.command == "organize")
        require(ready, "Required installed data is missing or mismatched. " + notice)
        legacy_present = guarded(user_data / "ReSeason").exists()
        print("Legacy private cache inside FM24 user data: " + ("present." if legacy_present else "absent."))
        require(not legacy_present or (args.command != "doctor" and not args.dry_run),
                "Legacy cache inside FM24 user data must be relocated. Close FM24 and run prepare or a real launch; checks remain read-only.")
        transactions = guarded(user_data / "FM24-History-Community/transactions")
        backups_present = transactions.exists() and any(transactions.iterdir())
        print("Legacy installation transactions inside FM24 user data: " + ("present." if backups_present else "absent."))
        require(not backups_present or (args.command != "doctor" and not args.dry_run),
                "Installer backups inside FM24 user data must be relocated. Close FM24 and run prepare or a real launch; checks remain read-only.")
        if args.command == "organize":
            organize_filenames(ctx, root, user_data, steam_game)
        elif args.command == "prepare":
            prepare(ctx, root, user_data, steam_game)
        elif args.command != "doctor":
            if not args.dry_run:
                require(subprocess.run(["pgrep", "-x", "fm"], capture_output=True).returncode == 1,
                        "FM must be closed; game-process check refused launch.")
                prepare(ctx, root, user_data, steam_game)
            cache = cache_path(root, user_data, key)
            verify_cache(backend, cache, manifest)
            mode = "initialise" if args.command == "new" else "cold"
            plan = backend.launch_plan(cache, steam_game, user_data, mode, sha(manifest))
            session_plan(plan, user_data)  # Validate log paths before any launch-side writes.
            print("New career: bounded initialisation module enabled." if mode == "initialise" else
                  "Continue career: normal launch with the module disabled.")
            print("Exact installed data verified. A fresh private log session will be used.")
            if args.dry_run:
                print("DRY RUN: no game launched; no logs or installed files changed.")
            else:
                require(subprocess.run(["pgrep", "-x", "fm"], capture_output=True).returncode == 1,
                        "FM must be closed; game-process check refused launch.")
                plan = session_plan(plan, user_data, create=True)
                subprocess.run(plan["command"], check=True, capture_output=True)
                print("Launch requested. Gameplay results are not certified by this CLI.")
        return 0
    except Refusal as error:
        print("Error: " + str(error), file=sys.stderr)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        print("Error: file or backend validation failed; no installation was attempted. Check doctor and existing cache/log safety.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
