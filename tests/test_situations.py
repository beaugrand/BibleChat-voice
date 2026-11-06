"""🕊 What would Jesus do? (packaging/build_situations.py, web/situations.js, the box under the phone's search field).

Every reference exists, "What Jesus said" is only verses with His words, the words in red stand exactly where the King
James marks them, the published file matches its hand-written source, the matching finds the right situation, and
the phone carries the feature, keeps it for offline use and sends nothing anywhere.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "packaging"))

import build_paths as bp  # noqa: E402
import build_situations as bs  # noqa: E402


def read(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
        return f.read()


SRC = json.loads(read("packaging", "situations.json"))
OUT = json.loads(read("web", "situations.json"))


class SituationRulesTest(unittest.TestCase):
    def test_published_file_matches_its_source_and_every_rule(self):
        have = os.path.exists(os.path.join(tempfile.gettempdir(), bp.FILES["KJV"]))
        if not have:
            self.skipTest("the King James download is not present; run python packaging/build_situations.py --check")
        built = bs.build(bp.Bibles(download=False))
        self.assertEqual(bp.dumps(built), read("web", "situations.json"), "run python packaging/build_situations.py")

    def test_references_only_never_verse_text(self):
        self.assertGreaterEqual(len(SRC["situations"]), 20)
        for s in SRC["situations"]:
            self.assertEqual(set(s) - {"id", "title", "words", "jesus", "did", "verses", "prayer", "path", "help"}, set(), s["id"])
            for g in s["did"] + s["verses"]:
                self.assertEqual(set(g), {"point", "refs"}, s["id"])
            for r in bs.all_refs(s):
                self.assertRegex(r, r"^[1-3]? ?[A-Z][A-Za-z ]+ \d+:\d+(-\d+)?$", s["id"])

    def test_prayers_and_paths_exist(self):
        prayers = {p["id"] for p in json.loads(read("web", "prayers.json"))["prayers"]}
        paths = {p["id"] for p in json.loads(read("web", "paths", "index.json"))}
        for s in OUT["situations"]:
            self.assertIn(s["prayer"], prayers, s["id"])
            if s.get("path"):
                self.assertIn(s["path"], paths, s["id"])

    def test_red_marks_only_for_verses_of_the_answers(self):
        verses = set()
        for s in OUT["situations"]:
            for r in bs.all_refs(s):
                book, (c1, v1), (c2, v2) = bp.parse_ref(r)
                verses.update(f"{book} {c1}:{v}" for v in range(v1, v2 + 1))
        self.assertTrue(OUT["red"])
        for ref, marks in OUT["red"].items():
            self.assertIn(ref, verses)
            for m in marks:
                self.assertEqual(set(m), {"n", "h", "s"})
                self.assertTrue(all(0 <= a < z <= m["n"] for a, z in m["s"]), ref)
        # the corrections the Study Paths make apply here too: the "Amen" of Matthew 28:20 is not red
        m = OUT["red"]["Matthew 28:20"][0]
        self.assertLess(m["s"][-1][1], m["n"])

    def test_a_crisis_gets_a_help_line(self):
        despair = next(s for s in OUT["situations"] if s["id"] == "despair")
        self.assertIn("988", despair["help"])
        self.assertIn("suicide", despair["words"])


@unittest.skipUnless(shutil.which("node"), "Node.js not installed")
class SituationMatchTest(unittest.TestCase):
    def run_js(self, body):
        js = ("const S = require(" + json.dumps(os.path.join(ROOT, "web", "situations.js")) + ");"
              "S.use(require(" + json.dumps(os.path.join(ROOT, "web", "situations.json")) + "));" + body)
        return json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)

    def test_situations_are_recognised(self):
        cases = {
            "I lost my job and I'm scared I can't pay the rent": "money-work",
            "My mother passed away last week": "grief",
            "My coworker keeps gossiping about me": "conflict",
            "What if my family doesn’t understand?": "family",
            "I can’t stop drinking": "temptation",
            "My husband cheated on me": "marriage",
            "I feel so alone": "lonely",
            "I have cancer": "sickness",
            "Should I take the new job offer?": "decision",
            "I feel hopeless and want to give up": "despair",
            "My friend betrayed me and I cannot forgive him": "someone-hurt-me",
            "I don't know if God is real": "doubt",
            "someone stole my car": "someone-hurt-me",
        }
        got = self.run_js("console.log(JSON.stringify(" + json.dumps(list(cases)) + ".map(q => (S.match(q)[0] || {}).id || null)))")
        self.assertEqual(dict(zip(cases, got)), cases)

    def test_nothing_found_and_no_double_counting(self):
        got = self.run_js("console.log(JSON.stringify([S.match('hello'), S.match(''), S.match('My mother passed away')[0].n, S.match('worried sick')[0].n]))")
        self.assertEqual(got[:2], [[], []])
        self.assertEqual(got[2], 3)   # "passed away" once, not "passed" again
        self.assertEqual(got[3], 3)   # "worried sick" once, not "worried" again

    def test_red_only_in_the_text_it_was_made_for(self):
        ref = "John 14:27"
        got = self.run_js(
            "const kjv = 'Peace I leave with you, my peace I give unto you: not as the world giveth, give I unto you. "
            "Let not your heart be troubled, neither let it be afraid.';"
            "console.log(JSON.stringify([S.redHtml(" + json.dumps(ref) + ", kjv), S.redHtml(" + json.dumps(ref) + ", kjv + ' x'), S.redHtml('Genesis 1:1', '<b>')]))")
        self.assertTrue(got[0].startswith('<span class="wj-red">Peace I leave'))
        self.assertNotIn("wj-red", got[1])          # another wording: no red rather than red in the wrong place
        self.assertEqual(got[2], "&lt;b&gt;")


class PhoneCarriesItTest(unittest.TestCase):
    def test_box_under_the_search_field(self):
        page = read("web", "index.html")
        self.assertIn('<script src="situations.js"></script>', page)
        search = page[page.index('<section id="v-search"'):page.index("<!-- BIBLES -->")]
        self.assertLess(search.index('id="sform"'), search.index('id="wwjd"'))   # right under the search field
        self.assertLess(search.index('id="wwjd"'), search.index('id="results"'))
        for part in ("🕊 What would Jesus do?", 'id="wwjdIn"', 'id="wwjdChat"', "Nothing you type leaves this phone."):
            self.assertIn(part, search)

    def test_nothing_is_sent_or_kept(self):
        page = read("web", "index.html")
        body = page[page.index("/* 🕊 What would Jesus do? (web/situations.js, web/situations.json)"):page.index("/* ---------- Bibles list ---------- */")]
        for bad in ("fetch(", "store.set", "askAI", "localStorage", "pastq"):
            self.assertNotIn(bad, body)
        self.assertIn("The headings are BibleChat's words, not Scripture.", body)
        self.assertNotIn("fetch(", read("web", "situations.js").replace('fetch(url || "situations.json")', ""))

    def test_kept_for_offline_use_and_published(self):
        sw = read("web", "sw.js")
        self.assertIn('"situations.js", "situations.json"', sw)
        self.assertIn('"situations.js", "situations.json"', read("web", "build_study.py"))

    def test_every_new_phrase_is_translated(self):
        src = read("web", "i18n.js")
        for k in ("🕊 What would Jesus do?", "Tell me your situation…", "What Jesus said", "What Jesus did",
                  "More from Scripture", "A prayer for this", "Search the Bible for these words",
                  "The headings are BibleChat's words, not Scripture. The verses are from the Bible you are reading."):
            self.assertIn(json.dumps(k, ensure_ascii=False) + ": [", src)
        page = read("web", "index.html")
        body = page[page.index("/* 🕊 What would Jesus do? (web/situations.js, web/situations.json)"):page.index("/* ---------- Bibles list ---------- */")]
        for k in re.findall(r'tr\("([^"]+)"\)', body):
            self.assertIn(json.dumps(k, ensure_ascii=False) + ": [", src, k)


if __name__ == "__main__":
    unittest.main()
