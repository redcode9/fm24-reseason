"""Private synthetic fixtures only: no game, installed user files or real FMFs."""
from contextlib import redirect_stderr, redirect_stdout
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest
from unittest import mock
import uuid

PROJECT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("public_reseason", PROJECT / "scripts/reseason.py")
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


def snapshot(root):
    """Include file bytes, permissions and timestamps to detect accidental writes."""
    result = {}
    for path in root.rglob("*"):
        s = path.lstat()
        result[path.relative_to(root).as_posix()] = (
            stat.S_IMODE(s.st_mode), s.st_mtime_ns,
            os.readlink(path) if path.is_symlink() else path.read_bytes() if path.is_file() else None)
    return result


class ReSeasonTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="reseason-synthetic-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / "public project"
        self.user = self.base / "private user data"
        self.game = self.base / "synthetic steam game"
        self.root.mkdir()
        (self.user / "editor data").mkdir(parents=True)
        self.binary = self.game / "fm.app/Contents/MacOS/fm"
        self.binary.parent.mkdir(parents=True)
        self.binary.write_bytes(b"synthetic executable; never executed\n")
        self.data = copy.deepcopy(json.loads((PROJECT / "toolkit/reference.json").read_bytes()))
        # Legacy tests exercise physical names with their own synthetic pins.
        self.data.pop("filename_updates", None)
        self.data["game"]["executable_sha256"] = cli.sha(self.binary.read_bytes())
        self.declared = {r["path"]: r for r in self.data["files"]}
        for i, row in enumerate(self.data["own_fmfs"]):
            content = f"synthetic private custom fixture {i}\n".encode()
            row["sha256"] = cli.sha(content)
            self.declared[row["payload"]].update(cli.pin(row["payload"], content))
            (self.user / "editor data" / row["name"]).write_bytes(content)
        replaced = {r["dependency_name"] for r in self.data["basic_replacements"]}
        for i, row in enumerate(self.data["basic_catalogue"]):
            content = f"synthetic external dependency fixture {i}\n".encode()
            row.update(bytes=len(content), sha256=cli.sha(content))
            if row["name"] not in replaced:
                (self.user / "editor data" / row["name"]).write_bytes(content)
        self.data["external_basic"] = [r for r in self.data["basic_catalogue"] if r["name"] not in replaced]
        catalogue = {r["name"]: r for r in self.data["basic_catalogue"]}
        for row in self.data["basic_replacements"]:
            origin = catalogue[row["dependency_name"]]
            row.update(dependency_sha256=origin["sha256"], dependency_bytes=origin["bytes"])
        selected = {"release_tools.py", "install.py", "launch.py", self.data["module"]["path"]}
        selected.update(r["payload"] for r in self.data["retention_ddt"])
        selected.update(n for n in self.declared if n.startswith("source/") and
                        (Path(n).suffix in {".c", ".inc", ".S"} or n.endswith("portable_library_derivation.json")))
        for name in selected:
            # Only the stdlib backend is real code; all gameplay bytes are inert text.
            content = ((PROJECT / "toolkit" / name).read_bytes() if name.endswith(".py") else
                       b'"RETAIN_PLAYERS" "71046777"\n' if name.endswith(".ddt") else
                       ("synthetic public code asset " + name).encode())
            target = self.root / "toolkit" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            self.declared[name].update(cli.pin(name, content))
        self.data["module"]["sha256"] = self.declared[self.data["module"]["path"]]["sha256"]
        for row in self.data["retention_ddt"]:
            target = self.game / row["steam_relative"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b'"RETAIN_PLAYERS" "71046777"\n')
        for name in ("LICENSE", "NOTICE", "README.md", "docs/LICENSING.md", "docs/SETUP.md"):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("Synthetic public " + name + "\n")
        (self.root / "publication.json").write_text(json.dumps({"public_files": ["docs/LICENSING.md", "docs/SETUP.md"]}))
        (self.root / "docs/private.md").write_text("Do not copy this private document.\n")
        self.seal()
        (self.user / "games").mkdir()
        (self.user / "games/personal.fm").write_bytes(b"synthetic personal save; preserve exactly")
        (self.user / "personal mod.fmf").write_bytes(b"unrelated synthetic mod outside editor data; preserve exactly")
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(cli.platform, "system", return_value="Darwin").start()
        mock.patch.object(cli.platform, "machine", return_value="arm64").start()
        self.process = mock.patch.object(cli.subprocess, "run", side_effect=AssertionError("No real process may be called by tests")).start()

    def seal(self):
        content = (json.dumps(self.data, sort_keys=True, indent=2) + "\n").encode()
        (self.root / "toolkit/reference.json").write_bytes(content)
        (self.root / "toolkit/REFERENCE.sha256").write_text(cli.sha(content) + "\n")

    def invoke(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main([*args, "--user-data", str(self.user), "--steam-game", str(self.game)], root=self.root)
        return code, out.getvalue(), err.getvalue()

    def cache(self):
        return cli.cache_path(self.root, self.user, cli.context(self.root)[4])

    def prepared(self):
        result = self.invoke("prepare")
        self.assertEqual(result[0], 0, result)
        return self.cache()

    def legacy_cache(self):
        cache = self.prepared()
        legacy = self.user / "ReSeason"
        legacy.mkdir(mode=0o700)
        cache.rename(legacy / cache.name)
        cache.parent.rmdir()
        return legacy

    def reseal_cache(self, cache, manifest):
        raw = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
        (cache / "release.json").write_bytes(raw)
        (cache / "RELEASE_MANIFEST.sha256").write_text(cli.sha(raw) + "\n")
        # These fixtures pass ordinary cache verification; migration must also
        # recognize their metadata and limit the permitted payload paths.
        cli.verify_cache(cli.context(self.root)[0], cache, raw)

    def assert_legacy_refused_without_writes(self):
        before = snapshot(self.base)
        result = self.invoke("prepare")
        self.assertEqual(result[0], 1, result)
        self.assertTrue(result[2], result)
        self.assertEqual(before, snapshot(self.base))
        self.process.assert_not_called()

    def transaction(self, transaction_id="1" * 32, status="COMMITTED", names=None):
        """A completed synthetic installer transaction; never run the installer."""
        backend = cli.context(self.root)[0]
        entry = self.user / "FM24-History-Community/transactions" / transaction_id
        (entry / "backup").mkdir(mode=0o700, parents=True)
        (entry / "stage").mkdir(mode=0o700)
        owned_names = {row["name"] for row in self.data["own_fmfs"]}
        actions = []
        for name in names or [self.data["own_fmfs"][0]["name"]]:
            before = ("Synthetic previous FMF: " + name + "\n").encode()
            (entry / "backup" / name).write_bytes(before)
            after = ("Synthetic staged FMF: " + name + "\n").encode() if name in owned_names else None
            if after is not None:
                (entry / "stage" / name).write_bytes(after)
            actions.append({"name": name, "action": "replace" if after is not None else "retire",
                            "before_sha256": cli.sha(before),
                            "after_sha256": cli.sha(after) if after is not None else None})
        journal = {"schema": 1, "pack_id": backend.PACK_ID, "transaction_id": transaction_id,
                   "status": status, "actions": actions}
        (entry / "journal.json").write_text(json.dumps(journal) + "\n")
        (entry / "installation_receipt.json").write_text(json.dumps({"transaction_id": transaction_id}) + "\n")
        (entry / "prior_owned_state.json").write_text(json.dumps({"pack_id": backend.PACK_ID, "owned": {}}) + "\n")
        return entry

    def assert_transaction_refused_without_writes(self):
        before = snapshot(self.base)
        result = self.invoke("prepare")
        self.assertEqual(result[0], 1, result)
        self.assertTrue(result[2], result)
        self.assertEqual(before, snapshot(self.base))
        self.process.assert_not_called()

    def ownership_state(self):
        state = self.user / "FM24-History-Community/owned_state.json"
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(json.dumps({"schema": 1, "pack_id": self.data["pack_id"],
                                     "owned": {row["name"]: row["sha256"] for row in self.data["own_fmfs"]}}) + "\n")
        return state

    def owned(self, index=0):
        return self.user / "editor data" / self.data["own_fmfs"][index]["name"]

    def alias(self, index=0):
        name = self.data["own_fmfs"][index]["name"]
        return self.user / "editor data" / self.data["filename_aliases"][name]

    def use_aliases(self, rows=None):
        for row in self.data["own_fmfs"] if rows is None else rows:
            source = self.user / "editor data" / row["name"]
            source.rename(self.user / "editor data" / self.data["filename_aliases"][row["name"]])

    def synthetic_filename_updates(self):
        """Opaque payloads and precomputed manifest suffixes; no FMF codec needed."""
        before, after, updates = {}, {}, {}
        for index, row in enumerate(self.data["own_fmfs"]):
            name = row["name"]
            # Include the old title in the payload too, to catch global rewrites.
            prefix = bytes(range(256)) + name.encode() + b"\x00opaque database payload\xff"
            old_tail = b"synthetic final manifest\x00" + Path(name).with_suffix(".dbc").name.encode()
            new_tail = b"synthetic final manifest\x00" + Path(self.alias(index).name).with_suffix(".dbc").name.encode()
            before[name], after[name] = prefix + old_tail, prefix + new_tail
            updates[name] = {"offset": len(prefix),
                             "before_sha256": cli.sha(before[name]), "before_bytes": len(before[name]),
                             "after_sha256": cli.sha(after[name]), "after_bytes": len(after[name]),
                             "before_tail_hex": old_tail.hex(), "after_tail_hex": new_tail.hex()}
            row["sha256"] = cli.sha(before[name])
            self.declared[row["payload"]].update(cli.pin(row["payload"], before[name]))
            self.alias(index).unlink(missing_ok=True)
            self.owned(index).write_bytes(before[name])
        self.data["filename_updates"] = updates
        self.seal()
        return before, after

    def test_archive_metadata_organize_preserves_payloads_backups_and_user_data(self):
        for readable in (False, True):
            with self.subTest(readable_source=readable):
                baseline, desired = self.synthetic_filename_updates()
                self.ownership_state()
                if readable:
                    self.use_aliases()
                for row in self.data["own_fmfs"]:
                    cli.installed_path(self.data, self.user, row["name"]).chmod(0o640)
                user, project, game = snapshot(self.user), snapshot(self.root), snapshot(self.game)
                parent = self.cache().parent
                previous = set(parent.glob("renamed-files-*/receipt.json"))
                checks = []

                def closed(command, **kwargs):
                    self.assertEqual(command, ["pgrep", "-x", "fm"])
                    self.assertEqual(user, snapshot(self.user))
                    checks.append(command)
                    if len(checks) == 2:
                        records = set(parent.glob("renamed-files-*/receipt.json")) - previous
                        self.assertEqual(len(records), 1)
                        folder = records.pop().parent
                        for name in baseline:
                            self.assertEqual((folder / "backup" / name).read_bytes(), baseline[name])
                            self.assertEqual((folder / "stage" / name).read_bytes(), desired[name])
                    return subprocess.CompletedProcess(command, 1)

                self.process.side_effect = closed
                result = self.invoke("organize")
                self.assertEqual(result[0], 0, result)
                self.assertEqual(len(checks), 2)
                records = set(parent.glob("renamed-files-*/receipt.json")) - previous
                self.assertEqual(len(records), 1)
                record = records.pop()
                self.assertFalse(record.is_relative_to(self.user))
                self.assertFalse(record.is_relative_to(self.root))
                self.assertEqual(stat.S_IMODE(record.stat().st_mode), 0o600)
                receipt = json.loads(record.read_bytes())
                self.assertEqual(receipt["status"], "COMPLETED")
                self.assertEqual({r["canonical"]: (r["original"], r["readable"], r["before_sha256"], r["after_sha256"])
                                  for r in receipt["files"]},
                                 {name: (self.data["filename_aliases"][name] if readable else name,
                                         self.data["filename_aliases"][name], cli.sha(baseline[name]), cli.sha(desired[name]))
                                  for name in baseline})
                self.assertEqual({p.name for p in (record.parent / "backup").iterdir()}, set(baseline))
                custom = set()
                for index, row in enumerate(self.data["own_fmfs"]):
                    name, update = row["name"], self.data["filename_updates"][row["name"]]
                    custom.update(("editor data/" + name, "editor data/" + self.alias(index).name))
                    self.assertFalse(self.owned(index).exists())
                    self.assertEqual(self.alias(index).read_bytes(), desired[name])
                    self.assertEqual(self.alias(index).read_bytes()[:update["offset"]], baseline[name][:update["offset"]])
                    self.assertEqual(stat.S_IMODE(self.alias(index).stat().st_mode), 0o640)
                    self.assertEqual((record.parent / "backup" / name).read_bytes(), baseline[name])
                actual = snapshot(self.user)
                self.assertEqual({k: v for k, v in user.items() if k not in custom | {"editor data"}},
                                 {k: v for k, v in actual.items() if k not in custom | {"editor data"}})
                self.assertEqual(set(actual) & custom,
                                 {"editor data/" + alias for alias in self.data["filename_aliases"].values()})
                self.assertEqual(project, snapshot(self.root))
                self.assertEqual(game, snapshot(self.game))
                self.process.side_effect = None
                self.process.return_value = subprocess.CompletedProcess([], 1)
                unchanged = snapshot(self.base)
                result = self.invoke("organize")
                self.assertEqual(result[0], 0, result)
                self.assertIn("already use readable filenames and internal titles", result[1])
                self.assertEqual(unchanged, snapshot(self.base))

    def test_archive_metadata_cache_normalizes_baseline_and_retitled_launches(self):
        baseline, desired = self.synthetic_filename_updates()
        state = self.ownership_state()
        receipt = state.read_bytes()
        for readable in (False, True):
            for retitled in (False, True):
                with self.subTest(readable=readable, retitled=retitled):
                    installed = desired if retitled else baseline
                    for index, row in enumerate(self.data["own_fmfs"]):
                        source = cli.installed_path(self.data, self.user, row["name"])
                        target = self.alias(index) if readable else self.owned(index)
                        if source != target:
                            source.rename(target)
                        target.write_bytes(installed[row["name"]])
                    user, project, game = snapshot(self.user), snapshot(self.root), snapshot(self.game)
                    cache = self.prepared()
                    backend, _, _, manifest, _ = cli.context(self.root)
                    cli.verify_cache(backend, cache, manifest)
                    package = json.loads((cache / "release.json").read_bytes())
                    self.assertEqual(package["own_fmfs"], self.data["own_fmfs"])
                    self.assertEqual(package["filename_updates"], self.data["filename_updates"])
                    for row in self.data["own_fmfs"]:
                        self.assertEqual((cache / row["payload"]).read_bytes(), baseline[row["name"]])
                        self.assertEqual(cli.canonical_content(self.data, row["name"], installed[row["name"]]), baseline[row["name"]])
                    plan = backend.installation_plan(cache, self.user, cli.sha(manifest), self.game)
                    self.assertEqual(plan["after_owned"], {name: cli.sha(raw) for name, raw in baseline.items()})
                    self.assertTrue(all(r["action"] == "keep" for r in plan["actions"] if r["name"] in baseline))
                    unchanged = snapshot(self.base)
                    for command, mode in (("new", "initialise"), ("continue", "cold")):
                        result = self.invoke(command, "--dry-run")
                        self.assertEqual(result[0], 0, result)
                        self.assertEqual(backend.launch_plan(cache, self.game, self.user, mode, cli.sha(manifest))["library_injected"], command == "new")
                    self.assertEqual(unchanged, snapshot(self.base))
                    self.assertEqual(user, snapshot(self.user))
                    self.assertEqual(project, snapshot(self.root))
                    self.assertEqual(game, snapshot(self.game))
                    self.assertEqual(receipt, state.read_bytes())
                    shutil.rmtree(cache)  # Rebuild each case, including normalization from retitled sources.
        self.process.assert_not_called()

    def test_partial_internal_title_updates_block_launch_until_organizing_finishes(self):
        _, desired = self.synthetic_filename_updates()
        cache = self.prepared()
        backend, _, _, manifest, _ = cli.context(self.root)
        self.use_aliases()
        name = self.data["own_fmfs"][0]["name"]
        self.alias().write_bytes(desired[name])
        before = snapshot(self.base)
        for command in (("doctor",), ("new",), ("continue",)):
            result = self.invoke(*command)
            self.assertEqual(result[0], 1, result)
            self.assertIn("Mixed internal archive titles", result[2])
        for mode in ("initialise", "cold"):
            with self.assertRaisesRegex(ValueError, "internal-title set"):
                backend.launch_plan(cache, self.game, self.user, mode, cli.sha(manifest))
        self.assertEqual(before, snapshot(self.base))
        self.process.assert_not_called()
        self.process.side_effect = None
        self.process.return_value = subprocess.CompletedProcess([], 1)
        self.assertEqual(self.invoke("organize")[0], 0)
        self.assertEqual(self.invoke("doctor")[0], 0)

    def test_archive_metadata_policy_refuses_malformed_or_incomplete_pins(self):
        self.synthetic_filename_updates()
        valid = copy.deepcopy(self.data["filename_updates"])
        name = self.data["own_fmfs"][0]["name"]
        invalid = [None, [], {k: v for k, v in valid.items() if k != name}, dict(valid, unknown=valid[name])]
        for field, value in (("before_sha256", "0" * 64), ("before_bytes", valid[name]["before_bytes"] + 1),
                             ("after_sha256", "invalid"), ("offset", 0), ("offset", True),
                             ("offset", valid[name]["before_bytes"]), ("after_bytes", True),
                             ("after_bytes", valid[name]["after_bytes"] + 1),
                             ("before_tail_hex", "zz"), ("after_tail_hex", ""),
                             ("after_tail_hex", "00" * 65537)):
            changed = copy.deepcopy(valid)
            changed[name][field] = value
            invalid.append(changed)
        backend = cli.context(self.root)[0]
        for index, updates in enumerate(invalid):
            with self.subTest(case=index):
                self.data["filename_updates"] = updates
                self.seal()
                before = snapshot(self.base)
                with self.assertRaises(ValueError):
                    backend.validate_policy(self.data)
                for command in ("doctor", "prepare", "organize"):
                    result = self.invoke(command)
                    self.assertEqual(result[0], 1, result)
                self.assertEqual(before, snapshot(self.base))
        self.process.assert_not_called()

    def test_archive_metadata_tampered_bytes_and_well_formed_pins_are_refused(self):
        baseline, desired = self.synthetic_filename_updates()
        self.use_aliases()
        name = self.data["own_fmfs"][0]["name"]
        valid = copy.deepcopy(self.data["filename_updates"])
        changed_prefix = bytes([desired[name][0] ^ 1]) + desired[name][1:]
        cases = (("baseline payload", bytes([baseline[name][0] ^ 1]) + baseline[name][1:]),
                 ("retitled payload", changed_prefix), ("retitled trailer", desired[name][:-1] + b"!"),
                 ("after digest", desired[name]), ("before trailer", desired[name]),
                 ("after trailer", desired[name]), ("forged payload digest", changed_prefix))
        for issue, raw in cases:
            with self.subTest(issue=issue):
                self.data["filename_updates"] = copy.deepcopy(valid)
                update = self.data["filename_updates"][name]
                if issue == "after digest":
                    update["after_sha256"] = "0" * 64
                elif issue in {"before trailer", "after trailer"}:
                    field = "before_tail_hex" if issue == "before trailer" else "after_tail_hex"
                    update[field] = "00" + update[field][2:]
                elif issue == "forged payload digest":
                    update["after_sha256"] = cli.sha(raw)
                self.alias().write_bytes(raw)
                self.seal()
                cli.context(self.root)[0].validate_policy(self.data)
                before = snapshot(self.base)
                with self.assertRaises(cli.Refusal):
                    cli.payload_content(self.data, self.alias(), self.declared[self.data["own_fmfs"][0]["payload"]])
                for command in ("doctor", "prepare", "organize", "new", "continue"):
                    result = self.invoke(command)
                    self.assertEqual(result[0], 1, result)
                self.assertEqual(before, snapshot(self.base))
        self.process.assert_not_called()

    def test_archive_metadata_rolls_back_link_replace_and_staging_process_failures(self):
        for operation in ("link", "replace", "busy after staging"):
            with self.subTest(operation=operation):
                baseline, desired = self.synthetic_filename_updates()
                self.ownership_state()
                if operation != "link":
                    self.use_aliases()
                user, project, game = snapshot(self.user), snapshot(self.root), snapshot(self.game)
                previous = set(self.cache().parent.glob("renamed-files-*/receipt.json"))
                self.process.side_effect = None
                self.process.return_value = subprocess.CompletedProcess([], 1)
                calls = 0
                if operation == "busy after staging":
                    self.process.side_effect = [subprocess.CompletedProcess([], 1), subprocess.CompletedProcess([], 0)]
                    result = self.invoke("organize")
                else:
                    original = getattr(cli.os, operation)

                    def fail_third(source, destination, *args, **kwargs):
                        nonlocal calls
                        if Path(destination).parent == self.user / "editor data" and Path(source).name in baseline:
                            calls += 1
                            if calls == 3:
                                self.assertEqual(self.alias().read_bytes(), desired[self.data["own_fmfs"][0]["name"]])
                                raise OSError("injected archive replacement failure")
                        return original(source, destination, *args, **kwargs)

                    with mock.patch.object(cli.os, operation, side_effect=fail_third):
                        result = self.invoke("organize")
                    self.assertEqual(calls, 3)
                self.assertEqual(result[0], 1, result)
                self.assertEqual(self.process.call_count, 2)
                self.process.reset_mock()
                actual = snapshot(self.user)
                for index, row in enumerate(self.data["own_fmfs"]):
                    path = self.owned(index) if operation == "link" else self.alias(index)
                    self.assertEqual(path.read_bytes(), baseline[row["name"]])
                    key = path.relative_to(self.user).as_posix()
                    self.assertEqual(actual[key][0], user[key][0])
                    # Replacement restores the original bytes and mode; mtimes may change.
                    actual[key] = user[key]
                user.pop("editor data")
                actual.pop("editor data")
                self.assertEqual(user, actual)
                self.assertEqual(project, snapshot(self.root))
                self.assertEqual(game, snapshot(self.game))
                records = set(self.cache().parent.glob("renamed-files-*/receipt.json")) - previous
                self.assertEqual(len(records), 1)
                record = records.pop()
                self.assertEqual(json.loads(record.read_bytes())["status"], "ROLLED_BACK")
                for name in baseline:
                    self.assertEqual((record.parent / "backup" / name).read_bytes(), baseline[name])

    def assert_alias_policy_refused(self, aliases):
        backend = cli.context(self.root)[0]
        original = self.data["filename_aliases"]
        self.data["filename_aliases"] = aliases
        try:
            self.seal()
            before = snapshot(self.base)
            with self.assertRaises(ValueError):
                backend.validate_policy(self.data)
            result = self.invoke("doctor")
            self.assertEqual(result[0], 1, result)
            self.assertEqual(before, snapshot(self.base))
            self.process.assert_not_called()
        finally:
            self.data["filename_aliases"] = original
            self.seal()

    def test_filename_alias_reference_is_complete_and_numbered_by_canonical_name(self):
        aliases = self.data["filename_aliases"]
        names = {row["name"] for row in self.data["own_fmfs"]}
        self.assertEqual(len(aliases), 51)
        self.assertEqual(set(aliases), names)
        self.assertEqual(len({alias.casefold() for alias in aliases.values()}), 51)
        for number, name in enumerate(sorted(names), 1):
            self.assertRegex(aliases[name], rf"^ReSeason 2026-27 - {number:02d} - [A-Za-z0-9].+\.fmf$")
        for row in self.data["own_fmfs"]:
            self.assertEqual(row["payload"], "payload/editor data/" + row["name"])
            self.assertNotIn("payload/editor data/" + aliases[row["name"]], self.declared)
        cli.context(self.root)[0].validate_policy(self.data)
        self.process.assert_not_called()

    def test_filename_aliases_are_optional_for_legacy_canonical_installs(self):
        del self.data["filename_aliases"]
        self.seal()
        self.assertEqual(self.invoke("doctor")[0], 0)
        self.prepared()
        before = snapshot(self.base)
        for command in ("new", "continue"):
            result = self.invoke(command, "--dry-run")
            self.assertEqual(result[0], 0, result)
        self.assertEqual(before, snapshot(self.base))
        self.process.assert_not_called()

    def test_filename_alias_policy_rejects_invalid_or_incomplete_mappings(self):
        aliases = self.data["filename_aliases"]
        first, second = sorted(aliases)[:2]
        incomplete = {name: alias for name, alias in aliases.items() if name != first}
        unknown = dict(aliases, unknown=aliases[first])
        swapped = dict(aliases)
        swapped[first], swapped[second] = swapped[second], swapped[first]
        for invalid in (None, [], "not a mapping", incomplete, unknown, swapped,
                        dict(aliases, **{first: 42})):
            with self.subTest(aliases=invalid):
                self.assert_alias_policy_refused(invalid)

    def test_filename_alias_policy_rejects_unsafe_or_colliding_basenames(self):
        aliases = self.data["filename_aliases"]
        first, second = sorted(aliases)[:2]
        for value in ("../outside.fmf", "/outside.fmf", "nested/inside.fmf", "a\\b.fmf",
                      "a:b.fmf", "bad\x00.fmf", "ReSeason 2026-27 - 01 - bad\nname.fmf",
                      first, self.data["external_basic"][0]["name"],
                      aliases[second], aliases[second].swapcase()):
            with self.subTest(alias=value):
                invalid = dict(aliases)
                invalid[first] = value
                self.assert_alias_policy_refused(invalid)

    def test_mixed_names_resolve_individually_but_wrapper_and_backend_refuse_launch(self):
        cache = self.prepared()
        backend, _, _, manifest, _ = cli.context(self.root)
        self.use_aliases(self.data["own_fmfs"][:1])
        self.assertEqual(cli.installed_path(self.data, self.user, self.data["own_fmfs"][0]["name"]), self.alias())
        self.assertEqual(cli.installed_path(self.data, self.user, self.data["own_fmfs"][1]["name"]), self.owned(1))
        before = snapshot(self.base)
        for command in (("doctor",), ("prepare",), ("new",), ("continue",),
                        ("new", "--dry-run"), ("continue", "--dry-run")):
            result = self.invoke(*command)
            self.assertEqual(result[0], 1, result)
            self.assertIn("Mixed filename conventions", result[2])
        for mode in ("initialise", "cold"):
            with self.assertRaisesRegex(ValueError, "complete filename set"):
                backend.launch_plan(cache, self.game, self.user, mode, cli.sha(manifest))
        self.assertEqual(before, snapshot(self.base))
        self.process.assert_not_called()

    def test_prepare_from_aliases_keeps_canonical_payloads_and_ownership(self):
        self.ownership_state()
        self.use_aliases()
        before, game = snapshot(self.user), snapshot(self.game)
        result = self.invoke("doctor")
        self.assertEqual(result[0], 0, result)
        self.assertIn("51/51 exact", result[1])
        self.assertIn("53/53 exact", result[1])
        self.assertIn("Extra editor FMFs: 0.", result[1])
        cache = self.prepared()
        package = json.loads((cache / "release.json").read_bytes())
        self.assertEqual(package["own_fmfs"], self.data["own_fmfs"])
        self.assertEqual(package["filename_aliases"], self.data["filename_aliases"])
        for index, row in enumerate(self.data["own_fmfs"]):
            self.assertEqual(cli.installed_path(self.data, self.user, row["name"]), self.alias(index))
            self.assertEqual((cache / row["payload"]).read_bytes(), self.alias(index).read_bytes())
            self.assertFalse((cache / "payload/editor data" / self.alias(index).name).exists())
        self.assertEqual(before, snapshot(self.user))
        self.assertEqual(game, snapshot(self.game))
        self.process.assert_not_called()

    def test_real_new_and_continue_launch_from_aliases_with_canonical_ownership(self):
        state = self.ownership_state()
        self.use_aliases()
        installed, saves, game, receipt = (snapshot(self.user / "editor data"),
                                          snapshot(self.user / "games"), snapshot(self.game), state.read_bytes())
        self.process.side_effect = lambda command, **kwargs: subprocess.CompletedProcess(command, 1 if command[0] == "pgrep" else 0)
        for command in ("new", "continue"):
            result = self.invoke(command)
            self.assertEqual(result[0], 0, result)
            actual = self.process.call_args.args[0]
            self.assertEqual(actual[:2], ["open", "-n"])
            environment = dict(actual[i + 1].split("=", 1)
                               for i, value in enumerate(actual[:-1]) if value == "--env")
            self.assertEqual(bool(environment["DYLD_INSERT_LIBRARIES"]), command == "new")
        backend, _, _, manifest, _ = cli.context(self.root)
        plan = backend.installation_plan(self.cache(), self.user, cli.sha(manifest), self.game)
        expected = {row["name"]: row["sha256"] for row in self.data["own_fmfs"]}
        self.assertEqual(plan["after_owned"], expected)
        self.assertTrue(all(row["action"] == "keep" for row in plan["actions"] if row["name"] in expected))
        self.assertEqual(receipt, state.read_bytes())
        self.assertEqual(installed, snapshot(self.user / "editor data"))
        self.assertEqual(saves, snapshot(self.user / "games"))
        self.assertEqual(game, snapshot(self.game))

    def test_both_names_refuse_in_wrapper_and_backend_even_for_identical_content(self):
        cache = self.prepared()
        backend, _, _, manifest, _ = cli.context(self.root)
        self.alias().write_bytes(self.owned().read_bytes())
        before = snapshot(self.base)
        for command in (("doctor",), ("prepare",), ("organize",), ("new",), ("continue",),
                        ("new", "--dry-run"), ("continue", "--dry-run")):
            result = self.invoke(*command)
            self.assertEqual(result[0], 1, result)
            self.assertIn("Both original and readable", result[2])
        for mode in ("initialise", "cold"):
            with self.assertRaisesRegex(ValueError, "Both canonical and readable"):
                backend.launch_plan(cache, self.game, self.user, mode, cli.sha(manifest))
        self.assertEqual(before, snapshot(self.base))
        self.process.assert_not_called()

    def test_alias_symlinks_and_mismatched_bytes_are_refused_without_writes(self):
        self.use_aliases()
        original = self.alias().read_bytes()
        self.alias().write_bytes(b"wrong readable variant")
        before = snapshot(self.base)
        for command in ("prepare", "organize"):
            result = self.invoke(command)
            self.assertEqual(result[0], 1, result)
            self.assertIn("1 mismatched", result[1])
            self.assertEqual(before, snapshot(self.base))
        self.alias().unlink()
        external = self.base / "external synthetic alias"
        external.write_bytes(original)
        self.alias().symlink_to(external)
        before = snapshot(self.base)
        for command in ("doctor", "prepare", "organize"):
            result = self.invoke(command)
            self.assertEqual(result[0], 1, result)
            self.assertIn("Symlink refused", result[2])
            self.assertEqual(before, snapshot(self.base))
        self.process.assert_not_called()

    def test_organize_preserves_inodes_and_noncustom_files_and_is_idempotent(self):
        self.ownership_state()
        project, game, user = snapshot(self.root), snapshot(self.game), snapshot(self.user)
        inodes = {row["name"]: self.owned(index).stat().st_ino
                  for index, row in enumerate(self.data["own_fmfs"])}
        self.process.side_effect = None
        self.process.return_value = subprocess.CompletedProcess([], 1)
        with mock.patch.object(cli.os, "link", wraps=os.link) as link:
            result = self.invoke("organize")
            self.assertEqual(result[0], 0, result)
            self.assertEqual(link.call_count, 51)
            expected = dict(user)
            for index, row in enumerate(self.data["own_fmfs"]):
                self.assertFalse(self.owned(index).exists())
                self.assertEqual(self.alias(index).stat().st_ino, inodes[row["name"]])
                expected["editor data/" + self.alias(index).name] = expected.pop("editor data/" + row["name"])
            actual = snapshot(self.user)
            # Adding/removing directory entries changes only the editor folder timestamp.
            expected.pop("editor data")
            actual.pop("editor data")
            self.assertEqual(expected, actual)
            self.assertEqual(project, snapshot(self.root))
            self.assertEqual(game, snapshot(self.game))
            records = list(self.cache().parent.glob("renamed-files-*/receipt.json"))
            self.assertEqual(len(records), 1)
            self.assertFalse(records[0].is_relative_to(self.user))
            self.assertEqual(stat.S_IMODE(records[0].stat().st_mode), 0o600)
            receipt = json.loads(records[0].read_bytes())
            self.assertEqual(receipt["status"], "COMPLETED")
            self.assertEqual({row["original"]: row["readable"] for row in receipt["files"]}, self.data["filename_aliases"])
            self.assertEqual({row["original"]: row["sha256"] for row in receipt["files"]},
                             {row["name"]: row["sha256"] for row in self.data["own_fmfs"]})
            before = snapshot(self.base)
            link.reset_mock()
            result = self.invoke("organize")
            self.assertEqual(result[0], 0, result)
            self.assertIn("already use readable names", result[1])
            self.assertEqual(before, snapshot(self.base))
            link.assert_not_called()
        self.assertTrue(all(call.args[0] == ["pgrep", "-x", "fm"] for call in self.process.call_args_list))

    def test_organize_completes_a_partial_alias_migration_without_ownership_receipt(self):
        self.use_aliases(self.data["own_fmfs"][:1])
        first = self.alias().stat().st_ino
        self.process.side_effect = None
        self.process.return_value = subprocess.CompletedProcess([], 1)
        result = self.invoke("organize")
        self.assertEqual(result[0], 0, result)
        self.assertIn("Organized 50", result[1])
        self.assertEqual(self.alias().stat().st_ino, first)
        self.assertTrue(all(self.alias(index).is_file() and not self.owned(index).exists() for index in range(51)))
        self.assertFalse((self.user / "FM24-History-Community/owned_state.json").exists())
        self.assertEqual(self.invoke("doctor")[0], 0)

    def test_organize_refuses_missing_mismatched_or_occupied_files_without_writes(self):
        original = self.owned().read_bytes()
        for issue in ("missing", "mismatched", "occupied"):
            with self.subTest(issue=issue):
                if issue == "missing":
                    self.owned().unlink()
                elif issue == "mismatched":
                    self.owned().write_bytes(b"unknown original variant")
                else:
                    self.alias().write_bytes(b"occupied destination; never overwrite")
                before = snapshot(self.base)
                with mock.patch.object(cli.os, "link", wraps=os.link) as link:
                    result = self.invoke("organize")
                    self.assertEqual(result[0], 1, result)
                    link.assert_not_called()
                self.assertEqual(before, snapshot(self.base))
                if issue == "occupied":
                    self.alias().unlink()
                self.owned().write_bytes(original)
        self.process.assert_not_called()

    def test_organize_busy_or_failed_process_checks_preserve_snapshot(self):
        before = snapshot(self.base)
        for outcome in (0, 2, OSError("synthetic process failure"), subprocess.SubprocessError("synthetic failure")):
            with self.subTest(outcome=outcome), mock.patch.object(cli.os, "link", wraps=os.link) as link:
                self.process.reset_mock()
                self.process.side_effect = outcome if isinstance(outcome, Exception) else None
                self.process.return_value = subprocess.CompletedProcess([], outcome if isinstance(outcome, int) else 1)
                result = self.invoke("organize")
                self.assertEqual(result[0], 1, result)
                self.assertEqual(before, snapshot(self.base))
                self.process.assert_called_once_with(["pgrep", "-x", "fm"], capture_output=True)
                link.assert_not_called()

    def test_organize_rolls_back_injected_link_and_unlink_failures(self):
        self.ownership_state()
        self.process.side_effect = None
        self.process.return_value = subprocess.CompletedProcess([], 1)
        for operation in ("link", "unlink"):
            with self.subTest(operation=operation):
                original = getattr(cli.os, operation)
                calls = 0
                user, project, game = snapshot(self.user), snapshot(self.root), snapshot(self.game)
                inodes = [self.owned(index).stat().st_ino for index in range(51)]

                def fail_third(source, *args, **kwargs):
                    nonlocal calls
                    source = Path(source)
                    if source.parent == self.user / "editor data" and source.name in self.data["filename_aliases"]:
                        calls += 1
                        if calls == 3:
                            raise OSError("injected synthetic filename operation failure")
                    return original(source, *args, **kwargs)

                with mock.patch.object(cli.os, operation, side_effect=fail_third):
                    result = self.invoke("organize")
                self.assertEqual(result[0], 1, result)
                self.assertGreaterEqual(calls, 3)
                actual = snapshot(self.user)
                user.pop("editor data")
                actual.pop("editor data")
                self.assertEqual(user, actual)
                self.assertEqual(project, snapshot(self.root))
                self.assertEqual(game, snapshot(self.game))
                self.assertEqual(inodes, [self.owned(index).stat().st_ino for index in range(51)])
                receipts = list(self.cache().parent.glob("renamed-files-*/receipt.json"))
                self.assertTrue(receipts)
                self.assertTrue(all(json.loads(record.read_bytes())["status"] == "ROLLED_BACK" for record in receipts))

    def test_legacy_cache_without_alias_metadata_is_preserved_after_files_are_renamed(self):
        legacy = self.legacy_cache()
        old_cache = next(legacy.iterdir())
        manifest = json.loads((old_cache / "release.json").read_bytes())
        del manifest["filename_aliases"]
        self.reseal_cache(old_cache, manifest)
        previous = snapshot(legacy)
        self.use_aliases()
        installed = snapshot(self.user / "editor data")
        self.process.side_effect = None
        self.process.return_value = subprocess.CompletedProcess([], 1)
        result = self.invoke("prepare")
        self.assertEqual(result[0], 0, result)
        archives = list(self.cache().parent.glob("preserved-legacy-*/ReSeason"))
        self.assertEqual(len(archives), 1)
        self.assertEqual(previous, snapshot(archives[0]))
        self.assertFalse(legacy.exists())
        self.assertEqual(installed, snapshot(self.user / "editor data"))

    def test_doctor_is_read_only_and_reports_all_counts(self):
        before = snapshot(self.base)
        result = self.invoke("doctor")
        self.assertEqual(result[0], 0, result)
        self.assertIn("Custom FMFs: 51/51 exact; 0 missing; 0 mismatched", result[1])
        self.assertIn("Basic FMFs: 53/53 exact", result[1])
        self.assertIn("Reference SHA and public toolkit: verified", result[1])
        self.assertEqual(before, snapshot(self.base))
        self.process.assert_not_called()

    def test_extra_editor_fmfs_including_original_basic_italy_refuse_without_writes(self):
        self.prepared()
        names = ("unknown mod.fmf", "another mod.FMF", self.data["basic_replacements"][0]["dependency_name"])
        for count, name in enumerate(names, 1):
            (self.user / "editor data" / name).write_bytes(b"synthetic conflict; preserve exactly")
            before = snapshot(self.base)
            for command in (("doctor",), ("prepare",), ("new", "--dry-run"), ("continue", "--dry-run")):
                with self.subTest(name=name, command=command):
                    result = self.invoke(*command)
                    self.assertEqual(result[0], 1, result)
                    self.assertIn(f"Extra editor FMFs: {count}.", result[1])
                    self.assertIn("51/51 exact", result[1])
                    self.assertIn("53/53 exact", result[1])
                    self.assertIn("conflict with the exact 104-file selection", result[2])
                    self.assertEqual(before, snapshot(self.base))
        self.process.assert_not_called()

    def test_first_use_missing_and_mismatched_are_distinct_and_no_basic_only_claim(self):
        self.owned(0).unlink()
        self.owned(1).write_bytes(b"wrong variant")
        basic = self.user / "editor data" / self.data["external_basic"][0]["name"]
        basic.unlink()
        before = snapshot(self.base)
        result = self.invoke("prepare")
        self.assertEqual(result[0], 1)
        self.assertIn("49/51 exact; 1 missing; 1 mismatched", result[1])
        self.assertIn("52/53 exact; 1 missing; 0 mismatched", result[1])
        self.assertIn("does not provide the 51 custom FMF files", result[2])
        self.assertIn("Basic alone is NOT enough", result[2])
        self.assertEqual(before, snapshot(self.base))

    def test_basic_alone_cannot_prepare_the_51_unavailable_custom_files(self):
        for row in self.data["own_fmfs"]:
            (self.user / "editor data" / row["name"]).unlink()
        result = self.invoke("prepare")
        self.assertEqual(result[0], 1)
        self.assertIn("0/51 exact; 51 missing", result[1])
        self.assertIn("53/53 exact", result[1])
        self.assertIn("public ZIP does not provide the 51 custom FMF files", result[2])
        self.assertFalse(self.cache().parent.exists())

    def test_reference_tamper_is_refused_without_writes(self):
        path = self.root / "toolkit/reference.json"
        path.write_bytes(path.read_bytes() + b" ")
        before = snapshot(self.base)
        result = self.invoke("doctor")
        self.assertEqual(result[0], 1)
        self.assertIn("Reference SHA mismatch", result[2])
        self.assertEqual(before, snapshot(self.base))

    def test_toolkit_tamper_is_refused_without_importing_changed_code(self):
        marker = self.base / "must never be created"
        (self.root / "toolkit/release_tools.py").write_text(f"open({str(marker)!r}, 'w').write('bad')\n")
        result = self.invoke("prepare")
        self.assertEqual(result[0], 1)
        self.assertIn("SHA or size mismatch", result[2])
        self.assertFalse(marker.exists())
        self.assertFalse((self.user.parent / "ReSeason FM24 cache").exists())

    def test_executable_mismatch_prevents_prepare(self):
        self.binary.write_bytes(b"another executable")
        result = self.invoke("prepare")
        self.assertEqual(result[0], 1)
        self.assertIn("Supported executable SHA: missing or mismatched", result[1])
        self.assertFalse(self.cache().parent.exists())

    def test_unsupported_platforms_refuse_before_writes(self):
        for system, machine in (("Linux", "aarch64"), ("Windows", "ARM64"), ("Darwin", "x86_64")):
            with self.subTest(system=system), mock.patch.object(cli.platform, "system", return_value=system), mock.patch.object(cli.platform, "machine", return_value=machine):
                before = snapshot(self.base)
                result = self.invoke("prepare")
                self.assertEqual(result[0], 1)
                self.assertIn("Only macOS arm64", result[2])
                self.assertEqual(before, snapshot(self.base))

    def test_installed_symlink_and_symlink_ancestor_are_refused(self):
        original = self.owned().read_bytes()
        self.owned().unlink()
        external = self.base / "external fixture"
        external.write_bytes(original)
        self.owned().symlink_to(external)
        before = snapshot(self.base)
        self.assertIn("Symlink refused", self.invoke("prepare")[2])
        self.assertEqual(before, snapshot(self.base))
        self.owned().unlink()
        self.owned().write_bytes(original)
        self.user.rename(self.base / "real data")
        self.user.symlink_to(self.base / "real data", target_is_directory=True)
        self.assertIn("Symlink refused", self.invoke("doctor")[2])

    def test_reference_traversal_is_refused_even_for_omitted_optional_files(self):
        for name in ("../outside", "/outside", "a/../outside", "a//b", "a\\b", "a:b"):
            with self.subTest(name=name):
                original = self.data["files"][0]["path"]
                self.data["files"][0]["path"] = name
                self.seal()
                self.assertEqual(self.invoke("prepare")[0], 1)
                self.assertFalse((self.user.parent / "ReSeason FM24 cache").exists())
                self.data["files"][0]["path"] = original

    def test_prepare_copies_only_declared_assets_and_is_idempotent(self):
        project_before, game_before = snapshot(self.root), snapshot(self.game)
        user_before = snapshot(self.user)
        fmfs_before = {p.relative_to(self.user) for p in self.user.rglob("*")
                       if p.suffix.lower() == ".fmf"}
        cache = self.prepared()
        self.assertEqual(cache, self.user.parent / "ReSeason FM24 cache" / cli.context(self.root)[4])
        self.assertFalse(cache.is_relative_to(self.root))
        self.assertFalse(cache.is_relative_to(self.user))
        self.assertFalse((self.user / "ReSeason").exists())
        self.assertFalse(any(p.name in {"release.json", "RELEASE_MANIFEST.sha256", "ReSeason FM24 cache"}
                             for p in self.user.rglob("*")))
        self.assertEqual(fmfs_before, {p.relative_to(self.user) for p in self.user.rglob("*")
                                     if p.suffix.lower() == ".fmf"})
        backend, _, _, manifest, _ = cli.context(self.root)
        cli.verify_cache(backend, cache, manifest)
        self.assertEqual(stat.S_IMODE(cache.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(cache.parent.stat().st_mode), 0o700)
        package = json.loads((cache / "release.json").read_bytes())
        self.assertEqual(package["snapshot"]["total_active_FMFs"], 104)
        self.assertEqual(package["status"], self.data["status"])
        self.assertEqual(package["module"], self.data["module"])
        self.assertEqual(package["own_fmfs"], self.data["own_fmfs"])
        names = {r["path"] for r in package["files"]}
        self.assertIn("docs/SETUP.md", names)
        self.assertIn("LICENSE", names)
        self.assertNotIn("LICENSE_TOOLS.txt", names)
        self.assertNotIn("docs/private.md", names)
        self.assertNotIn("source/upstream_launch.py.txt", names)
        self.assertFalse(any(n.startswith("payload/lnc/") for n in names))
        for row in self.data["own_fmfs"]:
            self.assertEqual((cache / row["payload"]).read_bytes(), (self.user / "editor data" / row["name"]).read_bytes())
        before = snapshot(self.base)
        self.assertIn("already complete", self.invoke("prepare")[1])
        self.assertEqual(before, snapshot(self.base))
        self.assertEqual(project_before, snapshot(self.root))
        self.assertEqual(game_before, snapshot(self.game))
        self.assertEqual(user_before, snapshot(self.user))
        self.process.assert_not_called()

    def test_cache_tampering_and_resealing_never_overwrites_existing_cache(self):
        cache = self.prepared()
        payload = cache / self.data["own_fmfs"][0]["payload"]
        payload.write_bytes(b"changed private cache")
        before = snapshot(self.base)
        self.assertEqual(self.invoke("prepare")[0], 1)
        self.assertEqual(before, snapshot(self.base))
        manifest = json.loads((cache / "release.json").read_bytes())
        for row in manifest["files"]:
            if row["path"] == self.data["own_fmfs"][0]["payload"]:
                row.update(cli.pin(row["path"], payload.read_bytes()))
        changed = json.dumps(manifest).encode()
        (cache / "release.json").write_bytes(changed)
        (cache / "RELEASE_MANIFEST.sha256").write_text(cli.sha(changed))
        self.assertIn("manifest differs", self.invoke("prepare")[2])

    def test_unexpected_cache_files_and_cache_symlinks_are_refused(self):
        cache = self.prepared()
        extra = cache / "unlisted"
        extra.write_text("unlisted")
        self.assertIn("unexpected files", self.invoke("prepare")[2])
        extra.unlink()
        extra.symlink_to(self.owned())
        self.assertIn("Symlink refused", self.invoke("prepare")[2])

    def test_existing_cache_permissions_are_checked_without_chmod_or_replacement(self):
        cache = self.prepared()
        cache.chmod(0o755)
        before = snapshot(self.base)
        self.assertIn("permissions are unsafe", self.invoke("prepare")[2])
        self.assertEqual(before, snapshot(self.base))

    def test_legacy_cache_root_symlink_is_refused_without_writes(self):
        (self.user / "ReSeason").symlink_to(self.base / "not created")
        before = snapshot(self.base)
        self.assertIn("Symlink refused", self.invoke("prepare")[2])
        self.assertEqual(before, snapshot(self.base))
        self.process.assert_not_called()

    def test_cache_parent_symlink_is_refused_without_writes(self):
        external = self.base / "external cache"
        external.mkdir()
        self.cache().parent.symlink_to(external, target_is_directory=True)
        before = snapshot(self.base)
        self.assertIn("Symlink refused", self.invoke("prepare")[2])
        self.assertEqual(before, snapshot(self.base))
        self.process.assert_not_called()

    def test_cache_path_rejects_repository_overlap_without_writes(self):
        before = snapshot(self.base)
        with self.assertRaisesRegex(cli.Refusal, "outside the project"):
            cli.cache_path(self.root, self.root / "private data", "key")
        self.assertEqual(before, snapshot(self.base))

    def test_cache_path_rejects_user_data_overlap_without_writes(self):
        overlapping = self.base / "ReSeason FM24 cache"
        overlapping.mkdir(mode=0o700)
        before = snapshot(self.base)
        with self.assertRaisesRegex(cli.Refusal, "outside the FM24 user-data"):
            cli.cache_path(self.root, overlapping, cli.context(self.root)[4])
        self.assertEqual(before, snapshot(self.base))

    def test_valid_legacy_caches_are_atomically_preserved_and_migration_is_idempotent(self):
        legacy = self.legacy_cache()
        entry = next(legacy.iterdir())
        historical = legacy / ("a" * 64)
        shutil.copytree(entry, historical)
        previous = json.loads((historical / "release.json").read_bytes())
        old_readme = historical / "README.md"
        old_readme.write_bytes(b"Synthetic public documentation from an earlier cache.\n")
        for row in previous["files"]:
            if row["path"] == "README.md":
                row.update(cli.pin("README.md", old_readme.read_bytes()))
        self.reseal_cache(historical, previous)
        legacy_before = snapshot(legacy)
        identity = legacy.stat().st_dev, legacy.stat().st_ino
        user_before = {name: value for name, value in snapshot(self.user).items()
                       if name != "ReSeason" and not name.startswith("ReSeason/")}
        project_before, game_before = snapshot(self.root), snapshot(self.game)

        def closed_game(command, **kwargs):
            self.assertEqual(command, ["pgrep", "-x", "fm"])
            self.assertEqual(legacy_before, snapshot(legacy))
            self.assertFalse(self.cache().parent.exists())
            return subprocess.CompletedProcess(command, 1)

        self.process.side_effect = closed_game
        cache = self.prepared()
        self.process.assert_called_once_with(["pgrep", "-x", "fm"], capture_output=True)
        self.assertFalse(legacy.exists())
        archives = list(cache.parent.glob("preserved-legacy-*"))
        self.assertEqual(len(archives), 1)
        archive = archives[0]
        self.assertEqual(str(uuid.UUID(archive.name.removeprefix("preserved-legacy-"))),
                         archive.name.removeprefix("preserved-legacy-"))
        self.assertEqual(stat.S_IMODE(archive.stat().st_mode), 0o700)
        preserved = archive / "ReSeason"
        self.assertEqual(list(archive.iterdir()), [preserved])
        self.assertEqual(identity, (preserved.stat().st_dev, preserved.stat().st_ino))
        self.assertEqual(stat.S_IMODE(preserved.stat().st_mode), 0o700)
        self.assertEqual(legacy_before, snapshot(preserved))
        backend, _, _, manifest, _ = cli.context(self.root)
        cli.verify_cache(backend, cache, manifest)
        self.assertEqual(user_before, snapshot(self.user))
        self.assertEqual(project_before, snapshot(self.root))
        self.assertEqual(game_before, snapshot(self.game))

        before = snapshot(self.base)
        self.process.reset_mock()
        self.process.side_effect = AssertionError("Migration must not run again")
        self.assertIn("already complete", self.invoke("prepare")[1])
        self.assertEqual(before, snapshot(self.base))
        self.process.assert_not_called()

    def test_legacy_is_migrated_even_when_current_cache_already_exists(self):
        legacy = self.legacy_cache()
        cache = self.cache()
        cache.parent.mkdir(mode=0o700)
        shutil.copytree(next(legacy.iterdir()), cache)
        cache_before, legacy_before = snapshot(cache), snapshot(legacy)
        self.process.side_effect = None
        self.process.return_value = subprocess.CompletedProcess([], 1)
        result = self.invoke("prepare")
        self.assertEqual(result[0], 0, result)
        self.assertIn("already complete", result[1])
        self.assertFalse(legacy.exists())
        self.assertEqual(cache_before, snapshot(cache))
        archives = list(cache.parent.glob("preserved-legacy-*/ReSeason"))
        self.assertEqual(len(archives), 1)
        self.assertEqual(legacy_before, snapshot(archives[0]))
        self.process.assert_called_once_with(["pgrep", "-x", "fm"], capture_output=True)

    def test_doctor_and_launch_dry_runs_refuse_legacy_without_writes_or_processes(self):
        self.legacy_cache()
        before = snapshot(self.base)
        for command in (("doctor",), ("new", "--dry-run"), ("continue", "--dry-run"), ("cold", "--dry-run")):
            with self.subTest(command=command):
                result = self.invoke(*command)
                self.assertEqual(result[0], 1, result)
                self.assertIn("legacy", result[2].lower())
                self.assertIn("relocat", result[2].lower())
                self.assertEqual(before, snapshot(self.base))
        self.process.assert_not_called()

    def test_unknown_legacy_root_file_or_empty_directory_is_refused_untouched(self):
        legacy = self.user / "ReSeason"
        for kind in ("file", "empty directory"):
            with self.subTest(kind=kind):
                if kind == "file":
                    legacy.write_bytes(b"Unrecognized synthetic user file; preserve exactly.")
                else:
                    legacy.mkdir(mode=0o700)
                self.assert_legacy_refused_without_writes()
                legacy.unlink() if legacy.is_file() else legacy.rmdir()

    def test_legacy_root_permissions_and_ownership_are_checked_without_changes(self):
        legacy = self.legacy_cache()
        legacy.chmod(0o755)
        self.assert_legacy_refused_without_writes()
        legacy.chmod(0o700)
        with mock.patch.object(cli.os, "getuid", return_value=os.getuid() + 1):
            self.assert_legacy_refused_without_writes()

    def test_unknown_legacy_entries_are_refused_without_partial_relocation(self):
        legacy = self.legacy_cache()
        for name, is_dir in (("unknown.txt", False), ("not-a-key", True),
                             ("A" * 64, True), ("a" * 63, True), ("b" * 64, False), ("c" * 64, True)):
            with self.subTest(name=name, is_dir=is_dir):
                unknown = legacy / name
                if is_dir:
                    unknown.mkdir(mode=0o700)
                else:
                    unknown.write_bytes(b"Synthetic unknown legacy entry; preserve exactly.")
                self.assert_legacy_refused_without_writes()
                unknown.rmdir() if is_dir else unknown.unlink()

    def test_legacy_cache_tampering_and_missing_files_are_refused_untouched(self):
        legacy = self.legacy_cache()
        entry = next(legacy.iterdir())
        names = ("release.json", "RELEASE_MANIFEST.sha256", self.data["own_fmfs"][0]["payload"])
        for name in names:
            path = entry / name
            original = path.read_bytes()
            for corruption in ("tampered", "missing"):
                with self.subTest(name=name, corruption=corruption):
                    if corruption == "tampered":
                        path.write_bytes(b"tampered synthetic cache content\n")
                    else:
                        path.unlink()
                    self.assert_legacy_refused_without_writes()
                    path.write_bytes(original)

    def test_resealed_legacy_metadata_must_match_reference_except_files(self):
        legacy = self.legacy_cache()
        entry = next(legacy.iterdir())
        original = json.loads((entry / "release.json").read_bytes())
        for field in ("release_id", "game", "unexpected_metadata"):
            with self.subTest(field=field):
                changed = copy.deepcopy(original)
                if field == "release_id":
                    changed[field] += "_unrecognized"
                elif field == "game":
                    changed[field]["executable_sha256"] = "0" * 64
                else:
                    changed[field] = "unrecognized metadata"
                self.reseal_cache(entry, changed)
                self.assert_legacy_refused_without_writes()

    def test_resealed_legacy_cache_cannot_declare_unrecognized_payload_paths(self):
        legacy = self.legacy_cache()
        entry = next(legacy.iterdir())
        original = json.loads((entry / "release.json").read_bytes())
        for name in ("docs/private.md", "payload/lnc/unlisted.lnc", "payload/editor data/unowned.fmf"):
            with self.subTest(name=name):
                path = entry / name
                path.parent.mkdir(parents=True, exist_ok=True)
                content = b"Synthetic unrecognized payload; preserve exactly.\n"
                path.write_bytes(content)
                changed = copy.deepcopy(original)
                changed["files"].append(cli.pin(name, content))
                self.reseal_cache(entry, changed)
                self.assert_legacy_refused_without_writes()
                path.unlink()

    def test_unlisted_legacy_cache_files_are_refused_untouched(self):
        entry = next(self.legacy_cache().iterdir())
        (entry / "unlisted.fmf").write_bytes(b"Synthetic undeclared FMF; preserve exactly.")
        self.assert_legacy_refused_without_writes()

    def test_legacy_cache_child_symlink_is_refused_untouched(self):
        legacy = self.legacy_cache()
        (legacy / ("f" * 64)).symlink_to(next(legacy.iterdir()), target_is_directory=True)
        self.assert_legacy_refused_without_writes()

    def test_legacy_cache_nested_symlinks_are_refused_untouched(self):
        entry = next(self.legacy_cache().iterdir())
        for name in ("README.md", "payload"):
            with self.subTest(name=name):
                path = entry / name
                external = self.base / ("external legacy " + name)
                path.rename(external)
                path.symlink_to(external, target_is_directory=external.is_dir())
                self.assert_legacy_refused_without_writes()
                path.unlink()
                external.rename(path)

    def test_legacy_relocation_requires_pgrep_to_confirm_fm_is_closed(self):
        self.legacy_cache()
        before = snapshot(self.base)
        self.process.side_effect = None
        for code in (0, 2, -15):
            with self.subTest(code=code):
                self.process.reset_mock()
                self.process.return_value = subprocess.CompletedProcess([], code)
                result = self.invoke("prepare")
                self.assertEqual(result[0], 1, result)
                self.assertIn("FM must be closed", result[2])
                self.assertEqual(before, snapshot(self.base))
                self.process.assert_called_once_with(["pgrep", "-x", "fm"], capture_output=True)

    def test_legacy_relocation_refuses_process_check_exceptions_without_writes(self):
        self.legacy_cache()
        before = snapshot(self.base)
        for error in (FileNotFoundError("synthetic pgrep unavailable"),
                      subprocess.SubprocessError("synthetic process-check failure")):
            with self.subTest(error=type(error).__name__):
                self.process.reset_mock()
                self.process.side_effect = error
                self.assertEqual(self.invoke("prepare")[0], 1)
                self.assertEqual(before, snapshot(self.base))
                self.process.assert_called_once_with(["pgrep", "-x", "fm"], capture_output=True)

    def test_legacy_archive_collision_never_overwrites_or_removes_existing_files(self):
        self.legacy_cache()
        reservation = self.cache().parent / "preserved-legacy-00000000-0000-0000-0000-000000000000"
        reservation.mkdir(mode=0o700, parents=True)
        (reservation / "ReSeason").mkdir(mode=0o700)
        (reservation / "ReSeason/keep.fmf").write_bytes(b"Synthetic previous archive; preserve exactly.")
        before = snapshot(self.base)
        self.process.side_effect = None
        self.process.return_value = subprocess.CompletedProcess([], 1)
        with mock.patch.object(cli.uuid, "uuid4", return_value="00000000-0000-0000-0000-000000000000"):
            self.assertEqual(self.invoke("prepare")[0], 1)
        self.assertEqual(before, snapshot(self.base))
        self.process.assert_called_once_with(["pgrep", "-x", "fm"], capture_output=True)

    def test_completed_transactions_are_atomically_preserved_with_state_and_logs_unchanged(self):
        names = ([self.data["own_fmfs"][0]["name"]] +
                 [row["name"] for row in self.data.get("retire_owned", [])] +
                 [row["dependency_name"] for row in self.data.get("basic_replacements", [])])
        source = self.transaction(names=names).parent
        self.transaction(transaction_id="2" * 32, status="ROLLED_BACK")
        state = source.parent
        self.ownership_state()
        (state / "logs/existing-session").mkdir(parents=True)
        (state / "logs/existing-session/stdout.log").write_bytes(b"Synthetic previous log; preserve exactly.\n")
        state_before = {name: value for name, value in snapshot(state).items()
                        if name != "transactions" and not name.startswith("transactions/")}
        transactions_before = snapshot(source)
        identity = source.stat().st_dev, source.stat().st_ino
        project_before, game_before = snapshot(self.root), snapshot(self.game)
        installed_before, saves_before = snapshot(self.user / "editor data"), snapshot(self.user / "games")
        personal_mod = (self.user / "personal mod.fmf").read_bytes()
        fmfs_before = {p.relative_to(self.user) for p in self.user.rglob("*")
                       if p.suffix.lower() == ".fmf" and not p.is_relative_to(source)}

        def closed_game(command, **kwargs):
            self.assertEqual(command, ["pgrep", "-x", "fm"])
            self.assertEqual(transactions_before, snapshot(source))
            self.assertFalse(self.cache().parent.exists())
            return subprocess.CompletedProcess(command, 1)

        self.process.side_effect = closed_game
        cache = self.prepared()
        self.process.assert_called_once_with(["pgrep", "-x", "fm"], capture_output=True)
        self.assertFalse(source.exists())
        archives = list(cache.parent.glob("preserved-transactions-*"))
        self.assertEqual(len(archives), 1)
        archive = archives[0]
        suffix = archive.name.removeprefix("preserved-transactions-")
        self.assertEqual(str(uuid.UUID(suffix)), suffix)
        self.assertEqual(stat.S_IMODE(archive.stat().st_mode), 0o700)
        preserved = archive / "transactions"
        self.assertEqual(list(archive.iterdir()), [preserved])
        self.assertEqual(identity, (preserved.stat().st_dev, preserved.stat().st_ino))
        self.assertEqual(transactions_before, snapshot(preserved))
        self.assertFalse(preserved.is_relative_to(self.user))
        self.assertFalse(preserved.is_relative_to(self.root))
        self.assertEqual(state_before, snapshot(state))
        self.assertEqual(installed_before, snapshot(self.user / "editor data"))
        self.assertEqual(saves_before, snapshot(self.user / "games"))
        self.assertEqual(personal_mod, (self.user / "personal mod.fmf").read_bytes())
        self.assertEqual(project_before, snapshot(self.root))
        self.assertEqual(game_before, snapshot(self.game))
        self.assertEqual(fmfs_before, {p.relative_to(self.user) for p in self.user.rglob("*")
                                     if p.suffix.lower() == ".fmf"})
        backend, _, _, manifest, _ = cli.context(self.root)
        cli.verify_cache(backend, cache, manifest)

        before = snapshot(self.base)
        self.process.reset_mock()
        self.process.side_effect = AssertionError("Completed transactions must not be migrated again")
        result = self.invoke("prepare")
        self.assertEqual(result[0], 0, result)
        self.assertIn("already complete", result[1])
        self.assertEqual(before, snapshot(self.base))
        self.process.assert_not_called()

    def test_transactions_are_relocated_even_when_current_cache_already_exists(self):
        cache = self.prepared()
        source = self.transaction().parent
        cache_before, transactions_before = snapshot(cache), snapshot(source)
        self.process.side_effect = None
        self.process.return_value = subprocess.CompletedProcess([], 1)
        result = self.invoke("prepare")
        self.assertEqual(result[0], 0, result)
        self.assertIn("already complete", result[1])
        self.assertFalse(source.exists())
        self.assertEqual(cache_before, snapshot(cache))
        archives = list(cache.parent.glob("preserved-transactions-*/transactions"))
        self.assertEqual(len(archives), 1)
        self.assertEqual(transactions_before, snapshot(archives[0]))
        self.process.assert_called_once_with(["pgrep", "-x", "fm"], capture_output=True)

    def test_prepare_relocates_legacy_cache_then_completed_transactions(self):
        legacy = self.legacy_cache()
        source = self.transaction().parent
        legacy_before, transactions_before = snapshot(legacy), snapshot(source)
        checks = []

        def closed_game(command, **kwargs):
            self.assertEqual(command, ["pgrep", "-x", "fm"])
            self.assertTrue(source.is_dir())
            self.assertEqual(transactions_before, snapshot(source))
            if not checks:
                self.assertEqual(legacy_before, snapshot(legacy))
            else:
                self.assertFalse(legacy.exists())
                self.assertEqual(len(list(self.cache().parent.glob("preserved-legacy-*"))), 1)
            checks.append(command)
            return subprocess.CompletedProcess(command, 1)

        self.process.side_effect = closed_game
        cache = self.prepared()
        self.assertEqual(len(checks), 2)
        self.assertFalse(legacy.exists())
        self.assertFalse(source.exists())
        legacy_archives = list(cache.parent.glob("preserved-legacy-*/ReSeason"))
        transaction_archives = list(cache.parent.glob("preserved-transactions-*/transactions"))
        self.assertEqual(len(legacy_archives), 1)
        self.assertEqual(len(transaction_archives), 1)
        self.assertEqual(legacy_before, snapshot(legacy_archives[0]))
        self.assertEqual(transactions_before, snapshot(transaction_archives[0]))

    def test_doctor_and_dry_runs_refuse_nonempty_transactions_without_writes_or_processes(self):
        self.prepared()
        self.transaction()
        before = snapshot(self.base)
        for command in (("doctor",), ("new", "--dry-run"), ("continue", "--dry-run"), ("cold", "--dry-run")):
            with self.subTest(command=command):
                result = self.invoke(*command)
                self.assertEqual(result[0], 1, result)
                self.assertIn("relocat", result[2].lower())
                self.assertEqual(before, snapshot(self.base))
        self.process.assert_not_called()

    def test_empty_transactions_are_left_in_place_without_archiving_or_process_checks(self):
        cache = self.prepared()
        source = self.user / "FM24-History-Community/transactions"
        source.mkdir(parents=True)
        before = snapshot(self.base)
        for command in (("doctor",), ("new", "--dry-run"), ("continue", "--dry-run"),
                        ("cold", "--dry-run"), ("prepare",)):
            with self.subTest(command=command):
                result = self.invoke(*command)
                self.assertEqual(result[0], 0, result)
                self.assertEqual(before, snapshot(self.base))
        self.assertEqual(list(source.iterdir()), [])
        self.assertEqual(list(cache.parent.glob("preserved-transactions-*")), [])
        self.process.assert_not_called()

    def test_unfinished_transactions_are_refused_without_writes(self):
        entry = self.transaction()
        path = entry / "journal.json"
        journal = json.loads(path.read_bytes())
        for status in ("PREPARING", "PREPARED", "APPLYING", "ROLLING_BACK", "FAILED", "UNKNOWN", "committed", None):
            with self.subTest(status=status):
                journal["status"] = status
                path.write_text(json.dumps(journal))
                self.assert_transaction_refused_without_writes()

    def test_transaction_journal_identity_and_schema_must_match(self):
        entry = self.transaction()
        path = entry / "journal.json"
        original = json.loads(path.read_bytes())
        for field, value in (("schema", 2), ("pack_id", "unrecognized-pack"),
                             ("transaction_id", "3" * 32), ("actions", None)):
            with self.subTest(field=field):
                changed = copy.deepcopy(original)
                changed[field] = value
                path.write_text(json.dumps(changed))
                self.assert_transaction_refused_without_writes()

    def test_missing_or_malformed_transaction_journal_is_refused_untouched(self):
        entry = self.transaction()
        path = entry / "journal.json"
        for content in (None, b"not JSON\n", b"{}\n"):
            with self.subTest(content=content):
                if content is None:
                    path.unlink()
                else:
                    path.write_bytes(content)
                self.assert_transaction_refused_without_writes()

    def test_unknown_transaction_entries_are_refused_without_partial_relocation(self):
        source = self.transaction().parent
        for name, is_dir in (("unknown.txt", False), ("not-a-transaction", True),
                             ("A" * 32, True), ("a" * 31, True), ("b" * 32, False), ("c" * 32, True)):
            with self.subTest(name=name, is_dir=is_dir):
                unknown = source / name
                if is_dir:
                    unknown.mkdir()
                else:
                    unknown.write_bytes(b"Unknown synthetic transaction entry; preserve exactly.\n")
                self.assert_transaction_refused_without_writes()
                unknown.rmdir() if is_dir else unknown.unlink()

    def test_transaction_actions_cannot_name_unowned_or_unrelated_basic_files(self):
        entry = self.transaction()
        path = entry / "journal.json"
        original = json.loads(path.read_bytes())
        for name in ("unowned.fmf", self.data["external_basic"][0]["name"], "../outside.fmf"):
            with self.subTest(name=name):
                changed = copy.deepcopy(original)
                changed["actions"].append({"name": name, "before_sha256": None, "after_sha256": None})
                path.write_text(json.dumps(changed))
                self.assert_transaction_refused_without_writes()

    def test_unknown_transaction_metadata_and_payload_files_are_refused_untouched(self):
        entry = self.transaction()
        owned_name = self.data["own_fmfs"][0]["name"]
        for name in ("owned_state.json", "journal.json.new", "unlisted.fmf", "backup/unlisted.fmf",
                     "stage/unlisted.fmf", "backup/nested/" + owned_name):
            with self.subTest(name=name):
                path = entry / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"Unknown synthetic transaction file; preserve exactly.\n")
                self.assert_transaction_refused_without_writes()
                path.unlink()

    def test_transaction_backup_and_stage_require_their_own_journal_hash(self):
        entry = self.transaction()
        name = self.data["own_fmfs"][0]["name"]
        originals = {kind: (entry / kind / name).read_bytes() for kind in ("backup", "stage")}
        for kind, other in (("backup", "stage"), ("stage", "backup")):
            path = entry / kind / name
            for content in (b"Tampered synthetic transaction FMF.\n", originals[other]):
                with self.subTest(kind=kind, content=content):
                    path.write_bytes(content)
                    self.assert_transaction_refused_without_writes()
                    path.write_bytes(originals[kind])

    def test_transaction_fmfs_with_missing_journal_hashes_are_refused_untouched(self):
        entry = self.transaction()
        path = entry / "journal.json"
        original = json.loads(path.read_bytes())
        for field in ("before_sha256", "after_sha256"):
            with self.subTest(field=field):
                changed = copy.deepcopy(original)
                changed["actions"][0][field] = None
                path.write_text(json.dumps(changed))
                self.assert_transaction_refused_without_writes()

    def test_transaction_symlinks_at_every_level_are_refused_untouched(self):
        entry = self.transaction()
        name = self.data["own_fmfs"][0]["name"]
        paths = (entry / "journal.json", entry / "backup" / name, entry / "stage" / name,
                 entry / "backup", entry, entry.parent, entry.parent.parent)
        for index, path in enumerate(paths):
            with self.subTest(path=path.relative_to(self.user)):
                external = self.base / f"external transaction {index}"
                path.rename(external)
                path.symlink_to(external, target_is_directory=external.is_dir())
                self.assert_transaction_refused_without_writes()
                path.unlink()
                external.rename(path)

    def test_running_fm_and_process_check_errors_prevent_transaction_relocation(self):
        self.transaction()
        before = snapshot(self.base)
        self.process.side_effect = None
        for code in (0, 2, -15):
            for command in ("prepare", "new", "continue"):
                with self.subTest(code=code, command=command):
                    self.process.reset_mock()
                    self.process.return_value = subprocess.CompletedProcess([], code)
                    result = self.invoke(command)
                    self.assertEqual(result[0], 1, result)
                    self.assertIn("FM must be closed", result[2])
                    self.assertEqual(before, snapshot(self.base))
                    self.process.assert_called_once_with(["pgrep", "-x", "fm"], capture_output=True)

    def test_transaction_relocation_refuses_process_check_exceptions_without_writes(self):
        self.transaction()
        before = snapshot(self.base)
        for error in (FileNotFoundError("synthetic pgrep unavailable"),
                      subprocess.SubprocessError("synthetic process-check failure")):
            with self.subTest(error=type(error).__name__):
                self.process.reset_mock()
                self.process.side_effect = error
                self.assertEqual(self.invoke("prepare")[0], 1)
                self.assertEqual(before, snapshot(self.base))
                self.process.assert_called_once_with(["pgrep", "-x", "fm"], capture_output=True)

    def test_transaction_archive_collision_preserves_source_and_existing_archive(self):
        self.transaction()
        reservation = self.cache().parent / "preserved-transactions-00000000-0000-0000-0000-000000000000"
        reservation.mkdir(mode=0o700, parents=True)
        (reservation / "transactions").mkdir()
        (reservation / "transactions/keep.fmf").write_bytes(b"Synthetic earlier archive; preserve exactly.\n")
        before = snapshot(self.base)
        self.process.side_effect = None
        self.process.return_value = subprocess.CompletedProcess([], 1)
        with mock.patch.object(cli.uuid, "uuid4", return_value="00000000-0000-0000-0000-000000000000"):
            self.assertEqual(self.invoke("prepare")[0], 1)
        self.assertEqual(before, snapshot(self.base))
        self.process.assert_called_once_with(["pgrep", "-x", "fm"], capture_output=True)

    def test_code_license_docs_and_reference_changes_invalidate_cache_key(self):
        original = cli.context(self.root)[4]
        for name in ("LICENSE", "NOTICE", "docs/SETUP.md"):
            path = self.root / name
            content = path.read_bytes()
            path.write_bytes(content + b"updated\n")
            self.assertNotEqual(original, cli.context(self.root)[4])
            path.write_bytes(content)
        self.data["release_id"] += "_updated"
        self.seal()
        self.assertNotEqual(original, cli.context(self.root)[4])
        self.data["release_id"] = self.data["release_id"].removesuffix("_updated")
        path = self.root / "toolkit/source/awards_init.c"
        path.write_bytes(b"updated synthetic code")
        self.declared["source/awards_init.c"].update(cli.pin("source/awards_init.c", path.read_bytes()))
        self.seal()
        self.assertNotEqual(original, cli.context(self.root)[4])

    def test_launch_requires_prepared_cache_and_dry_run_does_not_create_it(self):
        before = snapshot(self.base)
        for command in ("new", "continue", "cold"):
            result = self.invoke(command, "--dry-run")
            self.assertEqual(result[0], 1)
            self.assertIn("Run prepare first", result[2])
        self.assertEqual(before, snapshot(self.base))
        self.process.assert_not_called()

    def test_launch_dry_runs_preserve_every_file_and_do_not_print_paths_or_environment(self):
        self.prepared()
        before = snapshot(self.base)
        for command, description in (("new", "module enabled"), ("continue", "module disabled"), ("cold", "module disabled")):
            result = self.invoke(command, "--dry-run")
            self.assertEqual(result[0], 0, result)
            self.assertIn(description, result[1])
            self.assertIn("DRY RUN", result[1])
            self.assertNotIn(str(self.base), result[1] + result[2])
            self.assertNotIn("DYLD_INSERT_LIBRARIES", result[1])
        self.assertEqual(before, snapshot(self.base))
        self.process.assert_not_called()

    def test_launch_blocks_active_game_and_pgrep_errors_without_creating_logs(self):
        self.prepared()
        before = snapshot(self.base)
        for code in (0, 2):
            self.process.side_effect = None
            self.process.return_value = subprocess.CompletedProcess([], code)
            result = self.invoke("new")
            self.assertEqual(result[0], 1)
            self.assertIn("game-process check refused", result[2])
            self.assertEqual(before, snapshot(self.base))
        self.assertTrue(all(c.args[0] == ["pgrep", "-x", "fm"] for c in self.process.call_args_list))

    def test_real_new_career_prepares_missing_cache_before_launch(self):
        installed, game = snapshot(self.user / "editor data"), snapshot(self.game)
        self.assertFalse(self.cache().exists())

        def run(command, **kwargs):
            if command[0] == "pgrep":
                return subprocess.CompletedProcess(command, 1)
            self.assertTrue(self.cache().is_dir())
            self.assertEqual(command[:2], ["open", "-n"])
            return subprocess.CompletedProcess(command, 0)

        self.process.side_effect = run
        result = self.invoke("new")
        self.assertEqual(result[0], 0, result)
        self.assertIn("Private cache verified and prepared", result[1])
        self.assertIn("Launch requested", result[1])
        self.assertEqual(installed, snapshot(self.user / "editor data"))
        self.assertEqual(game, snapshot(self.game))

    def test_real_continue_prepares_missing_cache_and_launches_without_module(self):
        self.assertFalse(self.cache().exists())
        self.process.side_effect = lambda command, **kwargs: subprocess.CompletedProcess(command, 1 if command[0] == "pgrep" else 0)
        result = self.invoke("continue")
        self.assertEqual(result[0], 0, result)
        command = self.process.call_args.args[0]
        environment = dict(command[i + 1].split("=", 1) for i, value in enumerate(command[:-1]) if value == "--env")
        self.assertEqual(environment["DYLD_INSERT_LIBRARIES"], "")
        self.assertTrue(self.cache().is_dir())

    def test_real_new_and_continue_relocate_legacy_before_mocked_launch(self):
        self.process.side_effect = None
        self.process.return_value = subprocess.CompletedProcess([], 1)
        for command in ("new", "continue"):
            with self.subTest(command=command):
                cache = self.prepared()
                legacy = self.user / "ReSeason"
                legacy.mkdir(mode=0o700)
                cache.rename(legacy / cache.name)
                legacy_before = snapshot(legacy)
                installed, saves, game = (snapshot(self.user / "editor data"),
                                          snapshot(self.user / "games"), snapshot(self.game))
                archives_before = set(cache.parent.glob("preserved-legacy-*"))
                launches = []

                def run(actual, **kwargs):
                    if actual == ["pgrep", "-x", "fm"]:
                        return subprocess.CompletedProcess(actual, 1)
                    self.assertEqual(actual[:2], ["open", "-n"])
                    self.assertFalse(legacy.exists())
                    self.assertTrue(cache.is_dir())
                    new_archives = set(cache.parent.glob("preserved-legacy-*")) - archives_before
                    self.assertEqual(len(new_archives), 1)
                    self.assertEqual(legacy_before, snapshot(new_archives.pop() / "ReSeason"))
                    launches.append(actual)
                    return subprocess.CompletedProcess(actual, 0)

                self.process.side_effect = run
                result = self.invoke(command)
                self.assertEqual(result[0], 0, result)
                self.assertEqual(len(launches), 1)
                environment = dict(launches[0][i + 1].split("=", 1)
                                   for i, value in enumerate(launches[0][:-1]) if value == "--env")
                self.assertEqual(bool(environment["DYLD_INSERT_LIBRARIES"]), command == "new")
                self.assertEqual(installed, snapshot(self.user / "editor data"))
                self.assertEqual(saves, snapshot(self.user / "games"))
                self.assertEqual(game, snapshot(self.game))

    def test_busy_game_and_process_errors_block_legacy_migration_on_real_launch(self):
        self.legacy_cache()
        before = snapshot(self.base)
        self.process.side_effect = None
        for code in (0, 2):
            for command in ("new", "continue"):
                with self.subTest(code=code, command=command):
                    self.process.reset_mock()
                    self.process.return_value = subprocess.CompletedProcess([], code)
                    result = self.invoke(command)
                    self.assertEqual(result[0], 1, result)
                    self.assertIn("game-process check refused", result[2])
                    self.assertEqual(before, snapshot(self.base))
                    self.process.assert_called_once_with(["pgrep", "-x", "fm"], capture_output=True)

    def test_real_new_and_continue_relocate_transactions_before_mocked_launch(self):
        for command in ("new", "continue"):
            with self.subTest(command=command):
                cache = self.prepared()
                source = self.transaction().parent
                transactions_before = snapshot(source)
                state = self.ownership_state()
                state_before = state.read_bytes()
                installed, saves, game = (snapshot(self.user / "editor data"),
                                          snapshot(self.user / "games"), snapshot(self.game))
                archives_before = set(cache.parent.glob("preserved-transactions-*"))
                launches = []

                def run(actual, **kwargs):
                    if actual == ["pgrep", "-x", "fm"]:
                        return subprocess.CompletedProcess(actual, 1)
                    self.assertEqual(actual[:2], ["open", "-n"])
                    self.assertFalse(source.exists())
                    self.assertTrue(cache.is_dir())
                    new_archives = set(cache.parent.glob("preserved-transactions-*")) - archives_before
                    self.assertEqual(len(new_archives), 1)
                    self.assertEqual(transactions_before, snapshot(new_archives.pop() / "transactions"))
                    launches.append(actual)
                    return subprocess.CompletedProcess(actual, 0)

                self.process.side_effect = run
                result = self.invoke(command)
                self.assertEqual(result[0], 0, result)
                self.assertEqual(len(launches), 1)
                environment = dict(launches[0][i + 1].split("=", 1)
                                   for i, value in enumerate(launches[0][:-1]) if value == "--env")
                self.assertEqual(bool(environment["DYLD_INSERT_LIBRARIES"]), command == "new")
                self.assertEqual(state_before, state.read_bytes())
                self.assertEqual(installed, snapshot(self.user / "editor data"))
                self.assertEqual(saves, snapshot(self.user / "games"))
                self.assertEqual(game, snapshot(self.game))

    def test_busy_game_or_process_check_error_cannot_trigger_automatic_preparation(self):
        before = snapshot(self.base)
        self.process.side_effect = None
        for code in (0, 2):
            self.process.return_value = subprocess.CompletedProcess([], code)
            for command in ("new", "continue"):
                with self.subTest(code=code, command=command):
                    result = self.invoke(command)
                    self.assertEqual(result[0], 1)
                    self.assertIn("game-process check refused", result[2])
                    self.assertEqual(before, snapshot(self.base))
        self.assertFalse(self.cache().parent.exists())

    def test_actual_launch_uses_unique_private_logs_and_preserves_module_policy(self):
        self.prepared()
        installed = snapshot(self.user / "editor data")
        self.process.side_effect = lambda command, **kwargs: subprocess.CompletedProcess(command, 1 if command[0] == "pgrep" else 0)
        for command in ("new", "new", "continue"):
            result = self.invoke(command)
            self.assertEqual(result[0], 0, result)
            actual = self.process.call_args.args[0]
            self.assertEqual(actual[:2], ["open", "-n"])
            environment = dict(actual[i + 1].split("=", 1) for i, value in enumerate(actual[:-1]) if value == "--env")
            stdout = Path(actual[actual.index("--stdout") + 1])
            stderr = Path(actual[actual.index("--stderr") + 1])
            self.assertEqual(stdout.parent, stderr.parent)
            self.assertEqual(stat.S_IMODE(stdout.parent.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(stdout.stat().st_mode), 0o600)
            self.assertEqual(len(stdout.parent.name), 36)
            self.assertNotEqual(stdout, stderr)
            if command == "new":
                self.assertEqual(Path(environment["FM24_AWARDS_LOG"]).parent, stdout.parent)
                self.assertEqual(environment["FM24_AWARDS_SCHEDULE_MODE"], "apply")
                self.assertEqual(environment["FM24_INTERNATIONAL6_HISTORY_MODE"], "skip-completed")
            else:
                self.assertEqual(environment["FM24_AWARDS_LOG"], "")
                self.assertEqual(environment["DYLD_INSERT_LIBRARIES"], "")
                self.assertEqual(environment["FM24_AWARDS_SCHEDULE_MODE"], "")
        logs = self.user / "FM24-History-Community/logs"
        self.assertEqual(len(list(logs.iterdir())), 3)
        self.assertEqual(installed, snapshot(self.user / "editor data"))

    def test_symlinked_logs_and_old_output_paths_refuse_without_any_writes(self):
        cache = self.prepared()
        state = self.user / "FM24-History-Community"
        state.mkdir()
        logs = state / "logs"
        external = self.base / "external logs"
        external.mkdir()
        logs.symlink_to(external, target_is_directory=True)
        before = snapshot(self.base)
        self.assertEqual(self.invoke("new", "--dry-run")[0], 1)
        self.assertEqual(before, snapshot(self.base))
        logs.unlink()
        logs.mkdir()
        backend, _, _, manifest, _ = cli.context(self.root)
        plan = backend.launch_plan(cache, self.game, self.user, "initialise", cli.sha(manifest))
        output = Path(plan["environment"]["FM24_AWARDS_LOG"])
        output.symlink_to(self.owned())
        before = snapshot(self.base)
        with self.assertRaisesRegex(cli.Refusal, "Symlink refused"):
            cli.session_plan(plan, self.user, create=True)
        self.assertEqual(before, snapshot(self.base))
        output.unlink()
        output = Path(plan["command"][plan["command"].index("--stdout") + 1])
        output.symlink_to(self.owned())
        with self.assertRaisesRegex(cli.Refusal, "Symlink refused"):
            cli.session_plan(plan, self.user, create=True)

    def test_log_uuid_collision_preserves_all_existing_outputs(self):
        cache = self.prepared()
        backend, _, _, manifest, _ = cli.context(self.root)
        plan = backend.launch_plan(cache, self.game, self.user, "initialise", cli.sha(manifest))
        with mock.patch.object(cli.uuid, "uuid4", return_value="00000000-0000-0000-0000-000000000000"):
            cli.session_plan(plan, self.user, create=True)
            before = snapshot(self.base)
            with self.assertRaisesRegex(cli.Refusal, "already exists"):
                cli.session_plan(plan, self.user, create=True)
            self.assertEqual(before, snapshot(self.base))

    def test_source_change_during_prepare_cleans_only_new_staging_directory(self):
        original = cli.payload_content
        changed = False

        def read_with_mutation(data, path, expected):
            nonlocal changed
            content = original(data, path, expected)
            if Path(path) == self.owned() and not changed:
                changed = True
                self.owned().write_bytes(b"changed concurrently by synthetic fixture")
            return content

        with mock.patch.object(cli, "payload_content", side_effect=read_with_mutation):
            result = self.invoke("prepare")
        self.assertEqual(result[0], 1)
        self.assertFalse(self.cache().exists())
        self.assertEqual(list(self.cache().parent.iterdir()), [])
        self.assertEqual(self.owned().read_bytes(), b"changed concurrently by synthetic fixture")

    def test_file_replacement_during_a_read_is_refused(self):
        original = cli.os.fstat
        calls = 0

        def replace_on_second_stat(fd):
            nonlocal calls
            calls += 1
            result = original(fd)
            if calls == 2:
                content = self.owned().read_bytes()
                self.owned().unlink()
                self.owned().write_bytes(content)
            return result

        with mock.patch.object(cli.os, "fstat", side_effect=replace_on_second_stat):
            with self.assertRaisesRegex(cli.Refusal, "Source changed"):
                cli.read(self.owned())

    def test_new_cache_destination_cannot_replace_an_existing_empty_directory(self):
        original = cli.context
        calls = 0
        cache = self.cache()

        def context_with_concurrent_cache(root):
            nonlocal calls
            calls += 1
            result = original(root)
            if calls == 2:
                cache.mkdir(mode=0o700)
            return result

        with mock.patch.object(cli, "context", side_effect=context_with_concurrent_cache):
            result = self.invoke("prepare")
        self.assertEqual(result[0], 1)
        self.assertIn("Cache appeared", result[2])
        self.assertTrue(cache.is_dir())
        self.assertEqual(list(cache.iterdir()), [])

    def test_launch_requires_exact_ddt_without_installing_it(self):
        self.prepared()
        target = self.game / self.data["retention_ddt"][0]["steam_relative"]
        target.unlink()
        before = snapshot(self.base)
        self.assertEqual(self.invoke("new", "--dry-run")[0], 1)
        self.assertEqual(before, snapshot(self.base))
        self.process.assert_not_called()


if __name__ == "__main__":
    unittest.main()
