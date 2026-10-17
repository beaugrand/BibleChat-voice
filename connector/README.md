# BibleChat connector (MCP server)

Lets Claude and other AI apps use BibleChat: real Bible text plus Strong's Hebrew and Greek, cross-references,
Nave's topics, Matthew Henry and Easton's dictionary. Every answer quotes real verses with their references.
Code: [`bibleask/mcp_server.py`](../bibleask/mcp_server.py). Python standard library only.

## Tools (all read-only)

| Tool | What it does |
|---|---|
| `get_passage` | Exact text of a verse, range or chapter (`John 3:16`, `1 Cor 13:4-7`, `Psalm 23`) |
| `search_bible` | Verses by words or an idea, best match first |
| `study_verse` | One verse word by word with Strong's numbers, topics, cross-references, Matthew Henry |
| `strongs_word` | A Hebrew or Greek word (`H430`, `G26`) and the verses that use it |
| `find_topic` | Verses on a subject from Nave's Topical Bible |
| `cross_references` | Links from one verse, or between two books (`Daniel and Revelation`) |
| `bible_dictionary` | Easton's Bible Dictionary entry (`Patmos`) |
| `list_bibles` | The Bibles available |

## On your own computer (Claude Desktop, Claude Code)

Uses the built-in King James Version plus every Bible you added in BibleChat. Add this to Claude Desktop's
configuration (Settings → Developer → Edit Config), with the path to your BibleChat folder:

```json
{
  "mcpServers": {
    "biblechat": {
      "command": "python3",
      "args": ["-m", "bibleask.mcp_server"],
      "cwd": "/path/to/BibleChat-voice"
    }
  }
}
```

Claude Code: `claude mcp add biblechat -- python3 -m bibleask.mcp_server` (run it inside the BibleChat folder).

## As a public connector (for the Claude directory)

The directory only lists remote servers reachable over HTTPS. Public mode uses only the built-in public-domain
data and needs no login. Any host that runs a Docker container works (Render, Fly.io, Railway, Hugging Face Spaces):

```bash
docker build -f connector/Dockerfile -t biblechat-connector .
docker run -p 8000:8000 biblechat-connector     # MCP endpoint: http://localhost:8000/mcp
```

Without Docker: `python3 -m bibleask.mcp_server --http 8000 --host 0.0.0.0`.

Then: add the HTTPS address ending in `/mcp` as a custom connector in Claude, try every tool, and submit it at
[claude.ai/directory/manage](https://claude.ai/directory/manage) (needs a paid Claude plan). Privacy policy:
[PRIVACY.md](../PRIVACY.md). Documentation: this page. Support: the project's GitHub issues.

## Privacy

The connector stores nothing and logs no requests. See [PRIVACY.md](../PRIVACY.md).
