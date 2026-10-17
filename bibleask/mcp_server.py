"""BibleChat as a connector (MCP server) for Claude and other AI apps.

It lets an AI look up verses, search the Bible, open Strong's Hebrew and Greek words, cross-references,
Nave's topics, Matthew Henry and Easton's dictionary, always quoting real Bible text.

Two ways to run it (Python standard library only, nothing to install):

  python -m bibleask.mcp_server                 On your own computer, for Claude Desktop or Claude Code.
                                                Uses the built-in King James Bible plus every Bible you added
                                                to BibleChat.
  python -m bibleask.mcp_server --http 8000     As a public web service (MCP "Streamable HTTP" at /mcp, no login).
                                                Uses only the built-in public-domain data. Put it behind HTTPS.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional

from . import __version__
from .henry_easton import EASTON, HENRY
from .loaders import Bible, Verse, PROTESTANT_BOOKS
from .search import BookIndex, Index
from .strongs import STRONGS
from .topics import TOPICS
from .xref import XREFS

APP_URL = "https://beaugrand.github.io/BibleChat-voice/"
PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
MAX_BODY = 1_000_000
CREDIT = f"From BibleChat, the free Bible app by Hans W. Beaugrand: {APP_URL}"

INSTRUCTIONS = (
    "BibleChat gives you real Bible text and classic public-domain study tools. Quote verses exactly as the tools "
    "return them and give the reference with each one; never write Scripture from memory. Use get_passage for a "
    "reference, search_bible for words or ideas, study_verse for the original Hebrew/Greek words, cross-references, "
    "topics and Matthew Henry, strongs_word for a Strong's number, find_topic for a subject, cross_references for "
    "links between verses or whole books, and bible_dictionary for names and places."
)

# ---------------------------------------------------------------------------------------------- data
_lock = threading.Lock()
_kjv: Optional[tuple[Bible, Index]] = None
_mine: dict[str, tuple[Bible, Index]] = {}
USE_OWN_BIBLES = True   # switched off for the public web service


def kjv() -> tuple[Bible, Index]:
    """The King James Version that ships with BibleChat (from the Strong's data), indexed once."""
    global _kjv
    with _lock:
        if _kjv is None:
            STRONGS._load()
            verses = [Verse(b, c, v, STRONGS.kjv_text(b, c, v)) for (b, c, v) in STRONGS._verses]
            bible = Bible("King James Version (built in)", verses)
            _kjv = (bible, Index(bible))
        return _kjv


def own_bibles() -> list[dict]:
    if not USE_OWN_BIBLES:
        return []
    try:
        from . import storage
        out = []
        for bid in storage.list_bibles():
            try:
                out.append({"id": bid, "name": storage.open_bible(bid).name})
            except Exception:
                continue
        return out
    except Exception:
        return []


def pick(bible: Optional[str]) -> tuple[Bible, Index]:
    """A Bible by id or name; the built-in KJV when none is given or it isn't found."""
    want = (bible or "").strip().lower()
    if want and want not in ("kjv", "king james", "king james version") and USE_OWN_BIBLES:
        for b in own_bibles():
            if want in (b["id"].lower(), b["name"].lower()) or want in b["name"].lower():
                with _lock:
                    if b["id"] not in _mine:
                        from . import storage
                        bb = storage.open_bible(b["id"])
                        _mine[b["id"]] = (bb, Index(bb))
                    return _mine[b["id"]]
    return kjv()


_REF = re.compile(r"^\s*(.+?)\.?\s+(\d{1,3})(?:\s*[:.]\s*(\d{1,3})(?:\s*[-–]\s*(\d{1,3}))?)?\s*$")
_CANON = BookIndex(PROTESTANT_BOOKS)


def parse_ref(text: str) -> Optional[tuple[str, int, int, int]]:
    """'John 3:16', '1 Cor 13:4-7', 'Psalm 23' -> (book, chapter, first verse, last verse) with KJV book names."""
    m = _REF.match(text or "")
    if not m:
        return None
    book = _CANON.resolve(m.group(1))
    if not book:
        return None
    ch = int(m.group(2))
    v1 = int(m.group(3)) if m.group(3) else 0
    v2 = int(m.group(4)) if m.group(4) else (v1 if v1 else 999)
    return book, ch, max(v1, 1), v2


def fmt(verses: list[Verse], with_ref: bool = True) -> str:
    return "\n".join((f"{v.ref}  " if with_ref else f"{v.verse} ") + v.text for v in verses)


# ---------------------------------------------------------------------------------------------- tools
def t_list_bibles(_a: dict) -> str:
    lines = ["kjv: King James Version (built in, always available)"]
    lines += [f"{b['id']}: {b['name']}" for b in own_bibles()]
    return "Bibles you can use (pass the id or name as `bible`):\n" + "\n".join(lines)


def t_get_passage(a: dict) -> str:
    ref = str(a.get("reference", "")).strip()
    bible, idx = pick(a.get("bible"))
    hits = idx.lookup_reference(ref)
    if not hits:
        return f"Couldn't find the reference “{ref}” in {bible.name}. Try a form like John 3:16, 1 Cor 13:4-7 or Psalm 23."
    vs = [bible.verses[i] for i in hits[:200]]
    more = f"\n(First 200 of {len(hits)} verses.)" if len(hits) > 200 else ""
    return f"{bible.name}\n\n" + fmt(vs) + more


def t_search_bible(a: dict) -> str:
    q = str(a.get("query", "")).strip()
    k = max(1, min(int(a.get("limit") or 15), 50))
    bible, idx = pick(a.get("bible"))
    hits = idx.search(q, k=k)
    if not hits:
        return f"No verses in {bible.name} match “{q}”. Try other words."
    return f"{bible.name}: {len(hits)} verses for “{q}”, best match first\n\n" + fmt([bible.verses[h.index] for h in hits])


def _one_verse(ref: str) -> Optional[tuple[str, int, int]]:
    r = parse_ref(ref)
    if not r or r[2] == 0:
        return None
    return r[0], r[1], r[2]


def t_study_verse(a: dict) -> str:
    r = _one_verse(str(a.get("reference", "")))
    if not r:
        return "Give one verse, for example John 1:1."
    book, ch, v = r
    text = STRONGS.kjv_text(book, ch, v)
    if not text:
        return f"{book} {ch}:{v} isn't in the King James Version."
    out = [f"{book} {ch}:{v} (KJV): {text}", "", "Original words (Strong's numbers):"]
    for s in STRONGS.verse(book, ch, v):
        if isinstance(s, list):
            for n in s[1].split():
                e = STRONGS.entry(n)
                if e:
                    out.append(f"- “{s[0].strip()}” = {n} {e['word']} ({e['translit']}): {e['meaning'][:220]}")
    topics = TOPICS.for_verse(book, ch, v)[:12]
    if topics:
        out += ["", "Topics (Nave's Topical Bible): " + "; ".join(t["title"] for t in topics)]
    xr = XREFS.for_verse(book, ch, v)[:12]
    if xr:
        out += ["", "Cross-references (OpenBible.info), strongest first:"]
        out += [f"- {x['ref']}: {STRONGS.kjv_text(x['book'], x['chapter'], x['verse'])}" for x in xr]
    h = HENRY.for_verse(book, ch, v)
    if h:
        out += ["", f"Matthew Henry's Concise Commentary (on the passage from verse {h['from_verse']}):", h["text"][:1800]]
    return "\n".join(out)


def t_strongs_word(a: dict) -> str:
    e = STRONGS.entry(str(a.get("number", "")))
    if not e:
        return "Give a Strong's number such as H430 (Hebrew) or G26 (Greek)."
    uses = STRONGS.verses_with(e["number"])
    lines = [f"{e['number']} ({e['language']}) {e['word']}, {e['translit']}, pronounced {e['pron']}",
             f"Meaning: {e['meaning']}", f"KJV translates it as: {e['kjv']}",
             f"Used in {e['count']} KJV verses. First {min(25, len(uses))}:"]
    lines += [f"- {b} {c}:{v} (“{w}”): {STRONGS.kjv_text(b, c, v)}" for (b, c, v), w in uses[:25]]
    return "\n".join(lines)


def t_find_topic(a: dict) -> str:
    q = str(a.get("query", "")).strip()
    hits = TOPICS.find(q, k=1)
    titles = TOPICS.search_titles(q, k=10)
    if not hits and not titles:
        return f"No topic in Nave's Topical Bible matches “{q}”."
    out = []
    if hits:
        t = hits[0]
        out.append(f"Nave's Topical Bible: {t.title}")
        n = 0
        for b, c, v1, v2 in t.refs:
            for v in range(v1, v2 + 1):
                if n >= 40:
                    break
                out.append(f"- {b} {c}:{v}: {STRONGS.kjv_text(b, c, v)}")
                n += 1
    if titles:
        out += ["", "Other matching topics: " + "; ".join(t["title"] for t in titles[:10])]
    return "\n".join(out)


def t_cross_references(a: dict) -> str:
    ref, to_book = str(a.get("reference", "")).strip(), str(a.get("to_book") or "").strip()
    two = re.split(r"\s+(?:and|to|&|-|–|vs\.?)\s+", ref)
    if len(two) == 2 and not parse_ref(ref):
        b1, b2 = _CANON.resolve(two[0]), _CANON.resolve(two[1])
        if b1 and b2:
            links = XREFS.between(b1, b2)[:80]
            if not links:
                return f"No strong cross-references between {b1} and {b2}."
            return f"Cross-references between {b1} and {b2} (OpenBible.info), strongest first:\n" + "\n".join(
                f"- {x['from']} ↔ {x['to']}: {STRONGS.kjv_text(*x['from_ref'])} | {STRONGS.kjv_text(*x['to_ref'][:3])}"
                for x in links)
    r = _one_verse(ref)
    if not r:
        return "Give one verse (Daniel 7:13), or two books (Daniel and Revelation)."
    book, ch, v = r
    tb = _CANON.resolve(to_book) if to_book else None
    xr = XREFS.for_verse(book, ch, v, tb)[:40]
    if not xr:
        return f"No cross-references for {book} {ch}:{v}" + (f" into {tb}." if tb else ".")
    return f"Cross-references for {book} {ch}:{v} (OpenBible.info), strongest first:\n" + "\n".join(
        f"- {x['ref']}: {STRONGS.kjv_text(x['book'], x['chapter'], x['verse'])}" for x in xr)


def t_bible_dictionary(a: dict) -> str:
    e = EASTON.entry(str(a.get("term", "")))
    if not e:
        return "That name or word isn't in Easton's Bible Dictionary."
    return f"Easton's Bible Dictionary (1897): {e['term']}\n\n{e['text'][:6000]}"


def _tool(name, title, desc, props, required, fn):
    return {"name": name, "title": title, "description": desc,
            "inputSchema": {"type": "object", "properties": props, "required": required},
            "annotations": {"title": title, "readOnlyHint": True, "destructiveHint": False,
                            "idempotentHint": True, "openWorldHint": False}, "_fn": fn}


_BIBLE = {"type": "string", "description": "Optional Bible id or name from list_bibles. Default: King James Version."}
TOOLS = [
    _tool("get_passage", "Get a Bible passage",
          "Exact text of a verse, a range or a whole chapter, e.g. 'John 3:16', '1 Cor 13:4-7', 'Psalm 23'.",
          {"reference": {"type": "string", "description": "A Bible reference"}, "bible": _BIBLE}, ["reference"], t_get_passage),
    _tool("search_bible", "Search the Bible",
          "Find verses by words or an idea ('love is patient', 'ruler would change times'), best match first.",
          {"query": {"type": "string"}, "bible": _BIBLE,
           "limit": {"type": "integer", "minimum": 1, "maximum": 50, "description": "How many verses (default 15)"}},
          ["query"], t_search_bible),
    _tool("study_verse", "Study a verse",
          "One verse word by word with Strong's Hebrew/Greek numbers and meanings, its Nave's topics, "
          "cross-references and Matthew Henry's commentary (KJV).",
          {"reference": {"type": "string", "description": "One verse, e.g. 'Genesis 1:1'"}}, ["reference"], t_study_verse),
    _tool("strongs_word", "Look up a Strong's number",
          "A Hebrew (H...) or Greek (G...) word: original spelling, pronunciation, meaning, KJV renderings and verses using it.",
          {"number": {"type": "string", "description": "e.g. H430, G26"}}, ["number"], t_strongs_word),
    _tool("find_topic", "Find a Bible topic",
          "Verses on a subject from Nave's Topical Bible (e.g. 'prayer', 'fallen angels', 'God's name').",
          {"query": {"type": "string"}}, ["query"], t_find_topic),
    _tool("cross_references", "Cross-references",
          "Related verses for one verse (optionally only into one book), or every strong link between two books "
          "('Daniel and Revelation'). From OpenBible.info.",
          {"reference": {"type": "string", "description": "'Daniel 7:13' or 'Daniel and Revelation'"},
           "to_book": {"type": "string", "description": "Optional: only links into this book"}},
          ["reference"], t_cross_references),
    _tool("bible_dictionary", "Bible dictionary",
          "Easton's Bible Dictionary (1897) entry for a person, place or word, e.g. 'Patmos', 'Melchizedek'.",
          {"term": {"type": "string"}}, ["term"], t_bible_dictionary),
    _tool("list_bibles", "List Bibles", "The Bibles this connector can quote from.", {}, [], t_list_bibles),
]
_BY_NAME = {t["name"]: t for t in TOOLS}


# ---------------------------------------------------------------------------------------------- protocol
def handle(msg: dict) -> Optional[dict]:
    """One JSON-RPC message in, one reply out (None for notifications)."""
    if not isinstance(msg, dict):
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid request"}}
    mid, method, params = msg.get("id"), msg.get("method"), msg.get("params") or {}
    if mid is None:
        return None   # notifications (initialized, cancelled) need no answer
    ok = lambda result: {"jsonrpc": "2.0", "id": mid, "result": result}
    if method == "initialize":
        want = params.get("protocolVersion")
        return ok({"protocolVersion": want if want in PROTOCOLS else PROTOCOLS[0],
                   "capabilities": {"tools": {"listChanged": False}},
                   "serverInfo": {"name": "biblechat", "title": "BibleChat", "version": __version__},
                   "instructions": INSTRUCTIONS})
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": [{k: v for k, v in t.items() if k != "_fn"} for t in TOOLS]})
    if method == "tools/call":
        t = _BY_NAME.get(params.get("name"))
        if not t:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": f"Unknown tool: {params.get('name')}"}}
        try:
            text = t["_fn"](params.get("arguments") or {})
            return ok({"content": [{"type": "text", "text": text + "\n\n" + CREDIT}], "isError": False})
        except Exception as e:  # a tool problem is reported to the AI, not as a protocol error
            return ok({"content": [{"type": "text", "text": f"Something went wrong: {e}"}], "isError": True})
    if method in ("resources/list", "prompts/list"):
        return ok({method.split("/")[0]: []})
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"Method not found: {method}"}}


