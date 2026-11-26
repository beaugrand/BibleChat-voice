"""📘 The printed book "Walking with Yeshua" (web/book.js, handover of 22 November 2026).

The rules tested: the verse text in the book is the Yahweh Edition word for word (never written by anyone else); every
page group has its corner label ("Forgiveness, step 3 of 9") and there are no page numbers; "Yeshua", not "Jesus", in
the book's own words; the Friday night Bible study is left out unless asked for; the welcome note is Hans's approved
text; the Love Donations note and the credit stay; and the button is wired into the phone page."""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def read(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
        return f.read()


WELCOME = ("I made this book because I wanted to go back to the roots of Scripture. I wanted to use today's technology to look "
           "at the original languages, down to the letters themselves, like Paleo Hebrew and Ge'ez. This study holds the 66 books "
           "we have all been handed, and it also makes room for the books of the Ethiopian canon, because both are dear to my "
           "heart. Walk with me, and let's go back to the source.")

# Node: the plan of the book for the given options, with the real paths and prayers and verses handed in
HARNESS = r"""
const fs = require("fs"), path = require("path"), web = process.argv[1], opts = JSON.parse(process.argv[2]), verses = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const B = require(path.join(web, "book.js"));
const list = JSON.parse(fs.readFileSync(path.join(web, "paths", "index.json"), "utf8"));
const paths = B._choose(list, opts).map(p => Object.assign({}, p, JSON.parse(fs.readFileSync(path.join(web, "paths", p.id + ".json"), "utf8"))));
const prayers = JSON.parse(fs.readFileSync(path.join(web, "prayers.json"), "utf8"));
const refs = B._refs(opts, paths, prayers);
const groups = B._plan(opts, {paths, prayers, verses, qr: u => "<svg data-url=\"" + u + "\"></svg>", base: "paths/"});
process.stdout.write(JSON.stringify({ids: paths.map(p => p.id), refs, groups}));
"""


@unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
class BookPlanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from bibleask.loaders import load_bible
        cls.yahweh = {}
        for v in load_bible(os.path.join(ROOT, "bibles", "eng-yahweh-edition.usfx.xml")).verses:
            cls.yahweh.setdefault(v.book, {}).setdefault(v.chapter, {})[v.verse] = v.text
        cls.tmp = os.path.join(ROOT, "tests", "_book_verses.json")

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.tmp):
            os.unlink(cls.tmp)

    def verses_for(self, refs):
        out = {}
        for r in refs:
            m = re.match(r"^(.+?) (\d+)(?::(\d+))?(?:-(\d+)(?::(\d+))?)?$", r)
            book, c1, v1, x, y = m.groups()
            if book not in self.yahweh:
                continue
            c1 = int(c1)
            c2 = int(x) if (v1 is None and x) or y else c1
            vs = []
            for c in range(c1, c2 + 1):
                for v, t in sorted(self.yahweh[book].get(c, {}).items()):
                    lo = int(v1) if v1 and c == c1 else 1
                    hi = (int(y) if y else int(x) if x and v1 else 10 ** 6) if c == c2 else 10 ** 6
                    if lo <= v <= hi:
                        vs.append([book, c, v, t])
            if vs:
                out[r] = {"src": "YAHWEH", "vs": vs}
        return out

    def plan(self, opts):
        # two passes: the first asks which references the book needs, the second hands in their Yahweh Edition text
        with open(self.tmp, "w", encoding="utf-8") as f:
            json.dump({}, f)
        run = lambda: subprocess.run(["node", "-e", HARNESS, os.path.join(ROOT, "web"), json.dumps(opts), self.tmp],
                                     capture_output=True, text=True, check=True).stdout
        first = json.loads(run())
        with open(self.tmp, "w", encoding="utf-8") as f:
            json.dump(self.verses_for(first["refs"]), f)
        return json.loads(run())

    def test_forgiveness_alone(self):
        got = self.plan({"only": "forgiveness"})
        self.assertEqual(got["ids"], ["forgiveness"])
        labels = [g["label"] for g in got["groups"]]
        self.assertEqual(labels[0], "Forgiveness, start")
        self.assertIn("Forgiveness, step 3 of 9", labels)
        self.assertEqual(labels[-2:], ["Forgiveness, closing prayer", "Forgiveness, living it out"])
        self.assertNotIn("cover", [g["kind"] for g in got["groups"]])   # one path alone: no cover, no contents
        html = "".join("".join(g["blocks"]) for g in got["groups"])
        self.assertIn('data-url="https://beaugrand.github.io/BibleChat-voice/p/forgiveness/"', html)
        self.assertIn("seventy times seven", html)
        # every verse in the book is the Yahweh Edition, word for word
        verses = re.findall(r'<p class="bk-v"><sup>(\d+):(\d+)</sup> (.*?)</p>', html)
        self.assertGreater(len(verses), 50)
        import html as H
        for c, v, t in verses:   # the text stands at that chapter and verse in some book of the Yahweh Edition
            same = {b.get(int(c), {}).get(int(v)) for b in self.yahweh.values()}
            self.assertIn(H.unescape(t), same, f"{c}:{v}")

    def test_whole_book(self):
        got = self.plan({})
        kinds = [g["kind"] for g in got["groups"]]
        self.assertEqual(kinds[:3], ["cover", "welcome", "toc"])
        self.assertIn("library", kinds)
        # the Friday night Bible study (Daniel 2 to 5) only when asked for
        self.assertFalse([i for i in got["ids"] if i.startswith("daniel-")])
        self.assertTrue([i for i in self.plan({"daniel": True})["ids"] if i.startswith("daniel-")])
        welcome = "".join(got["groups"][1]["blocks"])
        self.assertIn(WELCOME.replace("'", "&#39;"), welcome)
        for x in ("Love Donations", "$HansBeaugrand", "@Hans-Beaugrand", "https://cash.app/$HansBeaugrand",
                  "https://venmo.com/u/Hans-Beaugrand", "Hans W. Beaugrand", "Apache License 2.0", "NOTICE"):
            self.assertIn(x, welcome)
        cover = "".join(got["groups"][0]["blocks"])
        for x in ("Walking with Yeshua", "Study paths, scripture and prayers", "Hans W. Beaugrand", 'data-url="https://beaugrand.github.io/BibleChat-voice/"'):
            self.assertIn(x, cover)
        for g in got["groups"][1:]:
            self.assertTrue(g["label"], g["kind"])   # every page but the cover has its corner label
            words = re.sub(r'<p class="bk-v">.*?</p>', "", "".join(g["blocks"]))   # the book's own words, not the verses
            self.assertNotRegex(words, r"\bJesus\b", g["label"])
        self.assertFalse(re.search(r"page \d", json.dumps(got["groups"]), re.I))   # no page numbers

    def test_lord_star(self):
        js = read("web", "book.js")
        self.assertIn('"Numbers 14:14": /\\byou Lord\\b/g', js)
        self.assertIn('"2 Chronicles 30:18": /\\bgood Lord\\b/g', js)
        self.assertEqual(self.yahweh["Numbers"][14][14].count("you Lord"), 2)
        self.assertIn("good Lord", self.yahweh["2 Chronicles"][30][18])


class BookWiringTest(unittest.TestCase):
    def test_phone_page(self):
        phone = read("web", "index.html")
        self.assertIn('<script src="book.js"></script>', phone)
        self.assertIn('YAHWEH: "eng-yahweh-edition"', phone)
        self.assertIn('"book.js", "book-cover.jpg"', read("web", "sw.js"))
        self.assertIn('"book.js", "book-cover.jpg"', read("web", "build_study.py"))
        self.assertTrue(os.path.exists(os.path.join(ROOT, "web", "book-cover.jpg")))
        js = read("web", "paths.js")
        self.assertIn('if(t.closest(".pv-book")){ BCBook.open(); return; }', js)
        self.assertIn('typeof BCBook !== "undefined"', js)
        self.assertNotIn("book.js", read("bibleask", "web", "index.html"))   # phone only for now

    def test_print_rules(self):
        js = read("web", "book.js")
        self.assertIn("@page{size:letter;margin:0}", js)   # US Letter, and no browser header or footer
        self.assertIn(".bk-body{position:absolute;top:.75in;bottom:.6in;left:1.15in;right:.65in", js)   # wide inner margin for the punch


if __name__ == "__main__":
    unittest.main()
