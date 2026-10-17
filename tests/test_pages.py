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
