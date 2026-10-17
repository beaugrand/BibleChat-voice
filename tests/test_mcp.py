import unittest

from bibleask import mcp_server as m


def call(name, **args):
    r = m.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": args}})
    return r["result"]["content"][0]["text"], r["result"]["isError"]


class ConnectorTest(unittest.TestCase):
    def test_initialize_and_tools_are_annotated(self):
        r = m.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
        self.assertEqual(r["result"]["serverInfo"]["name"], "biblechat")
        tools = m.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]
        self.assertGreaterEqual(len(tools), 8)
        for t in tools:
            self.assertTrue(t["title"] and t["annotations"]["readOnlyHint"], t["name"])
            self.assertNotIn("_fn", t)

    def test_notification_gets_no_reply(self):
        self.assertIsNone(m.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))

    def test_passage_and_search(self):
        t, err = call("get_passage", reference="John 3:16")
        self.assertFalse(err)
        self.assertIn("For God so loved the world", t)
        self.assertIn("beaugrand.github.io", t)
        t, _ = call("search_bible", query="change times and laws", limit=3)
        self.assertIn("Daniel 7:25", t)

    def test_study_tools(self):
        self.assertIn("H430", call("study_verse", reference="Genesis 1:1")[0])
        self.assertIn("ἀγάπη", call("strongs_word", number="G26")[0])
        self.assertIn("Revelation 1:7", call("cross_references", reference="Daniel 7:13", to_book="Revelation")[0])
        self.assertIn("Patmos", call("bible_dictionary", term="Patmos")[0])

    def test_unknown_tool(self):
        r = m.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "nope"}})
        self.assertIn("error", r)


if __name__ == "__main__":
    unittest.main()
