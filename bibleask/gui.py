"""The BibleAsk window (Tkinter - ships with Python, works the same on Windows and Mac)."""
from __future__ import annotations

import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from . import llm, storage
from .loaders import Bible, load_bible
from .search import Index, short_ref, short_title

APP_TITLE = "BibleAsk"
MAX_SHOWN_PASSAGE = 80  # verses shown when someone types a reference like "Psalm 119"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("980x760")
        self.minsize(720, 560)
        self.q: "queue.Queue[tuple]" = queue.Queue()
        self.index: Optional[Index] = None
        self.llm = llm.LocalLLM()
        self.settings = storage.load_settings()
        self.run_id = 0
        self.busy_bible = False
        self.busy_model = False
        self._build()
        self.after(60, self._poll)
        self._startup()

    # ------------------------------------------------------------------ layout
    def _build(self) -> None:
        pad = {"padx": 10, "pady": 4}
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True)

        # Bible row
        r1 = ttk.Frame(root)
        r1.pack(fill="x", **pad)
        ttk.Label(r1, text="Bible:", width=9).pack(side="left")
        self.bible_var = tk.StringVar()
        self.bible_box = ttk.Combobox(r1, textvariable=self.bible_var, state="readonly", width=42)
        self.bible_box.pack(side="left", padx=(0, 8))
        self.bible_box.bind("<<ComboboxSelected>>", lambda e: self._select_bible(self.bible_var.get()))
        ttk.Button(r1, text="Add Bible…", command=self._add_bible).pack(side="left")
        ttk.Button(r1, text="Remove", command=self._remove_bible).pack(side="left", padx=6)
        self.bible_info = ttk.Label(r1, text="", foreground="#666")
        self.bible_info.pack(side="left", padx=10)

        # AI row
        r2 = ttk.Frame(root)
        r2.pack(fill="x", **pad)
        ttk.Label(r2, text="AI helper:", width=9).pack(side="left")
        self.model_var = tk.StringVar(value=self.settings.get("model_label", llm.MODELS[0].label))
        self.model_box = ttk.Combobox(r2, textvariable=self.model_var, width=52,
                                      values=[m.label for m in llm.MODELS])
        self.model_box.pack(side="left", padx=(0, 8))
        self.model_btn = ttk.Button(r2, text="Get / load AI", command=self._load_model)
        self.model_btn.pack(side="left")
        self.model_state = ttk.Label(r2, text="not loaded", foreground="#a33")
        self.model_state.pack(side="left", padx=10)
        r2b = ttk.Frame(root)
        r2b.pack(fill="x", padx=10)
        ttk.Label(r2b, text="", width=9).pack(side="left")
        ttk.Label(r2b, foreground="#666",
                  text="Pick from the list, or type any Hugging Face model name ending in -GGUF (owner/name).").pack(side="left")

        # Question row
        r3 = ttk.Frame(root)
        r3.pack(fill="x", padx=10, pady=(14, 4))
        self.entry = ttk.Entry(r3, font=("TkDefaultFont", 13))
        self.entry.pack(side="left", fill="x", expand=True, ipady=5)
        self.entry.bind("<Return>", lambda e: self._ask())
        self.ask_btn = ttk.Button(r3, text="Ask", command=self._ask)
        self.ask_btn.pack(side="left", padx=(8, 0))
        r4 = ttk.Frame(root)
        r4.pack(fill="x", padx=10)
        self.use_ai = tk.BooleanVar(value=True)
        ttk.Checkbutton(r4, text="Also explain with the AI helper", variable=self.use_ai).pack(side="left")
        ttk.Button(r4, text="Copy results", command=self._copy).pack(side="right")
        ttk.Label(r4, text="Ask a question, or type a reference like  Daniel 7:25  or  Psalm 23",
                  foreground="#666").pack(side="right", padx=12)

        # Status bar
        bar = ttk.Frame(root)
        bar.pack(fill="x", side="bottom", padx=10, pady=(0, 8))
        self.status = ttk.Label(bar, text="", foreground="#444")
        self.status.pack(side="left")
        self.progress = ttk.Progressbar(bar, length=220, mode="determinate", maximum=100)
        self.progress.pack(side="right")

        # Results
        pane = ttk.PanedWindow(root, orient="vertical")
        pane.pack(fill="both", expand=True, padx=10, pady=8)
        self.verses_txt = self._text_box(pane, "Verses from your Bible", weight=3)
        self.ai_txt = self._text_box(pane, "AI explanation (based only on the verses above)", weight=1)
        for t in (self.verses_txt, self.ai_txt):
            t.tag_configure("ref", font=("TkDefaultFont", 11, "bold"), foreground="#1a4d8f")
            t.tag_configure("hint", foreground="#777")
            t.tag_configure("err", foreground="#a33")

    def _text_box(self, pane: ttk.PanedWindow, title: str, weight: int) -> tk.Text:
        frame = ttk.LabelFrame(pane, text=title)
        txt = tk.Text(frame, wrap="word", font=("TkDefaultFont", 12), padx=8, pady=6, spacing1=2, spacing3=6,
                      height=14 if weight >= 3 else 7,
                      relief="flat", borderwidth=0, state="disabled")
        sb = ttk.Scrollbar(frame, command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        txt.pack(side="left", fill="both", expand=True)
        pane.add(frame, weight=weight)
        return txt

    # ------------------------------------------------------------------ helpers
    def _put(self, widget: tk.Text, text: str, tag: str = "", clear: bool = False) -> None:
        widget.configure(state="normal")
        if clear:
            widget.delete("1.0", "end")
        widget.insert("end", text, tag)
        widget.configure(state="disabled")
        widget.see("end") if widget is self.ai_txt else None

    def _set_status(self, msg: str, frac: Optional[float] = None) -> None:
        self.status.configure(text=msg)
        if frac is not None:
            self.progress.configure(value=max(0, min(100, frac * 100)))

    def _thread(self, fn, *a) -> None:
        threading.Thread(target=fn, args=a, daemon=True).start()

    # ------------------------------------------------------------------ startup / Bibles
    def _startup(self) -> None:
        self._refresh_library()
        if not llm.engine_available():
            self.model_state.configure(text="AI engine not installed", foreground="#a33")
        names = storage.list_bibles()
        last = self.settings.get("bible")
        if last in names:
            self._select_bible(last)
        elif names:
            self._select_bible(names[0])
        else:
            self._welcome()

    def _welcome(self) -> None:
        self._put(self.verses_txt,
                  "Welcome!\n\n1.  Click  Add Bible…  and choose your Bible file (PDF, XML or TXT).\n"
                  "2.  Type a question, or a reference like  John 3:16,  and press Enter.\n"
                  "3.  Optional: click  Get / load AI  once to download a small free AI helper that explains the verses.\n\n"
                  "Everything runs on this computer. Your Bible files never leave it.", "hint", clear=True)

    def _refresh_library(self) -> None:
        names = storage.list_bibles()
        self.bible_box["values"] = names
        if self.bible_var.get() not in names:
            self.bible_var.set(names[0] if names else "")

    def _add_bible(self) -> None:
        if self.busy_bible:
            return
        path = filedialog.askopenfilename(
            title="Choose a Bible file",
            filetypes=[("Bible files", "*.pdf *.xml *.txt *.json"), ("PDF", "*.pdf"), ("XML", "*.xml"),
                       ("Text", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        self.busy_bible = True
        self._set_status("Reading Bible… this can take a minute for a big PDF.", 0.02)

        def work() -> None:
            try:
                b = load_bible(path, progress=lambda m, f: self.q.put(("status", m, f)))
                slug = storage.save_bible(b)
                self.q.put(("bible", slug, b))
            except Exception as e:  # noqa: BLE001 - show any problem to the user
                self.q.put(("error", f"Could not read that file: {e}"))
        self._thread(work)

    def _remove_bible(self) -> None:
        slug = self.bible_var.get()
        if not slug:
            return
        if messagebox.askyesno(APP_TITLE, f"Remove '{slug}' from BibleAsk?\n(Your original file is not touched.)"):
            storage.remove_bible(slug)
            self.index = None
            self.bible_var.set("")
            self._refresh_library()
            names = storage.list_bibles()
            if names:
                self._select_bible(names[0])
            else:
                self.bible_info.configure(text="")
                self._welcome()

    def _select_bible(self, slug: str) -> None:
        if not slug:
            return
        self.bible_var.set(slug)
        self._set_status(f"Opening {slug}…", 0.1)

        def work() -> None:
            try:
                b = storage.open_bible(slug)
                self.q.put(("bible", slug, b))
            except Exception as e:  # noqa: BLE001
                self.q.put(("error", f"Could not open {slug}: {e}"))
        self._thread(work)

    # ------------------------------------------------------------------ AI model
    def _selected_repo(self) -> str:
        text = self.model_var.get().strip()
        for m in llm.MODELS:
            if text == m.label:
                return m.repo
        return llm.repo_from_text(text)

    def _load_model(self) -> None:
        if self.busy_model:
            return
        if not llm.engine_available():
            messagebox.showinfo(
                APP_TITLE,
                "The AI engine (llama-cpp-python) is not installed in this copy of BibleAsk.\n\n"
                "Searching still works. See the README to add the AI engine.")
            return
        problem = llm.cpu_problem()
        if problem:
            messagebox.showinfo(APP_TITLE, problem)
            return
        try:
            repo = self._selected_repo()
        except ValueError as e:
            messagebox.showerror(APP_TITLE, str(e))
            return
        self.busy_model = True
        self.model_btn.state(["disabled"])
        self.model_state.configure(text="working…", foreground="#a60")

        def work() -> None:
            try:
                path = llm.download_model(repo, lambda m, f: self.q.put(("status", m, f)))
                self.q.put(("status", "Loading the AI model into memory…", 1.0))
                self.llm.load(path, llm.style_for_repo(repo))
                self.q.put(("model_ready", repo))
            except Exception as e:  # noqa: BLE001
                self.q.put(("model_error", f"Could not get the AI model: {e}"))
        self._thread(work)

    # ------------------------------------------------------------------ asking
    def _ask(self) -> None:
        question = self.entry.get().strip()
        if not question:
            return
        if self.index is None:
            self._put(self.verses_txt, "Please add a Bible first (Add Bible… button).", "err", clear=True)
            return
        ix = self.index
        self.run_id += 1
        rid = self.run_id
        self._put(self.ai_txt, "", clear=True)

        ref_idx = ix.lookup_reference(question)
        if ref_idx:
            shown = ref_idx[:MAX_SHOWN_PASSAGE]
            self._show_verses(shown, header=None)
            if len(ref_idx) > MAX_SHOWN_PASSAGE:
                self._put(self.verses_txt, f"\n… showing the first {MAX_SHOWN_PASSAGE} of {len(ref_idx)} verses.\n", "hint")
            ai_idx = shown[:llm.passages_wanted(self.llm.style)]
        else:
            hits = ix.search(question, k=8)
            if not hits:
                self._put(self.verses_txt, "No matching verses found. Try different or fewer words.", "hint", clear=True)
                return
            self._show_verses([h.index for h in hits], header=None)
            want = llm.passages_wanted(self.llm.style)
            if self.llm.style == "bible":
                ai_idx = [h.index for h in hits[:want]]  # exactly the top verses, as the model was trained
            else:
                ai_idx = []
                for h in hits[:6]:
                    for j in ix.context(h.index, 0, 1):
                        if j not in ai_idx:
                            ai_idx.append(j)
                ai_idx = ai_idx[:want]

        if not self.use_ai.get():
            return
        if not self.llm.loaded:
            self._put(self.ai_txt, "The AI helper is not loaded yet. Click “Get / load AI” above "
                                   "(one-time download). The verses on top are already the answer from your Bible.", "hint")
            return
        passages = [(short_ref(ix.verses[j]), ix.verses[j].text[:600]) for j in ai_idx]
        self._set_status("AI is reading the verses…", 0.0)
        self.progress.configure(mode="indeterminate")
        self.progress.start(12)

        def work() -> None:
            try:
                for piece in self.llm.stream(question, passages):
                    if rid != self.run_id:
                        return  # a newer question replaced this one
                    self.q.put(("ai", rid, piece))
                self.q.put(("ai_done", rid))
            except Exception as e:  # noqa: BLE001
                self.q.put(("ai_error", rid, f"AI problem: {e}"))
        self._thread(work)

    def _show_verses(self, idxs: list[int], header: Optional[str]) -> None:
        ix = self.index
        assert ix is not None
        self._put(self.verses_txt, "", clear=True)
        for j in idxs:
            v = ix.verses[j]
            self._put(self.verses_txt, short_ref(v) + "   ", "ref")
            self._put(self.verses_txt, v.text + "\n")
        self.verses_txt.yview_moveto(0)

    def _copy(self) -> None:
        text = self.verses_txt.get("1.0", "end").strip() + "\n\n" + self.ai_txt.get("1.0", "end").strip()
        self.clipboard_clear()
        self.clipboard_append(text.strip())
        self._set_status("Copied to clipboard.")

    # ------------------------------------------------------------------ messages from worker threads
    def _poll(self) -> None:
        try:
            while True:
                msg = self.q.get_nowait()
                self._handle(msg)
        except queue.Empty:
            pass
        self.after(60, self._poll)

    def _handle(self, msg: tuple) -> None:
        kind = msg[0]
        if kind == "status":
            self._set_status(msg[1], msg[2])
        elif kind == "bible":
            slug, b = msg[1], msg[2]
            self.index = Index(b)
            self.busy_bible = False
            self._refresh_library()
            self.bible_var.set(slug)
            self.settings["bible"] = slug
            storage.save_settings(self.settings)
            books = len({v.book for v in b.verses})
            self.bible_info.configure(text=f"{len(b.verses):,} verses · {books} books")
            self._set_status("Ready. Ask a question or type a reference.", 1.0)
            self._put(self.verses_txt, "Bible loaded. Type your question above and press Enter.", "hint", clear=True)
            self.entry.focus_set()
        elif kind == "error":
            self.busy_bible = False
            self._set_status("", 0)
            self._put(self.verses_txt, msg[1], "err", clear=True)
        elif kind == "model_ready":
            self.busy_model = False
            self.model_btn.state(["!disabled"])
            self.model_state.configure(text="ready ✓", foreground="#2a7a2a")
            self.settings["model_label"] = self.model_var.get()
            storage.save_settings(self.settings)
            self._set_status("AI helper ready.", 1.0)
        elif kind == "model_error":
            self.busy_model = False
            self.model_btn.state(["!disabled"])
            self.model_state.configure(text="failed", foreground="#a33")
            self._set_status("", 0)
            messagebox.showerror(APP_TITLE, msg[1])
        elif kind == "ai":
            if msg[1] == self.run_id:
                self._put(self.ai_txt, msg[2])
        elif kind in ("ai_done", "ai_error"):
            if msg[1] == self.run_id:
                self.progress.stop()
                self.progress.configure(mode="determinate", value=0)
                self._set_status("Done.", 1.0)
                if kind == "ai_error":
                    self._put(self.ai_txt, "\n" + msg[2], "err")


def main() -> None:
    if sys.platform.startswith("win"):
        try:
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    App().mainloop()
