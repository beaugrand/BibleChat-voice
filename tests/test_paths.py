"""📜 Study Paths: the rules of "only the truth" (packaging/build_paths.py, web/paths.js).

Every reference exists in its Bible, every quiz answer is a verse of its path, no question or step without a
verse, quoted words really stand in the verses, commentary never shows without its label, the published files
in web/paths/ match their hand-written sources, and both versions of BibleChat carry the feature.
"""
import copy
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "packaging"))

import build_paths as bp  # noqa: E402


def read(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
        return f.read()


SOURCES = sorted(glob.glob(os.path.join(bp.SRC_DIR, "*.json")))
_BIBLES = None


def bibles():
    """KJV (built in, or the downloaded copy if the build left one), the Ethiopian Canon, and the BSB if present."""
    global _BIBLES
    if _BIBLES is None:
        _BIBLES = bp.Bibles(download=False)
    return _BIBLES


def need_full_texts(test):
    """The quotation rules compare against the downloaded KJV and BSB (packaging/build_paths.py fetches them; the
    phone build runs it with --check). Without those files, e.g. offline or in the computer build, skip instead of
    failing on wording that only the full texts carry."""
    import tempfile
    have = all(os.path.exists(os.path.join(tempfile.gettempdir(), f)) for f in bp.FILES.values())
    if not have:
        test.skipTest("KJV/BSB downloads not present; run python packaging/build_paths.py --check")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class PathRulesTest(unittest.TestCase):
    def test_every_path_passes_every_rule(self):
        self.assertGreaterEqual(len(SOURCES), 6)
        need_full_texts(self)
        B = bibles()
        for f in SOURCES:
            with self.subTest(path=os.path.basename(f)):
                p = load(f)
                bp.check_path(p, B, os.path.basename(f)[:-5])   # raises PathError on any broken rule
                for s in p["steps"]:
                    self.assertTrue(s["question"].strip() and s["refs"])
                for q in p["quiz"]:
                    self.assertTrue(q["q"].strip() and q.get("answer_refs"), q)
        bp.check_quoted(B)

    def test_broken_paths_are_refused(self):
        need_full_texts(self)
        B = bibles()
        good = load(os.path.join(bp.SRC_DIR, "light-before-sun.json"))
        def broken(change):
            p = copy.deepcopy(good); change(p)
            with self.assertRaises(bp.PathError):
                bp.check_path(p, B, "light-before-sun")
        broken(lambda p: p["steps"][0].update(refs=["Genesis 1:99"]))                     # no such verse
        broken(lambda p: p["steps"][0].update(refs=[]))                                    # a step without a verse
        broken(lambda p: p["quiz"][0].update(answer_refs=["Romans 8:28"]))                 # answer outside the path
        broken(lambda p: p["quiz"][0].update(answer_refs=[]))                              # a question without a verse
        broken(lambda p: p["quiz"][2].update(word="sunshine"))                             # fill-in word not in the verse
        broken(lambda p: p["quiz"][1].update(check={"bible": "KJV", "word": "Sunday"}))    # multiple choice not proved by the verse
        broken(lambda p: p["steps"][0].update(notes=["my-own-notes"]))                     # unlabelled commentary
        broken(lambda p: p["quiz"][4].update(q='Which verse says "the sun shall rule for ever"?'))   # a made-up quotation
        broken(lambda p: p["required_refs"].append("John 3:16"))                           # a listed verse no step shows
        broken(lambda p: p.update(quiz=p["quiz"][:8]))                                     # bank no bigger than what is shown
        ok = copy.deepcopy(good); bp.check_path(ok, B, "light-before-sun")

    def test_published_paths_match_their_sources(self):
        index = load(os.path.join(bp.OUT_DIR, "index.json"))
        self.assertEqual(sorted(x["id"] for x in index), sorted(os.path.basename(f)[:-5] for f in SOURCES))
        for f in SOURCES:
            built = load(os.path.join(bp.OUT_DIR, os.path.basename(f)))
            self.assertEqual(built["built_from"]["sha"], bp.sha(f), f"run python packaging/build_paths.py ({os.path.basename(f)})")
            self.assertEqual(built["built_from"]["checked_in"], ["KJV", "ETH", "BSB"])   # checked against all three
            self.assertEqual(built["labels"], bp.NOTES)
            for q in built["quiz"]:
                self.assertIn("why", q); self.assertIn("score", q)
                self.assertTrue(all(isinstance(w, str) and w for w in q["why"]))

    def test_paths_hold_references_not_scripture(self):
        # a path file holds references and questions; whole verses never sit in it
        B = bibles()
        kjv = {bp.norm(t) for t in B.text["KJV"].values() if len(t) > 60}
        for f in SOURCES:
            s = bp.norm(read("packaging", "paths", os.path.basename(f)))
            self.assertFalse([t for t in kjv if t in s], f)

    def test_first_paths_cover_hans_list(self):
        names = {os.path.basename(f)[:-5] for f in SOURCES}
        for pid in ("light-before-sun", "mist-not-rain", "the-name", "heavens-and-earth", "enoch-and-the-watchers", "word-made-flesh"):
            self.assertIn(pid, names)
        p = load(os.path.join(bp.SRC_DIR, "the-name.json"))
        facts = [f for s in p["steps"] for f in s.get("facts", [])]
        self.assertTrue(any("H3091" in f.get("strongs", []) for f in facts) and any("G2424" in f.get("strongs", []) for f in facts))
        self.assertTrue(any(s["look_closer"].get("letters") == "H3068" for s in p["steps"]))   # YHWH letter by letter


    def test_hans_new_paths_and_pictures(self):
        names = {os.path.basename(f)[:-5] for f in SOURCES}
        self.assertIn("husband-and-wife", names); self.assertIn("the-rainbow", names)
        self.assertIn("freedom-from-bondage", names)
        self.assertIn("my-body-a-temple", names); self.assertIn("life-in-the-womb", names)
        m1 = load(os.path.join(bp.SRC_DIR, "mirror-1-four-beasts.json"))
        self.assertEqual(m1["series"]["id"], "mirror-prophecies"); self.assertEqual(m1["series"]["session"], 1)
        sessions = sorted(load(f)["series"]["session"] for f in SOURCES if load(f).get("series", {}).get("id") == "mirror-prophecies")
        self.assertEqual(sessions, [1, 2, 3, 4, 5, 6, 7])                         # all seven sessions of the series
        self.assertIn("Revelation 13:1-2", m1["required_refs"]); self.assertIn("Daniel 7:1-8", m1["required_refs"])
        for f in SOURCES:                                                            # every picture moves (or says why not)
            self.assertIn(load(f).get("anim", {}).get("kind"), bp.ANIMS, os.path.basename(f))
        d2 = load(os.path.join(bp.SRC_DIR, "daniel-2-statue-and-stone.json"))
        self.assertEqual(d2["category"], bp.GROUPS); self.assertTrue(d2["group"])
        self.assertTrue(d2["read_along"]["url"].startswith("https://"))           # TS2009: a link, never its text
        i53 = load(os.path.join(bp.SRC_DIR, "isaiah-53-suffering-servant.json"))   # Isaiah 52:13-53:12 with its fulfilment
        for r in ("Isaiah 52:13-15", "Isaiah 53:1-12", "Acts 8:27-35", "1 Peter 2:21-25", "Luke 22:37", "Matthew 8:16-17"):
            self.assertIn(r, i53["required_refs"])
        self.assertEqual(i53["category"], "Prophecy"); self.assertTrue(i53["read_along"]["url"].startswith("https://"))
        gs = load(os.path.join(bp.SRC_DIR, "garden-serpent-and-cain.json"))   # the serpent, Eve, Cain and Abel, tested by the text
        for r in ("Genesis 3:1-6", "Genesis 3:14-15", "Genesis 4:1-2", "Genesis 4:3-8", "Genesis 38:2-5", "Romans 9:10-12", "1 John 3:8-12", "John 8:37-44"):
            self.assertIn(r, gs["required_refs"])
        wt = load(os.path.join(bp.SRC_DIR, "wheat-and-tares.json"))           # who is gathered first, and the falling away
        for r in ("Matthew 13:24-30", "Matthew 13:36-43", "Matthew 24:36-42", "John 14:3", "2 Thessalonians 2:3-12", "Matthew 24:23-27"):
            self.assertIn(r, wt["required_refs"])
        self.assertEqual(gs["category"], "Creation"); self.assertEqual(wt["category"], "Prophecy")
        fb = load(os.path.join(bp.SRC_DIR, "freedom-from-bondage.json"))
        for r in ("John 8:34", "John 8:36", "Psalms 107:13-14", "Romans 6:14", "1 Corinthians 10:13", "Galatians 5:1", "1 John 1:9"):
            self.assertIn(r, fb["required_refs"])
        hw = load(os.path.join(bp.SRC_DIR, "husband-and-wife.json"))
        for r in ("Genesis 2:18-25", "Proverbs 31:10-31", "Song of Solomon 2:1-16", "Ephesians 5:21-33", "Colossians 3:18-19",
                  "1 Corinthians 7:1-16", "1 Corinthians 13:4-8", "1 Peter 3:1-7", "Hebrews 13:4", "Ecclesiastes 4:9-12", "Mark 10:6-9"):
            self.assertIn(r, hw["required_refs"])
        rb = load(os.path.join(bp.SRC_DIR, "the-rainbow.json"))
        for r in ("Genesis 9:8-17", "Ezekiel 1:26-28", "Revelation 4:2-3", "Revelation 10:1", "Isaiah 54:9-10"):
            self.assertIn(r, rb["required_refs"])
        # every path has a category (the filter chips) and its own picture, and the cards get them from index.json
        index = {x["id"]: x for x in load(os.path.join(bp.OUT_DIR, "index.json"))}
        for f in SOURCES:
            pid = os.path.basename(f)[:-5]
            self.assertTrue(load(f).get("category"), pid)
            img = os.path.join(bp.IMG_DIR, pid + ".jpg")
            self.assertTrue(os.path.exists(img), pid)
            with open(img, "rb") as fh:
                self.assertEqual(fh.read(3), b"\xff\xd8\xff")                     # a real JPEG
            self.assertLess(os.path.getsize(img), 150_000)                            # small enough for a phone
            x = index[pid]
            self.assertEqual(x["image"], "img/" + pid + ".jpg")
            self.assertEqual(len(x["step_questions"]), x["steps"])
            self.assertGreaterEqual(x["minutes"], 10)


class PathPagesTest(unittest.TestCase):
    def test_make_your_own_and_community(self):
        js = read("web", "paths.js")
        for part in ("Study Paths / Community", "pv-segb", "communityView", "＋ Make your own study path", "editPath", "normRef", "edAddRef",
                     "A.findVerses", "edWords", "Paleo-Hebrew", "data-opt=\"${opt}\"", "my_note", "autoQuiz", "VIS", "sendToCommunity",
                     "openShared", "v: 2", "findPaths", "openCommunity"):
            self.assertIn(part, js)
        self.assertEqual(js.count('class="pnote"'), 1)          # the maker's own note is never drawn as commentary...
        self.assertIn('class="pv-cnote"', js); self.assertIn("not Scripture, and not checked by BibleChat", js)   # ...but labelled as theirs
        phone, computer = read("web", "index.html"), read("bibleask", "web", "index.html")
        for part in ('data-tab="paths"', "BCPaths.findPaths", "findVerses:", "Study Paths about this"):
            self.assertIn(part, phone)
        for part in ('id="sidePaths"', "Study Paths / Community", "data-openpath", "findVerses:", "/api/find?bible="):
            self.assertIn(part, computer)
        self.assertIn('path == "/api/find"', read("bibleask", "server.py"))
        index = load(os.path.join(bp.OUT_DIR, "index.json"))
        self.assertTrue(all(x["books"] for x in index))                          # a search for a book finds its paths

    @unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
    def test_search_finds_study_paths(self):
        script = """global.document = undefined; const P = require(process.argv[1]); console.log("ok");"""
        r = subprocess.run(["node", "-e", script, os.path.join(ROOT, "web", "paths.js")], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        index = load(os.path.join(bp.OUT_DIR, "index.json"))
        hay = " ".join([x for p in index if "garden" in p["id"] for x in [p["title"], p["opening_question"]] + p["step_questions"]]).lower()
        self.assertIn("adam", hay); self.assertIn("eve", hay)                    # "Adam Eve" in a search finds The Garden, the serpent and Cain

    def test_card_grid_layout(self):
        js = read("web", "paths.js")
        for part in ("pv-chips", "pv-grid", "pv-pc-img", "pv-pc-meta", "pv-dots", "pv-pc-steps", "pv-tick", "pv-jump", "pv-track",
                     "grid-template-columns:repeat(2,", "grid-template-columns:repeat(3,", "pv-dark"):
            self.assertIn(part, js)
        for part in ("pv-pc-share", "pv-sharewide", "📤 Send to someone", "sms:?&body=", "https://wa.me/?text=", "mailto:?subject=",
                     "shareHash(p, 0)", "Someone shared this study path with you",
                     "Bible Study Groups", "Add your own study path", "formsubmit.co/ajax/", "issues/new?title=", "Read in ",
                     "pv-shareall", "#/paths/series/", "pv-serqr", "pv-qrbig", "prefers-reduced-motion", "pv-a-fire", "pv-a-mist", "pv-a-rainbow", "pv-ember",
                     "facebook.com/sharer", "x.com/intent", "t.me/share", "pinterest.com/pin", "linkedin.com/sharing", "reddit.com/submit", "pv-so-tt", "shareCard"):
            self.assertIn(part, js)                                                  # a path can be sent to someone
        sw = read("web", "sw.js")
        self.assertIn('"paths/" + p.image', sw)                                     # pictures work offline
        self.assertIn(r"/paths/img/[a-z0-9-]+\.jpg", read("bibleask", "server.py"))  # and on the computer

    def test_commentary_only_with_its_label(self):
        js = read("web", "paths.js")
        for kind, lab in bp.NOTES.items():
            self.assertIn(f'{kind}: "{lab}"', js)
        self.assertEqual(js.count('class="pnote"'), 1)          # one place draws commentary...
        self.assertIn("<h4>${esc(LABEL[kind])}</h4>", js)       # ...and it always starts with the label
        self.assertIn("if(!LABEL[kind]) continue;", js)          # nothing unlabelled gets through
        self.assertIn("not Scripture", js)

    def test_both_versions_carry_study_paths(self):
        phone, computer = read("web", "index.html"), read("bibleask", "web", "index.html")
        for page, src in ((phone, 'src="paths.js"'), (computer, 'src="/paths.js"')):
            for part in (src, 'id="pathsView"', "pathsBtn", "BCPaths.mount", "Make a study path", 'id="homePaths"'):
                self.assertIn(part, page)
        self.assertIn("BCPaths.openHash", phone)                 # links and QR codes open a path
        self.assertIn("/^#\\/paths?(\\/|$)/", phone)
        for part in ('property="og:image"', 'name="twitter:card"', "og-studypaths.jpg"):
            self.assertIn(part, phone)                                                # a posted link shows a picture   # "#/paths" opens the list of all Study Paths
        sw = read("web", "sw.js")
        for part in ('"paths.js"', '"paths/index.json"', '"quoted.json"', '"paths/" + p.id'):
            self.assertIn(part, sw)                               # works offline
        study = read("web", "build_study.py")                   # the phone build (pages.yml runs build_study.py)
        for part in ('"paths.js", "quoted.json"', 'os.path.join(web, "paths")'):
            self.assertIn(part, study)
        self.assertIn("build_study.py site", read(".github", "workflows", "pages.yml"))
        spec = read("BibleChat.spec")
        self.assertIn('("web/paths", "web/paths")', spec); self.assertIn('("web/paths.js", "web")', spec)
        i18n = read("web", "i18n.js")
        self.assertIn(".pvx", i18n)                               # path content is never run through the translator
        for phrase in ("📜 Study Paths", "What do you see?", "Questions and answers", "Why this question?", "Show the answer"):
            self.assertIn(f'"{phrase}":', i18n)

    def test_computer_serves_the_same_study_files(self):
        from bibleask import studyfiles
        self.assertEqual(studyfiles.get("books.json")[0], "Genesis")
        kjv = studyfiles.get("kjv/0.json"); self.assertIn("1:1", kjv)
        self.assertTrue(any(isinstance(w, list) and w[1].startswith("H") for w in kjv["1:1"]))
        x = studyfiles.get("xref/0.json")["1:1"][0]; self.assertEqual(len(x), 6)            # book, ch, v, ch2, v2, votes
        self.assertIn("H216", studyfiles.get("dict/H0.json"))
        self.assertTrue(studyfiles.get("where/H2.json")["H216"])
        self.assertIsNone(studyfiles.get("../server.py"))
        from bibleask.server import shared_web_dir
        self.assertTrue(os.path.exists(os.path.join(shared_web_dir(), "paths", "index.json")))

    @unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
    def test_question_choice(self):
        # the strongest questions first, at least one of each kind, never more than the path shows
        script = """const P = require(process.argv[1]); const p = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
const c = P.choose(p); console.log(JSON.stringify({n: c.pick.length, rest: c.rest.length, types: [...new Set(c.pick.map(q => q.type))].sort(),
  sorted: c.pick.every((q, i) => !i || c.pick[i - 1].rank >= q.rank), refs: P.parseRef('John 17:11-12'), whole: P.parseRef('Jubilees 4-5')}));"""
        for f in SOURCES:
            built = os.path.join(bp.OUT_DIR, os.path.basename(f))
            r = subprocess.run(["node", "-e", script, os.path.join(ROOT, "web", "paths.js"), built], capture_output=True, text=True, encoding="utf-8", timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            out, p = json.loads(r.stdout), load(built)
            self.assertEqual(out["n"], p.get("show", 8)); self.assertEqual(out["n"] + out["rest"], len(p["quiz"]))
            self.assertEqual(out["types"], sorted({q["type"] for q in p["quiz"]}))
            self.assertTrue(out["sorted"])
            self.assertEqual(out["refs"], {"book": "John", "c1": 17, "v1": 11, "c2": 17, "v2": 12})
            self.assertEqual(out["whole"], {"book": "Jubilees", "c1": 4, "v1": None, "c2": 5, "v2": None})


if __name__ == "__main__":
    unittest.main()
