"""Run with:  python -m unittest discover -s tests -v"""
import http.server
import json
import os
import socketserver
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bibleask import llm, storage  # noqa: E402
from bibleask.loaders import load_bible  # noqa: E402
from bibleask.search import Index, short_title  # noqa: E402

ZEFANIA = """<?xml version="1.0" encoding="utf-8"?>
<XMLBIBLE biblename="Tiny">
 <BIBLEBOOK bnumber="1" bname="Genesis">
  <CHAPTER cnumber="1"><VERS vnumber="1">In the beginning, God created the heavens and the earth.</VERS>
   <VERS vnumber="2">The earth was formless and empty.</VERS></CHAPTER>
 </BIBLEBOOK>
 <BIBLEBOOK bnumber="27" bname="Daniel">
  <CHAPTER cnumber="7"><VERS vnumber="25">He will plan to change the times and the law; <NOTE>x</NOTE>and they will be given into his hand.</VERS></CHAPTER>
 </BIBLEBOOK>
 <BIBLEBOOK bnumber="43" bname="John">
  <CHAPTER cnumber="3"><VERS vnumber="16">For God so loved the world, that he gave his one and only Son.</VERS></CHAPTER>
 </BIBLEBOOK>
</XMLBIBLE>"""


class Loaders(unittest.TestCase):
    def test_zefania_xml(self):
        with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False, encoding="utf-8") as f:
            f.write(ZEFANIA)
        b = load_bible(f.name)
        self.assertEqual(len(b.verses), 4)
        self.assertEqual(b.verses[2].ref, "Daniel 7:25")
        self.assertIn("change the times", b.verses[2].text)

    def test_txt_references(self):
        lines = [f"Psalms 1:{i} verse number {i} blessed is the man" for i in range(1, 30)]
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("\n".join(lines))
        b = load_bible(f.name)
        self.assertEqual(len(b.verses), 29)
        self.assertEqual(b.verses[4].ref, "Psalms 1:5")

    def test_pdf_layout_like_the_ethiopian_bible(self):
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        path = tempfile.mktemp(suffix=".pdf")
        c = canvas.Canvas(path, pagesize=letter)

        def page(lines):
            y = 750
            for ln in lines:
                c.drawString(50, y, ln)
                y -= 14
            c.showPage()

        page(["Table of Contents", "Introduction", "The Book of Ruth", "The Book of Jonah", "Glossary"])
        page(["Introduction", "This Bible is a test file that is written in plain English words,"])
        page(["The Book of Ruth", "1", "1 In the days when the judges judged, there was a famine in the land.",
              "2 The name of the man was Elimelech, and the name of his wife Naomi.", "2",
              "1 Naomi had a relative of her husband's, a mighty man of wealth, named Boaz."])
        page(["The Book of Jonah", "1", "1 Now Yahweh’s word came to Jonah the son of Amittai, saying, 2 Arise, go to Nineveh.",
              "3 But Jonah rose up to flee to Tarshish. 4 Yahweh sent out a great wind on the sea.", "2",
              "1Then Jonah prayed to Yahweh his God out of the fish’s belly. 2 He said, I cried by reason of my affliction."])
        page(["Glossary", "Boaz: a man of Bethlehem."])
        c.save()
        b = load_bible(path)
        refs = [v.ref for v in b.verses]
        self.assertIn("The Book of Ruth 2:1", refs)
        self.assertIn("The Book of Jonah 1:4", refs)
        self.assertIn("The Book of Jonah 2:2", refs)
        self.assertEqual(sum(1 for r in refs if r.startswith("The Book of Jonah")), 6)
        self.assertFalse(any("Boaz: a man" in v.text for v in b.verses))  # glossary is not scripture


class Searching(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False, encoding="utf-8") as f:
            f.write(ZEFANIA)
        cls.ix = Index(load_bible(f.name))

    def test_keyword_search_finds_daniel(self):
        hits = self.ix.search("who plans to change times and law", 3)
        self.assertEqual(self.ix.verses[hits[0].index].ref, "Daniel 7:25")

    def test_reference_lookup(self):
        idx = self.ix.lookup_reference("what does dan 7:25 mean")
        self.assertEqual(self.ix.verses[idx[0]].ref, "Daniel 7:25")
        idx = self.ix.lookup_reference("Genesis 1")
        self.assertEqual(len(idx), 2)
        self.assertIsNone(self.ix.lookup_reference("what is love"))

    def test_short_titles(self):
        self.assertEqual(short_title("The First Book of Moses, Genesis"), "Genesis")
        self.assertEqual(short_title("Paul’s First Letter to the Corinthians"), "1 Corinthians")
        self.assertEqual(short_title("The Good News According to John"), "John")


