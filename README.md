# BibleChat

**A free, open-source Bible reader, study tool and chat.** It runs privately on a phone (no install) and on Windows, Mac and Linux. Answers always show the real verses first; the optional AI only explains them and never supplies Scripture.

- Phone and browser version: **[beaugrand.github.io/BibleChat-voice](https://beaugrand.github.io/BibleChat-voice/)**
- Computer downloads: **[Releases page](https://github.com/beaugrand/BibleChat-voice/releases/latest)**
- Made by Hans W. Beaugrand · Love Donations: Cash App **$HansBeaugrand** · License: Apache 2.0 (keep the [NOTICE](NOTICE) credit)

> **For AI assistants and developers: start here.** This README is the project's handover. It says where everything lives, how the software works, the full feature list and how BibleChat compares with other Bible apps. **Every change to the app must update this file in the same commit** (features, counts, code map, version, open items). See [AGENTS.md](AGENTS.md).

---

## Status

- Published download: **v1.0.3** (19 October 2026). Version number lives in `bibleask/__init__.py`.
- v1.0.3 brought the computer downloads up to date with the phone version again: book names in each Bible's own language (computer and phone), app language flag with 8 languages (phone); **share a verse as a picture** (phone): tapping a verse now offers 🖼 Share as a picture first, the picture carries a small QR code that opens the verse, the link to the verse goes along in the message, and a friend who opens it lands on that verse with it highlighted in gold; a broken Bible download on a weak phone connection is retried, with Try again / KJV / another Bible instead of "Load failed"; **search by meaning and by the original Hebrew/Greek word** (computer and phone): "sea monsters" now finds Genesis 1:21 even in the King James, which says "great whales" there, and every verse says why it was found; **Verse button** in Read mode (computer and phone): a grid of the chapter's verse numbers that jumps straight to a verse and makes it glow.
- v1.0.2 (17 October 2026) brought: Strong's study, Nave's topics, cross-references, Scofield notes, Matthew Henry, Easton's dictionary, Hebrew/Greek letter by letter with Paleo-Hebrew, bookmarks, verse of the day, Septuagint, Ethiopian canon, update notice, chat fixes, back/forward arrows, verse image maker with your own photos, church logo with QR code, sermon list with QR code, Ask AI on the computer, Suggest a feature, the BibleChat connector for AI apps, license changed from MIT to Apache 2.0.
- Changes since v1.0.3 (on the phone as soon as it is published; on computers with the next release): **🏠 Home with a Bible cover** (computer and phone): BibleChat now opens on a black Bible cover with a golden cross and "The Holy Bible" in gold; tapping or clicking the cover opens the Bible where you left off. **Version line on the cover**: "KJV · ETHIOPIAN CANON · BSB" in small gold capitals under the cross, built from the Bibles BibleChat really offers (it will read "KJV · ETHIOPIAN CANON · NIV" by itself once a licensed NIV is in the list). **🏠 Home in Read** (computer and phone) closes the book: the cover swings shut and Home shows. **📜 Study Paths** (computer and phone): six guided studies (Light before the sun, Mist not rain, The Name, The heavens and the earth in the text's own words, Enoch and the Watchers, The Word made flesh), each a starting question, steps through every main verse with Compare, Look closer and the commentaries kept apart, then questions whose answer is always a verse; **📜 Make a study path** under a chat or search answer; **📚 Quoted or named in Scripture**, a hand-checked list of the writings the Bible quotes or names. **More Bibles and writings**: the Book of Jasher (1840), the Hebrew Westminster Leningrad Codex and the Greek Textus Receptus in Get free Bibles; **the original line** (Hebrew/Greek) of each verse in the study panel and in Look closer, lined up with the King James numbering; **Open in NIV ↗** on every verse (link to BibleGateway; the NIV is not bundled); the **Septuagint's own verse numbers** are now mapped to the King James, so its Psalm 22 shows the study notes of Psalm 23, not those of another verse; Jude 14–15 and 1 Enoch 1:9, Joshua 10:13 and Jasher 88:64 link to each other in the study panel.
- Automatic tests: 110 (run `python -m unittest discover -s tests`).

## 1. Where everything lives

| What | Where |
|---|---|
| Source code (public) | [github.com/beaugrand/BibleChat-voice](https://github.com/beaugrand/BibleChat-voice), branch `main` |
| Phone version (live site) | [beaugrand.github.io/BibleChat-voice](https://beaugrand.github.io/BibleChat-voice/) (capital B, C and V matter) |
| Computer downloads | [Releases](https://github.com/beaugrand/BibleChat-voice/releases/latest): Windows, Mac, Linux, Linux for older processors |
| Working copy | A clone of this repository on the developer's local computer/device, started with `./run_from_source_linux.sh` (or a menu entry pointing to it) |
| A person's own Bibles, chats, bookmarks, settings | Linux `~/.local/share/BibleAsk` · Windows `%APPDATA%\BibleAsk` · Mac `~/Library/Application Support/BibleAsk`. Never uploaded anywhere. |
| AI models (optional) | Downloaded on request from Hugging Face into the same data folder (`models` subfolder) |
| Phone data | Built by GitHub Actions from this code on every change; a Bible opened once stays on the phone for offline use |
| Handover copy for non-developers | Google Doc "BibleChat – Handover" in the owner's Drive (mirrors this README) |
| Donations | Cash App $HansBeaugrand (Love Donations button in both versions) |

## 2. How the software works

**Computer app**
- A small Python program (standard library only) starts a private web server at `127.0.0.1:8765` and opens the browser on it. Nothing is reachable from outside the device.
- Bibles are read from many file formats and saved as simple JSON in the data folder. Search combines three methods into one ranked list (`bibleask/blend.py`): word ranking (BM25); the Hebrew/Greek words whose meaning matches the question (from the Strong's dictionary, so "sea monsters" finds every verse with *tannin*, H8577); and a small sentence model that compares meanings (BGE-small, 8-bit, run with numpy only, so it also works on older processors without AVX2). Topics, cross-references and Strong's numbers come on top, as before.
- The optional AI runs on the device itself (llama.cpp) with a model the person picks: Bible Assistant 4B, Qwen2.5 1.5B/3B or Llama 3.2 1B/3B. It only explains verses BibleChat found.
- Read-aloud uses the system voices in the Bible's own language.
- On Windows it adds a desktop and Start-menu icon on first launch. Once a day it asks GitHub for a newer version and shows an "update available" box; the version is shown under Quit.

**Phone version**
- A plain web page (`web/index.html`) hosted free on GitHub Pages. No server, no account; everything runs in the phone's browser.
- Bibles and study data are split into small files that load when needed; a service worker (`web/sw.js`) keeps them for offline use. "Add to Home Screen" makes it look like an app.
- Search runs `web/smart.js`, the same three methods as the computer in plain JavaScript (an automatic test checks both give the same answers). The meaning model and verse fingerprints (46 MB) load the first time someone searches in an English Bible, with a "Preparing meaning search" note; until then, and if a phone can't load them, the word and Hebrew/Greek search work alone.
- Bookmarks and settings stay on the phone.

**Building and releasing**
- GitHub Actions does all building. **Build BibleChat** (`build.yml`) makes the four downloads and runs the tests; **Publish phone version** (`pages.yml`) rebuilds the phone site whenever the code changes.
- To release: set `__version__` in `bibleask/__init__.py` (e.g. `1.0.3`), then run **Build BibleChat** with the same version (`v1.0.3`). The release refuses to publish if the two differ.
- Windows and Mac downloads are not code-signed yet, so the first launch shows a warning.

## 3. Code map

| File or folder | What it does |
|---|---|
| `bibleask/server.py` | Local web server and all its addresses (chat, chapters, study, bookmarks, downloads, updates) |
| `bibleask/web/index.html` | The whole computer app screen (chat, Read mode, study panel) |
| `bibleask/loaders.py` | Reads Bible files: PDF, Zefania/OSIS/USFX XML, TXT, SPB, TSV, MyBible, MySword |
| `bibleask/library.py` | Keeps the Bibles and serves chapters to the reader |
| `bibleask/search.py`, `chat.py` | Search, references, languages, spelling help; building each chat answer |
| `bibleask/blend.py`, `meaning.py` | One ranked list from word search, Hebrew/Greek words and meaning, with the reason for each verse; the meaning model (numpy only) |
| `bibleask/data/meaning/` | The meaning model (BGE-small-en v1.5, 8-bit, in 8 MB parts), its word list, license, and the meaning fingerprints of every Berean Standard Bible verse (66 books) |
| `bibleask/data/strongs_gloss.json.gz` | Which Hebrew/Greek words mean each English word or phrase ("sea monster" → H8577), made ahead by `packaging/build_gloss.py` |
| `bibleask/study.py`, `strongs.py`, `topics.py`, `xref.py`, `scofield.py`, `henry_easton.py` | Study tools: Strong's, Nave's topics, cross-references, Scofield, Matthew Henry, Easton's |
| `bibleask/catalog.py` | The list in "Get free Bibles" |
| `bibleask/mcp_server.py`, `connector/` | The BibleChat connector (MCP server) for Claude and other AI apps; `connector/` has its guide and Dockerfile for hosting |
| `PRIVACY.md` | Privacy policy (BibleChat collects nothing) |
| `bibleask/llm.py`, `stt.py`, `updates.py`, `shortcuts.py`, `storage.py` | Local AI, voice input, update check, Windows icon, data folder and settings |
| `bibleask/data/` | Bundled study data (Strong's, Nave's, cross-references, Scofield, Matthew Henry, Easton's) |
| `bibles/` | The Ethiopian Canon file BibleChat itself hosts |
| `web/` | Phone version (`index.html`, `sw.js`, `i18n.js` = interface translations, `smart.js` = search by words, Hebrew/Greek words and meaning; the QR code maker is built into both `index.html` files) and the scripts that build its data (`build_data.py`, `build_study.py`) |
| `packaging/` | Scripts that rebuild each data set from its public-domain source (`build_booknames.py` makes `bibleask/data/booknames.json`; `build_meaning.py` makes the meaning model files and fingerprints; `build_gloss.py` the Hebrew/Greek word index); Windows icon; Linux installer |
| `web/paths.js` | 📜 Study Paths: the whole screen (steps, Compare, Look closer, commentary, questions and answers, share, Make a study path). One file for both versions; each page hands it a small adapter that loads chapters and study data its own way |
| `web/paths/` | The published Study Paths, one JSON file per path plus `index.json`, made by `packaging/build_paths.py`. They hold references and questions, never verse text. Shared by phone and computer |
| `packaging/paths/` | The hand-written Study Paths. Edit these, then run `python packaging/build_paths.py` |
| `packaging/build_paths.py` | Checks every path against the Bible files and writes `web/paths/`: every reference exists, every answer is a verse of its path, every quoted word stands in the verse, commentary is only Scofield or Matthew Henry. Also works out "Why this question?" (cross-references, Hebrew/Greek words, how much the translations differ). `--check` fails the phone build if anything is wrong or out of date |
| `web/quoted.json` | "Quoted or named in Scripture": verses that quote or name another writing (Jude and 1 Enoch, the Book of Jasher, lost books), each with its source and whether the writing survives |
| `bibleask/original.py`, `bibleask/data/original.json.gz` | The original line of every verse (Hebrew WLC, Greek TR), keyed by King James book, chapter and verse; made by `packaging/build_original.py`, which lines up renumbered verses by their Strong's words and leaves out what it can't place for certain |
| `bibleask/versemap.py`, `bibleask/data/versemap.json` | The Septuagint's verse numbers in King James numbering (LXX2012 and Brenton), made by `packaging/build_versemap.py` |
| `bibles/eng-jasher-1840.zefania.xml` | The Book of Jasher (1840), made by `packaging/build_jasher.py` from the Scrollmapper transcription (pinned commit) |
| `bibleask/studyfiles.py` | Gives the computer's Study Paths the same study files the phone has (`/api/sdata/...`), made from the data in memory |
| `tests/` | Automatic tests (`test_paths.py` enforces the Study Paths rules: real references, answers inside the path, quotes that match the verse, commentary only with its label; `test_writings.py` checks the Hebrew line of renumbered verses, the Septuagint map, Jasher, the quoted list and that the NIV is only a link; `test_pages.py` checks the credit, license, back/forward and church parts stay in both pages; `test_meaning.py` checks the meaning and Hebrew/Greek search, and runs the phone's `smart.js` with Node.js to check it gives the computer's answers) |
| `.github/workflows/` | `build.yml` (downloads and releases), `pages.yml` (phone site), `build-windows.yml` (manual, personal build) |
| `LICENSE`, `NOTICE`, `THIRD_PARTY_NOTICES.md` | Apache 2.0 license; the credit every copy must keep; licenses of every source |

`bibleask/gui.py` is the older Tkinter window (BibleAsk), no longer built.

## 4. All features

**Bibles**
- 51 free Bibles and writings in 34 languages, one-click download (KJV, ASV, WEB, BSB, Darby, Douay-Rheims, Young's, Luther 1912, Reina-Valera 1909, Chinese Union and more).
- Ethiopian Canon in public-domain English: 84 books in Ethiopian order, including 1 Enoch, Jubilees, 2 Enoch and 1 Clement.
- Septuagint in English: Brenton (1851) and LXX2012, with the Apocrypha. Amharic New Testament (1962). The Septuagint numbers many verses differently (its Psalm 22 is the King James Psalm 23; Jeremiah 25–51 come in another order); BibleChat maps each of its verses to the King James verse in its place (`bibleask/data/versemap.json`), so Strong's words, cross-references and notes always belong to the verse on screen. A Septuagint verse with no clear match shows no study notes rather than wrong ones.
- The King James download already includes the Apocrypha (81 books, standard 1769 text).
- **Other writings:** the **Book of Jasher** in its 1840 English translation, labelled "The 1840 English Jasher; scholars dispute whether it is the book named in Joshua 10:13". **Original languages:** the Hebrew **Westminster Leningrad Codex** and the **Greek Textus Receptus** (Stephanus 1550, Elzevir 1624 and Scrivener 1881 collated), both public domain from eBible.org. A link to the Leon Levy Dead Sea Scrolls Digital Library for pictures of the scrolls (link only).
- **NIV:** copyrighted (© Biblica), so it is not bundled or downloaded. Every verse has **Open in NIV ↗**, which opens it on BibleGateway; in Compare the Berean Standard Bible is the modern column. The cover prints NIV only once a licensed NIV is in the list.
- Add your own Bible files: PDF, XML (Zefania, OSIS, USFX), TXT, SPB, TSV, MyBible and unlocked MySword.

**Reading**
- **🏠 Home: the Bible cover** (computer and phone). BibleChat opens on a black leather-look Bible cover with a golden cross, "The Holy Bible" in gold (on the phone with the app language set to Deutsch: "Die Heilige Schrift"), gilt page edges and a red ribbon. Near the bottom, inside the gold border, the standard versions in small gold capitals: "KJV · ETHIOPIAN CANON · BSB". The line is made from the `COVER_VERSIONS` list and only names Bibles BibleChat really offers, so it switches to "… · NIV" by itself once a licensed NIV is added; the abbreviations stay the same in every app language. Under it: "Continue reading: John 3 · KJV". Tapping or clicking the cover opens the Bible there, with a short page-turn movement (none if the device asks for reduced motion). Home is the first tab on the phone and the first button (🏠 Home · 💬 Chat · 📖 Read) on the computer. In Read, **🏠 Home** (first button in the reading tools) closes the book: the cover swings shut and Home shows. A link or QR code to a verse or sermon list still goes straight to it. The cover is drawn in code (no picture file), so it is sharp on every screen and works offline.
- Book names in the Bible's own language ("1. Mose", "创世记", "Génesis"), on the phone and the computer; references can be typed that way too ("Römer 8:28").
- **App language flag** (phone, top bar): English, Deutsch, Español, Français, Português, 中文, Русский, 한국어. It changes buttons and menus only; the Bible text stays in the Bible you chose. Words live in `web/i18n.js`, one line per phrase.
- Read mode by book and chapter, flowing text or one verse per line, text size, dark mode, read-aloud chapter after chapter. Chapters are picked from a grid of numbers.
- **Verse button** (computer and phone, next to the chapter title): opens a grid of the chapter's verse numbers, big enough to tap on a phone. Tapping one closes the grid, scrolls straight to that verse and makes it glow gold for a moment. The grid shows the verses the chapter really has, so it fits every Bible, including the Ethiopian Canon.
- **← → arrows** at the top go back and forward to where you have been (chapters, search results, chats), like a browser's back button. On the computer, Alt+← and Alt+→ do the same.
- Scofield Reference Notes (1917) as highlighted words in the text; Easton's Bible Dictionary (1897) on names and places.
- Bookmarks; verse of the day.
- **🖼 Verse image:** pick one or more verses (＋ verse / − verse), a background or one of your own photos (it stays on the device), a size (square post, story, lock screen), text size and font, then **↗ Share** (Facebook, Instagram, WhatsApp, Messages…) or **⬇ Save image**.
- **🖼 Share as a picture (phone):** tap a verse → **🖼 Share as a picture**. Pick a background or one of your photos. The picture gets a small **▦ QR code** (tap the button to turn it off) that opens that verse in BibleChat. **↗ Share** sends the picture plus the verse link as text; where a phone can't share pictures, the picture is saved and the link copied. Whoever opens the link or scans the code sees "A friend shared a verse with you" and the verse stays highlighted in gold. Everything happens on the device: no upload, no server, no cost.

**Studying a verse** (click or tap a verse)
- **The original line:** the verse in Hebrew (Westminster Leningrad Codex) or Greek (Textus Receptus). The Hebrew Bible numbers some verses differently (Malachi 4:1 is Hebrew Malachi 3:19); BibleChat lines each King James verse up with the Hebrew verse that has its words and shows the Hebrew number when it differs. About 340 verses it couldn't place for certain (mostly Psalm titles and the first verse of a renumbered passage) show no line rather than a wrong one.
- **Open in NIV ↗** (BibleGateway) and **📚 Quoted or named in Scripture** (for example Jude 1:14 ↔ 1 Enoch 1:9, Joshua 10:13 ↔ Jasher 88:64).
- KJV word by word with Strong's numbers; each word opens the Hebrew or Greek word, pronunciation, meaning, KJV renderings and every verse that uses it.
- Letter by letter: Hebrew letters with name, sound, number, ancient picture meaning and Paleo-Hebrew form (YHWH: hand · behold · nail · behold); Greek letters with name, sound, number and Hebrew ancestor.
- Cross-references (OpenBible.info) with a book filter; Nave's topics; Matthew Henry's Concise Commentary; look-up box for `G25`, `H430` or a topic.

**📜 Study Paths** (computer and phone)
- A guided study: a starting question ("If the sun was made on Day 4, what was the light on Day 1?"), then steps through the text, then 5–10 questions and answers. Open it from **📜 Study Paths** on Home (under the cover) or **📜 Paths** in Read. Each path shows "Step 3 of 7" and remembers where you stopped.
- Six paths: **Light before the sun**, **Mist, not rain**, **The Name** (YHWH letter by letter in Paleo-Hebrew; the name chain Hoshea → Yehoshua → Yeshua → Iesous → Jesus as facts about the words, each with its verse and Strong's entry), **The heavens and the earth in the text's own words** (including 1 Enoch 72–82, the Book of the Luminaries), **Enoch and the Watchers** (Jude 14–15 side by side with 1 Enoch 1:9; 1 Enoch 6–16; Jubilees 4–5) and **The Word made flesh, the way, the truth, the light**.
- **Only the truth.** Each step shows the verses in your Bible (a verse your Bible doesn't have comes from the Bible that does, and says so). It shows every main verse on the topic, including the ones that seem to point the other way (Isaiah 45:7 "I form the light" next to 1 John 1:5 "God is light"; Romans 3:28 next to 1 John 2:4). The path asks; you decide. BibleChat gives no verdict.
- **⇄ Compare**: the same verses in the King James, the Ethiopian Canon and the Berean Standard Bible side by side, with the words that differ highlighted. The NIV is copyrighted, so each passage has an **Open in NIV ↗** link to BibleGateway.
- **🔎 Look closer**: the Strong's words of the step (Hebrew/Greek, meaning, how often they occur in the whole Bible and in this path, every verse that uses them, letter by letter with Paleo-Hebrew) and the strongest cross-references (OpenBible.info votes).
- **📝 Text and notes**: Scofield (1917) and Matthew Henry's notes on the verses, always under the heading "Commentary (Scofield, 1917)" or "Commentary (Matthew Henry, Concise)", in a grey box apart from the text, with "The notes of a man, not Scripture".
- **What do you see?**: a box for your own notes on each step, kept on the device.
- **Questions and answers**: find the verse, multiple choice, fill in the word from the verse, which translation says this. The answer is always the verse itself: it shows the reference and the full text. Each path has more questions than it shows; the strongest come first, and **Why this question?** says why ("45 cross-references point here", "The Hebrew word 'ôr (H216) is in 13 verses of this path", "Translations differ here", "Quoted in Jude 1:14-15"). **More questions** shows the rest. The score stays on the device. On the phone, an option (off unless ticked) puts questions close to what you searched before first, using the meaning search on the phone.
- **📜 Make a study path** under a chat answer (computer) or search answer (phone): a path from that answer's verses, with their Hebrew/Greek words, cross-references and "find the verse" questions. Nothing written by AI goes in as Scripture.
- **↗ Share** a path by link or QR code; the link opens the path on the phone version.
- **📚 Quoted or named in Scripture** (in Study Paths): verses that quote or name another writing, each with its source and whether the writing survives: Jude 14–15 and 1 Enoch 1:9 (in BibleChat), the Book of Jasher (Joshua 10:13, 2 Samuel 1:18; an 1840 English book of that name exists, and scholars dispute whether it is the same), the Book of the Wars of the LORD (Numbers 21:14, lost), Jannes and Jambres (2 Timothy 3:8), the books of Nathan, Gad, Ahijah and Iddo (lost), the poets Paul quotes (Acts 17:28, Titus 1:12).
- New paths: write `packaging/paths/<id>.json`, run `python packaging/build_paths.py`. The build refuses a path with a wrong reference, an answer outside the path, a quoted word that isn't in the verse or unlabelled commentary.

**Search and chat**
- Plain questions or references (`Daniel 7:25`, `1 Cor 13:4-7`, `Psalm 23`); topic answers for concept questions (fallen angels, God's name).
- **Search by meaning and by the original word** (computer and phone, English Bibles): "love is patient" finds 1 Corinthians 13:4 in the King James ("Charity suffereth long"), "sea monsters" finds Genesis 1:21 ("great whales", Hebrew *tannin*), "do not worry about tomorrow" finds Matthew 6:34. Under each verse, **Found by** says why: *matched word*, *matched by meaning*, or the Hebrew/Greek word, e.g. "Hebrew word tannin (H8577): sea monster, dragon, serpent, whale". Everything runs on the device; nothing is sent anywhere. Nonsense words are not guessed at.
- Cross-reference questions, including between whole books ("Daniel to Revelation cross references"), on the phone too.
- Strong's numbers in chat; several Bibles side by side, only those in the question's language; typing slips corrected and shown.
- Optional private AI explanation on the computer. On both versions, **✨ Ask AI** opens Claude, ChatGPT, Gemini, Grok or Perplexity with the verse (or the chat answer's verses) and question filled in.
- Voice questions on the computer.

**For churches**
- A church types its name and adds its logo (a picture, or the logo's web address). The name and logo then show at the top of BibleChat.
- Clicking the church name shows a QR code card (logo, name, QR code) to save, print or share. The same card sits at the top of Love Donations, above the Cash App code. Closing the church form with ✕ keeps what was typed. Scanning it opens the free phone version with the church's name at the top; with a logo web address, the logo shows there too.

- **Sermon list:** the pastor adds verses (📋 Add to sermon), gives the list a title and shows it full screen with a QR code. People scan it to follow along on their phones; the list stays on their phone to take home (📋 in Read).

**For AI apps: the BibleChat connector**
- An MCP server (`bibleask/mcp_server.py`) that lets Claude and other AI apps look up passages, search, study a verse (Strong's, topics, cross-references, Matthew Henry), Strong's numbers, Nave's topics, cross-references between books and Easton's dictionary. Every answer quotes real verses and credits BibleChat.
- Runs on the local computer/device for Claude Desktop or Claude Code (built-in KJV plus the Bibles added in BibleChat), or as a public web service for the Claude directory. See [connector/README.md](connector/README.md).

**Sharing and practical**
- Share a verse by text or email; the link opens straight to that verse.
- Love Donations button with Cash App QR code.
- **💡 Suggest a feature** (Love tab on the phone, Love Donations on the computer): sends the idea to Hans by email, or posts it on GitHub.
- Works offline (phone after first open; computer except downloads and the daily update check). On a weak phone connection a Bible download is tried 3 times; if it still fails, the app says so and offers Try again, the King James Version or another Bible. Windows icon, Linux menu entry, Linux build for older processors.

## 5. How BibleChat compares with other Bible apps

Checked October 2026 against each app's store page or published reviews. "Not listed" means the source didn't mention it, not that the app lacks it. Prices and features change; check the sources before quoting them.

| | BibleChat | YouVersion | Blue Letter Bible | e-Sword | Logos | bible.ai |
|---|---|---|---|---|---|---|
| Price | Free, all features | Free | Free | Free core; modern translations and many books are paid add-ons | Free basic version; main libraries are paid packages or subscription | Free download; Plus $12.99/month or $89.99/year |
| Account | None | Optional (for sync) | Not stated | None | Not stated | Not stated |
| Data collection | None; stays on the device | App Store lists data linked to you (contact info, search history) and usage data for advertising | Not checked | Stays on the computer | Not checked | App Store lists contact info for marketing |
| AI chat | Yes; answers show real verses first, AI is optional and runs privately on the computer | Not listed | Not listed | No | Reviewers mention a new AI integration | Yes; core feature, AI model and checking not disclosed |
| Strong's / original languages | Yes, plus letter by letter and Paleo-Hebrew | Not listed | Yes, plus interlinear | Yes | Yes, plus interlinear | Not listed |
| Commentaries / dictionary | Matthew Henry, Scofield, Nave's, Easton's | Reading plans and devotionals | Matthew Henry, Guzik, Chuck Smith, TSK | Matthew Henry, Gill, Clarke, JFB, Easton's, Smith's | Very large paid library | Devotionals |
| Ethiopian canon (Enoch, Jubilees), Septuagint | Yes | Not listed | Not listed | Not listed | Not checked | Not listed |
| Load your own Bible files | Yes (PDF, XML, MySword, MyBible…) | Not listed | Not listed | e-Sword modules | Not listed | Not listed |
| Offline | Yes | Some versions | Mainly KJV | Yes | Downloaded books | Not stated |
| Platforms | Phone browser, Windows, Mac, Linux | iPhone, Android, web | iPhone, Android, Mac, web | Windows, Mac, iPad; no official Android | Desktop, web, phones | iPhone only |
| Open source | Yes (Apache 2.0) | No | No | No | No | No |

**In short:** YouVersion leads on translations, reading plans and community; Logos on depth of paid scholarly libraries; Blue Letter Bible and e-Sword on free classic study tools. BibleChat is the one that combines free study tools, a chat that always quotes the real verses, the Ethiopian canon and Septuagint, your own Bible files, no account and open source code.

Sources: [YouVersion on the App Store](https://apps.apple.com/us/app/bible/id282935706) · [bible.ai on the App Store](https://apps.apple.com/us/app/bible-ai-chat-about-anything/id6739915445) · [Logos on Capterra](https://www.capterra.com/p/275095/Logos/) · [Blue Letter Bible review, Bible in a Year](https://bibleinyear.com/blog/blue-letter-bible-app) (written by a competing app maker) · [e-Sword, Learn of Christ](https://learnofchrist.com/resources/e-sword)

## 6. Sources and licenses of the data

- Bibles: open-bibles collection (public domain / CC BY / CC BY-SA, shown per Bible); eBible.org (Septuagint public domain; Amharic NT free non-commercial use with notice).
- Ethiopian Canon: assembled from the World English Bible, R. H. Charles (1 Enoch, Jubilees), Morfill/Charles (2 Enoch) and the Ante-Nicene Fathers (1 Clement), all public domain.
- Strong's, KJV with Strong's numbers, Nave's, Scofield 1917, Matthew Henry's Concise (CrossWire): public domain.
- Easton's 1897: public domain (dataset by NEUU, CC BY 4.0). Cross-references: OpenBible.info, CC BY.
- Meaning search: BGE-small-en v1.5 by BAAI (MIT license, stored with 8-bit weights); verse fingerprints from the Berean Standard Bible (public domain). Numpy (BSD) runs it on the computer.
- Book of Jasher: the 1840 English translation (public domain), as transcribed by the Scrollmapper project. Westminster Leningrad Codex and Greek Textus Receptus: public domain, from eBible.org (license pages checked October 2026).
- Study Paths and "Quoted or named in Scripture": written and hand-checked for BibleChat (Apache 2.0, like the code); they hold references and questions only. The verses come from the Bibles above, the words from Strong's, the cross-references from OpenBible.info, the notes from Scofield and Matthew Henry.
- Hebrew letter pictures: as taught by Jeff A. Benner, Ancient Hebrew Research Center (labelled in the app). Paleo-Hebrew font: Noto Sans Phoenician (OFL). QR codes: qrcode-generator by Kazuhiko Arase (MIT). Book names in 30 languages: The SWORD Project locale files (CrossWire), plus the names printed in each Bible file.

## 7. Open items

- Test the Windows and Mac downloads on real machines.
- Share as a picture: test on a real iPhone and Android (some messaging apps drop the text that rides along with a picture; the QR code on the picture covers that). Bring the same QR code and link to the computer version's picture maker.
- Not possible as a web page: lock-screen widgets and daily reminders (need a store app); built-in AI on the phone (needs a paid server or a large on-phone model).
- **NIV license.** Not bundled, not downloaded, not scraped. A request to Biblica for a free, open-source, non-commercial app is drafted (it says openly that BibleChat has a chat and optional on-device AI, which Biblica licenses separately). API.Bible offers the NIV, but its terms (updated 3 September 2026) require web apps to use its usage tracking (FUMS), a visible link to api.bible and a refresh of stored text every 30 days; the tracking breaks BibleChat's "nothing leaves the device" rule, so it isn't used. Until a license comes: "Open in NIV ↗" links and the BSB in Compare.
- Ethiopian Canon still missing Meqabyan I–III and 4 Baruch. The Scrollmapper 4 Baruch reads like a modern translation whose license isn't stated, so it was left out; a public-domain English translation still has to be found. No freely licensed Ge'ez text found yet.
- **Dead Sea Scrolls.** The ETCBC/Abegg Hebrew transcriptions are CC BY-NC 4.0 (checked October 2026). That could work as a separate optional download with its license shown, but Hans should decide first whether the Love Donations button fits "non-commercial". The "Compare Isaiah" view (Great Isaiah Scroll 1QIsa^a next to the Masoretic text and the KJV) also still has to be built from their Text-Fabric data. The Leon Levy library is linked (pictures, link only).
- **Not built yet:** Josephus (Whiston) and the Didache and Apostolic Fathers (Lightfoot). Both translations are old enough to be public domain, but a clean public-domain transcription with chapter and section numbers still has to be picked and converted.
- **Greek text:** the Textus Receptus from eBible.org is a collation of Stephanus 1550, Elzevir 1624 and Scrivener 1881, not exactly Scrivener's 1894 edition. A clean Scrivener 1894 file would match the brief better.
- Septuagint on the computer's Study Paths: Jeremiah 25–51 (another chapter order) is only gathered within two chapters of the King James number.
- Church logos picked from a device show only on that device and on the QR card; members see the logo only when the church gives a logo web address. Hosting church logos for them would need a server.
- Connector: choose a host for the public version (Render, Fly.io, Railway or Hugging Face Spaces; needs a free account), add its HTTPS address in Claude as a custom connector, test every tool, then submit at claude.ai/directory/manage (paid Claude plan).
- App language flag: the computer version's menus are still English only (phone has 8 languages). Book names fall back to English for Albanian, Maori, Swahili, Tagalog and Cherokee (no name list found).
- German Luther 1912 (and the Luther 1545 and eBible copies checked) has only the 66 books: no Apocrypha such as Weisheit Salomos. A free German text with the Apocrypha still has to be found.
- Meaning search: English only, 66 books (fingerprints of the Apocrypha, Enoch and Jubilees could be added from the World English Bible, about 2.5 MB more); test speed on a real older phone (one search took under 1 second on a 2012 Intel i7 without AVX2, in Chrome and in Python); the phone's "Found by" words are translated, but the Hebrew/Greek meanings stay English; the BibleChat connector (MCP) still uses word search only; the computer's first question after starting waits 5–10 seconds while the data loads.
- Study Paths: the paths' own questions and facts are English only (buttons and headings follow the app language on the phone). The option "questions close to what I asked before" is on the phone only; the computer's meaning search runs in Python and isn't wired to it yet. The Name: the Latin/1611 spelling "Iesus" in the name chain needs a public-domain source file (the Clementine Vulgate in Get free Bibles prints "Jesus"/"Jesum"; a transcription of the 1611 King James would show "Iesus"); until then the chain shows Hebrew, Greek and English with their sources.
- Non-English search works but is rougher than English. Code-signing would remove the first-launch warnings (yearly cost).

---

# User guide

## How to use it

1. Open **BibleChat**. Your browser opens on the **Home** page, a Bible cover with a golden cross; click the cover to start reading, or press **💬 Chat** to ask a question. (Closing the tab stops the app after about 3 minutes, or press **Quit** in the sidebar.)
2. **⬇ Get free Bibles** in the sidebar opens a list of 51 public-domain and freely licensed Bibles (KJV, ASV, World English Bible, Berean Standard Bible, Douay-Rheims, Luther 1912, Reina-Valera 1909 and many other languages, from the [open-bibles](https://github.com/seven1m/open-bibles) collection, plus an **Ethiopian Canon** of 84 books in public-domain English, with 1 Enoch, Jubilees, 2 Enoch and 1 Clement, and the 1962 **Amharic New Testament**). Click **Download** and it's added. Or use **Add Bible from a file** (or drag a file onto the page): PDF, XML or TXT. A big PDF takes 10–60 seconds the first time. After that it is instant.
3. Tick the Bibles you want searched. With several ticked, a reference such as *Daniel 7:25* is shown in each one side by side.
4. Type a question and press **Enter**. The verses appear first, with your words highlighted, then the AI's explanation.
5. Optional: under **AI helper** click **Get / load** once. It downloads a model (Bible Assistant 4B is about 2.7 GB; Qwen2.5 1.5B is about 1.1 GB and faster). Untick **Explain with AI** to see verses only.

You can type references: `Daniel 7:25`, `1 Cor 13:4-7`, `Psalm 23`, `Rev 22`.

**Reading a whole chapter.** Press **📖 Read** at the top of the sidebar. Pick a Bible, click a book to show its chapters, and click a chapter. To jump to a verse, press **Verse** next to the chapter title and tap its number (on the phone: tap the chapter name to change chapter, **Verse** to pick a verse). Use **‹ Prev / Next ›** (or the ← → keys) to turn chapters, **🔊 Listen** to have it read aloud (it carries on into the next chapter until you press Stop), **¶** to switch between one verse per line and flowing text, and **A− / A+** for text size. **💬 Ask** takes you back to Chat with that chapter filled in. In a chat answer, click a verse reference to open it in the reader. BibleChat remembers where you stopped.

**Bookmarks, verse of the day, Hebrew letters.** Click a verse, then **🔖 Bookmark this verse**; the 🔖 button above the text lists them. The chat's start page shows a **verse of the day** with a button that makes a lock-screen picture of it. In a Hebrew Strong's entry, click the Hebrew word to go **letter by letter**: each letter's name, sound, number and ancient picture (e.g. יהוה: hand · behold · nail · behold). On the phone, tap a verse for 🔖 Bookmark, ✨ Ask AI (opens Claude, ChatGPT, Gemini, Grok or Perplexity with the verse filled in, using your own account) and 🖼 Lock-screen picture.

**Home.** **🏠 Home** (first tab on the phone, first button in the sidebar on the computer) shows the Bible cover. Tap or click it to open the Bible where you stopped. While reading, **🏠 Home** in the reading tools closes the book again.

**📜 Study Paths.** Press **📜 Study Paths** on Home (under the cover) or **📜 Paths** in Read, and pick a path. Read the starting question, then go step by step: read the verses, open **⇄ Compare** to see the King James, the Ethiopian Canon and the Berean Standard Bible side by side, **🔎 Look closer** for the Hebrew/Greek words and the strongest cross-references, and **📝 Text and notes** for what Scofield and Matthew Henry wrote (kept apart from the text, so you can judge whether a note matches it). Write what you notice in **What do you see?**. At the end, **Questions and answers**: the answer to every question is a verse. To make your own path, ask something in Chat (computer) or Search (phone) and press **📜 Make a study path** under the answer. **↗** at the top shares a path by link or QR code. **📚 Quoted or named in Scripture** (at the bottom of the list of paths) shows the writings the Bible quotes or names, and which are lost.

**Language.** Tap the flag at the top of the phone version to switch the app's buttons and menus to Deutsch, Español, Français, Português, 中文, Русский or 한국어. Book names always follow the Bible you are reading.

**Back and forward.** The **←** and **→** arrows at the top take you back to where you were (a chapter, a search, a chat) and forward again. On a computer, **Alt+←** and **Alt+→** work too.

**For churches.** Press **⛪ Church** (computer) or **Love → Brand BibleChat for your church** (phone). Type the church's name and pick its logo. The name and logo show at the top of BibleChat; click them to get a QR code card to save, print in the bulletin or show on the screen. People who scan it open the free phone version with your church's name at the top. If you also give the logo's web address (starting with https://), they see the logo too; a logo picked from your device stays on that device and on the QR card.

**Sermon list (for pastors).** Click a verse, then **📋 Add to sermon**. Open the list with **📋** (Read mode), give it a title, move verses up or down, then press **📺 Show with QR code**. The verses and a big QR code fill the screen; people scan it and get the same verses on their phone, saved there to take home.

**Make an image to post.** Tap a verse, then **🖼 Image** (phone) or **🖼 Make an image to post** (computer). Add the next verses with **＋ verse**, pick a background or **📷** one of your photos, choose Post, Story or Lock screen, then **↗ Share** or **⬇ Save image**. On a phone, Share → Save Image puts it in your photos.

**Ask an AI.** Click a verse, then **✨ Ask an AI**, or press **✨ Ask another AI** under a chat answer. Pick Claude, ChatGPT, Gemini, Grok or Perplexity; it opens with the verses and question filled in, using your own account there.

**Suggest a feature.** In **Love Donations** (computer) or the **Love** tab (phone), type your idea and press **✉ Send by email** or **Post on GitHub**.

**Notes in the text.** In Read mode, words with a yellow highlight and a small letter have a **Scofield Reference note** (1917): click the word or the letter to read it. Names and places with a dotted underline (Babylon, Michael, Patmos) open their entry in **Easton's Bible Dictionary**.

**Studying a verse (Strong's and Nave's).** In Read mode, click any verse. A panel shows the verse word by word with **Strong's numbers**. Click a word to see the original Hebrew or Greek word, how to say it, what it means, how the KJV translates it, and **every verse that uses it**. Below that are the verse's **cross-references** (from OpenBible.info, strongest first, with a book filter, so you can show only the links into Revelation, say) its **topics from Nave's Topical Bible**, and **Matthew Henry's Commentary** on the passage. Click a topic to see all of its verses. The box at the top looks up a number (`G25`, `H430`) or a topic (`prayer`). In Chat, typing a Strong's number such as `G26` lists the verses that use that word; `cross references Daniel 7:13` lists that verse's cross-references, and `Daniel to Revelation cross references` lists every link between two books. The Strong's numbers belong to the King James wording, so the word-by-word view always shows the KJV; the verse lists use the Bible you are reading.

The chat only talks about the Bibles you added. If nothing matches, it says so instead of guessing, and the AI is not asked.

**Supported Bible files**

| Format | Notes |
|---|---|
| PDF | Works best with a layout like the Ethiopian Bible PDF: book title, chapter number on its own line, verses numbered inline. Other layouts are still searchable as plain passages. |
| XML | Zefania, OSIS and USFX XML (read exactly). |
| TXT | Project Gutenberg style (`1:1 In the beginning…` under a book title), or lines like `Genesis 1:1 In the beginning…`. |
| SPB | SoftProjector Bible files. |
| TSV | Six tab-separated columns: book name, abbreviation, book number, chapter, verse, text. |
| SQLite3 | MyBible Bible modules (`.SQLite3`). Strong's numbers and footnote markers are left out. |
| .bbl.mybible | MySword Bibles that aren't locked. Locked (encrypted) ones, such as The Scriptures 2009, only open inside MySword. |

Project Gutenberg's well-known 1455 "Gutenberg Bible" is in Latin, so the English AI can't explain it. Use the Gutenberg *King James* text instead (search "King James Bible" at gutenberg.org and save the "Plain Text UTF-8" file).

---

## On a phone: BibleChat for the web

**[beaugrand.github.io/BibleChat-voice](https://beaugrand.github.io/BibleChat-voice/)** opens BibleChat in any phone or computer browser. No sign-up, nothing to install. It has reading, search (same method as the app), the 48 free Bibles, read-aloud with the phone's own voice, links to any verse, Strong's Hebrew/Greek words and Nave's topics (tap a verse, then **Study it**), and Love Donations. Bibles you open are kept on the phone, so it also works offline. **Share → Add to Home Screen** keeps it like an app.

The built-in AI explanations and voice questions need the computer app, because they run an AI model on your own machine. On the phone, **✨ Ask AI** hands the verse to an AI site of your choice instead.

The site is built from the `web/` folder by **Publish phone version (GitHub Pages)** whenever it changes. One-time setup: **Settings → Pages → Source: GitHub Actions**.

## Getting the app

**Download it free from the [Releases page](https://github.com/beaugrand/biblechat-voice/releases/latest).** End users need **nothing installed**: no Python, no setup.

| Computer | File | How to open it |
|---|---|---|
| Windows | `BibleChat-Windows.zip` | Unzip, open `BibleChat\BibleChat.exe`. A **BibleChat** icon then appears on the desktop and in the Start menu; use that from now on. |
| Mac (Apple Silicon, M1 and newer) | `BibleChat-Mac.zip` | Unzip, drag `BibleChat.app` to Applications |
| Linux | `BibleChat-Linux.tar.gz` | Unpack, run `./install.sh`, open BibleChat from the menu |
| Linux, older processor (no AVX2) | `BibleChat-Linux-OldCPU.tar.gz` | Same steps. Use this if the AI helper says your processor is too old. Slower. |

**First-launch warnings** (normal until the app is code-signed, which costs money at Microsoft and Apple):
- Windows: "Windows protected your PC" → **More info** → **Run anyway**.
- Mac: right-click the app → **Open** → **Open**. If it says "damaged", run `xattr -cr /Applications/BibleChat.app` in Terminal.
- The app has no window of its own. After you open it, give it a few seconds and your browser opens by itself. If your browser doesn't, go to `http://127.0.0.1:8765`.

### How a new release is made

A Windows program can only be built on Windows and a Mac program only on a Mac, so GitHub builds them.

1. Save the changes on GitHub (the `main` branch).
2. Open **Actions** → **Build BibleChat (Windows + Mac + Linux)** → **Run workflow**, type the new version (such as `v1.0.1`) and press **Run workflow**. (Pushing a `v…` tag works too.)
3. About 15–25 minutes later the four download files are attached to the release with that tag.

To try a build without publishing, open **Actions** → **Build BibleChat (Windows + Mac + Linux)** → **Run workflow**; the files appear under **Artifacts** at the bottom of the finished run.

The separate **Build Windows app** workflow bakes the AI models into a Windows app for personal use. It is manual only and not part of public releases, because some bundled models (such as the Pocket TTS voice) have their own terms.

### On your own Linux machine

Use `BibleChat-Linux.tar.gz` as above. It needs Linux Mint 22 or newer (glibc 2.38+); the copy built by GitHub works on Mint 21 and newer. To tinker with the code instead: `sudo apt install python3-venv` once, then `./run_from_source_linux.sh`.

---

## What to expect

- **The verses shown are always real text from your files.** The AI never supplies verses. It only explains the ones found.
- **Older processors (no AVX2, roughly pre-2014):** BibleChat shows a yellow box in the sidebar. Searching, reading and Listen still work; only the AI explanation is off. When BibleChat runs from source code, the box has a **Rebuild the AI helper** button that recompiles the AI engine for your processor in the background (10–40 minutes; needs `sudo apt install build-essential` once). Then Quit and reopen. The packaged app uses the Linux-OldCPU download instead.
- **Small AI models make mistakes.** Check the explanation against the verses above it.
- **Search looks at words, the original Hebrew/Greek words and meaning together** (English Bibles). Under each verse, "Found by" says which of the three found it. Meaning search compares your question with the meaning of each verse of the Berean Standard Bible and then shows that verse from your Bible, so it works for the 66 books (not yet the Apocrypha, Enoch or Jubilees) and only in English. On the phone it needs a one-time 46 MB download the first time you search. In other languages search is by words only: different Bibles word things differently (the Ethiopian text says "rebellion" where the King James says "falling away"), so try another phrase or tick more than one Bible.
- **PDF reading was tuned on the Ethiopian Orthodox Bible PDF** (89 books, about 40,000 verses). A few verse numbers in some books (Mark, Acts, Sirach) may be off.
- **The Bible Assistant model was trained on the 66 Protestant books** with an evangelical/Reformed lean. It reads whatever verses it is handed, including Enoch and Jubilees, but its explanations of those may carry that slant.
- **Model licenses differ.** Bible Assistant 4B and Qwen2.5 1.5B are Apache-2.0; Llama 3.2 uses Meta's community license; Qwen2.5 3B is research-only. Check the license of any model you add.

## Where things are stored

| What | Windows | Mac | Linux |
|---|---|---|---|
| Bibles, AI models, settings | `%APPDATA%\BibleAsk` | `~/Library/Application Support/BibleAsk` | `~/.local/share/BibleAsk` |

Your chat history lives in your browser. Delete the folder above to reset the Bibles and models.

## For developers

```bash
python -m unittest discover -s tests -v     # 110 tests (one runs the phone search with Node.js if it is installed)
python -m bibleask.mcp_server               # the connector, for Claude Desktop / Claude Code
./run_from_source_linux.sh                  # run from source on Linux
```

Read [AGENTS.md](AGENTS.md) before changing anything: it lists the rules for keeping this README and the handover current.

## License

BibleChat is free and open source under the [Apache License 2.0](LICENSE): anyone may use, copy, change and share it, as long as they keep the [NOTICE](NOTICE) file with Hans W. Beaugrand's credit and say what they changed. Please keep the About credit and the Love Donations button in the app. Bibles and study data keep their own licenses, listed in **Get free Bibles** and in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Credits

The reading view and the SPB, TSV and MyBible readers follow **Bible** by Lugsole
(<https://github.com/Lugsole/net.lugsole.bible_gui>), used under the MIT License:

> Copyright (c) 2020 Lugsole. Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
