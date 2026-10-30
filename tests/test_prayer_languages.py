"""🌍 The prayers in Spanish and German (web/prayers.es.json, web/prayers.de.json, read by web/prayers.js)."""
import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")


def load(name):
    with open(os.path.join(WEB, name), encoding="utf-8") as f:
        return json.load(f)


class PrayerLanguagesTest(unittest.TestCase):
    def test_every_prayer_is_translated(self):
        en = {p["id"]: p for p in load("prayers.json")["prayers"]}
        for lang, amen in (("es", "Amén."), ("de", "Amen.")):
            tr = load(f"prayers.{lang}.json")["prayers"]
            self.assertEqual(sorted(tr), sorted(en), f"{lang}: a prayer is missing or left over")
            for pid, p in en.items():
                with self.subTest(lang=lang, prayer=pid):
                    t = tr[pid]
                    self.assertTrue(t["title"].strip())
                    if p.get("text"):   # a written prayer: the same paragraphs, ending with Amen
                        self.assertEqual(len(t["text"]), len(p["text"]))
                        self.assertTrue(all(x.strip() for x in t["text"]))
                        self.assertTrue(t["text"][-1].rstrip().endswith(amen))
                    else:               # a prayer of the Bible: the verses are the prayer, no typed text
                        self.assertNotIn("text", t)
                        self.assertTrue(t.get("by"))

    def test_the_files_go_everywhere(self):
        with open(os.path.join(WEB, "prayers.js"), encoding="utf-8") as f:
            self.assertIn('LANGS = ["es", "de"]', f.read())
        for path, needle in ((os.path.join(WEB, "build_study.py"), '"prayers.es.json", "prayers.de.json"'),
                             (os.path.join(WEB, "sw.js"), '"prayers.es.json", "prayers.de.json"'),
                             (os.path.join(ROOT, "bibleask", "server.py"), '"/prayers.es.json", "/prayers.de.json"'),
                             (os.path.join(ROOT, "BibleChat.spec"), '("web/prayers.es.json", "web")')):
            with open(path, encoding="utf-8") as f:
                self.assertIn(needle, f.read(), path)


if __name__ == "__main__":
    unittest.main()
