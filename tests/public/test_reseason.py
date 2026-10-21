"""Private synthetic fixtures only: no game, installed user files or real FMFs."""
from contextlib import redirect_stderr, redirect_stdout
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest import mock

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

    def owned(self, index=0):
        return self.user / "editor data" / self.data["own_fmfs"][index]["name"]

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
        self.assertFalse((self.user / "ReSeason").exists())

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
        self.assertFalse((self.user / "ReSeason").exists())

    def test_executable_mismatch_prevents_prepare(self):
        self.binary.write_bytes(b"another executable")
        result = self.invoke("prepare")
        self.assertEqual(result[0], 1)
        self.assertIn("Supported executable SHA: missing or mismatched", result[1])
        self.assertFalse((self.user / "ReSeason").exists())

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
                self.assertFalse((self.user / "ReSeason").exists())
                self.data["files"][0]["path"] = original

    def test_prepare_copies_only_declared_assets_and_is_idempotent(self):
        project_before, game_before = snapshot(self.root), snapshot(self.game)
        installed_before = snapshot(self.user / "editor data")
        cache = self.prepared()
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
        self.assertEqual(installed_before, snapshot(self.user / "editor data"))

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

    def test_cache_parent_symlink_and_repository_cache_are_refused(self):
        (self.user / "ReSeason").symlink_to(self.base / "not created")
        before = snapshot(self.base)
        self.assertIn("Symlink refused", self.invoke("prepare")[2])
        self.assertEqual(before, snapshot(self.base))
        with self.assertRaisesRegex(cli.Refusal, "outside the project"):
            cli.cache_path(self.root, self.root / "private data", "key")

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
        original = cli.read
        changed = False

        def read_with_mutation(path, expected=None):
            nonlocal changed
            content = original(path, expected)
            if Path(path) == self.owned() and expected is not None and not changed:
                changed = True
                self.owned().write_bytes(b"changed concurrently by synthetic fixture")
            return content

        with mock.patch.object(cli, "read", side_effect=read_with_mutation):
            result = self.invoke("prepare")
        self.assertEqual(result[0], 1)
        self.assertFalse(self.cache().exists())
        self.assertEqual(list((self.user / "ReSeason").iterdir()), [])
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