def handle_payload(data):
    if isinstance(data, list):
        out = [r for r in (handle(m) for m in data) if r is not None]
        return out or None
    return handle(data)


def run_stdio() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            reply = handle_payload(json.loads(line))
        except json.JSONDecodeError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        if reply is not None:
            sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            sys.stdout.flush()


class _Http(BaseHTTPRequestHandler):
    server_version = "BibleChatMCP/" + __version__

    def _send(self, code: int, body: bytes = b"", ctype: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Mcp-Session-Id, Mcp-Protocol-Version, Authorization")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self._send(204)

    def do_GET(self) -> None:
        if self.path.split("?")[0] in ("/", "/health"):
            self._send(200, f"BibleChat connector {__version__}. MCP endpoint: /mcp\n{CREDIT}\n".encode(), "text/plain; charset=utf-8")
        else:
            self._send(405, b'{"error":"Use POST for MCP requests"}')

    def do_POST(self) -> None:
        if self.path.split("?")[0] != "/mcp":
            return self._send(404, b'{"error":"The MCP endpoint is /mcp"}')
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > MAX_BODY:
            return self._send(413 if n > MAX_BODY else 400, b'{"error":"Bad request size"}')
        try:
            reply = handle_payload(json.loads(self.rfile.read(n)))
        except json.JSONDecodeError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        if reply is None:
            return self._send(202)
        self._send(200, json.dumps(reply, ensure_ascii=False).encode("utf-8"))

    def log_message(self, fmt, *args) -> None:  # keep quiet; nothing about requests is stored
        pass


def run_http(port: int, host: str) -> None:
    kjv()   # build the index before the first request
    srv = ThreadingHTTPServer((host, port), _Http)
    print(f"BibleChat connector listening on http://{host}:{port}/mcp", flush=True)
    srv.serve_forever()


def main(argv: Optional[list[str]] = None) -> None:
    global USE_OWN_BIBLES
    ap = argparse.ArgumentParser(description="BibleChat connector (MCP server) for Claude and other AI apps")
    ap.add_argument("--http", type=int, nargs="?", const=int(os.environ.get("PORT", "8000")),
                    help="serve MCP over HTTP on this port (public mode: built-in data only)")
    ap.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"), help="address to listen on (0.0.0.0 on a host)")
    args = ap.parse_args(argv)
    if args.http:
        USE_OWN_BIBLES = False
        run_http(args.http, args.host)
    else:
        run_stdio()


if __name__ == "__main__":
    main()
