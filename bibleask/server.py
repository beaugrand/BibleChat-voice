"""BibleChat: a tiny web server that lives on your own computer and shows a chat page in your browser."""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional

from . import catalog, chat, llm, storage, study, stt
from .library import Library

PORT = 8765
IDLE_SECONDS = 180  # quit this long after the last browser tab is closed
MAX_UPLOAD = 600 * 1024 * 1024
SIGNATURE = "bible-chat"
TTS_URL = "http://127.0.0.1:8000"  # Kyutai Pocket TTS, if the person started it separately


def web_dir() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


# ---- speaking answers aloud, via a separately-running Kyutai Pocket TTS server ---------
def _tts_available() -> bool:
    try:
        with urllib.request.urlopen(TTS_URL + "/", timeout=0.4):
            return True
    except Exception:
        return False


def _ensure_tts_helper() -> None:
    """Starts Pocket TTS in the background if it isn't already running - bundled builds ship it
    as a sibling helper program (PocketTTS); a from-source run falls back to the pocket-tts command
    on PATH, if installed. Either way, the person never has to start it themselves."""
    if _tts_available():
        return
    try:
        if getattr(sys, "frozen", False):
            name = "PocketTTS.exe" if sys.platform.startswith("win") else "PocketTTS"
            exe = os.path.join(os.path.dirname(sys.executable), name)
            if not os.path.exists(exe):
                return
            flags = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
            subprocess.Popen([exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
        elif shutil.which("pocket-tts"):
            subprocess.Popen(["pocket-tts", "serve", "--port", "8000"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            return  # nothing to launch; the Listen button just won't appear
    except Exception:
        return
    for _ in range(45):  # give the voice model a little while to load
        time.sleep(1)
        if _tts_available():
            return


def _tts_speak(text: str) -> bytes:
    boundary = uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"text\"\r\n\r\n{text}\r\n"
            f"--{boundary}--\r\n").encode("utf-8")
    req = urllib.request.Request(TTS_URL + "/tts", data=body, method="POST",
                                  headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


class App:
    def __init__(self) -> None:
        self.lib = Library()
        self.model = llm.LocalLLM()
        self.jobs: dict[str, dict] = {}
        self.model_state: dict = {"status": "none", "repo": "", "message": "", "progress": 0.0}
        self.last_ping = time.time()
        self.seen_ping = False
        self.busy = 0  # running jobs + chats; keeps the app alive
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.cpu_fix_job: Optional[str] = None  # rebuilding the AI engine for an older processor

    # ---- jobs -------------------------------------------------------------------------
    def start_job(self, fn) -> str:
        jid = uuid.uuid4().hex[:10]
        job = {"status": "running", "message": "Starting…", "progress": 0.0, "error": None, "result": None}
        self.jobs[jid] = job

        def progress(msg: str, frac: float = 0.0) -> None:
            job["message"], job["progress"] = msg, max(0.0, min(1.0, float(frac)))

        def run() -> None:
            with self.lock:
                self.busy += 1
            try:
                job["result"] = fn(progress)
                job["status"] = "done"
            except Exception as e:  # shown to the person in plain words
                job["status"], job["error"] = "error", str(e) or e.__class__.__name__
            finally:
                with self.lock:
                    self.busy -= 1

        threading.Thread(target=run, daemon=True).start()
        return jid

    # ---- free Bibles from the catalog ------------------------------------------------------
    def fetch_bible(self, file: str, progress) -> str:
        name = catalog.display_name(file)
        progress(f"Downloading {name}…", 0.02)
        chunks, got = [], 0
        with llm._open(catalog.url(file)) as r:
            total = int(r.headers.get("Content-Length") or 0)
            while True:
                b = r.read(256 * 1024)
                if not b:
                    break
                chunks.append(b)
                got += len(b)
                if total:
                    progress(f"Downloading {name}… {got * 100 // total}%", 0.02 + 0.6 * got / total)
        progress("Reading the verses…", 0.65)
        return self.lib.add_file(name + os.path.splitext(file)[1], b"".join(chunks),
                                 lambda m, f: progress(m, 0.65 + 0.35 * f))

    # ---- model ------------------------------------------------------------------------
    def load_model(self, repo: str) -> None:
        st = self.model_state
        if st["status"] in ("downloading", "loading"):
            return
        problem = self.cpu_problem()
        if problem or not llm.engine_available():
            st.update(status="error", repo=repo, message=problem or "The AI engine isn't available in this build.")
            return
        st.update(status="downloading", repo=repo, message="Preparing…", progress=0.0)

        def work() -> None:
            with self.lock:
                self.busy += 1
            try:
                def cb(msg: str, frac: float) -> None:
                    st["message"], st["progress"] = msg, frac

                path = llm.download_model(repo, cb)
                st.update(status="loading", message="Loading the AI helper into memory…", progress=1.0)
                self.model.load(path, llm.style_for_repo(repo))
                st.update(status="ready", message="Ready")
                s = storage.load_settings()
                s["model"] = repo
                storage.save_settings(s)
            except Exception as e:
                st.update(status="error", message=str(e) or e.__class__.__name__)
            finally:
                with self.lock:
                    self.busy -= 1

        threading.Thread(target=work, daemon=True).start()

    def cpu_problem(self) -> Optional[str]:
        job = self.jobs.get(self.cpu_fix_job or "")
        if job and job["status"] == "done":
            return "Almost done: press Quit, then open BibleChat again to switch on the AI helper."
        return llm.cpu_problem()

    def cpu_fix(self) -> dict:
        job = self.jobs.get(self.cpu_fix_job or "")
        return {"can": llm.can_rebuild_for_old_cpu(),
                "status": job["status"] if job else "none",
                "message": (job["error"] if job["status"] == "error" else job["message"]) if job else "",
                "progress": job["progress"] if job else 0.0}

    def state(self) -> dict:
        models = []
        for m in llm.MODELS:
            models.append({"repo": m.repo, "label": m.label, "size": m.note, "style": m.style,
                           "downloaded": llm.local_path(m.repo) is not None})
        return {
            "app": SIGNATURE,
            "bibles": self.lib.summary(),
            "models": models,
            "model": dict(self.model_state),
            "engine": llm.engine_available(),
            "cpu_problem": self.cpu_problem(),
            "cpu_fix": self.cpu_fix(),
            "selected_model": (storage.load_settings().get("model")
                               or (llm.DEFAULT_BUNDLED_REPO if llm.local_path(llm.DEFAULT_BUNDLED_REPO) else llm.MODELS[0].repo)),
            "tts": _tts_available(),
            "stt": stt.available(),
        }

    # ---- idle watcher -----------------------------------------------------------------
    def watch_idle(self, httpd: ThreadingHTTPServer) -> None:
        while not self.stop.wait(5):
            if self.busy:
                self.last_ping = max(self.last_ping, time.time() - IDLE_SECONDS / 2)
                continue
            limit = IDLE_SECONDS if self.seen_ping else IDLE_SECONDS * 3
            if time.time() - self.last_ping > limit:
                httpd.shutdown()
                return


def make_handler(app: App, port: int):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "BibleChat"

        def log_message(self, *a) -> None:  # keep the console quiet
            pass

        # -- helpers
        def _host_ok(self) -> bool:
            host = (self.headers.get("Host") or "").lower()
            return host in (f"127.0.0.1:{port}", f"localhost:{port}")

        def _send(self, code: int, body: bytes, ctype: str = "application/json", extra: Optional[dict] = None) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code: int = 200) -> None:
            self._send(code, json.dumps(obj).encode("utf-8"))

        def _body(self) -> bytes:
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_UPLOAD:
                raise ValueError("That file is too large.")
            return self.rfile.read(n) if n else b""

        def _guard(self) -> bool:
            if not self._host_ok():
                self._send(403, b"Forbidden", "text/plain")
                return False
            return True

        # -- routes
        def do_GET(self) -> None:
            if not self._guard():
                return
            path = urllib.parse.urlparse(self.path).path
            if path in ("/", "/index.html"):
                with open(os.path.join(web_dir(), "index.html"), "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            elif path == "/api/ping":
                app.last_ping, app.seen_ping = time.time(), True
                self._json({"app": SIGNATURE, "ok": True})
            elif path == "/api/state":
                self._json(app.state())
            elif path in ("/api/books", "/api/chapter"):
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                bid = (q.get("bible") or [""])[0]
                try:
                    if path == "/api/books":
                        self._json({"books": app.lib.books(bid)})
                    else:
                        self._json(app.lib.chapter(bid, (q.get("book") or [""])[0], int((q.get("chapter") or ["1"])[0])))
                except Exception as e:
                    self._json({"error": str(e) or "That Bible isn't available."}, 404)
            elif path in ("/api/study/verse", "/api/study/strongs", "/api/study/topic", "/api/study/topics"):
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                g = lambda k, d="": (q.get(k) or [d])[0]
                try:
                    bid = g("bible")
                    if path == "/api/study/verse":
                        res = study.verse(app.lib, bid, g("book"), int(g("chapter", "1")), int(g("verse", "1")))
                    elif path == "/api/study/strongs":
                        res = study.strongs(app.lib, bid, g("number"))
                    elif path == "/api/study/topic":
                        res = study.topic(app.lib, bid, int(g("id", "-1")))
                    else:
                        res = {"topics": study.find_topics(g("q"))}
                    self._json(res if res is not None else {"error": "Not found."}, 200 if res is not None else 404)
                except Exception as e:
                    self._json({"error": str(e) or "Something went wrong."}, 400)
            elif path == "/api/catalog":
                have = {b["name"] for b in app.lib.summary()}
                items = catalog.entries()
                for it in items:
                    it["have"] = it["name"] in have
                self._json({"source": catalog.SOURCE, "items": items})
            elif path.startswith("/api/jobs/"):
                job = app.jobs.get(path.rsplit("/", 1)[1])
                self._json(job or {"status": "error", "error": "Unknown job"}, 200 if job else 404)
            else:
                self._send(404, b"Not found", "text/plain")

        def do_DELETE(self) -> None:
            if not self._guard():
                return
            path = urllib.parse.urlparse(self.path).path
            if path.startswith("/api/bibles/"):
                app.lib.remove(urllib.parse.unquote(path.rsplit("/", 1)[1]))
                self._json({"ok": True})
            else:
                self._send(404, b"Not found", "text/plain")

        def do_POST(self) -> None:
            if not self._guard():
                return
            path = urllib.parse.urlparse(self.path).path
            try:
                if path == "/api/bibles":
                    name = urllib.parse.unquote(self.headers.get("X-Filename") or "bible.txt")
                    data = self._body()
                    jid = app.start_job(lambda progress: app.lib.add_file(name, data, progress))
                    self._json({"job": jid})
                elif path == "/api/model/load":
                    req = json.loads(self._body() or b"{}")
                    repo = llm.repo_from_text(req.get("repo") or "")
                    if not repo:
                        self._json({"error": "Choose a model first."}, 400)
                        return
                    app.load_model(repo)
                    self._json({"ok": True})
                elif path == "/api/catalog/get":
                    req = json.loads(self._body() or b"{}")
                    file = req.get("file") or ""
                    try:
                        catalog.display_name(file)
                    except KeyError:
                        self._json({"error": "That Bible isn't on the list."}, 400)
                        return
                    self._json({"job": app.start_job(lambda progress: app.fetch_bible(file, progress))})
                elif path == "/api/cpu-fix":
                    cur = app.jobs.get(app.cpu_fix_job or "")
                    if not (cur and cur["status"] == "running"):
                        app.cpu_fix_job = app.start_job(llm.rebuild_for_old_cpu)
                    self._json({"job": app.cpu_fix_job})
                elif path == "/api/chat":
                    self._chat(json.loads(self._body() or b"{}"))
                elif path == "/api/speak":
                    req = json.loads(self._body() or b"{}")
                    text = (req.get("text") or "").strip()
                    if not text:
                        self._json({"error": "Nothing to say."}, 400)
                        return
                    try:
                        audio = _tts_speak(text)
                    except Exception:
                        self._json({"error": "Couldn't reach the voice helper. Is Pocket TTS running?"}, 503)
                        return
                    self._send(200, audio, "audio/wav")
                elif path == "/api/listen":
                    try:
                        text = stt.transcribe(self._body())
                    except Exception as e:
                        self._json({"error": str(e) or e.__class__.__name__}, 400)
                        return
                    self._json({"text": text})
                elif path == "/api/quit":
                    self._json({"ok": True})
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                else:
                    self._send(404, b"Not found", "text/plain")
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as e:
                try:
                    self._json({"error": str(e) or e.__class__.__name__}, 400)
                except OSError:
                    pass

        def _chat(self, req: dict) -> None:
            question = (req.get("question") or "").strip()
            if not question:
                self._json({"error": "Type a question first."}, 400)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True

            def emit(event: str, data) -> None:
                self.wfile.write(f"event: {event}\ndata: {json.dumps(data)}\n\n".encode("utf-8"))
                self.wfile.flush()

            with app.lock:
                app.busy += 1
            gen = chat.respond(question, req.get("previous"), app.lib, list(req.get("bibles") or []),
                               app.model, use_ai=bool(req.get("use_ai", True)))
            try:
                for kind, payload in gen:
                    emit(kind, payload)
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as e:
                try:
                    emit("error", f"Something went wrong: {e}")
                except OSError:
                    pass
            finally:
                gen.close()
                with app.lock:
                    app.busy -= 1

    return Handler


def _already_running(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ping", timeout=1.5) as r:
            return json.loads(r.read()).get("app") == SIGNATURE
    except Exception:
        return False


def _free(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def main(open_browser: bool = True) -> int:
    port = PORT
    if _already_running(port):
        if open_browser:
            webbrowser.open(f"http://127.0.0.1:{port}/")
        return 0
    while not _free(port) and port < PORT + 20:
        port += 1
    app = App()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app, port))
    httpd.daemon_threads = True
    threading.Thread(target=app.watch_idle, args=(httpd,), daemon=True).start()

    # if the AI helper was already downloaded (or came bundled with the app), wake it up now
    repo = storage.load_settings().get("model") or llm.DEFAULT_BUNDLED_REPO
    if llm.local_path(repo) and llm.engine_available() and not app.cpu_problem():
        app.load_model(repo)

    threading.Thread(target=_ensure_tts_helper, daemon=True).start()

    from . import shortcuts
    shortcuts.ensure_in_background()   # Windows: a BibleChat icon on the desktop and in the Start menu

    url = f"http://127.0.0.1:{port}/"
    try:  # there is no console when the app is double-clicked on Windows/Mac
        print(f"BibleChat is running at {url}  (close the browser tab or press Quit to stop it)", flush=True)
    except Exception:
        pass
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        app.stop.set()
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
