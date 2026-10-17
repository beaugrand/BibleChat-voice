# BibleChat

**A free, open-source Bible reader, study tool and chat.** It runs privately on a phone (no install) and on Windows, Mac and Linux. Answers always show the real verses first; the optional AI only explains them and never supplies Scripture.

- Phone and browser version: **[beaugrand.github.io/BibleChat-voice](https://beaugrand.github.io/BibleChat-voice/)**
- Computer downloads: **[Releases page](https://github.com/beaugrand/BibleChat-voice/releases/latest)**
- Made by Hans W. Beaugrand · Love Donations: Cash App **$HansBeaugrand**

> **For AI assistants and developers: start here.** This README is the project's handover. It says where everything lives, how the software works, the full feature list and how BibleChat compares with other Bible apps. **Every change to the app must update this file in the same commit** (features, counts, code map, version, open items). See [AGENTS.md](AGENTS.md).

---

## Status

- Published download: **v1.0.1**. Version number lives in `bibleask/__init__.py`.
- Changes since v1.0.1, already live on the phone version and in `main`, reach computer users with the next release (v1.0.2): Strong's study, Nave's topics, cross-references, Scofield notes, Matthew Henry, Easton's dictionary, Hebrew/Greek letter by letter with Paleo-Hebrew, bookmarks, verse of the day, Septuagint, Ethiopian canon, update notice, chat fixes.
- Automatic tests: 68 (run `python -m unittest discover -s tests`).

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
- Bibles are read from many file formats and saved as simple JSON in the data folder. Search uses word ranking (BM25) plus topics, cross-references and Strong's numbers.
- The optional AI runs on the device itself (llama.cpp) with a model the person picks: Bible Assistant 4B, Qwen2.5 1.5B/3B or Llama 3.2 1B/3B. It only explains verses BibleChat found.
- Read-aloud uses the system voices in the Bible's own language.
- On Windows it adds a desktop and Start-menu icon on first launch. Once a day it asks GitHub for a newer version and shows an "update available" box; the version is shown under Quit.

**Phone version**
- A plain web page (`web/index.html`) hosted free on GitHub Pages. No server, no account; everything runs in the phone's browser.
- Bibles and study data are split into small files that load when needed; a service worker (`web/sw.js`) keeps them for offline use. "Add to Home Screen" makes it look like an app.
- Bookmarks and settings stay on the phone.

**Building and releasing**
- GitHub Actions does all building. **Build BibleChat** (`build.yml`) makes the four downloads and runs the tests; **Publish phone version** (`pages.yml`) rebuilds the phone site whenever the code changes.
- To release: set `__version__` in `bibleask/__init__.py` (e.g. `1.0.2`), then run **Build BibleChat** with the same version (`v1.0.2`). The release refuses to publish if the two differ.
- Windows and Mac downloads are not code-signed yet, so the first launch shows a warning.

## 3. Code map

| File or folder | What it does |
|---|---|
| `bibleask/server.py` | Local web server and all its addresses (chat, chapters, study, bookmarks, downloads, updates) |
| `bibleask/web/index.html` | The whole computer app screen (chat, Read mode, study panel) |
| `bibleask/loaders.py` | Reads Bible files: PDF, Zefania/OSIS/USFX XML, TXT, SPB, TSV, MyBible, MySword |
| `bibleask/library.py` | Keeps the Bibles and serves chapters to the reader |
| `bibleask/search.py`, `chat.py` | Search, references, languages, spelling help; building each chat answer |
| `bibleask/study.py`, `strongs.py`, `topics.py`, `xref.py`, `scofield.py`, `henry_easton.py` | Study tools: Strong's, Nave's topics, cross-references, Scofield, Matthew Henry, Easton's |
| `bibleask/catalog.py` | The list in "Get free Bibles" |
| `bibleask/llm.py`, `stt.py`, `updates.py`, `shortcuts.py`, `storage.py` | Local AI, voice input, update check, Windows icon, data folder and settings |
| `bibleask/data/` | Bundled study data (Strong's, Nave's, cross-references, Scofield, Matthew Henry, Easton's) |
| `bibles/` | The Ethiopian Canon file BibleChat itself hosts |
| `web/` | Phone version (`index.html`, `sw.js`) and the scripts that build its data (`build_data.py`, `build_study.py`) |
| `packaging/` | Scripts that rebuild each data set from its public-domain source; Windows icon; Linux installer |
| `tests/` | Automatic tests |
| `.github/workflows/` | `build.yml` (downloads and releases), `pages.yml` (phone site), `build-windows.yml` (manual, personal build) |
| `LICENSE`, `THIRD_PARTY_NOTICES.md` | MIT license; credits and licenses of every source |

`bibleask/gui.py` is the older Tkinter window (BibleAsk), no longer built.

## 4. All features

**Bibles**
- 48 free Bibles in 32 languages, one-click download (KJV, ASV, WEB, BSB, Darby, Douay-Rheims, Young's, Luther 1912, Reina-Valera 1909, Chinese Union and more).
- Ethiopian Canon in public-domain English: 84 books in Ethiopian order, including 1 Enoch, Jubilees, 2 Enoch and 1 Clement.
- Septuagint in English: Brenton (1851) and LXX2012, with the Apocrypha. Amharic New Testament (1962).
- Add your own Bible files: PDF, XML (Zefania, OSIS, USFX), TXT, SPB, TSV, MyBible and unlocked MySword.

**Reading**
- Read mode by book and chapter, flowing text or one verse per line, text size, dark mode, read-aloud chapter after chapter.
- Scofield Reference Notes (1917) as highlighted words in the text; Easton's Bible Dictionary (1897) on names and places.
- Bookmarks; verse of the day with a lock-screen picture.

**Studying a verse** (click or tap a verse)
- KJV word by word with Strong's numbers; each word opens the Hebrew or Greek word, pronunciation, meaning, KJV renderings and every verse that uses it.
- Letter by letter: Hebrew letters with name, sound, number, ancient picture meaning and Paleo-Hebrew form (YHWH: hand · behold · nail · behold); Greek letters with name, sound, number and Hebrew ancestor.
- Cross-references (OpenBible.info) with a book filter; Nave's topics; Matthew Henry's Concise Commentary; look-up box for `G25`, `H430` or a topic.

**Search and chat**
- Plain questions or references (`Daniel 7:25`, `1 Cor 13:4-7`, `Psalm 23`); topic answers for concept questions (fallen angels, God's name).
- Cross-reference questions, including between whole books ("Daniel to Revelation cross references"), on the phone too.
- Strong's numbers in chat; several Bibles side by side, only those in the question's language; typing slips corrected and shown.
- Optional private AI explanation on the computer; on the phone, **Ask AI** opens Claude, ChatGPT, Gemini, Grok or Perplexity with the verse filled in.
- Voice questions on the computer.

**Sharing and practical**
- Share a verse by text or email; the link opens straight to that verse.
- Love Donations button with Cash App QR code.
- Works offline (phone after first open; computer except downloads and the daily update check). Windows icon, Linux menu entry, Linux build for older processors.

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
| Open source | Yes (MIT) | No | No | No | No | No |

**In short:** YouVersion leads on translations, reading plans and community; Logos on depth of paid scholarly libraries; Blue Letter Bible and e-Sword on free classic study tools. BibleChat is the one that combines free study tools, a chat that always quotes the real verses, the Ethiopian canon and Septuagint, your own Bible files, no account and open source code.

Sources: [YouVersion on the App Store](https://apps.apple.com/us/app/bible/id282935706) · [bible.ai on the App Store](https://apps.apple.com/us/app/bible-ai-chat-about-anything/id6739915445) · [Logos on Capterra](https://www.capterra.com/p/275095/Logos/) · [Blue Letter Bible review, Bible in a Year](https://bibleinyear.com/blog/blue-letter-bible-app) (written by a competing app maker) · [e-Sword, Learn of Christ](https://learnofchrist.com/resources/e-sword)

## 6. Sources and licenses of the data

- Bibles: open-bibles collection (public domain / CC BY / CC BY-SA, shown per Bible); eBible.org (Septuagint public domain; Amharic NT free non-commercial use with notice).
- Ethiopian Canon: assembled from the World English Bible, R. H. Charles (1 Enoch, Jubilees), Morfill/Charles (2 Enoch) and the Ante-Nicene Fathers (1 Clement), all public domain.
- Strong's, KJV with Strong's numbers, Nave's, Scofield 1917, Matthew Henry's Concise (CrossWire): public domain.
- Easton's 1897: public domain (dataset by NEUU, CC BY 4.0). Cross-references: OpenBible.info, CC BY.
- Hebrew letter pictures: as taught by Jeff A. Benner, Ancient Hebrew Research Center (labelled in the app). Paleo-Hebrew font: Noto Sans Phoenician (OFL).

## 7. Open items

- Release v1.0.2 so the computer downloads get everything since v1.0.1.
- Test the Windows and Mac downloads on real machines.
- Not possible as a web page: lock-screen widgets and daily reminders (need a store app); built-in AI on the phone (needs a paid server or a large on-phone model).
- Ethiopian Canon still missing Meqabyan I–III and 4 Baruch (no public-domain English found); no freely licensed Ge'ez text found.
- Non-English search works but is rougher than English. Code-signing would remove the first-launch warnings (yearly cost).

---

# User guide

## How to use it

1. Open **BibleChat**. Your browser opens the chat page. (Closing the tab stops the app after about 3 minutes, or press **Quit** in the sidebar.)
2. **⬇ Get free Bibles** in the sidebar opens a list of 48 public-domain and freely licensed Bibles (KJV, ASV, World English Bible, Berean Standard Bible, Douay-Rheims, Luther 1912, Reina-Valera 1909 and many other languages, from the [open-bibles](https://github.com/seven1m/open-bibles) collection, plus an **Ethiopian Canon** of 84 books in public-domain English, with 1 Enoch, Jubilees, 2 Enoch and 1 Clement, and the 1962 **Amharic New Testament**). Click **Download** and it's added. Or use **Add Bible from a file** (or drag a file onto the page): PDF, XML or TXT. A big PDF takes 10–60 seconds the first time. After that it is instant.
3. Tick the Bibles you want searched. With several ticked, a reference such as *Daniel 7:25* is shown in each one side by side.
4. Type a question and press **Enter**. The verses appear first, with your words highlighted, then the AI's explanation.
5. Optional: under **AI helper** click **Get / load** once. It downloads a model (Bible Assistant 4B is about 2.7 GB; Qwen2.5 1.5B is about 1.1 GB and faster). Untick **Explain with AI** to see verses only.

You can type references: `Daniel 7:25`, `1 Cor 13:4-7`, `Psalm 23`, `Rev 22`.

**Reading a whole chapter.** Press **📖 Read** at the top of the sidebar. Pick a Bible, click a book to show its chapters, and click a chapter. Use **‹ Prev / Next ›** (or the ← → keys) to turn chapters, **🔊 Listen** to have it read aloud (it carries on into the next chapter until you press Stop), **¶** to switch between one verse per line and flowing text, and **A− / A+** for text size. **💬 Ask** takes you back to Chat with that chapter filled in. In a chat answer, click a verse reference to open it in the reader. BibleChat remembers where you stopped.

**Bookmarks, verse of the day, Hebrew letters.** Click a verse, then **🔖 Bookmark this verse**; the 🔖 button above the text lists them. The chat's start page shows a **verse of the day** with a button that makes a lock-screen picture of it. In a Hebrew Strong's entry, click the Hebrew word to go **letter by letter**: each letter's name, sound, number and ancient picture (e.g. יהוה: hand · behold · nail · behold). On the phone, tap a verse for 🔖 Bookmark, ✨ Ask AI (opens Claude, ChatGPT, Gemini, Grok or Perplexity with the verse filled in, using your own account) and 🖼 Lock-screen picture.

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
- **Search is by keywords, not meaning.** "Where does it say a ruler would try to change times" works because the words overlap with the verse. Different Bibles word things differently (the Ethiopian text says "rebellion" where the King James says "falling away"), so try another phrase or tick more than one Bible.
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
python -m unittest discover -s tests -v     # 68 tests
./run_from_source_linux.sh                  # run from source on Linux
```

Read [AGENTS.md](AGENTS.md) before changing anything: it lists the rules for keeping this README and the handover current.

## License

BibleChat is free and open source under the [MIT License](LICENSE): anyone may use, copy, change and share it. Bibles and study data keep their own licenses, listed in **Get free Bibles** and in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Credits

The reading view and the SPB, TSV and MyBible readers follow **Bible** by Lugsole
(<https://github.com/Lugsole/net.lugsole.bible_gui>), used under the MIT License:

> Copyright (c) 2020 Lugsole. Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