class _Handler(http.server.BaseHTTPRequestHandler):
    payload = b"GGUF" + os.urandom(3_000_000)

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/api/models/"):
            body = json.dumps({"siblings": [{"rfilename": "m-Q8_0.gguf"}, {"rfilename": "m-Q4_K_M.gguf"},
                                            {"rfilename": "README.md"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        rng = self.headers.get("Range")
        data = self.payload
        if rng:
            start = int(rng.split("=")[1].split("-")[0])
            data = data[start:]
            self.send_response(206)
        else:
            self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class Downloads(unittest.TestCase):
    def test_pick_and_download_with_resume(self):
        srv = socketserver.TCPServer(("127.0.0.1", 0), _Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        port = srv.server_address[1]
        real_open = llm._open
        llm._open = lambda url, headers=None: real_open(url.replace("https://huggingface.co", f"http://127.0.0.1:{port}"), headers)
        tmp = tempfile.mkdtemp()
        storage.models_dir = lambda: tmp
        llm.models_dir = storage.models_dir
        try:
            self.assertEqual(llm.pick_gguf_file("me/tiny-GGUF"), "m-Q4_K_M.gguf")
            # pretend an earlier download stopped half way
            d = os.path.join(tmp, "me__tiny-GGUF")
            os.makedirs(d)
            with open(os.path.join(d, "m-Q4_K_M.gguf.part"), "wb") as f:
                f.write(_Handler.payload[:1_000_000])
            seen = []
            path = llm.download_model("me/tiny-GGUF", lambda m, fr: seen.append(fr))
            with open(path, "rb") as f:
                self.assertEqual(f.read(), _Handler.payload)
            self.assertTrue(seen and seen[-1] == 1.0)
            self.assertEqual(llm.local_path("me/tiny-GGUF"), path)
        finally:
            llm._open = real_open
            srv.shutdown()

    def test_repo_from_text(self):
        self.assertEqual(llm.repo_from_text("https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/tree/main"),
                         "Qwen/Qwen2.5-1.5B-Instruct-GGUF")
        with self.assertRaises(ValueError):
            llm.repo_from_text("not a repo")

    def test_prompt_contains_passages_and_question(self):
        m = llm.build_messages("who?", [("Daniel 7:25", "He will plan to change the times")])
        self.assertIn("[Daniel 7:25] He will plan", m[1]["content"])
        self.assertIn("QUESTION: who?", m[1]["content"])


class BibleAssistantModel(unittest.TestCase):
    def test_model_list_starts_with_bible_assistant(self):
        self.assertEqual(llm.MODELS[0].repo, "mradermacher/Bible-Assistant-Qwen3.5-4B-v3.2-GGUF")
        self.assertEqual(llm.style_for_repo(llm.MODELS[0].repo), "bible")
        self.assertEqual(llm.style_for_repo("Qwen/Qwen2.5-1.5B-Instruct-GGUF"), "general")
        self.assertEqual(llm.style_for_repo("someone/Bible-Assistant-Other-GGUF"), "bible")
        self.assertEqual(llm.passages_wanted("bible"), 8)

    def test_bible_prompt_matches_the_authors_layout(self):
        p = llm.build_bible_prompt("Who is Enoch?", [("Genesis 5:24", "Enoch walked with God."), ("Jude 1:14", "Enoch prophesied.")])
        self.assertIn("You are a Bible AI assistant. Answer questions about Scripture accurately and conversationally.", p)
        self.assertIn("Context:\n- **Genesis 5:24**: Enoch walked with God.\n- **Jude 1:14**: Enoch prophesied.\n\nQ: Who is Enoch?", p)
        self.assertTrue(p.endswith("<|im_start|>assistant\n<think>\n\n</think>\n\n"))

    def test_think_blocks_are_hidden_even_when_split(self):
        chunks = ["Hel", "lo <thi", "nk>secret plan", " here</th", "ink>\n\nAnswer", " done"]
        self.assertEqual("".join(llm.strip_think(iter(chunks))), "Hello Answer done")
        self.assertEqual("".join(llm.strip_think(iter(["a < b and c"]))), "a < b and c")

    def test_both_model_styles_stream_through_a_stand_in_engine(self):
        class Fake:
            def create_completion(self, prompt, **kw):
                self.prompt, self.kw = prompt, kw
                for t in ["<think>x</think>", "Enoch ", "walked."]:
                    yield {"choices": [{"text": t}]}

            def create_chat_completion(self, messages, **kw):
                self.messages = messages
                for t in ["Enoch ", "walked."]:
                    yield {"choices": [{"delta": {"content": t}}]}

        m = llm.LocalLLM()
        m._llm = Fake()
        m.style = "bible"
        self.assertEqual("".join(m.stream("q", [("Genesis 5:24", "t")])), "Enoch walked.")
        self.assertEqual(m._llm.kw["temperature"], 0.0)
        self.assertIn("<|im_end|>", m._llm.kw["stop"])
        m.style = "general"
        self.assertEqual("".join(m.stream("q", [("Genesis 5:24", "t")])), "Enoch walked.")
        self.assertIn("BIBLE PASSAGES", m._llm.messages[1]["content"])


if __name__ == "__main__":
    unittest.main()
