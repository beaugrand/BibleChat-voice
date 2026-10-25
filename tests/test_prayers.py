"""🙏 Prayers (web/prayers.json, web/prayers.js): every prayer stands on real verses, every Study Path ends with its own
closing prayer, every book of the Bible has a prayer for 🙏 Pray in Read, written prayers say they are not Scripture, both
versions of BibleChat carry the feature, and the AI prayer on the computer is built only on the verses it is given."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "packaging"))
os.environ.setdefault("XDG_DATA_HOME", tempfile.mkdtemp())   # keep test data out of the real data folder

import build_paths as bp  # noqa: E402
from bibleask import llm, server  # noqa: E402


def read(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
        return f.read()


DATA = json.loads(read("web", "prayers.json"))
PAGES = [os.path.join("web", "index.html"), os.path.join("bibleask", "web", "index.html")]
BOOKS66 = ("Genesis Exodus Leviticus Numbers Deuteronomy Joshua Judges Ruth|1 Samuel|2 Samuel|1 Kings|2 Kings|1 Chronicles|"
           "2 Chronicles|Ezra Nehemiah Esther Job Psalms Proverbs Ecclesiastes|Song of Solomon|Isaiah Jeremiah Lamentations "
           "Ezekiel Daniel Hosea Joel Amos Obadiah Jonah Micah Nahum Habakkuk Zephaniah Haggai Zechariah Malachi Matthew Mark "
           "Luke John Acts Romans|1 Corinthians|2 Corinthians|Galatians Ephesians Philippians Colossians|1 Thessalonians|"
           "2 Thessalonians|1 Timothy|2 Timothy|Titus Philemon Hebrews James|1 Peter|2 Peter|1 John|2 John|3 John|Jude Revelation")
BOOKS66 = [b for part in BOOKS66.split("|") for b in ([part] if part[0].isdigit() or part == "Song of Solomon" else part.split())]


class PrayerDataTest(unittest.TestCase):
    def test_every_reference_is_a_real_verse(self):
        B = bp.Bibles(download=False)   # the King James text built into BibleChat
        for p in DATA["prayers"]:
            self.assertTrue(p["refs"], p["id"])
            for r in p["refs"]:
                with self.subTest(prayer=p["id"], ref=r):
                    book, (c1, v1), (c2, v2) = bp.parse_ref(r)
                    got = B.verses(r, "KJV")
                    self.assertTrue(got, f"{r} is not in the King James Version")
                    if v1 is not None and c1 == c2:
                        self.assertEqual(len(got), v2 - v1 + 1, f"{r}: a verse in the range is missing")

    def test_shape_ids_categories_and_labels(self):
        cats = {c["id"] for c in DATA["categories"]}
        ids = [p["id"] for p in DATA["prayers"]]
        self.assertEqual(len(ids), len(set(ids)), "two prayers share an id")
        self.assertGreaterEqual(len(ids), 60)
        for want in ("protection", "peace", "strength", "gratitude", "healing", "family", "salvation", "bible", "paths"):
            self.assertIn(want, cats)
        for p in DATA["prayers"]:
            with self.subTest(prayer=p["id"]):
                self.assertRegex(p["id"], r"^[a-z0-9-]+$")
                self.assertIn(p["category"], cats)
                if p["category"] == "bible":   # the Bible's own prayers: the verses are the prayer, nothing typed in
                    self.assertNotIn("text", p)
                    self.assertTrue(p.get("by"))
                else:
                    self.assertTrue(p["text"] and all(t.strip() for t in p["text"]))
                    self.assertTrue(p["text"][-1].rstrip().endswith("Amen."), "a written prayer ends with Amen.")
        self.assertIn("ring-of-fire", ids)   # the prayer that started the feature (Psalm 91, Zechariah 2:5, 2 Kings 6:17)

    def test_every_study_path_has_its_own_closing_prayer(self):
        paths = {p["id"] for p in json.loads(read("web", "paths", "index.json"))}
        have = {}
        for p in DATA["prayers"]:
            for x in p.get("paths", []):
                self.assertIn(x, paths, f"{p['id']} closes a path that doesn't exist")
                self.assertEqual(p["category"], "paths")
                have[x] = p["id"]
        self.assertEqual(sorted(paths - set(have)), [], "these Study Paths have no closing prayer")

    def test_every_book_has_a_prayer_for_read(self):
        ids = {p["id"] for p in DATA["prayers"]}
        for b in BOOKS66:
            self.assertIn(DATA["books"].get(b), ids, f"{b} has no prayer for 🙏 Pray in Read")
        self.assertIn(DATA["fallback"], ids)
        self.assertEqual(len(BOOKS66), 66)

    def test_written_prayers_are_labelled_not_scripture(self):
        js = read("web", "prayers.js")
        self.assertIn("The prayer is the words of a man, not Scripture; the verses are Scripture.", js)
        self.assertIn("Written by an AI from the verses below. It is not Scripture", js)
        self.assertIn("not Scripture", DATA["about"])


@unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
class PrayerChoiceTest(unittest.TestCase):
    """Runs web/prayers.js with Node.js: which prayer shows for a chapter, a day, an answer and a path."""
    def run_js(self, body):
        script = f"""
