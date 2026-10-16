"""The 'Update available' box: shown only when GitHub's newest release is newer than this copy."""
import io
import json
import tempfile
import unittest
from unittest import mock

from bibleask import __version__, updates


class Updates(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        # its own settings folder on every system (macOS ignores XDG_DATA_HOME)
        self.env = mock.patch("bibleask.storage.data_dir", return_value=self.tmp.name)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def _github_says(self, tag):
        class R(io.BytesIO):
            def __enter__(s): return s
            def __exit__(s, *a): return False
        return mock.patch("bibleask.llm._open", return_value=R(json.dumps({"tag_name": tag}).encode()))

    def test_version_compare(self):
        self.assertTrue(updates.newer("v1.0.10", "1.0.9"))
        self.assertTrue(updates.newer("v2.0.0", "1.9.9"))
        self.assertFalse(updates.newer("v1.0.1", "1.0.1"))
        self.assertFalse(updates.newer("v1.0.0", "1.0.1"))

    def test_newer_release_is_offered(self):
        with self._github_says("v99.0.0"):
            u = updates.check(force=True)
        self.assertEqual(u["version"], "99.0.0")
        self.assertIn("releases/latest", u["url"])
        self.assertEqual(updates.status()["version"], __version__)

    def test_same_version_shows_nothing(self):
        with self._github_says("v" + __version__):
            self.assertIsNone(updates.check(force=True))

    def test_offline_shows_nothing(self):
        with mock.patch("bibleask.llm._open", side_effect=OSError("offline")):
            self.assertIsNone(updates.check(force=True))

    def test_asks_github_once_a_day(self):
        with self._github_says("v99.0.0") as m:
            updates.check(force=True)
            updates.check()
            self.assertEqual(m.call_count, 1)


if __name__ == "__main__":
    unittest.main()
