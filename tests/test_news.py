"""📰 In the news (web/news.js, web/prophecy.json, packaging/build_news.py)."""
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "packaging"))
sys.path.insert(0, ROOT)
import build_news as bn  # noqa: E402
import build_paths as bp  # noqa: E402

DATA = bn.load_themes()

SAMPLE = """<?xml version="1.0"?><rss><channel>
<item><title>Israel and Hamas agree to a ceasefire in Gaza</title><link>https://example.com/a</link><pubDate>{d}</pubDate></item>
<item><title>Earthquake of magnitude 7 strikes off Japan</title><link>https://example.com/b</link><pubDate>{d}</pubDate></item>
<item><title>Local bakery wins a prize</title><link>https://example.com/c</link><pubDate>{d}</pubDate></item>
<item><title>Central bank tests a digital dollar with biometric ID</title><link>https://example.com/d</link><pubDate>{d}</pubDate></item>
</channel></rss>"""


class ProphecyDataTest(unittest.TestCase):
    def test_every_verse_is_real_and_every_quote_is_in_it(self):
        B = bp.Bibles(download=False)   # the King James text built into BibleChat
        kjv = lambda refs: " ".join(bp.norm(B.text["KJV"].get(k, "")) for r in refs for k in B.verses(r, "KJV"))
        for r in DATA["caution"]:
            self.assertTrue(B.verses(r, "KJV"), r)
        for q in re.findall(r'"([^"]+)"', DATA["caution_text"]):
            self.assertIn(bp.norm(q), kjv(DATA["caution"]), q)
        for th in DATA["themes"]:
            with self.subTest(theme=th["id"]):
                self.assertTrue(th["refs"] and th["words"] and th["note"] and th["title"])
                for r in th["refs"]:
                    self.assertTrue(B.verses(r, "KJV"), r)
                for q in re.findall(r'"([^"]+)"', th["note"]):
                    self.assertIn(bp.norm(q), kjv(th["refs"]), q)

    def test_four_readings_and_labelled_sources(self):
        self.assertEqual([x["name"] for x in DATA["readings"]], ["Futurist", "Historicist", "Preterist", "Idealist"])
        labels = {s["label"] for s in DATA["sources"]}
        self.assertEqual(labels, {"Mainstream", "Israeli press", "Christian", "Alternative / independent"})
        for s in DATA["sources"]:
            self.assertTrue(s["feed"].startswith("https://"), s["name"])

    def test_the_words_on_screen_are_translated(self):
        with open(os.path.join(ROOT, "web", "i18n.js"), encoding="utf-8") as f:
            src = f.read()
        for phrase in ["In the news", "Paste a headline or a link", "Find the passages", "How Christians read it"] + \
                      sorted({s["label"] for s in DATA["sources"]}) + [x["name"] for x in DATA["readings"]]:
            self.assertIn(f'\n"{phrase}": [', src, phrase)


class PickerTest(unittest.TestCase):
    def test_match_is_whole_words(self):
        self.assertEqual(bn.match("Israel strikes back", DATA["themes"])[0][0]["id"], "israel")
        self.assertFalse(bn.match("The waiter said hello", DATA["themes"]))   # "ai" inside a word is not AI
        self.assertFalse(bn.match("Local bakery wins a prize", DATA["themes"]))

    def test_two_picks_from_different_themes(self):
        email_date = dt.datetime.now(dt.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
        with tempfile.TemporaryDirectory() as t:
            feed, out = os.path.join(t, "f.xml"), os.path.join(t, "news.json")
            with open(feed, "w", encoding="utf-8") as f:
                f.write(SAMPLE.format(d=email_date))
            self.assertEqual(bn.main([out, "--feed", feed]), 0)
            with open(out, encoding="utf-8") as f:
                res = json.load(f)
        self.assertEqual(len(res["picks"]), 2)
        self.assertEqual(len({p["theme"] for p in res["picks"]}), 2)
        self.assertTrue(all(p["source"] and p["label"] and p["link"] for p in res["picks"]))
        self.assertNotIn("Local bakery wins a prize", [p["title"] for p in res["picks"] + res["more"]])


@unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
class SameMatchOnPhoneTest(unittest.TestCase):
    def test_phone_and_picker_agree(self):
        heads = ["Israel and Hamas agree to a ceasefire in Gaza", "Central bank tests a digital dollar with biometric ID",
                 "Comet seen over Texas", "Putin meets Iran's leader in Tehran", "The waiter said hello",
                 "https://example.com/world/2026/10/30/earthquake-strikes-off-japan-12345"]
        js = """
const fs = require("fs"); const [dir, heads] = process.argv.slice(1);
global.fetch = u => Promise.resolve({ok: true, json: () => JSON.parse(fs.readFileSync(dir + "/" + u, "utf8"))});
global.BCPaths = {parseRef: () => null};
eval(fs.readFileSync(dir + "/news.js", "utf8") + "; global.BCNews = BCNews;");
const el = {hidden: true, set innerHTML(v){}, addEventListener(){}, querySelector(){ return null; }};
BCNews.card(el, {});
setTimeout(() => { console.log(JSON.stringify(JSON.parse(heads).map(h => { const m = BCNews.match(BCNews._words(h)); return m.length ? m[0].th.id : null; }))); }, 50);
"""
        web = os.path.join(ROOT, "web")
        fake_news = os.path.join(web, "news.json")
        made = not os.path.exists(fake_news)
        if made:
            with open(fake_news, "w") as f:
                f.write('{"picks": []}')
        try:
            got = subprocess.run(["node", "-e", js, web, json.dumps(heads)], capture_output=True, text=True, timeout=60)
        finally:
            if made:
                os.remove(fake_news)
        self.assertEqual(got.returncode, 0, got.stderr)
        phone = json.loads(got.stdout.strip().splitlines()[-1])
        def py(h):
            words = re.sub(r"[-_/+.=?&]+", " ", h.split("://", 1)[1].split("/", 1)[1]) if h.startswith("http") else h
            m = bn.match(re.sub(r"\b\d+\b", " ", words), DATA["themes"])
            return m[0][0]["id"] if m else None
        self.assertEqual(phone, [py(h) for h in heads])
        self.assertEqual(phone[:2], ["israel", "mark"])


if __name__ == "__main__":
    unittest.main()
