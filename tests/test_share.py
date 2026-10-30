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


class PrayerPictureTest(unittest.TestCase):
    """Hans, 27 October: the prayer on Home could only be opened with "Pray it", and a prayer shared to Facebook arrived as
    a bare "github.io" link. Facebook takes no text from other apps, so a prayer goes as a picture, like the verse of the day."""
    def test_todays_prayer_opens_when_tapped(self):
        js = read("web", "prayers.js")
        self.assertIn('<div class="pr-tap" data-prt="open" role="button" tabindex="0"', js)   # title, text and verses are one tap target
        self.assertIn("Read the whole prayer", js)
        self.assertIn('e.key === "Enter"', js)

    def test_a_prayer_can_be_shared_as_a_picture(self):
        js = read("web", "prayers.js")
        for part in ("async function picture(p, url)", "function sharePicture()", "navigator.share({files: [pic.file]", "pr-pic", "pr-picprev",
                     "pr-fb", "navigator.clipboard.writeText", "Share as a picture (Facebook, Instagram…)", "Save the prayer as a picture",
                     "S.pic = pic"):
            self.assertIn(part, js, part)
        self.assertIn("    S.back = back || (p ? () => showPrayer(p.id) : () => showList());", js)   # Back on the share screen (it had slipped into a comment)
        i18n = read("web", "i18n.js")
        for phrase in ("Read the whole prayer", "Share as a picture (Facebook, Instagram…)", "The prayer and its link are copied: paste them into your post."):
            self.assertIn(f'\n"{phrase}": [', i18n, phrase)


class XButtonTest(unittest.TestCase):
    """Hans, 29 October: X (Twitter) on the iPhone opened X's sign-up page, and the iPhone share menu didn't list X.
    On a phone the button now copies the post and says to open the X app and paste; on a computer it opens X as before."""
    def test_x_on_a_phone_copies_the_post(self):
        js = read("web", "paths.js")
        for part in ("function xPhone(e, btn, box, say)", "if(!isPhone()) return false;", "e.preventDefault();", "navigator.clipboard.writeText(text)",
                     'const xb = t.closest(".pv-so-x"); if(xb && xPhone(e, xb, root, A.toast)) return;', "pv-xhint", 'data-copy="${esc(both)}"'):
            self.assertIn(part, js, part)
        pr = read("web", "prayers.js")
        for part in ("BCPaths.xPhone(e, xb, root, toast)", "pv-xhint", 'data-copy="${esc(both)}"', "x.com/intent/post"):
            self.assertIn(part, pr, part)
        self.assertIn('\n"Copied. Now open the X app, start a new post, and tap and hold in the text box to paste.": [', read("web", "i18n.js"))


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
        groups = {p["group"] for p in index if p.get("group")}                   # a Bible study group's folder has a page too
        english = [f for f in self.files if not re.search(r"/(es|de)/index\.html$", f)]
        self.assertEqual(len(english), 2 + len(index) + len(series) + len(groups) + len(prayers))
        for p in index:
            h = self.page("p", p["id"])
            self.assertEqual(self.meta(h, "og:image"), build_share.SITE + "paths/" + p["image"] + "?v=2")   # its own picture
            self.assertEqual((self.meta(h, "og:image:width"), self.meta(h, "og:image:height")), ("624", "416"))   # size given: no broken picture on Facebook
            self.assertEqual(self.meta(h, "og:image:type"), "image/jpeg")
            self.assertEqual(self.meta(h, "og:url"), build_share.SITE + "p/" + p["id"] + "/")
            self.assertIn('location.replace("../../#/path/%s/1"' % p["id"], h)
            self.assertNotIn('http-equiv="refresh"', h)            # a crawler must stay on this page to read its preview
        for sid in series:
            self.assertIn('location.replace("../../#/paths/series/%s"' % sid, self.page("series", sid))
        for p in prayers:
            h = self.page("pray", p["id"])
            self.assertIn('location.replace("../../#/prayers/%s"' % p["id"], h)
            self.assertTrue(self.meta(h, "og:image").endswith(".jpg?v=2"))
            self.assertTrue(int(self.meta(h, "og:image:width")) >= 600 and int(self.meta(h, "og:image:height")) >= 315)
        self.assertIn('location.replace("../#/paths"', self.page("p"))
        self.assertIn('location.replace("../#/prayers"', self.page("pray"))
        self.assertIn("og-prayers.jpg", self.meta(self.page("pray"), "og:image"))
        self.assertEqual((self.meta(self.page("pray"), "og:image:width"), self.meta(self.page("pray"), "og:image:height")), ("1200", "630"))
        self.assertTrue(os.path.exists(os.path.join(ROOT, "web", "paths", "img", "og-prayers.jpg")))

    def test_a_prayer_shared_in_german_or_spanish_previews_in_that_language(self):
        # Hans: "When I share through sms it sends it in German but the description is in English"
        de = json.loads(read("web", "prayers.de.json"))["prayers"]
        es = json.loads(read("web", "prayers.es.json"))["prayers"]
        pid = sorted(set(de) & set(es))[0]
        h = self.page("pray", pid, "de")
        self.assertIn('lang="de"', h)
        self.assertIn(de[pid]["title"], self.meta(h, "og:title"))
        self.assertIn('location.replace("../../../?lang=de#/prayers/%s"' % pid, h)
        self.assertEqual(self.meta(h, "og:url"), build_share.SITE + "pray/" + pid + "/de/")
        self.assertIn("Gebet", h)
        h = self.page("pray", pid, "es")
        self.assertIn(es[pid]["title"], self.meta(h, "og:title"))
        self.assertIn("oración", h)
        # the app's share text and picture label follow the language too
        i18n = read("web", "i18n.js")
        for phrase in ("A prayer", "A prayer for you", "Pray it in BibleChat (free, no sign-up):"):
            self.assertIn('\n"%s": [' % phrase, i18n)
        self.assertIn('L + "/"', read("web", "paths.js"))
        self.assertIn('get("lang")', read("web", "index.html"))

    def test_the_phone_build_writes_them(self):
        self.assertIn("write_share_pages(out, web)", read("web", "build_study.py"))
        self.assertIn("build_study.py site", read(".github", "workflows", "pages.yml"))


if __name__ == "__main__":
    unittest.main()
