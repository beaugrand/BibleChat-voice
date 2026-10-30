"""🌍 Study paths in Spanish and German (packaging/paths/i18n/<lang>/<id>.json, checked and built by
packaging/build_paths.py into web/paths/<id>.json "i18n", shown by web/paths.js inLang)."""
import glob
import json
import os
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
I18N = os.path.join(ROOT, "packaging", "paths", "i18n")


def load(*rel):
    with open(os.path.join(ROOT, *rel), encoding="utf-8") as f:
        return json.load(f)


class PathLanguagesTest(unittest.TestCase):
    def test_the_daniel_series_is_in_spanish_and_german(self):
        for lang in ("es", "de"):
            for n, pid in ((2, "daniel-2-statue-and-stone"), (3, "daniel-3-fiery-furnace"),
                           (4, "daniel-4-the-tree-and-the-king"), (5, "daniel-5-writing-on-the-wall")):
                self.assertTrue(os.path.exists(os.path.join(I18N, lang, pid + ".json")), f"{lang} Daniel {n}")

    def test_the_five_foundations_are_in_spanish_and_german(self):
        for lang in ("es", "de"):
            for pid in ("jesus-in-the-gospels", "salvation-how-are-we-saved", "prayer-teach-us-to-pray",
                        "the-holy-spirit", "the-psalms"):
                self.assertTrue(os.path.exists(os.path.join(I18N, lang, pid + ".json")), f"{lang} {pid}")

    def test_the_mirror_series_is_in_spanish_and_german(self):
        for lang in ("es", "de"):
            for n in range(1, 8):
                self.assertEqual(len(glob.glob(os.path.join(I18N, lang, f"mirror-{n}-*.json"))), 1, f"{lang} mirror {n}")

    def test_each_translation_matches_its_english_path(self):
        files = glob.glob(os.path.join(I18N, "*", "*.json"))
        self.assertTrue(files)
        for fn in files:
            lang, pid = fn.split(os.sep)[-2], os.path.basename(fn)[:-5]
            with self.subTest(lang=lang, path=pid):
                self.assertIn(lang, ("es", "de"))
                t, en = load(fn), load("packaging", "paths", pid + ".json")
                self.assertTrue(t["title"].strip() and t["opening_question"].strip())
                self.assertEqual(len(t["steps"]), len(en["steps"]))
                for ts, es in zip(t["steps"], en["steps"]):
                    self.assertTrue(ts["question"].strip())
                    self.assertEqual(len(ts["facts"]), len(es["facts"]))
                self.assertEqual(len(t["remember"]), len(en.get("remember", [])))
                self.assertNotIn("“", json.dumps(t, ensure_ascii=False))   # quotes are straight, so the checker finds them

    def test_quotes_are_checked_against_reina_valera_and_luther(self):
        src = open(os.path.join(ROOT, "packaging", "build_paths.py"), encoding="utf-8").read()
        for part in ('"es": ("RV1909"', '"de": ("LUT"', "def translations(", 'is not in the {key} near'):
            self.assertIn(part, src)

    def test_the_app_shows_the_path_in_the_app_language(self):
        js = open(os.path.join(ROOT, "web", "paths.js"), encoding="utf-8").read()
        self.assertIn("function inLang(p)", js)
        self.assertIn("return inLang(await cache[id]);", js)
        self.assertIn("list.forEach(inLang)", js)

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_switching_language_and_back(self):
        script = r"""
const fs = require("fs"), src = fs.readFileSync(process.argv[1] + "/web/paths.js", "utf8");
eval(src.match(/function inLang\(p\)\{[\s\S]*?\n  \}\n/)[0].replace("function inLang", "globalThis.inLang = function"));
const p = JSON.parse(fs.readFileSync(process.argv[1] + "/web/paths/daniel-5-writing-on-the-wall.json", "utf8"));
const en = [p.title, p.steps[0].question, p.steps[0].facts[0].text, p.remember[0].text];
globalThis.UI_LANG = "de"; inLang(p); const de = [p.title, p.steps[0].question, p.steps[0].facts[0].text, p.remember[0].text, p.steps[0].facts[0].refs];
globalThis.UI_LANG = "fr"; inLang(p); const fr = [p.title, p.steps[0].question, p.steps[0].facts[0].text, p.remember[0].text];
console.log(JSON.stringify({en, de, fr}));
"""
        built = os.path.join(ROOT, "web", "paths", "daniel-5-writing-on-the-wall.json")
        if "i18n" not in load(built):
            self.skipTest("web/paths not built with translations")
        out = json.loads(subprocess.run(["node", "-e", script, ROOT], capture_output=True, text=True, check=True).stdout)
        self.assertEqual(out["de"][0], "Daniel 5: die Schrift an der Wand")
        self.assertNotIn(out["de"][1], out["en"])
        self.assertEqual(out["de"][4], ["Daniel 1:2"])        # the verses stay the same
        self.assertEqual(out["fr"], out["en"])                 # no French version: English again


if __name__ == "__main__":
    unittest.main()
