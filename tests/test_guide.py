"""The search guide (web/guide.json, web/guide.js, bibleask/guide.py): key passages by theme for broad topics, which
Bibles a book is in, "In the original" and "In context" notes, spreading broad answers over the parts of the Bible,
and the balance rule for Study Paths."""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

from bibleask import guide  # noqa: E402
from bibleask.strongs import STRONGS  # noqa: E402

WEB = os.path.join(ROOT, "web")
G = guide.load()
_ETH = None


def eth() -> dict:
    """The Ethiopian Canon file BibleChat hosts: the books outside the 66 (Sirach, 1 Enoch...)."""
    global _ETH
    if _ETH is None:
        _ETH = {}
        root = ET.parse(os.path.join(ROOT, "bibles", "eng-ethiopian-canon.zefania.xml")).getroot()
        for b in root.iter("BIBLEBOOK"):
            for c in b.iter("CHAPTER"):
                for v in c.iter("VERS"):
                    _ETH[(b.get("bname"), int(c.get("cnumber")), int(v.get("vnumber")))] = "".join(v.itertext())
    return _ETH


def exists(book, ch, v) -> bool:
    return bool(STRONGS.kjv_text(book, ch, v)) or (book, ch, v) in eth()


def all_refs():
    for t in G["topics"]:
        for th in t["themes"]:
            for r in th["refs"]:
                yield t["id"], r
    for key, n in G["notes"].items():
        yield "note", key
        for x in n.values():
            for r in x.get("refs", []):
                yield "note " + key, r


