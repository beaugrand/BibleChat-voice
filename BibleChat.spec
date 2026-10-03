# PyInstaller recipe for BibleChat (Windows, Mac and Linux).  Build with:  pyinstaller --noconfirm BibleChat.spec
import os, sys
from PyInstaller.utils.hooks import collect_all

datas = [("bibleask/web", "bibleask/web")]
if os.environ.get("BIBLECHAT_COMPAT"):  # engine compiled without AVX2, for older processors
    open("bibleask/compat_build.flag", "w").write("1")
    datas.append(("bibleask/compat_build.flag", "bibleask"))
for extra in ("bundled_models", "hf_cache"):  # AI models pre-fetched by packaging/fetch_models.py,
    if os.path.isdir(extra):                  # baked in so the finished app needs no first-run download
        datas.append((extra, extra))

binaries, hiddenimports = [], []
for pkg in ("llama_cpp", "pypdfium2", "pypdfium2_raw", "certifi", "torch", "transformers", "pocket_tts"):
    try:
        d, b, h = collect_all(pkg)
        datas += d; binaries += b; hiddenimports += h
    except Exception:
        pass

a = Analysis(["chat_app.py"], datas=datas, binaries=binaries, hiddenimports=hiddenimports,
             excludes=["tkinter", "matplotlib", "PIL.ImageTk"])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="BibleChat",
          console=sys.platform.startswith("linux"))   # no black window on Windows/Mac; Linux prints the address

# A second, hidden helper: Pocket TTS's own server, bundled right alongside so BibleChat can speak
# its answers with no separate install step. bibleask/server.py launches it automatically.
exes, all_binaries, all_zipfiles, all_datas = [exe], a.binaries, a.zipfiles, a.datas
if os.path.isfile("pocket_tts_entry.py"):
    a2 = Analysis(["pocket_tts_entry.py"], hiddenimports=hiddenimports, excludes=["tkinter", "matplotlib"])
    pyz2 = PYZ(a2.pure)
    exe2 = EXE(pyz2, a2.scripts, [], exclude_binaries=True, name="PocketTTS", console=False)
    exes.append(exe2)
    all_binaries += a2.binaries; all_zipfiles += a2.zipfiles; all_datas += a2.datas

coll = COLLECT(*exes, all_binaries, all_zipfiles, all_datas, name="BibleChat")
if sys.platform == "darwin":
    app = BUNDLE(coll, name="BibleChat.app", bundle_identifier="local.biblechat")
