"""Tests for the BibleChat engine and local web server (uses a fake AI model)."""
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
_TMP = tempfile.mkdtemp()
os.environ["XDG_DATA_HOME"] = _TMP  # keep test Bibles out of the real data folder

from bibleask import chat, llm, server  # noqa: E402
from bibleask.library import Library  # noqa: E402
from bibleask.loaders import load_bible  # noqa: E402

KJV_TXT = """The Project Gutenberg eBook of The King James Bible

*** START OF THE PROJECT GUTENBERG EBOOK ***

The Gospel According to Saint John


3:16 For God so loved the world, that he gave his only begotten Son,
that whosoever believeth in him should not perish, but have everlasting
life.

3:17 For God sent not his Son into the world to condemn the world.

The Second Epistle of Paul the Apostle to the Thessalonians


2:3 Let no man deceive you by any means: for that day shall not come,
except there come a falling away first.

""" + "".join(f"2:{i} Filler sentence number {i} about nothing special.\n" for i in range(4, 130)) + """
*** END OF THE PROJECT GUTENBERG EBOOK ***
"""

ZEFANIA = """<?xml version="1.0" encoding="utf-8"?>
<XMLBIBLE biblename="Tiny">
 <BIBLEBOOK bnumber="43" bname="John"><CHAPTER cnumber="3"><VERS vnumber="16">God loved the world so much that he gave his one and only Son.</VERS></CHAPTER></BIBLEBOOK>
 <BIBLEBOOK bnumber="27" bname="Daniel"><CHAPTER cnumber="7"><VERS vnumber="25">He will plan to change the times and the law.</VERS></CHAPTER></BIBLEBOOK>
</XMLBIBLE>"""


class FakeModel:
    loaded = True
    style = "general"
    seen = None

    def stream(self, question, passages):
        FakeModel.seen = passages
        for w in ["Hello ", "from ", "the ", "model."]:
            yield w


