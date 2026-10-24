import os, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = [os.path.join(ROOT, "web", "index.html"), os.path.join(ROOT, "bibleask", "web", "index.html")]


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


class LicenseTest(unittest.TestCase):
    def test_apache_license_and_notice(self):
        self.assertIn("Apache License", read(os.path.join(ROOT, "LICENSE")))
        notice = read(os.path.join(ROOT, "NOTICE"))
        self.assertIn("Hans W. Beaugrand", notice)
        self.assertIn("$HansBeaugrand", notice)

    def test_pages_keep_credit_and_donations(self):
        for p in PAGES:
            s = read(p)
            self.assertIn("Hans W. Beaugrand", s, p)
            self.assertIn("Apache License 2.0", s, p)
            self.assertIn("$HansBeaugrand", s, p)


class PagesTest(unittest.TestCase):
    def test_back_forward_and_church_parts(self):
        for p in PAGES:
            s = read(p)
            for part in ('id="navBack"', 'id="navFwd"', 'id="churchBtn"', 'id="churchDlg"', 'id="chFile"',
                         "var qrcode", "function churchLink", "function navGo", 'id="smDlg"', 'id="smScreen"',
                         "function sermonLink", 'id="sgText"', "mailto:wbeaugrand@gmail.com", "issues/new", "function askAI", 'id="viDlg"', "function viDraw", 'id="viPhoto"'):
                self.assertIn(part, s, f"{part} missing in {p}")

    def test_home_bible_cover(self):
        # Home (phone: first tab; computer: first mode button) shows a black Bible cover with a golden cross and
        # "The Holy Bible"; clicking it opens Read. A normal start opens on Home; a link to a verse goes straight to it.
        for p, button in [(PAGES[0], '<button data-tab="home">'), (PAGES[1], 'id="modeHome"')]:
            s = read(p)
            for part in (button, 'id="homeCover"', 'class="coverart"', 'aria-label="The Holy Bible', ">The</tspan>",
                         ">Holy Bible</tspan>", 'id="cvGold"', 'id="cvLeather"', "function homeWhere", 'id="homeWhere"'):
                self.assertIn(part, s, f"{part} missing in {p}")
        self.assertIn('show("home", true)', read(PAGES[0]))
        self.assertIn('de: ["Die", "Heilige Schrift"', read(PAGES[0]))   # the cover in German
        self.assertIn('setMode("home")', read(PAGES[1]))

    def test_verse_of_the_day_on_home(self):
        # Phone: the verse of the day sits on Home above the Bible cover, not above the chapter in Read.
        s = read(PAGES[0])
        home = s[s.index('<section id="v-home"'):s.index('<!-- READ -->')]
        readv = s[s.index('<!-- READ -->'):s.index('<!-- SEARCH -->')]
        self.assertIn('id="votd"', home)
        self.assertLess(home.index('id="votd"'), home.index('id="homeCover"'))
        self.assertNotIn('id="votd"', readv)
        self.assertNotIn('id="votdOpen"', s)
        self.assertNotIn("votdShow(false)", s)
        self.assertIn("votdShow();", s[s.index("function homeWhere"):s.index("function closeBook")])

    def test_cover_version_line(self):
        # The cover prints the standard versions in small gold capitals inside the inner gold border, under the
        # cross: only versions BibleChat really offers (NIV only once it is licensed; until then BSB).
        import re, shutil, subprocess, json
        for p in PAGES:
            s = read(p)
            m = re.search(r'<text id="cvVer"([^>]*)>([^<]*)</text>', s)
            self.assertTrue(m, f"cover line missing in {p}")
            a = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(1)))
            self.assertEqual(a["fill"], "url(#cvGold)")                     # fixed gold: same in light and dark mode
            self.assertEqual(a["x"], "160"); self.assertEqual(a["text-anchor"], "middle")
            self.assertTrue(338 < float(a["y"]) - float(a["font-size"]) and float(a["y"]) + 3 < 389, a)   # under the cross, above the border
            self.assertLessEqual(float(a["textLength"]) / 2, 160 - 53 - 4)   # inside the inner border (x 53–267)
            self.assertIn("NIV", s)                                          # the code knows the NIV...
            self.assertNotIn("NIV", m.group(2))                              # ...but the cover doesn't promise it yet
            g = s.index('<g filter="url(#cvEmboss)"')
            self.assertTrue(g < m.start() < s.index("</g>", g), "the line must sit in the embossed group")
            self.assertIn("ETHIOPIAN CANON · BSB", s[s.index('aria-label="The Holy Bible'):][:120])
            self.assertIn("const COVER_VERSIONS", s)
            self.assertIn('id="' + ("closeBook" if p == PAGES[0] else "rHome") + '"', s)   # 🏠 in Read closes the book
            if not shutil.which("node"):
                continue
            js = s[s.index("const COVER_VERSIONS"):s.index("return s;\n}", s.index("function coverLine")) + 11]
            script = js + """
const el = {t: "", a: {}, set textContent(v){ this.t = v; }, setAttribute(k, v){ this.a[k] = v; }};
global.document = {getElementById: () => el};
const out = [];
for(const abbrs of [["KJV","ETH","BSB","WEB"], ["KJV","ETH","BSB","NIV"], ["KJV","BSB"]]){ coverLine(abbrs); out.push([el.t, +el.a.textLength]); }
console.log(JSON.stringify(out));"""
            r = subprocess.run(["node", "-e", script], capture_output=True, text=True, encoding="utf-8", timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            out = json.loads(r.stdout)
            self.assertEqual([o[0] for o in out], ["KJV · ETHIOPIAN CANON · BSB", "KJV · ETHIOPIAN CANON · NIV", "KJV · BSB"])
            self.assertTrue(all(o[1] <= 196 for o in out), out)
        self.assertIn(".coverart", read(os.path.join(ROOT, "web", "i18n.js")))   # same abbreviations in every app language

    def test_love_tab_section_tabs(self):
        # the phone's Love tab starts with tabs (Donate, About, Churches, Ideas), so people see there is more below
        s = read(PAGES[0])
        self.assertIn('id="loveTabs"', s)
        for sec in ("lvDonate", "lvAbout", "lvChurch", "lvIdeas"):
            self.assertIn(f'data-sec="{sec}"', s); self.assertIn(f'id="{sec}"', s)
        self.assertLess(s.index('id="loveTabs"'), s.index('src="cashapp-qr.jpg"'))   # the tabs come before the QR code
        i18n = read(os.path.join(ROOT, "web", "i18n.js"))
        for label in ("♥ Donate", "ℹ About", "⛪ Churches", "💡 Ideas"):
            self.assertIn(f'"{label}":', i18n)

    def test_start_up_says_loading_please_wait(self):
        # the computer app can take 15+ seconds to start: the page says "Loading BibleChat, please wait…" until
        # the Bibles are open, and Windows shows a start-up picture the moment the app is double-clicked
        s = read(PAGES[1])
        self.assertIn('id="boot"', s); self.assertIn("Loading BibleChat, please wait", s)
        self.assertIn('$("#boot").remove()', s)
        spec = read(os.path.join(ROOT, "BibleChat.spec"))
        self.assertIn('Splash("packaging/splash.png"', spec)
        self.assertTrue(os.path.isfile(os.path.join(ROOT, "packaging", "splash.png")))
        self.assertIn("pyi_splash.close()", read(os.path.join(ROOT, "bibleask", "server.py")))

    def test_linux_install_without_typing(self):
        # Linux users who aren't programmers: double-click "Install BibleChat"; the read-me says ./install.sh
        # with the dot and slash, and the installer adds a menu entry and a desktop icon and starts BibleChat
        d = read(os.path.join(ROOT, "packaging", "Install BibleChat.desktop"))
        self.assertIn("Terminal=true", d); self.assertIn("install.sh --from-desktop", d); self.assertIn("%k", d)
        rd = read(os.path.join(ROOT, "packaging", "READ_ME_FIRST_linux.txt"))
        self.assertIn("double-click \"Install BibleChat\"", rd); self.assertIn("./install.sh", rd); self.assertIn("command not found", rd)
        sh = read(os.path.join(ROOT, "packaging", "install_linux.sh"))
        for part in ("biblechat.desktop", "xdg-user-dir DESKTOP", "metadata::trusted", 'nohup "$DEST/BibleChat"'):
            self.assertIn(part, sh)

    def test_new_version_takes_over_from_old_one(self):
        # an old BibleChat kept alive by a browser tab must not be shown instead of the new version
        srv = read(os.path.join(ROOT, "bibleask", "server.py"))
        self.assertIn('"version": __version__', srv)
        self.assertIn("other != __version__", srv); self.assertIn("_stop_other_version(port)", srv)
        sh = read(os.path.join(ROOT, "packaging", "install_linux.sh"))
        self.assertIn('pkill -f "/BibleChat/BibleChat"', sh); self.assertIn('rm -rf "$DEST"', sh)

    def test_listen_bar_and_suggest_without_account(self):
        # Listen: a bar that stays in reach (Pause/Resume, Stop, from verse 1), the place is remembered, and a
        # verse can be read from; Suggest a feature sends without GitHub or a mail program
        for p, start in [(PAGES[0], 'id="shareSay"'), (PAGES[1], 'class="tp saythis"')]:
            s = read(p)
            for part in ('id="player"', 'id="plPause"', 'id="plStop"', 'id="plStart"', "sayAt", start, 'id="sgSend"', 'id="sgReply"'):
                self.assertIn(part, s, f"{part} missing in {p}")
        self.assertIn("formsubmit.co/ajax/", read(PAGES[0]))
        self.assertIn('fetch("/api/suggest"', read(PAGES[1]))
        srv = read(os.path.join(ROOT, "bibleask", "server.py"))
        self.assertIn('"/api/suggest"', srv); self.assertIn("formsubmit.co/ajax/", srv)
        self.assertNotIn("formsubmit.co/ajax/wbeaugrand", read(PAGES[0]) + srv)   # a private address, not the email

    def test_version_in_names(self):
        # which BibleChat is which: the Linux desktop icon and menu say "BibleChat 1.0.6", the computer app's
        # window title carries the version, and the phone/web version installs as "BibleChat Web"
        sh = read(os.path.join(ROOT, "packaging", "install_linux.sh"))
        self.assertIn('NAME="BibleChat${VER:+ $VER}"', sh); self.assertIn("Name=$NAME", sh); self.assertIn("pkill -9", sh)
        srv = read(os.path.join(ROOT, "bibleask", "server.py"))
        self.assertIn('f"<title>BibleChat {__version__}</title>"', srv)
        self.assertIn("document.title = `BibleChat ${state.version}`", read(PAGES[1]))
        self.assertIn('"name": "BibleChat Web"', read(os.path.join(ROOT, "web", "manifest.webmanifest")))

    def test_links_to_other_bibles_have_a_way_back(self):
        # a link to 1 Enoch while reading the KJV opens the Bible that has it (KJV first) with "← Back to KJV",
        # "← Back to Study Paths" when it came from a path, and an offer to download a missing Bible
        phone, comp = read(PAGES[0]), read(PAGES[1])
        for s in (phone, comp):
            for part in ('id="rReturn"', "function retShow", 'id="retBible"', 'id="retPaths"', "BCPaths.reopen()"):
                self.assertIn(part, s)
        self.assertIn('"eng-kjv", book === "Jasher"', phone)
        self.assertIn("async function openRef", comp); self.assertIn('id="getHome"', comp)
        self.assertIn("if(rChap){ chSay(j.error); return; }", comp)   # a chapter that can't open never empties the page
        self.assertIn("reopen", read(os.path.join(ROOT, "web", "paths.js")))

    def test_verse_picker_in_read_mode(self):
        # a "Verse" button next to the chapter title opens a grid of the chapter's own verse numbers
        # (so a Bible that skips or joins verses, like the Ethiopian Canon, shows only real ones); a tap jumps
        # to the verse and makes it glow; colours come from the theme, so dark mode works
        for p, button, popup in [(PAGES[0], 'id="vpick"', 'id="vpSheet"'), (PAGES[1], 'id="rVerse"', 'id="vpDlg"')]:
            s = read(p)
            for part in (button, popup, 'id="vpGrid"', "function jumpToVerse", "new Set(", "@keyframes vjump",
                         ".vpgrid button{min-height:", "var(--line)", "var(--text)"):
                self.assertIn(part, s, f"{part} missing in {p}")
            self.assertLess(s.index("id=\"rtitle\"" if p == PAGES[1] else "id=\"where\""), s.index(button))
        i18n = read(os.path.join(ROOT, "web", "i18n.js"))
        import re
        for phrase in ("Verse", "Choose a verse", "Jump to a verse"):
            m = re.search(r'^"' + re.escape(phrase) + r'": \[(.*)\],$', i18n, re.M)
            self.assertTrue(m, phrase)
            self.assertEqual(m.group(1).count('", "') + 1, 7, phrase)   # all 7 other app languages


if __name__ == "__main__":
    unittest.main()


class LanguagesTest(unittest.TestCase):
    def test_every_phrase_has_every_language(self):
        import json, re
        src = read(os.path.join(ROOT, "web", "i18n.js"))
        order = json.loads(re.search(r"const I18N_ORDER = (\[[^\]]*\]);", src).group(1))
        body = src[src.index("const I18N = {") + len("const I18N = "):src.index("\n};", src.index("const I18N = {")) + 2]
        table = json.loads(re.sub(r",\s*}$", "}", body))
        self.assertGreater(len(table), 150)
        for k, v in table.items():
            self.assertEqual(len(v), len(order), k)
            self.assertTrue(all(isinstance(x, str) and x for x in v), k)

    def test_phone_has_language_flag_and_book_names(self):
        s = read(PAGES[0])
        for part in ('id="langBtn"', 'src="i18n.js"', "function setLang", "const bName"):
            self.assertIn(part, s)
        self.assertIn("i18n.js", read(os.path.join(ROOT, "web", "sw.js")))
        self.assertIn("web/i18n.js", read(os.path.join(ROOT, ".github", "workflows", "pages.yml")))  # the phone build must publish it
        self.assertIn("web/smart.js", read(os.path.join(ROOT, ".github", "workflows", "pages.yml")))  # the phone search
        self.assertIn("smart.js", read(os.path.join(ROOT, "web", "sw.js")))   # kept for offline use

    def test_book_names_table(self):
        import json
        with open(os.path.join(ROOT, "bibleask", "data", "booknames.json"), encoding="utf-8") as f:
            t = json.load(f)
        self.assertEqual(t["deu"]["Genesis"], "1. Mose")
        self.assertIn("kor", t)
        from bibleask.library import book_names
        self.assertEqual(book_names("deu-luther1912.osis")["Revelation"], "Offenbarung")
        self.assertEqual(book_names("eng-kjv"), {})


class HomeScreenButtonTest(unittest.TestCase):
    def test_phone_offers_add_to_home_screen(self):
        page = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "index.html"), encoding="utf-8").read()
        for part in ('id="homeInstall"', "Add BibleChat to your home screen", 'id="installSheet"', "beforeinstallprompt", ".prompt()",
                     "appinstalled", "display-mode: standalone", "navigator.standalone", "Add to Home Screen", "Add to Home screen",
                     'name="apple-mobile-web-app-capable"', 'rel="manifest"'):
            self.assertIn(part, page)
        self.assertLess(page.index('id="homeInstall"'), page.index('id="homeCover"'))   # first thing on Home, above the cover