global.BCPaths = require({json.dumps(os.path.join(ROOT, "web", "paths.js"))});
const P = require({json.dumps(os.path.join(ROOT, "web", "prayers.js"))});
P._setData(JSON.parse(require("fs").readFileSync({json.dumps(os.path.join(ROOT, "web", "prayers.json"))}, "utf8")));
const out = {{}};
{body}
console.log(JSON.stringify(out));"""
        r = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_choices(self):
        books = json.dumps(BOOKS66)
        o = self.run_js(f"""
out.ps91 = P.forChapter("Psalms", 91).map(p => p.id);
out.matt6 = P.forChapter("Matthew", 6).map(p => p.id);
out.obadiah = P.forChapter("Obadiah", 1)[0].id;
out.enoch = P.forChapter("1 Enoch", 3)[0].id;
out.empty = {books}.filter(b => !P.forChapter(b, 1).length);
out.today91 = P.today({{book: "Psalms", ch: 91, v: 1}}).id;
out.todayAny = P.today({{book: "Obadiah", ch: 1, v: 1}}, new Date(2026, 9, 25)).id;
out.todayCat = P.today({{book: "Obadiah", ch: 1, v: 1}}, new Date(2026, 9, 25)).category;
out.afraid = P.forAnswer("I am afraid", ["Isaiah 41:10"]).map(p => p.id);
out.sick = P.forAnswer("pray for my sick mother", []).map(p => p.id);
out.none = P.forAnswer("zzqx", []).length;
out.path = P.forPath({{id: "freedom-from-bondage"}}).id;
out.mine = P.forPath({{id: "mine-1", title: "Not afraid", steps: [{{refs: ["Isaiah 41:10"]}}]}}).id;
""")
        self.assertEqual(o["ps91"][0], "ring-of-fire")            # a written prayer from the chapter comes first
        self.assertIn("psalm-91", o["ps91"])                      # then the Bible's own text of it
        self.assertIn("lords-prayer", o["matt6"])
        self.assertEqual(o["obadiah"], DATA["books"]["Obadiah"])  # no prayer from the chapter: the book's own prayer
        self.assertEqual(o["enoch"], DATA["fallback"])           # a book outside the 66: the general prayer
        self.assertEqual(o["empty"], [])
        self.assertEqual(o["today91"], "ring-of-fire")           # today's prayer follows the verse of the day
        self.assertNotIn(o["todayCat"], ("paths", "bible"))
        self.assertEqual(o["afraid"][0], "fear-not")
        self.assertIn("prayer-of-faith", o["sick"])
        self.assertEqual(o["none"], 0)
        self.assertEqual(o["path"], "path-freedom-from-bondage")
        self.assertEqual(o["mine"], "fear-not")                  # a path someone made: the closest library prayer


class PrayerPagesTest(unittest.TestCase):
    def test_both_versions_carry_prayers(self):
        for p, parts in [(PAGES[0], ['src="prayers.js"', 'data-tab="pray"', 'id="prayView"', 'id="prayToday"', 'id="prayChap"',
                                     "🙏 Pray about this", "BCPrayers.mount(", 'url: "prayers.json"', "BCPrayers.openHash(", "BCPrayers.todayCard("]),
                         (PAGES[1], ['src="/prayers.js"', 'id="sidePray"', 'id="prayView"', 'id="prayToday"', 'id="rPray"',
                                     "data-pray", "BCPrayers.mount(", 'url: "/prayers.json"', '"/api/pray"', "aiReady:", "BCPrayers.todayCard("])]:
            s = read(p)
            for part in parts:
                self.assertIn(part, s, f"{part} missing in {p}")
            self.assertLess(s.index('paths.js"></script>'), s.index('prayers.js"></script>'), "prayers.js borrows the Study Paths adapter")
        self.assertIn("BCPrayers.closing(", read("web", "paths.js"))   # the closing prayer under Questions and answers
        sw = read("web", "sw.js")
        self.assertIn('"prayers.js"', sw); self.assertIn('"prayers.json"', sw)   # offline on the phone
        self.assertIn('"prayers.js", "prayers.json"', read("web", "build_study.py"))   # copied into the phone site
        self.assertIn('"/prayers.js", "/prayers.json"', read("bibleask", "server.py"))

    def test_phone_words_are_translated(self):
        src = read("web", "i18n.js")
        for phrase in ("Pray", "🙏 Pray", "🙏 Pray about this", "Today's prayer", "All prayers", "A closing prayer", "Protection",
                       "Prayers of the Bible", "After a Study Path"):
            self.assertIn(f'\n"{phrase}": [', src, phrase)
        for c in DATA["categories"]:
            self.assertIn(f'\n"{c["name"]}": [', src, c["name"])


class FakePrayerModel:
    loaded = True
    style = "general"
    seen = None

    def stream_prayer(self, topic, passages):
        FakePrayerModel.seen = (topic, passages)
        for w in ["Lord, ", "keep me ", "(Psalms 91:11). ", "In Jesus' name, Amen."]:
            yield w


class AIPrayerTest(unittest.TestCase):
    def test_prompt_uses_only_the_given_verses(self):
        msgs = llm.build_prayer_messages("protection", [("Psalms 91:11", "For he shall give his angels charge over thee")])
        self.assertIn("Never quote or name a verse that is not in the list", msgs[0]["content"])
        self.assertIn("[Psalms 91:11] For he shall give his angels", msgs[1]["content"])
        self.assertIn("TOPIC: protection", msgs[1]["content"])
        self.assertIn("Use only the verses", llm.prayer_question("protection"))

    def test_api_pray_streams_and_refuses_without_verses(self):
        app = server.App()
        app.model = FakePrayerModel()
        s = __import__("socket").socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
        httpd = ThreadingHTTPServer(("127.0.0.1", port), server.make_handler(app, port)); httpd.daemon_threads = True
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            def post(body):
                req = urllib.request.Request(f"http://127.0.0.1:{port}/api/pray", data=json.dumps(body).encode(), method="POST")
                with urllib.request.urlopen(req, timeout=20) as r:
                    return r.read().decode()
            raw = post({"topic": "protection", "passages": [["Psalms 91:11", "For he shall give his angels charge over thee"]]})
            toks = [json.loads(b.split("\n")[1][6:]) for b in raw.strip().split("\n\n") if b.startswith("event: token")]
            self.assertEqual("".join(toks), "Lord, keep me (Psalms 91:11). In Jesus' name, Amen.")
            self.assertIn("event: done", raw)
            self.assertEqual(FakePrayerModel.seen[1], [("Psalms 91:11", "For he shall give his angels charge over thee")])
            with self.assertRaises(urllib.error.HTTPError):
                post({"topic": "protection", "passages": []})
            for f in ("/prayers.js", "/prayers.json"):   # the computer serves the phone's files
                with urllib.request.urlopen(f"http://127.0.0.1:{port}{f}", timeout=10) as r:
                    self.assertEqual(r.status, 200)
        finally:
            httpd.shutdown(); httpd.server_close()


if __name__ == "__main__":
    unittest.main()
