"""↗ Shared links: a Study Path, a series, a prayer or a verse sent to someone must open what was sent, also after
Facebook, Messenger, Instagram or an email program added its own tracking to the end of the link (?fbclid=…).
And every path, series and prayer has a short share page (web/build_share.py) with its own preview."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "web"))
import build_share  # noqa: E402


def read(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
        return f.read()


@unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
class CleanLinkTest(unittest.TestCase):
    def run_js(self, body):
        script = f"""const P = require({json.dumps(os.path.join(ROOT, "web", "paths.js"))}); const out = {{}};
{body}
console.log(JSON.stringify(out));"""
        r = subprocess.run(["node", "-e", script], capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_tracking_and_punctuation_are_cut_off(self):
        cases = {
            "#/path/husband-and-wife/1?fbclid=IwAR0abc": "#/path/husband-and-wife/1",   # Facebook Messenger (Carolyn's link)
            "#/path/husband-and-wife/1&fbclid=x": "#/path/husband-and-wife/1",
            "#/path/husband-and-wife/1%3Ffbclid%3Dx": "#/path/husband-and-wife/1",
            "#/path/husband-and-wife/1.": "#/path/husband-and-wife/1",                # the end of a sentence
            "#/path/husband-and-wife/1)": "#/path/husband-and-wife/1",
            "#/prayers/ring-of-fire?utm_source=whatsapp": "#/prayers/ring-of-fire",
            "#/paths/series/mirror-prophecies/?igshid=1": "#/paths/series/mirror-prophecies/",
            "#/eng-kjv/John/3/16/s?fbclid=abc": "#/eng-kjv/John/3/16/s",
            "#/path/mine/eyJ2IjoyLCJ0aSI6IkEifQ": "#/path/mine/eyJ2IjoyLCJ0aSI6IkEifQ",   # a path someone made: untouched
            "#/eng-kjv/1%20John/4/8": "#/eng-kjv/1%20John/4/8",
        }
        out = self.run_js(f"const C = {json.dumps(cases)}; for(const k in C) out[k] = P.cleanHash(k);")
        self.assertEqual(out, cases)

    def test_share_addresses_are_short_pages(self):
        out = self.run_js("""for(const h of ["#/path/husband-and-wife/1", "#/paths", "#/paths/series/mirror-prophecies", "#/prayers/ring-of-fire",
  "#/prayers", "#/path/mine/eyJ2IjoyfQ", "#/path/husband-and-wife/3"]) out[h] = P.shortPath(h);""")
        self.assertEqual(out["#/path/husband-and-wife/1"], "p/husband-and-wife/")
        self.assertEqual(out["#/paths"], "p/")
        self.assertEqual(out["#/paths/series/mirror-prophecies"], "series/mirror-prophecies/")
        self.assertEqual(out["#/prayers/ring-of-fire"], "pray/ring-of-fire/")
        self.assertEqual(out["#/prayers"], "pray/")
        self.assertIsNone(out["#/path/mine/eyJ2IjoyfQ"])          # travels in the link itself
        self.assertIsNone(out["#/path/husband-and-wife/3"])       # a later step keeps the long form


class LinkCodeTest(unittest.TestCase):
    def test_phone_cleans_the_link_before_it_reads_it(self):
        s = read("web", "index.html")
        first = s.index("BCPaths.cleanHash(location.hash)")
        self.assertLess(first, s.index("function parseHash"))
        self.assertLess(first, s.index("const PATH_HASH"))
        self.assertLess(s.index('"use strict";'), first)                      # strict mode stays on
        self.assertGreaterEqual(s.count("BCPaths.cleanHash(location.hash)"), 2)  # also when the link changes later

    def test_path_links_never_break_on_a_bad_step_or_id(self):
        js = read("web", "paths.js")
        self.assertIn("h = cleanHash(h);", js)
        self.assertIn("parseInt(m[2], 10)", js)
        self.assertNotIn("+m[2] - 1", js)                                      # "1?fbclid=…" became NaN: the bug
        self.assertIn("an old or mistyped link: show all the paths instead", js)
        for part in ("url = linkOf(t.hash)", "A.qr(linkOf(t.hash)", "remember()"):
            self.assertIn(part, js)

    def test_prayers_can_be_shared_like_paths(self):
        js = read("web", "prayers.js")
        for part in ("↗ \" + T(\"Share this prayer\")", "pr-shareall", "pr-sys", "sms:?&body=", "https://wa.me/?text=", "mailto:?subject=",
                     "facebook.com/sharer", "x.com/intent", "t.me/share", "linkedin.com/sharing", "pr-copylink", "pr-copyall", "pv-qr",
                     'data-prt="share"', "pr-cl-share", "Someone shared this prayer with you.", "Someone shared the BibleChat Prayers with you.",
                     "BCPaths.cleanHash", "share: shareFrom"):
            self.assertIn(part, js, part)
        i18n = read("web", "i18n.js")
        for phrase in ("Share this prayer", "Share the prayer", "Copy link", "Copy the whole prayer", "Someone shared this prayer with you."):
            self.assertIn(f'\n"{phrase}": [', i18n, phrase)


class SharePagesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = tempfile.mkdtemp()
        cls.files = build_share.write_share_pages(cls.out)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.out, ignore_errors=True)

    def page(self, *rel):
        with open(os.path.join(self.out, *rel, "index.html"), encoding="utf-8") as f:
            return f.read()

    def meta(self, html, prop):
        m = re.search(r'<meta (?:property|name)="%s" content="([^"]*)"' % re.escape(prop), html)
        return m and m.group(1)

    def test_every_path_series_and_prayer_has_a_page(self):
        index = json.loads(read("web", "paths", "index.json"))
        prayers = json.loads(read("web", "prayers.json"))["prayers"]
        series = {p["series"]["id"] for p in index if isinstance(p.get("series"), dict)}
        self.assertEqual(len(self.files), 2 + len(index) + len(series) + len(prayers))
        for p in index:
            h = self.page("p", p["id"])
            self.assertEqual(self.meta(h, "og:image"), build_share.SITE + "paths/" + p["image"])     # its own picture
            self.assertEqual(self.meta(h, "og:url"), build_share.SITE + "p/" + p["id"] + "/")
            self.assertIn('location.replace("../../#/path/%s/1"' % p["id"], h)
            self.assertNotIn('http-equiv="refresh"', h)            # a crawler must stay on this page to read its preview
        for sid in series:
            self.assertIn('location.replace("../../#/paths/series/%s"' % sid, self.page("series", sid))
        for p in prayers:
            h = self.page("pray", p["id"])
            self.assertIn('location.replace("../../#/prayers/%s"' % p["id"], h)
            self.assertTrue(self.meta(h, "og:image").endswith(".jpg"))
        self.assertIn('location.replace("../#/paths"', self.page("p"))
        self.assertIn('location.replace("../#/prayers"', self.page("pray"))
        self.assertIn("og-prayers.jpg", self.meta(self.page("pray"), "og:image"))
        self.assertTrue(os.path.exists(os.path.join(ROOT, "web", "paths", "img", "og-prayers.jpg")))

    def test_the_phone_build_writes_them(self):
        self.assertIn("write_share_pages(out, web)", read("web", "build_study.py"))
        self.assertIn("build_study.py site", read(".github", "workflows", "pages.yml"))


if __name__ == "__main__":
    unittest.main()
