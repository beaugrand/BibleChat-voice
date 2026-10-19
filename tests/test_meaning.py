"""Search by Hebrew/Greek word (Strong's) and by meaning, on the computer and the phone (web/smart.js)."""
import gzip
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

from bibleask import blend, chat  # noqa: E402
from bibleask.meaning import MEANING, Meaning, WordPiece  # noqa: E402
from bibleask.mcp_server import kjv  # noqa: E402
from bibleask.search import short_ref  # noqa: E402
from bibleask.strongs import STRONGS, build_gloss_index  # noqa: E402

try:
    import numpy  # noqa: F401
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False

# the questions the owner checks by hand, with the verse that must come first (King James only)
TARGETS = [("sea monsters fifth day", ["Genesis 1:21"]), ("sea monsters", ["Genesis 1:21"]),
           ("God rested after making everything", ["Genesis 2:2", "Genesis 2:3"]),
           ("love is patient", ["1 Corinthians 13:4"]), ("the beast that rises out of the sea", ["Revelation 13:1"])]


def top(question, k=5):
    _b, ix = kjv()
    return [short_ref(ix.verses[f.index]) for f in blend.blended(question, ix, k)]


class HebrewGreekWords(unittest.TestCase):
    def test_sea_monster_is_tannin(self):
        m = STRONGS.meaning_matches("sea monsters")
        self.assertEqual(m[0]["number"], "H8577")
        self.assertEqual(m[0]["label"], "Hebrew word tannin (H8577): sea monster, dragon, serpent, whale")
        self.assertIn(("Genesis", 1, 21), m[0]["verses"])   # the KJV says "great whales" there

    def test_common_words_are_left_out(self):
        self.assertEqual(STRONGS.meaning_matches("God day"), [])
        self.assertEqual({m["term"] for m in STRONGS.meaning_matches("sea monsters fifth day")}, {"sea monster", "fifth"})

    def test_love_and_patient(self):
        numbers = {m["number"] for m in STRONGS.meaning_matches("love is patient")}
        self.assertTrue({"G26", "G3114"} <= numbers)   # agape and makrothymeo, both in 1 Corinthians 13:4

    def test_bundled_index_is_up_to_date(self):
        STRONGS._load()
        with gzip.open(os.path.join(ROOT, "bibleask", "data", "strongs_gloss.json.gz"), "rt", encoding="utf-8") as f:
            shipped = json.load(f)
        fresh = json.loads(json.dumps(build_gloss_index(STRONGS._dict, STRONGS._where)))
        self.assertEqual(shipped, fresh, "run python packaging/build_gloss.py")


@unittest.skipUnless(HAVE_NUMPY, "numpy is not installed")
class Meaning_(unittest.TestCase):
    def test_word_pieces(self):
        tok = WordPiece(["[PAD]", "[UNK]", "[CLS]", "[SEP]", "love", "is", "pat", "##ient", ",", "naive"])
        self.assertEqual(tok.encode("Love is patient, naïve!"), [2, 4, 5, 6, 7, 8, 9, 1, 3])

    def test_meaning_finds_verses_without_shared_words(self):
        found = [ref for ref, _s in MEANING.search("love is patient", 3)]
        self.assertEqual(found[0], ("1 Corinthians", 13, 4))
        found = [ref for ref, _s in MEANING.search("God rested after making everything", 3)]
        self.assertEqual(found[0], ("Genesis", 2, 2))
        self.assertTrue(MEANING.knows("worry") and not MEANING.knows("asdf"))


class Blended(unittest.TestCase):
    @unittest.skipUnless(HAVE_NUMPY, "numpy is not installed")
    def test_owner_questions_come_first(self):
        for question, want in TARGETS:
            self.assertIn(top(question, 1)[0], want, question)

    @unittest.skipUnless(HAVE_NUMPY, "numpy is not installed")
    def test_each_verse_says_why(self):
        _b, ix = kjv()
        f = blend.blended("sea monsters fifth day", ix, 3)[0]
        self.assertEqual(short_ref(ix.verses[f.index]), "Genesis 1:21")
        self.assertIn("matched by meaning", f.why)
        self.assertIn("Hebrew word tannin (H8577): sea monster, dragon, serpent, whale", f.why)

    def test_nonsense_is_not_guessed(self):
        self.assertEqual(top("asdf qwzx"), [])

    def test_without_the_meaning_model_word_search_carries_on(self):
        import bibleask.meaning as m
        real = m.MEANING
        m.MEANING = Meaning(data_dir=tempfile.mkdtemp())   # no files: as on a computer without the model
        try:
            self.assertEqual(top("sea monsters", 1), ["Genesis 1:21"])   # the Hebrew word still finds it
            self.assertIn("John 3:16", top("for God so loved the world", 3))
        finally:
            m.MEANING = real


