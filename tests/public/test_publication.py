"""Regression checks for keeping a mixed private/public workspace private."""
from pathlib import Path
import hashlib
import importlib.util
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[2] / "scripts/check_publication.py"
spec = importlib.util.spec_from_file_location("publication_guard", SOURCE)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class PublicationTests(unittest.TestCase):
    def test_traversal_and_absolute_paths_are_refused(self):
        for name in ("../private", "/private", "a/../secret", "a\\secret", "", "a//b"):
            with self.subTest(name=name):
                self.assertFalse(guard.safe_relative(name))

    def test_clean_file_is_accepted(self):
        with tempfile.TemporaryDirectory() as t:
            r = Path(t)
            (r / "README.md").write_text("Public documentation.")
            self.assertEqual(guard.check(r, {"public_files": ["README.md"]}), [])

    def test_private_path_is_refused_without_printing_its_value(self):
        with tempfile.TemporaryDirectory() as t:
            r = Path(t)
            (r / "sample.txt").write_text("/" + "Users/" + "private-person/Downloads/file")
            errors = guard.check(r, {"public_files": ["sample.txt"]})
            self.assertTrue(errors)
            self.assertNotIn("private-person", str(errors))

    def test_token_is_refused_without_printing_it(self):
        with tempfile.TemporaryDirectory() as t:
            r = Path(t)
            (r / "sample.txt").write_text("gh" + "p_" + "A" * 36)
            self.assertTrue(guard.check(r, {"public_files": ["sample.txt"]}))

    def test_save_file_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            r = Path(t)
            (r / "personal.fm").write_bytes(b"not a real save")
            self.assertTrue(guard.check(r, {"public_files": ["personal.fm"]}))

    def test_symlink_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            r = Path(t)
            (r / "source.txt").write_text("local only")
            (r / "link.txt").symlink_to("source.txt")
            self.assertTrue(guard.check(r, {"public_files": ["link.txt"]}))

    def test_payload_tampering_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            r = Path(t)
            (r / "payload.txt").write_text("changed")
            m = {"public_files": ["payload.txt"], "pinned_files": {"payload.txt": hashlib.sha256(b"original").hexdigest()}}
            self.assertTrue(guard.check(r, m))

    def test_duplicate_allowlist_is_refused(self):
        self.assertTrue(guard.check(Path("."), {"public_files": ["same", "same"]}))


if __name__ == "__main__":
    unittest.main()
