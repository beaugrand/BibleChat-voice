"""Windows desktop / Start-menu icons. Runs on the Windows build machine; skipped elsewhere."""
import os
import subprocess
import sys
import tempfile
import unittest

_TMP = tempfile.mkdtemp()
os.environ["APPDATA"] = _TMP         # keep test settings out of the real BibleChat folder
os.environ["XDG_DATA_HOME"] = _TMP
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bibleask import shortcuts, storage  # noqa: E402


def _target(lnk: str) -> str:
    ps = f"(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}').TargetPath"
    return subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True).stdout.strip()


@unittest.skipUnless(sys.platform.startswith("win"), "Windows only")
class Shortcuts(unittest.TestCase):
    def test_create_then_follow_a_move_but_respect_a_delete(self):
        desk, menu = tempfile.mkdtemp(), tempfile.mkdtemp()
        storage.save_settings({})
        first = shortcuts.ensure(target=sys.executable, desktop=desk, menu=menu)
        d, m = os.path.join(desk, "BibleChat.lnk"), os.path.join(menu, "BibleChat.lnk")
        self.assertEqual(sorted(first), sorted([d, m]))
        self.assertEqual(_target(d).lower(), sys.executable.lower())
        self.assertEqual(shortcuts.ensure(target=sys.executable, desktop=desk, menu=menu), [])  # nothing to do
        os.remove(d)                                              # the person deleted the desktop icon
        moved = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        shortcuts.ensure(target=moved, desktop=desk, menu=menu)    # the app folder moved
        self.assertFalse(os.path.exists(d))                       # not put back
        self.assertEqual(_target(m).lower(), moved.lower())       # Start-menu icon follows the move


class NotWindows(unittest.TestCase):
    def test_does_nothing_elsewhere(self):
        if not sys.platform.startswith("win"):
            self.assertEqual(shortcuts.ensure(target="/x/BibleChat"), [])


if __name__ == "__main__":
    unittest.main()
