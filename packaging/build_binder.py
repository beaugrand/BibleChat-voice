"""Walking with Yeshua: a sample PDF for a US Letter ring binder.

Builds the cover, the welcome page and one study path (default: Forgiveness).

    python packaging/build_binder.py . COVER_IMAGE OUT.pdf [path-id] [--no-lines]

COVER_IMAGE is the approved cover picture (Hans's Google Drive: "Walking with Yeshua – Cover Image (22 Nov 2026).png");
it is not stored in this repository. This is the first sample (22 Nov 2026), to check the margins in a real binder
before the "Export the book" button is built.

Rules from the binder spec (22 Nov 2026):
- US Letter, a wide LEFT margin for the punched holes (every page is printed on one side).
- No page numbers. A small label in the top outer corner says which path and step, so a loose page can be re-filed.
- Verse text comes word for word from the Yahweh Edition in bibles/. Nothing here is AI-written Scripture.
- QR codes are plain links. Nothing about the reader is in them.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

from PIL import Image
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable, Frame, Image as RLImage, KeepTogether,
                                NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle)

SITE = "https://beaugrand.github.io/BibleChat-voice"
CASHAPP = "https://cash.app/$HansBeaugrand"
VENMO = "https://venmo.com/u/Hans-Beaugrand"

PAGE_W, PAGE_H = letter                 # 8.5 x 11 inches
LEFT = 1.25 * inch                      # wide margin on the hole side
RIGHT = 0.75 * inch
TOP = 0.85 * inch
BOTTOM = 0.75 * inch

INK = HexColor("#2b2118")               # warm dark brown, prints well in black and white too
SOFT = HexColor("#7a6a58")
LINE = HexColor("#c9bfb2")

WELCOME = ("I made this book because I wanted to go back to the roots of Scripture. I wanted to use today's technology "
           "to look at the original languages, down to the letters themselves, like Paleo Hebrew and Ge'ez. This study "
           "holds the 66 books we have all been handed, and it also makes room for the books of the Ethiopian canon, "
           "because both are dear to my heart. Walk with me, and let's go back to the source.")

# ---------------------------------------------------------------- styles
S = {
    "h1": ParagraphStyle("h1", fontName="Times-Bold", fontSize=26, leading=31, textColor=INK, spaceAfter=10),
    "h2": ParagraphStyle("h2", fontName="Times-Bold", fontSize=17, leading=21, textColor=INK, spaceBefore=6, spaceAfter=6),
    "step": ParagraphStyle("step", fontName="Times-Italic", fontSize=12, leading=15, textColor=SOFT, spaceAfter=2),
    "q": ParagraphStyle("q", fontName="Times-Bold", fontSize=13, leading=17, textColor=INK, spaceAfter=8),
    "apply": ParagraphStyle("apply", fontName="Times-Italic", fontSize=12.5, leading=16.5, textColor=INK, spaceBefore=4, spaceAfter=4),
    "ref": ParagraphStyle("ref", fontName="Times-Bold", fontSize=11.5, leading=15, textColor=INK, spaceBefore=6, spaceAfter=1),
    "verse": ParagraphStyle("verse", fontName="Times-Roman", fontSize=11.5, leading=15, textColor=INK),
    "body": ParagraphStyle("body", fontName="Times-Roman", fontSize=12.5, leading=17.5, textColor=INK, spaceAfter=8),
    "small": ParagraphStyle("small", fontName="Times-Roman", fontSize=9, leading=11.5, textColor=SOFT),
    "smallc": ParagraphStyle("smallc", fontName="Times-Roman", fontSize=9.5, leading=12, textColor=SOFT, alignment=TA_CENTER),
    "list": ParagraphStyle("list", fontName="Times-Roman", fontSize=12, leading=16, textColor=INK, leftIndent=14),
    "prayer": ParagraphStyle("prayer", fontName="Times-Roman", fontSize=14, leading=21, textColor=INK, spaceAfter=12),
}


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------- Scripture
def load_verses(repo: str) -> dict:
    sys.path.insert(0, repo)
    from bibleask.loaders import load_bible
    b = load_bible(os.path.join(repo, "bibles", "eng-yahweh-edition.usfx.xml"))
    return {(v.book, v.chapter, v.verse): v.text for v in b.verses}


REF = re.compile(r"^(.+?) (\d+):(\d+)(?:-(\d+))?$")


def verses_of(text: dict, ref: str) -> list[tuple[int, str]]:
    m = REF.match(ref)
    if not m:
        raise ValueError(f"cannot read the reference {ref!r}")
    book, ch, a, b = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4) or m.group(3))
    out = [(v, text[(book, ch, v)]) for v in range(a, b + 1) if (book, ch, v) in text]
    if len(out) != b - a + 1:
        raise ValueError(f"{ref}: missing verses in the Yahweh Edition")
    return out


def scripture(text: dict, ref: str) -> list:
    """One reference: its heading, then the verses as one paragraph with small verse numbers."""
    parts = [f'<font size="7.5" color="#7a6a58"><super>{n}</super></font>{esc(t)}' for n, t in verses_of(text, ref)]
    return [Paragraph(esc(ref), S["ref"]), Paragraph(" ".join(parts), S["verse"])]


# ---------------------------------------------------------------- small pieces
def qr(url: str, size: float) -> Drawing:
    w = QrCodeWidget(url, barLevel="M")
    x0, y0, x1, y1 = w.getBounds()
    d = Drawing(size, size, transform=[size / (x1 - x0), 0, 0, size / (y1 - y0), 0, 0])
    d.add(w)
    return d


class WritingLines(Flowable):
    """Ruled lines that fill the rest of the page (at least `minimum` tall)."""

    def __init__(self, gap: float = 0.36 * inch, minimum: float = 1.6 * inch, title: str = "My notes"):
        super().__init__()
        self.gap, self.minimum, self.title = gap, minimum, title

    def wrap(self, aw, ah):
        self.w = aw
        self.h = ah - 2 if ah >= self.minimum else self.minimum
        return aw, self.h

    def draw(self):
        c = self.canv
        c.setFont("Times-Italic", 10.5)
        c.setFillColor(SOFT)
        c.drawString(0, self.h - 12, self.title)
        c.setStrokeColor(LINE)
        c.setLineWidth(0.6)
        y = self.h - 12 - self.gap
        while y > 4:
            c.line(0, y, self.w, y)
            y -= self.gap


class Label(Flowable):
    """Invisible marker: sets the corner label for the page it lands on (and the pages after it)."""

    def __init__(self, text: str):
        super().__init__()
        self.text = text

    def wrap(self, aw, ah):
        return 0, 0

    def draw(self):
        self.canv._binder_label = self.text


# ---------------------------------------------------------------- pages
def draw_corner_label(c, doc):
    label = getattr(c, "_binder_label", "")
    if not label:
        return
    c.saveState()
    c.setFont("Times-Italic", 9.5)
    c.setFillColor(SOFT)
    c.drawRightString(PAGE_W - RIGHT, PAGE_H - 0.5 * inch, label)
    c.setStrokeColor(LINE)
    c.setLineWidth(0.5)
    c.line(PAGE_W - RIGHT - 2.2 * inch, PAGE_H - 0.58 * inch, PAGE_W - RIGHT, PAGE_H - 0.58 * inch)
    c.restoreState()


def draw_cover(c, doc, cover_path: str):
    """Full-page picture, title in the open sky, author, and one QR code to the app."""
    img = Image.open(cover_path).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=95)
    buf.seek(0)
    iw, ih = img.size
    scale = max(PAGE_W / iw, PAGE_H / ih)          # fill the page, crop what is left over
    w, h = iw * scale, ih * scale
    c.drawImage(ImageReader(buf), (PAGE_W - w) / 2, PAGE_H - h, w, h)   # keep the top (the sky), crop the bottom

    # a soft light wash behind the title so it reads on the bright sky
    c.saveState()
    for i in range(40):
        c.setFillColor(Color(1, 0.98, 0.93, alpha=0.018))
        c.rect(0, PAGE_H - 2.6 * inch + i * 0.03 * inch, PAGE_W, 2.6 * inch, stroke=0, fill=1)
    c.restoreState()

    c.setFillColor(INK)
    c.setFont("Times-Bold", 46)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 1.25 * inch, "Walking with Yeshua")
    c.setFont("Times-Italic", 20)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 1.72 * inch, "Study paths, scripture and prayers")
    c.setFont("Times-Roman", 16)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 2.15 * inch, "Hans W. Beaugrand")

    # QR code in a white card, bottom left on the grass
    size, pad = 1.05 * inch, 0.1 * inch
    x, y = 0.6 * inch, 0.6 * inch
    c.setFillColor(white)
    c.roundRect(x - pad, y - pad - 0.22 * inch, size + 2 * pad, size + 2 * pad + 0.22 * inch, 6, stroke=0, fill=1)
    renderPDF.draw(qr(SITE, size), c, x, y)
    c.setFillColor(INK)
    c.setFont("Times-Roman", 8.5)
    c.drawCentredString(x + size / 2, y - 0.17 * inch, "Open BibleChat")


def welcome(repo: str) -> list:
    out = [Label("Welcome"), Spacer(1, 0.4 * inch), Paragraph("Welcome", S["h1"]), Spacer(1, 6),
           Paragraph(esc(WELCOME), S["body"]),
           Paragraph("<i>Hans W. Beaugrand</i>", ParagraphStyle("sig", parent=S["body"], fontSize=14, spaceBefore=4)),
           Spacer(1, 0.55 * inch)]

    gift = ParagraphStyle("gift", parent=S["body"], fontSize=12, leading=16)
    out += [Paragraph("Love Donations", S["h2"]),
            Paragraph("This book and the BibleChat app are free, and they will stay free. If they bless you and you "
                      "would like to help, a gift of any size is welcome, only if you want to.", gift),
            Spacer(1, 8)]
    cells = [[qr(CASHAPP, 1.15 * inch), qr(VENMO, 1.15 * inch)],
             [Paragraph("Cash App<br/><b>$HansBeaugrand</b>", S["smallc"]),
              Paragraph("Venmo<br/><b>@Hans-Beaugrand</b>", S["smallc"])]]
    t = Table(cells, colWidths=[1.9 * inch, 1.9 * inch], hAlign="LEFT")
    t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    out += [t, Spacer(1, 0.5 * inch),
            Paragraph("The QR codes in this book are plain links. Nothing about you is saved, and no account is needed.",
                      S["small"]),
            Spacer(1, 4),
            Paragraph("Scripture: Yahweh Edition, based on the World Messianic Bible (public domain), with God's Name "
                      "written “Yahweh”. Questions and prayers are written for BibleChat; they are the words "
                      "of a man, not Scripture. BibleChat by Hans W. Beaugrand, Apache License 2.0.", S["small"]),
            PageBreak()]
    return out


def study_path(repo: str, text: dict, path_id: str, lines: bool) -> list:
    p = json.load(open(os.path.join(repo, "web", "paths", f"{path_id}.json"), encoding="utf-8"))
    name = p["title"].split(":")[0].strip()           # "Forgiveness: seventy times seven" -> "Forgiveness"
    steps = p["steps"]
    n = len(steps)

    # 1. title page: name, picture, QR code, Scripture list by step
    out = [Label(f"{name}, title page"), Paragraph(esc(p["title"]), S["h1"])]
    pic = os.path.join(repo, "web", "paths", p.get("image", ""))
    qr_size = 1.3 * inch
    left = []
    if os.path.isfile(pic):
        iw, ih = Image.open(pic).size
        w = PAGE_W - LEFT - RIGHT - qr_size - 0.35 * inch
        h = min(w * ih / iw, 3.0 * inch)
        left = [RLImage(pic, width=h * iw / ih, height=h)]
    right = [qr(f"{SITE}/p/{path_id}/", qr_size), Paragraph("Open this path<br/>in BibleChat", S["smallc"])]
    t = Table([[left, right]], colWidths=[PAGE_W - LEFT - RIGHT - qr_size - 0.2 * inch, qr_size + 0.2 * inch])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("ALIGN", (1, 0), (1, 0), "CENTER")]))
    out += [t, Spacer(1, 10), Paragraph(esc(p["opening_question"]), S["apply"]), Spacer(1, 6),
            Paragraph("Scripture in this path", S["h2"])]
    for i, s in enumerate(steps, 1):
        out.append(Paragraph(f"<b>Step {i}.</b> " + esc("; ".join(s["refs"])), S["list"]))
    out.append(PageBreak())

    # 2. one page per step: verses, question, writing space
    for i, s in enumerate(steps, 1):
        out += [Label(f"{name}, step {i} of {n}"), Paragraph(f"Step {i} of {n}", S["step"]),
                Paragraph(esc(s["question"]), S["q"])]
        for ref in s["refs"]:
            out += scripture(text, ref)
        out += [Spacer(1, 10), KeepTogether([Paragraph("For me: " + esc(s["apply"]), S["apply"])])]
        if lines:
            out += [Spacer(1, 6), CondPageBreak(1.6 * inch), WritingLines()]
        out.append(PageBreak())

    # 3. the closing prayer on its own page
    prayers = json.load(open(os.path.join(repo, "web", "prayers.json"), encoding="utf-8"))["prayers"]
    pr = next(x for x in prayers if path_id in x.get("paths", []))
    out += [Label(f"{name}, closing prayer"), Spacer(1, 0.5 * inch), Paragraph("A closing prayer", S["step"]),
            Paragraph(esc(pr["title"]), S["h1"]), Spacer(1, 8)]
    out += [Paragraph(esc(par), S["prayer"]) for par in pr["text"]]
    out += [Spacer(1, 10), Paragraph("Drawn from " + esc("; ".join(pr["refs"])), S["small"]), PageBreak()]

    # 4. Living it out: the verses to remember (Yahweh Edition text), then space to write
    out += [Label(f"{name}, living it out"), Paragraph("Living it out", S["h1"]),
            Paragraph("Verses to remember", S["h2"])]
    for r in p.get("remember", []):
        for ref in r["refs"]:
            out += scripture(text, ref)
    if lines:
        out += [Spacer(1, 14), CondPageBreak(1.6 * inch), WritingLines(title="What I will do")]
    return out


def build(repo: str, cover: str, out_pdf: str, path_id: str = "forgiveness", lines: bool = True) -> None:
    text = load_verses(repo)
    doc = BaseDocTemplate(out_pdf, pagesize=letter, title="Walking with Yeshua (sample)",
                          author="Hans W. Beaugrand", subject="Study paths, scripture and prayers",
                          leftMargin=LEFT, rightMargin=RIGHT, topMargin=TOP, bottomMargin=BOTTOM)
    full = Frame(0, 0, PAGE_W, PAGE_H, id="full", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    body = Frame(LEFT, BOTTOM, PAGE_W - LEFT - RIGHT, PAGE_H - TOP - BOTTOM, id="body",
                 leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate("cover", [full], onPage=lambda c, d: draw_cover(c, d, cover)),
                          PageTemplate("page", [body], onPageEnd=draw_corner_label)])
    story = [NextPageTemplate("page"), PageBreak()]
    story += welcome(repo)
    story += study_path(repo, text, path_id, lines)
    doc.build(story)


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    build(a[0], a[1], a[2], a[3] if len(a) > 3 else "forgiveness", "--no-lines" not in sys.argv)
    print("wrote", a[2])
