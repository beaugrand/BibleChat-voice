# BibleChat

A chat window, like the ones you use with an AI assistant, but **only for Bibles**. You add Bibles (the Ethiopian Orthodox Bible PDF, a King James text from Project Gutenberg, any Zefania/OSIS XML Bible…), then ask questions or type a reference. BibleChat shows the matching verses from your Bibles and a small free AI model from Hugging Face explains them.

It runs on your own computer and opens in your web browser. Nothing is uploaded anywhere. The only download is the AI model, once.

---

## How to use it

1. Open **BibleChat**. Your browser opens the chat page. (Closing the tab stops the app after about 3 minutes, or press **Quit** in the sidebar.)
2. **Add Bible** in the sidebar (or drag a file onto the page): PDF, XML or TXT. A big PDF takes 10–60 seconds the first time. After that it is instant.
3. Tick the Bibles you want searched. With several ticked, a reference such as *Daniel 7:25* is shown in each one side by side.
4. Type a question and press **Enter**. The verses appear first, with your words highlighted, then the AI's explanation.
5. Optional: under **AI helper** click **Get / load** once. It downloads a model (Bible Assistant 4B is about 2.7 GB; Qwen2.5 1.5B is about 1.1 GB and faster). Untick **Explain with AI** to see verses only.

You can type references: `Daniel 7:25`, `1 Cor 13:4-7`, `Psalm 23`, `Rev 22`.

The chat only talks about the Bibles you added. If nothing matches, it says so instead of guessing, and the AI is not asked.

**Supported Bible files**

| Format | Notes |
|---|---|
| PDF | Works best with a layout like the Ethiopian Bible PDF: book title, chapter number on its own line, verses numbered inline. Other layouts are still searchable as plain passages. |
| XML | Zefania XML and OSIS XML (read exactly). |
| TXT | Project Gutenberg style (`1:1 In the beginning…` under a book title), or lines like `Genesis 1:1 In the beginning…`. |

Project Gutenberg's well-known 1455 "Gutenberg Bible" is in Latin, so the English AI can't explain it. Use the Gutenberg *King James* text instead (search "King James Bible" at gutenberg.org and save the "Plain Text UTF-8" file).

---

## Getting the app

End users need **nothing installed**: no Python, no setup.

| Computer | File | How to open it |
|---|---|---|
| Windows | `BibleChat-Windows.zip` | Unzip, open `BibleChat\BibleChat.exe` |
| Mac (Apple Silicon, M1 and newer) | `BibleChat-Mac.zip` | Unzip, drag `BibleChat.app` to Applications |
| Linux | `BibleChat-Linux.tar.gz` | Unpack, run `./install.sh`, open BibleChat from the menu |
| Linux, older processor (no AVX2) | `BibleChat-Linux-OldCPU.tar.gz` | Same steps. Use this if the AI helper says your processor is too old. Slower. |

**First-launch warnings** (normal until the app is code-signed, which costs money at Microsoft and Apple):
- Windows: "Windows protected your PC" → **More info** → **Run anyway**.
- Mac: right-click the app → **Open** → **Open**. If it says "damaged", run `xattr -cr /Applications/BibleChat.app` in Terminal.
- The app has no window of its own. After you open it, give it a few seconds and your browser opens by itself. If your browser doesn't, go to `http://127.0.0.1:8765`.

### How the Windows and Mac files are made

A Windows program can only be built on Windows and a Mac program only on a Mac. GitHub does all three for free.

1. Make a free account at [github.com](https://github.com) and create a new **private** repository called `BibleChat`.
2. Upload everything in this folder, including the hidden `.github` folder.
3. Open **Actions** → **Build BibleChat (Windows + Mac + Linux)** → **Run workflow**.
4. About 10 minutes later download the three files from **Artifacts** at the bottom of the finished run.

### On your own Linux machine

Use `BibleChat-Linux.tar.gz` as above. It needs Linux Mint 22 or newer (glibc 2.38+); the copy built by GitHub works on Mint 21 and newer. To tinker with the code instead: `sudo apt install python3-venv` once, then `./run_from_source_linux.sh`.

---

## What to expect

- **The verses shown are always real text from your files.** The AI never supplies verses. It only explains the ones found.
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
python -m unittest discover -s tests -v     # 23 tests
```

`bibleask/loaders.py` reads PDF/XML/TXT, `search.py` does BM25 search and reference lookup, `chat.py` decides what to show and ask the AI, `server.py` is the local web server, `web/index.html` is the whole chat page, `llm.py` downloads and runs the model. `gui.py` is the older Tkinter window (BibleAsk), no longer built.
