"""Short share pages for the phone site: one small page per Study Path, series and prayer, plus one for each list.

    p/<path-id>/index.html       opens  #/path/<id>/1          (a Study Path, at step 1)
    p/index.html                 opens  #/paths                (all the Study Paths)
    series/<series-id>/index.html opens #/paths/series/<id>    (a folder of study sessions)
    group/<group-name>/index.html opens #/paths/group/<name>   (a Bible study group's folder, the next study first)
    pray/<prayer-id>/index.html  opens  #/prayers/<id>         (one prayer)
    pray/index.html              opens  #/prayers              (all the prayers)

Why: a link with "#/path/…" in it shows the same general picture everywhere it is posted, and some apps add their own
tracking to the end of a link (Facebook Messenger adds "?fbclid=…" after the "#"). A short page has the path's or prayer's
own title, question and picture for the preview (Open Graph tags; Facebook, Messenger, WhatsApp, iMessage and others read
them), and then opens BibleChat at that path or prayer. Anything an app adds to the short address is simply ignored.

paths.js (linkOf) makes these addresses when someone presses Share. web/build_study.py calls write_share_pages().

Usage:  python web/build_share.py OUT_DIR
"""
from __future__ import annotations

import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
SITE = "https://beaugrand.github.io/BibleChat-voice/"
OG_PATHS = "paths/img/og-studypaths.jpg"
OG_PRAYERS = "paths/img/og-prayers.jpg"

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · BibleChat</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="BibleChat">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{image}">
<meta property="og:image:secure_url" content="{image}">
<meta property="og:image:type" content="image/jpeg">
<meta property="og:image:width" content="{width}">
<meta property="og:image:height" content="{height}">
<meta property="og:image:alt" content="{title}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{image}">
<meta name="theme-color" content="#16191d">
<style>
body{{margin:0;background:#16191d;color:#e9ecef;font:17px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;display:flex;min-height:100vh;align-items:center;justify-content:center}}
main{{max-width:520px;margin:20px;background:#1f2328;border:1px solid #343a40;border-radius:16px;overflow:hidden}}
img{{display:block;width:100%;height:auto;max-height:300px;object-fit:cover}}
div{{padding:16px 18px 20px}}h1{{font:700 24px/1.25 Georgia,serif;color:#d9b44a;margin:0 0 8px}}p{{margin:0 0 14px}}
a{{display:inline-block;background:#d9b44a;color:#16191d;font-weight:700;text-decoration:none;border-radius:10px;padding:11px 18px}}
small{{display:block;color:#9aa3ad;margin-top:12px}}
</style>
</head>
<body>
<main>
<img src="{image}" alt="">
<div>
<h1>{title}</h1>
<p>{desc}</p>
<a href="{app}">{button}</a>
<small>{kind} in BibleChat. Free, no sign-up, nothing to install.</small>
</div>
</main>
<script>location.replace({app_js} );</script>
</body>
</html>
"""


def short(text: str, n: int = 220) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "…"


def jpeg_size(path: str) -> tuple[int, int]:
    """Width and height of a JPEG, read from its header (no image library on the build machine)."""
    with open(path, "rb") as f:
        data = f.read()
    i = 2
    while i < len(data) - 9:
        if data[i] != 0xFF:
            i += 1
            continue
        marker, size = data[i + 1], int.from_bytes(data[i + 2:i + 4], "big")
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):   # start of frame
            return int.from_bytes(data[i + 7:i + 9], "big"), int.from_bytes(data[i + 5:i + 7], "big")
        i += 2 + size
    raise ValueError(f"not a JPEG: {path}")


def page(out: str, rel: str, title: str, desc: str, image: str, app: str, kind: str, button: str) -> str:
    """Write OUT/<rel>index.html. `app` is the address of BibleChat at the path or prayer, relative to the page."""
    e = lambda s: html.escape(str(s), quote=True)  # noqa: E731
    url = SITE + rel
    # Facebook and Messenger show a broken or empty picture on the first share of a link unless the page says how big the
    # picture is; "?v=" makes them fetch it afresh instead of using a copy they kept from before the size was given
    width, height = jpeg_size(os.path.join(WEB, *image.split("/")))
    body = PAGE.format(title=e(title), desc=e(short(desc)), url=e(url), image=e(SITE + image + "?v=2"), width=width, height=height, app=e(app),
                       app_js=json.dumps(app), kind=e(kind), button=e(button))
    path = os.path.join(out, *rel.strip("/").split("/"), "index.html") if rel else os.path.join(out, "index.html")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return path


def write_share_pages(out: str, web: str = WEB) -> list[str]:
    with open(os.path.join(web, "paths", "index.json"), encoding="utf-8") as f:
        paths = json.load(f)
    with open(os.path.join(web, "prayers.json"), encoding="utf-8") as f:
        prayers = json.load(f)
    written: list[str] = []
    images = {p["id"]: "paths/" + p["image"] for p in paths if p.get("image")}
    written.append(page(out, "p/", "BibleChat Study Paths: free guided Bible studies",
                        "The verses side by side, the Hebrew and Greek words, and questions. Free, no sign-up, on any phone or computer.",
                        OG_PATHS, "../#/paths", "Study Paths", "📜 Open the Study Paths"))
    series = {}
    for p in paths:
        written.append(page(out, f"p/{p['id']}/", p["title"], p.get("opening_question", ""), images.get(p["id"], OG_PATHS),
                            f"../../#/path/{p['id']}/1", "A guided Bible study", "📜 Start this study"))
        se = p.get("series")
        if isinstance(se, dict) and se.get("id") and (se["id"] not in series or se.get("session", 99) < series[se["id"]][0].get("session", 99)):
            series[se["id"]] = (se, p)
    for sid, (se, first) in series.items():
        written.append(page(out, f"series/{sid}/", se.get("title", sid), f"{se.get('of', '')} study sessions, Daniel and Revelation side by side.".strip(),
                            images.get(first["id"], OG_PATHS), f"../../#/paths/series/{sid}", "Study sessions", "📂 Open the sessions"))
    groups = {}
    for p in paths:   # a Bible study group: its folder, with the picture of its newest study
        if p.get("group"):
            gid = re.sub(r"[^a-z0-9]+", "-", p["group"].lower().replace("’", "'")).strip("-")[:60]
            if gid not in groups or p.get("study_date", "") > groups[gid][1].get("study_date", ""):
                groups[gid] = (p["group"], p)
    for gid, (name, newest) in groups.items():
        written.append(page(out, f"group/{gid}/", name, "The chapters this Bible study group studies, the next one first: read ahead and come prepared.",
                            images.get(newest["id"], OG_PATHS), f"../../#/paths/group/{gid}", "Bible study group", "👥 Open the group"))
    written.append(page(out, "pray/", "BibleChat Prayers", "Prayers drawn from the Bible, and the prayers the Bible itself records. Pray, listen, share.",
                        OG_PRAYERS, "../#/prayers", "Prayers", "🙏 Open the prayers"))
    for p in prayers["prayers"]:
        rs = [r.replace("-", "–") for r in p.get("refs", [])]
        refs = "; ".join(rs[:2]) + (" and more" if len(rs) > 2 else "")
        desc = (f"{short(p['text'][0], 170)} ({refs})" if p.get("text") else f"A prayer the Bible itself records: {refs}.")
        img = next((images[x] for x in p.get("paths", []) if x in images), OG_PRAYERS)
        written.append(page(out, f"pray/{p['id']}/", p["title"] if "prayer" in p["title"].lower() else f"{p['title']}: a prayer", desc, img,
                            f"../../#/prayers/{p['id']}", "A prayer", "🙏 Pray it in BibleChat"))
    return written


if __name__ == "__main__":
    n = write_share_pages(sys.argv[1])
    print(f"share pages: {len(n)}")