@unittest.skipUnless(STRONGS.available(), "Strong's data not bundled")
class GuideData(unittest.TestCase):
    def test_every_reference_exists(self):
        bad = []
        for where, r in all_refs():
            p = guide.parse_ref(r)
            if not p:
                bad.append((where, r, "not a reference"))
                continue
            book, ch, v1, v2 = p
            bad += [(where, r, v) for v in range(v1, v2 + 1) if not exists(book, ch, v)]
        self.assertEqual(bad, [])

    def test_original_notes_name_words_that_stand_in_the_verse(self):
        """"In the original" names a Strong's number that is on a word of that verse, and the King James words it explains."""
        for key, n in G["notes"].items():
            o = n.get("original")
            if not o:
                continue
            book, ch, v1, v2 = guide.parse_ref(key)
            nums, text = set(), ""
            for v in range(v1, v2 + 1):
                nums |= {w[1].split()[0] for w in STRONGS.verse(book, ch, v) if not isinstance(w, str)}
                text += STRONGS.kjv_text(book, ch, v) + " "
            with self.subTest(key):
                self.assertTrue(o["strongs"])
                self.assertEqual([s for s in o["strongs"] if s not in nums], [])
                self.assertIn(o["kjv"].lower(), text.lower())

    def test_every_note_is_short_plain_and_never_a_verdict(self):
        for key, n in G["notes"].items():
            for kind, x in n.items():
                with self.subTest(key=key, kind=kind):
                    self.assertIn(kind, ("original", "context"))
                    self.assertLess(len(x["text"]), 650)
                    self.assertNotRegex(x["text"].lower(), r"\b(clearly means|the correct view|the right view|obviously)\b")

    def test_topics_have_themes_with_both_sides(self):
        ids = [t["id"] for t in G["topics"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 15)
        for t in G["topics"]:
            with self.subTest(t["id"]):
                self.assertGreaterEqual(len(t["themes"]), 7)
                self.assertTrue(all(th["refs"] and th["point"] for th in t["themes"]))
                self.assertTrue(t["words"])

    def test_women_shows_what_the_review_found_missing(self):
        """The review of a "women in the Bible" search: Deborah, Proverbs 31, Phoebe and Junia were missing."""
        t = guide.topic_for("women in the Bible")
        self.assertEqual(t["id"], "women")
        have = guide.verses_of(r for th in t["themes"] for r in th["refs"])
        for ref in ("Judges 4:4", "Proverbs 31:10", "Romans 16:1", "Romans 16:7", "Psalms 68:11", "1 Corinthians 14:34", "Galatians 3:28"):
            self.assertIn(guide.parse_ref(ref)[:3], have, ref)
        self.assertIn("feminine", guide.notes_for("Psalms", 68, 11)["original"]["text"])
        self.assertIn("Catholic and Orthodox", guide.notes_for("Sirach", 42, 13)["context"]["text"])

    def test_canon_labels(self):
        self.assertEqual(guide.canon_short("Sirach"), "In Catholic and Orthodox Bibles")
        self.assertEqual(guide.canon_short("Ecclesiasticus"), "In Catholic and Orthodox Bibles")
        self.assertEqual(guide.canon_short("1 Enoch"), "Ethiopian Bible only")
        self.assertEqual(guide.canon_short("Romans"), "")
        sixty_six = {b for _n, books in G["sections"] for b in books}
        self.assertEqual(len(sixty_six), 66)
        for b in {k[0] for k in eth()} - sixty_six:   # every book of the Ethiopian Canon outside the 66 has its label
            self.assertTrue(guide.canon_short(b), b)
        from bibleask.loaders import _BOOK_CODES   # ... and every Apocrypha book the loaders know
        for _o, _u, name in _BOOK_CODES:
            if name not in sixty_six:
                self.assertTrue(guide.canon_short(name), name)

    def test_topic_matching(self):
        self.assertEqual(guide.topic_for("What does the Bible say about the love of money?")["id"], "money")
        self.assertEqual(guide.topic_for("end times")["id"], "end-times")
        self.assertEqual(guide.topic_for("holy ghost")["id"], "holy-spirit")
        self.assertIsNone(guide.topic_for("John 3:16"))
        self.assertIsNone(guide.topic_for("sea monsters"))
        self.assertTrue(guide.broad("angels"))
        self.assertFalse(guide.broad("the beast that was and is not and yet is"))

    def test_spread_keeps_the_best_first_and_mixes_the_parts(self):
        items = ["Romans", "1 Corinthians", "Galatians", "Ephesians", "1 Timothy", "Judges", "Proverbs", "Luke", "Titus"]
        out = guide.spread(items, lambda b: b, k=6, cap=3)
        self.assertEqual(out[0], "Romans")
        self.assertEqual(out[:6], ["Romans", "1 Corinthians", "Galatians", "Judges", "Proverbs", "Luke"])
        self.assertEqual(sorted(out), sorted(items))
        self.assertEqual(guide.spread(["Romans"] * 5, lambda b: b, k=3), ["Romans"] * 5)   # one part only: nothing lost


class BalanceRule(unittest.TestCase):
    def test_paths_linked_to_a_topic_read_every_theme(self):
        for t in G["topics"]:
            if not t.get("path"):
                continue
            with open(os.path.join(WEB, "paths", t["path"] + ".json"), encoding="utf-8") as f:
                p = json.load(f)
            with self.subTest(t["id"]):
                self.assertEqual(guide.missing_themes(t, p), [])

    def test_the_rule_catches_a_missing_side(self):
        t = next(x for x in G["topics"] if x["id"] == "women")
        one_sided = {"steps": [{"refs": ["1 Corinthians 14:33-35", "1 Timothy 2:9-15"]}]}
        self.assertIn("Women prophesied, judged and spoke for God in Israel", guide.missing_themes(t, one_sided))

    def test_build_paths_enforces_it(self):
        with open(os.path.join(ROOT, "packaging", "build_paths.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn("balance(out)", src)
        self.assertIn("missing_themes", src)


@unittest.skipUnless(shutil.which("node"), "Node.js not installed")
class SameOnPhoneAndComputer(unittest.TestCase):
    QUESTIONS = ["women in the Bible", "What does the Bible say about the love of money?", "end times", "prayer",
                 "holy ghost", "John 3:16", "sea monsters", "women and marriage", "wives submit", "angels",
                 "the beast that was and is not", "why does god allow suffering", "Women’s role in the church"]
    BOOKS = ["Romans", "Sirach", "1 Corinthians", "Galatians", "Ephesians", "1 Timothy", "Judges", "Proverbs", "Luke",
             "Titus", "1 Enoch", "Psalms", "Ruth", "Acts", "Revelation", "Jasher"]

    def test_guide_js_matches_guide_py(self):
        js = f"""
const G = require({json.dumps(os.path.join(WEB, "guide.js"))}); G.use(require({json.dumps(os.path.join(WEB, "guide.json"))}));
const qs = {json.dumps(self.QUESTIONS)}, books = {json.dumps(self.BOOKS)};
console.log(JSON.stringify({{
  topics: qs.map(q => {{ const t = G.topicFor(q); return t ? t.id : null; }}),
  broad: qs.map(q => G.broad(q)),
  canon: books.map(b => {{ const c = G.canon(b); return c ? c.short : ""; }}),
  sections: books.map(b => G.sectionOf(b)),
  spread: G.spread(books, b => b, 8, 3),
  spread2: G.spread(books.slice(2), b => b, 5, 2),
  notes: [["Psalms", 68, 11], ["1 Timothy", 2, 12], ["1 Corinthians", 14, 35], ["John", 3, 16]].map(([b, c, v]) => Object.keys(G.notesFor(b, c, v)).sort()),
  html: G.notesHtml("Psalms", 68, 11) + G.tagHtml("Sirach") + G.passageNotesHtml("1 Timothy", 2, 9, 15),
  keys: G.keysHtml(G.topicFor("women"), null, {{path: {{id: "women-in-the-bible", title: "Women"}}}}),
  ai: G.aiText("women in the bible", ["Sirach 42:13", "Psalms 68:11"])
}}));"""
        out = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
        self.assertEqual(out["topics"], [(guide.topic_for(q) or {}).get("id") for q in self.QUESTIONS])
        self.assertEqual(out["broad"], [guide.broad(q) for q in self.QUESTIONS])
        self.assertEqual(out["canon"], [guide.canon_short(b) for b in self.BOOKS])
        self.assertEqual(out["sections"], [guide.section_of(b) for b in self.BOOKS])
        self.assertEqual(out["spread"], guide.spread(self.BOOKS, lambda b: b, 8, 3))
        self.assertEqual(out["spread2"], guide.spread(self.BOOKS[2:], lambda b: b, 5, 2))
        self.assertEqual(out["notes"], [sorted(guide.notes_for(b, c, v)) for b, c, v in
                                        [("Psalms", 68, 11), ("1 Timothy", 2, 12), ("1 Corinthians", 14, 35), ("John", 3, 16)]])
        h = out["html"]
        self.assertIn("In the original", h)
        self.assertIn("A BibleChat note, not Scripture.", h)   # never mistaken for a verse
        self.assertIn("📚 In Catholic and Orthodox Bibles", h)
        self.assertEqual(h.count("authenteo"), 1)              # a note on verses 11-12 shows once in a passage
        self.assertIn("In context", h)
        k = out["keys"]
        self.assertIn('data-guidepath="women-in-the-bible"', k)
        self.assertIn("Women prophesied, judged and spoke for God in Israel", k)
        self.assertIn("Romans 16:1–7", k)
        a = out["ai"]
        self.assertIn("Key passages on women in the bible", a)
        self.assertIn("Notes from BibleChat (not Scripture)", a)
        self.assertIn("If the verses lean one way, say so", a)


class Wiring(unittest.TestCase):
    def read(self, *p):
        with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
            return f.read()

    def test_both_pages_and_the_paths_use_it(self):
        phone, computer, paths = self.read("web", "index.html"), self.read("bibleask", "web", "index.html"), self.read("web", "paths.js")
        self.assertIn('<script src="guide.js"></script>', phone)
        self.assertIn('<script src="/guide.js"></script>', computer)
        for page in (phone, computer):
            self.assertIn("BCGuide.notesHtml(", page)
            self.assertIn("BCGuide.aiText(", page)
            self.assertIn("BCGuide.tagHtml(", page)
        self.assertIn("BCGuide.keysHtml(", phone)
        self.assertIn("BCGuide.spread(", phone)
        self.assertIn("passageNotesHtml", paths)
        self.assertIn("tagHtml", paths)

    def test_shipped_everywhere(self):
        self.assertIn('"guide.js", "guide.json"', self.read("web", "sw.js"))           # kept for offline use
        self.assertIn('"guide.js", "guide.json"', self.read("web", "build_study.py"))  # copied into the phone site
        self.assertIn('"/guide.js", "/guide.json"', self.read("bibleask", "server.py"))  # served on the computer
        spec = self.read("BibleChat.spec")
        for f in ("web/guide.js", "web/guide.json", "web/prayers.js", "web/prayers.json"):   # in the computer downloads
            self.assertIn(f'("{f}", "web")', spec)

    def test_ui_words_are_translated(self):
        i18n = self.read("web", "i18n.js")
        for w in ("Key passages", "In the original", "In context", "Read with", "A BibleChat note, not Scripture.", "Found in",
                  "Law", "History", "Wisdom & Psalms", "Prophets", "Gospels", "Acts", "Letters", "Revelation", "Other books"):
            m = re.search(r'^"' + re.escape(w) + r'": \[(.*)\],$', i18n, re.M)
            self.assertTrue(m, w)
            self.assertEqual(len(json.loads("[" + m[1] + "]")), 7, w)


if __name__ == "__main__":
    unittest.main()
