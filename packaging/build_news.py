"""📰 In the news: picks one or two of today's headlines that touch a prophecy theme, for the Home screen.

Runs in the "Publish phone version" workflow (on every publish and twice a day on a timer). It reads the news feeds
listed in web/prophecy.json, matches every headline to the themes there (the same word rules as web/news.js), and
writes news.json next to the published site:

  {"updated": "2026-10-30T22:17:00Z", "picks": [ {title, link, source, label, theme, words, date} ... ], "more": [...]}

The picks come from different themes and, where possible, different kinds of source (Mainstream, Israeli press,
Christian, Alternative / independent), so the Home screen never shows one side only. A feed that fails is skipped;
if every feed fails, the file says so and the app simply shows the box for pasting a headline.

Usage:  python packaging/build_news.py OUT.json            (fetch the feeds)
        python packaging/build_news.py OUT.json --feed F  (read saved feed files instead, for tests; F may repeat)
"""
from __future__ import annotations

import datetime as dt
import email.utils
import html
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROPHECY = os.path.join(ROOT, "web", "prophecy.json")
MAX_AGE_HOURS = 60


def load_themes(path: str = PROPHECY) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def norm(s: str) -> str:
    return " " + re.sub(r"[^a-z0-9]+", " ", html.unescape(s).lower()).strip() + " "


def match(title: str, themes: list) -> list:
    """[(theme, [words found])] best first: a word or phrase counts when it stands whole in the headline."""
    t = norm(title)
    out = []
    for th in themes:
        found = [w for w in th["words"] if norm(w) in t]
        if found:
            out.append((th, found))
    out.sort(key=lambda x: -len(x[1]))
    return out


def parse_feed(xml_text: str, source: dict) -> list:
    """The items of an RSS feed: title, link, date. Google News adds " - Source" to titles; that is removed."""
    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        if not title or not link.startswith("http"):
            continue
        title = re.sub(r"\s+-\s+[^-]{2,60}$", "", title) if "news.google.com" in source["feed"] else title
        when = None
        raw = it.findtext("pubDate")
        if raw:
            try:
                when = email.utils.parsedate_to_datetime(raw).astimezone(dt.timezone.utc)
            except (TypeError, ValueError):
                when = None
        items.append({"title": html.unescape(title), "link": link, "source": source["name"], "label": source["label"],
                      "date": when.strftime("%Y-%m-%dT%H:%M:%SZ") if when else None})
    return items


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "BibleChat news picker (+https://beaugrand.github.io/BibleChat-voice/)"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "replace")


def choose(items: list, data: dict, now: dt.datetime) -> dict:
    themes = data["themes"]
    scored = []
    for it in items:
        if it["date"]:
            age = (now - dt.datetime.strptime(it["date"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)).total_seconds() / 3600
            if age > MAX_AGE_HOURS or age < -6:
                continue
        m = match(it["title"], themes)
        if not m:
            continue
        th, found = m[0]
        scored.append(dict(it, theme=th["id"], words=found, score=len(found)))
    scored.sort(key=lambda x: (x["score"], x["date"] or ""), reverse=True)
    picks, used_t, used_l, seen = [], set(), set(), set()
    for want_new_label in (True, False):          # first try a new theme from a new kind of source, then any new theme
        for x in scored:
            if len(picks) == 2:
                break
            key = norm(x["title"])
            if key in seen or x["theme"] in used_t or (want_new_label and x["label"] in used_l):
                continue
            picks.append(x); used_t.add(x["theme"]); used_l.add(x["label"]); seen.add(key)
    more = []
    for x in scored:
        key = norm(x["title"])
        if key not in seen and len(more) < 8:
            more.append(x); seen.add(key)
    clean = lambda xs: [{k: x[k] for k in ("title", "link", "source", "label", "theme", "words", "date")} for x in xs]
    return {"updated": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "picks": clean(picks), "more": clean(more)}


def main(argv: list) -> int:
    if not argv:
        print(__doc__)
        return 2
    out = argv[0]
    data = load_themes()
    items, report = [], []
    saved = [argv[i + 1] for i, a in enumerate(argv) if a == "--feed" and i + 1 < len(argv)]
    if saved:
        for i, path in enumerate(saved):
            with open(path, encoding="utf-8") as f:
                items += parse_feed(f.read(), data["sources"][i % len(data["sources"])])
    else:
        for s in data["sources"]:
            try:
                got = parse_feed(fetch(s["feed"]), s)
                items += got
                report.append(f"{s['name']}: {len(got)}")
            except Exception as e:   # one feed down never stops the others, or the site
                report.append(f"{s['name']}: failed ({type(e).__name__})")
    res = choose(items, data, dt.datetime.now(dt.timezone.utc))
    if not items:
        res["note"] = "No news feed could be read this time."
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("feeds:", "; ".join(report) or "saved files")
    print("picks:", " | ".join(f"[{p['label']}] {p['title']} -> {p['theme']}" for p in res["picks"]) or "none")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
