# PyInstaller recipe for BibleChat (Windows, Mac and Linux).  Build with:  pyinstaller --noconfirm BibleChat.spec
import os, sys
from PyInstaller.utils.hooks import collect_all

datas = [("bibleask/web", "bibleask/web")]
if os.environ.get("BIBLECHAT_COMPAT"):  # engine compiled without AVX2, for older processors
    open("bibleask/compat_build.flag", "w").write("1")
    datas.append(("bibleask/compat_build.flag", "bibleask"))
binaries, hiddenimports = [], []
for pkg in ("llama_cpp", "pypdfium2", "pypdfium2_raw", "certifi"):
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
coll = COLLECT(exe, a.binaries, a.datas, name="BibleChat")
if sys.platform == "darwin":
    app = BUNDLE(coll, name="BibleChat.app", bundle_identifier="local.biblechat")
