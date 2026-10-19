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