class ChatAnswers(unittest.TestCase):
    class Lib:
        def get(self, _bid):
            return kjv()

    def test_verses_carry_their_reasons_and_topics_still_lead(self):
        r = chat.retrieve("sea monsters", None, self.Lib(), ["kjv"])
        v = [g for g in r.groups if not g.get("topic")][0]["verses"][0]   # below Nave's "Whale" topic
        self.assertEqual(v["ref"], "Genesis 1:21")
        self.assertTrue(any(w.startswith("Hebrew word tannin") for w in v["why"]))
        r = chat.retrieve("fallen angels", None, self.Lib(), ["kjv"])
        self.assertTrue(r.groups[0].get("topic"))   # Nave's topic answer first, as before


@unittest.skipUnless(shutil.which("node") and HAVE_NUMPY, "Node.js or numpy is not installed")
class PhoneGivesTheSameAnswers(unittest.TestCase):
    """Runs web/smart.js under Node.js on the phone's own data files and compares with the Python answers."""

    def test_same_results_as_the_computer(self):
        tmp = tempfile.mkdtemp()
        subprocess.run([sys.executable, os.path.join(ROOT, "web", "build_study.py"), tmp], check=True, capture_output=True)
        _b, ix = kjv()
        with open(os.path.join(tmp, "kjv.json"), "w") as f:
            json.dump([{"b": v.book, "c": v.chapter, "v": v.verse, "t": v.text} for v in ix.verses], f)
        questions = [q for q, _ in TARGETS] + ["fallen angels", "do not worry about tomorrow", "asdf"]
        want = [[[f"{v.book} {v.chapter}:{v.verse}", x.why] for x in blend.blended(q, ix, 10) for v in [ix.verses[x.index]]]
                for q in questions]
        texts = [MEANING.prefix + q for q in questions + ["Naïve “quotes” — 1 Cor 13:4 ἀγάπη 爱"]]
        tokens = [MEANING.tok.encode(t) for t in texts]
        script = """
const fs = require("fs"), path = require("path"), [smart, dir] = process.argv.slice(1);
const {Smart} = require(smart), qs = JSON.parse(fs.readFileSync(0, "utf8"));
Smart.setLoader(async (p, kind) => { const f = path.join(dir, "data", p);
  return kind === "bin" ? new Uint8Array(fs.readFileSync(f)).buffer : kind === "text" ? fs.readFileSync(f, "utf8") : JSON.parse(fs.readFileSync(f, "utf8")); });
(async () => {
  await Smart.loadMeaning();
  const flat = JSON.parse(fs.readFileSync(path.join(dir, "kjv.json"))), ix = Smart.makeIndex(flat), out = {found: [], tokens: []};
  for(const q of qs.questions) out.found.push((await Smart.blend(q, {flat, ix, english: true}, 10)).map(f => [flat[f.i].b + " " + flat[f.i].c + ":" + flat[f.i].v, f.why]));
  for(const t of qs.texts) out.tokens.push(Smart.encode(t));
  console.log(JSON.stringify(out));
})().catch(e => { console.error(e); process.exit(1); });
"""
        r = subprocess.run(["node", "-e", script, os.path.join(ROOT, "web", "smart.js"), tmp],
                           input=json.dumps({"questions": questions, "texts": texts}), capture_output=True, text=True, timeout=600)
        self.assertEqual(r.returncode, 0, r.stderr)
        got = json.loads(r.stdout)
        self.assertEqual(got["tokens"], tokens)
        for q, py, js in zip(questions, want, got["found"]):
            self.assertEqual(js, py, q)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
