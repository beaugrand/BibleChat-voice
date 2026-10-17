# BibleChat

A chat window, like the ones you use with an AI assistant, but **only for Bibles**. You add Bibles (the Ethiopian Orthodox Bible PDF, a King James text from Project Gutenberg, any Zefania/OSIS XML Bible…), then ask questions or type a reference. BibleChat shows the matching verses from your Bibles and a small free AI model from Hugging Face explains them.

It runs on your own computer and opens in your web browser. Nothing is uploaded anywhere. The only download is the AI model, once.

---

## How to use it

1. Open **BibleChat**. Your browser opens the chat page. (Closing the tab stops the app after about 3 minutes, or press **Quit** in the sidebar.)
2. **⬇ Get free Bibles** in the sidebar opens a list of 44 public-domain and freely licensed Bibles (KJV, ASV, World English Bible, Berean Standard Bible, Douay-Rheims, Luther 1912, Reina-Valera 1909 and many other languages, from the [open-bibles](https://github.com/seven1m/open-bibles) collection, plus an **Ethiopian Canon** of 84 books in public-domain English, with 1 Enoch, Jubilees, 2 Enoch and 1 Clement, and the 1962 **Amharic New Testament**). Click **Download** and it's added. Or use **Add Bible from a file** (or drag a file onto the page): PDF, XML or TXT. A big PDF takes 10–60 seconds the first time. After that it is instant.
3. Tick the Bibles you want searched. With several ticked, a reference such as *Daniel 7:25* is shown in each one side by side.
4. Type a question and press **Enter**. The verses appear first, with your words highlighted, then the AI's explanation.
5. Optional: under **AI helper** click **Get / load** once. It downloads a model (Bible Assistant 4B is about 2.7 GB; Qwen2.5 1.5B is about 1.1 GB and faster). Untick **Explain with AI** to see verses only.

You can type references: `Daniel 7:25`, `1 Cor 13:4-7`, `Psalm 23`, `Rev 22`.

**Reading a whole chapter.** Press **📖 Read** at the top of the sidebar. Pick a Bible, click a book to show its chapters, and click a chapter. Use **‹ Prev / Next ›** (or the ← → keys) to turn chapters, **🔊 Listen** to have it read aloud (it carries on into the next chapter until you press Stop), **¶** to switch between one verse per line and flowing text, and **A− / A+** for text size. **💬 Ask** takes you back to Chat with that chapter filled in. In a chat answer, click a verse reference to open it in the reader. BibleChat remembers where you stopped.

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

**[beaugrand.github.io/BibleChat-voice](https://beaugrand.github.io/BibleChat-voice/)** opens BibleChat in any phone or computer browser. No sign-up, nothing to install. It has reading, search (same method as the app), the 44 free Bibles, read-aloud with the phone's own voice, links to any verse, Strong's Hebrew/Greek words and Nave's topics (tap a verse, then **Study it**), and Love Donations. Bibles you open are kept on the phone, so it also works offline. **Share → Add to Home Screen** keeps it like an app.

The AI explanations and voice questions need the computer app, because they run an AI model on your own machine.

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
- **Older processors (no AVX2, roughly pre-2014):** BibleChat shows a yellow box in the sidebar. Searching, reading and Listen still work; only the AI explanation is off. When BibleChat runs from this folder (BibleChat 2), the box has a **Rebuild the AI helper** button that recompiles the AI engine for your processor in the background (10–40 minutes; needs `sudo apt install build-essential` once). Then Quit and reopen. The packaged app uses the Linux-OldCPU download instead.
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
python -m unittest discover -s tests -v     # 31 tests
```

`bibleask/loaders.py` reads PDF/XML/TXT/SPB/TSV/MyBible, `library.py` keeps the Bibles and serves whole chapters to the reader, `search.py` does BM25 search and reference lookup, `chat.py` decides what to show and ask the AI, `server.py` is the local web server, `web/index.html` is the whole chat page, `llm.py` downloads and runs the model. `gui.py` is the older Tkinter window (BibleAsk), no longer built.

## License

BibleChat is free and open source under the [MIT License](LICENSE): anyone may use, copy, change and share it. No Bibles are included. The ones people download keep their own licenses, shown next to each in **Get free Bibles**. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the libraries and models BibleChat uses.

## Credits

The reading view and the SPB, TSV and MyBible readers follow **Bible** by Lugsole
(<https://github.com/Lugsole/net.lugsole.bible_gui>), used under the MIT License:

> Copyright (c) 2020 Lugsole. Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