def _call(url, data=None, headers=None, method=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


class ChatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = server.App()
        cls.app.model = FakeModel()
        s = __import__("socket").socket(); s.bind(("127.0.0.1", 0)); cls.port = s.getsockname()[1]; s.close()
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", cls.port), server.make_handler(cls.app, cls.port))
        cls.httpd.daemon_threads = True
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def upload(self, name, text):
        j = json.loads(_call(self.base + "/api/bibles", text.encode("utf-8"), {"X-Filename": urllib.parse.quote(name)}))
        for _ in range(100):
            s = json.loads(_call(self.base + "/api/jobs/" + j["job"]))
            if s["status"] != "running":
                return s
            time.sleep(0.1)
        self.fail("upload job never finished")

    def ask(self, question, bibles, previous=None, use_ai=True):
        body = json.dumps({"question": question, "bibles": bibles, "previous": previous, "use_ai": use_ai}).encode()
        raw = _call(self.base + "/api/chat", body).decode()
        events = []
        for block in raw.strip().split("\n\n"):
            ev = block.split("\n")[0][7:]
            events.append((ev, json.loads(block.split("\n")[1][6:])))
        return events

    def test_1_gutenberg_text_and_xml_upload(self):
        a = self.upload("King James.txt", KJV_TXT)
        self.assertEqual(a["status"], "done", a)
        b = self.upload("Tiny.xml", ZEFANIA)
        self.assertEqual(b["status"], "done", b)
        st = json.loads(_call(self.base + "/api/state"))
        names = {x["name"] for x in st["bibles"]}
        self.assertEqual(names, {"King James", "Tiny"})
        kjv = next(x for x in st["bibles"] if x["name"] == "King James")
        self.assertEqual(kjv["books"], 2)

    def test_2_reference_shows_every_selected_bible(self):
        ev = self.ask("John 3:16", ["King_James", "Tiny"])
        kinds = [k for k, _ in ev]
        self.assertEqual(kinds[0], "sources")
        groups = ev[0][1]["groups"]
        self.assertEqual({g["bible"] for g in groups}, {"King James", "Tiny"})
        self.assertIn("so loved the world", json.dumps(groups))
        self.assertEqual(kinds[-1], "done")
        self.assertIn("token", kinds)

    def test_2b_abbreviated_reference_in_gutenberg_text(self):
        ev = self.ask("2 Thess 2:3", ["King_James"])
        self.assertEqual(ev[0][0], "sources", ev)
        self.assertIn("falling away", json.dumps(ev[0][1]))

    def test_3_search_and_model_gets_only_found_verses(self):
        ev = self.ask("falling away", ["King_James"])
        src = ev[0][1]
        self.assertEqual(src["kind"], "search")
        self.assertEqual(src["groups"][0]["verses"][0]["ref"].split(":")[0].endswith("2"), True)
        self.assertTrue(all(len(t) > 0 for _, t in FakeModel.seen))
        self.assertIn("falling away", FakeModel.seen[0][1])

    def test_4_nothing_found_never_calls_model(self):
        FakeModel.seen = None
        ev = self.ask("zzzqqq xyzzy", ["King_James", "Tiny"])
        self.assertEqual([k for k, _ in ev], ["token", "done"])
        self.assertIn("couldn't find", ev[0][1])
        self.assertIsNone(FakeModel.seen)
        ev = self.ask("zzzqqq xyzzy", ["King_James"], previous="falling away")  # nonsense is not a follow-up
        self.assertIn("couldn't find", ev[0][1])

    def test_5_no_bibles_selected_and_ai_off(self):
        ev = self.ask("anything", [])
        self.assertIn("Add a Bible", ev[0][1])
        ev = self.ask("Daniel 7:25", ["Tiny"], use_ai=False)
        self.assertEqual([k for k, _ in ev], ["sources", "done"])

    def test_6_short_followup_uses_previous_question(self):
        ev = self.ask("verse 3?", ["King_James"], previous="falling away in Thessalonians")
        self.assertEqual(ev[0][0], "sources")
        self.assertIn("falling away", json.dumps(ev[0][1]))

    def test_7_no_model_gives_notice(self):
        old = self.app.model
        class NoModel(FakeModel):
            loaded = False
        self.app.model = NoModel()
        try:
            ev = self.ask("Daniel 7:25", ["Tiny"])
            self.assertEqual([k for k, _ in ev], ["sources", "notice", "done"])
        finally:
            self.app.model = old

    def test_7b_highlights_are_kept(self):
        url = self.base + "/api/highlights"
        post = lambda body: json.loads(_call(url, json.dumps(body).encode(), {"Content-Type": "application/json"}))["items"]
        items = post({"set": {"Genesis|3|15": {"col": "y", "t": "And I will put enmity", "a": "KJV"},
                              "John|3|16": {"col": "g", "t": "For God so loved", "a": "KJV"},
                              "bad key": {"col": "y"}, "Genesis|1|1": {"col": "purple"}}})
        self.assertEqual(sorted(items), ["Genesis|3|15", "John|3|16"])
        self.assertEqual(items["Genesis|3|15"]["col"], "y")
        items = post({"set": {"Genesis|3|15": {"col": "b"}}, "remove": ["John|3|16"]})
        self.assertEqual(list(items), ["Genesis|3|15"]); self.assertEqual(items["Genesis|3|15"]["col"], "b")
        self.assertEqual(json.loads(_call(url))["items"], items)   # kept by the app, there after a restart too
        post({"remove": ["Genesis|3|15"]})

    def test_8_rejects_foreign_host_and_serves_page(self):
        req = urllib.request.Request(self.base + "/api/state", headers={"Host": "evil.example"})
        with self.assertRaises(Exception):
            urllib.request.urlopen(req, timeout=5)
        self.assertIn(b"BibleChat", _call(self.base + "/"))

    def test_9_remove_bible(self):
        _call(self.base + "/api/bibles/Tiny", method="DELETE")
        st = json.loads(_call(self.base + "/api/state"))
        self.assertEqual([x["id"] for x in st["bibles"]], ["King_James"])


if __name__ == "__main__":
    unittest.main()
