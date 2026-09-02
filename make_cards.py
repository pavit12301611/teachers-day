#!/usr/bin/env python3
"""
make_cards.py — generate St_Marys_Teacher_Cards_A4-fold.pdf

One A4 LANDSCAPE sheet per teacher, printed DOUBLE-SIDED —
A4 LANDSCAPE, FLIP ON SHORT EDGE (the vertical fold needs the page
to flip about the short edge; flipping on the long edge prints the
inside upside down):

  Sheet side 1 (OUTER)   :  [ BACK / logo ]  |  [ FRONT / photo + name ]
  Sheet side 2 (INSIDE)  :  [ THE MESSAGE ]  |  [ BIG QR + secrets ]

Fold the sheet in half along the dashed centre line (inside facing you,
right half folded over the left) and you get a standing card:
front cover on the front, logo-back on the back, message + QR inside.
The panel order is mirrored for the duplex flip, so nothing comes out
upside down.

QR codes point at the live per-teacher page, e.g.
  https://teachers-day-rosy.vercel.app/teacher.html?t=p001

Usage:
  python3 make_cards.py                 # build the PDF
  python3 make_cards.py --extract       # re-extract card_messages.json
                                        #   from the old PDF first

Depends on: reportlab, pillow, qrcode  (pip install reportlab pillow qrcode)
"""

import json
import os
import re
import sys
import math
import random

import qrcode
from PIL import Image

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

# --------------------------------------------------------------------------
# paths
# --------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_JS = os.path.join(ROOT, "js", "data.js")
MESSAGES_JSON = os.path.join(ROOT, "card_messages.json")
OLD_PDF = os.path.join(ROOT, "St_Marys_Teacher_Cards_A4-fold.pdf")
OUT_PDF = os.path.join(ROOT, "St_Marys_Teacher_Cards_A4-fold.pdf")
BUILD = "/tmp/cardbuild"
os.makedirs(BUILD, exist_ok=True)

SITE = "https://teachers-day-rosy.vercel.app"

# --------------------------------------------------------------------------
# fonts (system DejaVu — same family the original cards used)
# --------------------------------------------------------------------------
FDIR = "/usr/share/fonts/truetype/dejavu"
pdfmetrics.registerFont(TTFont("Serif", os.path.join(FDIR, "DejaVuSerif.ttf")))
pdfmetrics.registerFont(TTFont("Serif-B", os.path.join(FDIR, "DejaVuSerif-Bold.ttf")))
pdfmetrics.registerFont(TTFont("Sans", os.path.join(FDIR, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("Sans-B", os.path.join(FDIR, "DejaVuSans-Bold.ttf")))
ITALIC = "Times-Italic"      # built-in PDF font, elegant script-ish italic
ITALIC_B = "Times-BoldItalic"

# --------------------------------------------------------------------------
# colours
# --------------------------------------------------------------------------
INK = HexColor("#2a2440")
MUTED = HexColor("#7c7693")
FAINT = HexColor("#a7a1b8")
GOLD = HexColor("#b0862f")
WHITE = HexColor("#ffffff")
PAPER = HexColor("#fdfbff")
RAINBOW = ["#f43f5e", "#fb923c", "#facc15", "#4ade80",
           "#22d3ee", "#6366f1", "#a855f7"]
FLOWER_COLS = [HexColor("#ec4899"), HexColor("#f59e0b"),
               HexColor("#3b82f6"), HexColor("#8b5cf6"),
               HexColor("#10b981")]
LEAF = HexColor("#7cb342")

SUBJECT_LABEL = {
    "english": "English", "maths": "Mathematics", "science": "Science",
    "pe": "Physical Education", "computer": "Computer Science",
    "social": "Social Studies", "music": "Music", "hindi": "Hindi",
    "sanskrit": "Sanskrit",
}

# --------------------------------------------------------------------------
# data loading
# --------------------------------------------------------------------------
def load_teachers():
    src = open(DATA_JS, encoding="utf-8").read()
    m = re.search(r"window\.SITE_DATA\s*=\s*(\{.*?\});\s*$", src, re.S)
    data = json.loads(m.group(1))
    out = []
    for t in data["teachers"]:
        theme = t["theme"]
        out.append({
            "id": t["id"], "num": t["num"], "name": t["name"],
            "title": t.get("title") or "",
            "designation": t["designation"], "group": t["group"],
            "qual": (t.get("qualification") or "").strip(),
            "subject": SUBJECT_LABEL.get(t.get("subject", "default")),
            "photo": os.path.join(ROOT, t["photo"]),
            "c1": HexColor(theme["c1"]), "c2": HexColor(theme["c2"]),
            "soft": HexColor(theme["soft"]),
        })
    return out


def extract_messages():
    """Pull every teacher's personalised letter out of the old PDF."""
    import pymupdf
    doc = pymupdf.open(OLD_PDF)
    MID = 841.89 / 2

    def norm(s):
        return s.replace(" ", "").upper()

    def lines_of(pno):
        d = doc[pno].get_text("dict")
        lines = []
        for b in d["blocks"]:
            if b["type"] != 0:
                continue
            for l in b["lines"]:
                txt = "".join(s["text"] for s in l["spans"]).strip()
                if not txt:
                    continue
                x0, y0, x1, y1 = l["bbox"]
                lines.append({"x": (x0 + x1) / 2, "y": y0, "text": txt})
        lines = [l for l in lines
                 if not (abs(l["x"] - MID) < 40 and norm(l["text"]) == "FOLD")]
        return sorted(lines, key=lambda l: (l["y"], l["x"]))

    msgs = {}
    for t in range(83):
        lines = lines_of(t * 2 + 1)
        left = [l["text"] for l in lines if l["x"] < MID]
        right = [l["text"] for l in lines if l["x"] >= MID]
        gi = next(i for i, x in enumerate(left) if x.startswith("Dear "))
        wi = next(i for i, x in enumerate(left) if x.startswith("With love"))
        body = [x for x in left[gi + 1:wi]]
        rh = next(i for i, x in enumerate(left)
                  if norm(x).startswith("THREETHINGS"))
        things = [re.sub(r"^[\W_]+", "", x).strip()
                  for x in left[rh + 1:rh + 4]]
        url = next((x for x in right if "teacher.html" in x.replace(" ", "")), "")
        m = re.search(r"t=(p\d+)", url.replace(" ", ""))
        tid = m.group(1) if m else f"p{t + 1:03d}"
        msgs[tid] = {"greeting": left[gi], "body": body, "things": things}
    json.dump(msgs, open(MESSAGES_JSON, "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print(f"extracted {len(msgs)} messages -> {MESSAGES_JSON}")


# --------------------------------------------------------------------------
# image prep
# --------------------------------------------------------------------------
def prep_photo(path, num):
    """Square-crop + round the corners of the logo-style frame not needed;
    we circle-clip in the PDF, just return a centred square JPEG."""
    out = os.path.join(BUILD, f"photo_{num:03d}.jpg")
    if not os.path.exists(out):
        im = Image.open(path).convert("RGB")
        w, h = im.size
        s = min(w, h)
        im = im.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2))
        im = im.resize((640, 640), Image.LANCZOS)
        im.save(out, "JPEG", quality=82)
    return out


def prep_logo():
    out = os.path.join(BUILD, "logo_rounded.png")
    if not os.path.exists(out):
        im = Image.open(os.path.join(ROOT, "logo.png")).convert("RGBA")
        im = im.resize((240, 240), Image.LANCZOS)
        # rounded corners with transparent padding
        mask = Image.new("L", (240, 240), 0)
        from PIL import ImageDraw
        d = ImageDraw.Draw(mask)
        d.rounded_rectangle((0, 0, 239, 239), radius=44, fill=255)
        canvas_img = Image.new("RGBA", (260, 260), (0, 0, 0, 0))
        canvas_img.paste(im, (10, 10), mask)
        canvas_img.save(out)
    return out


def make_qr(url, name):
    out = os.path.join(BUILD, name)
    if not os.path.exists(out):
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                           box_size=12, border=3)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color=(38, 30, 64), back_color="white")
        img = img.convert("RGB")
        img.save(out, "PNG")
    return out


# --------------------------------------------------------------------------
# low-level drawing helpers
# --------------------------------------------------------------------------
def tracked(c, cx, y, text, font, size, color, track=0.6, char=None):
    """Centre-aligned letter-spaced caps text."""
    c.setFont(font, size)
    c.setFillColor(color)
    if char is None:
        char = track * size
    widths = [c.stringWidth(ch, font, size) for ch in text]
    total = sum(widths) + char * (len(text) - 1)
    x = cx - total / 2
    for ch, w in zip(text, widths):
        c.drawString(x, y, ch)
        x += w + char


def tracked_left(c, x, y, text, font, size, color, track=0.6, char=None):
    c.setFont(font, size)
    c.setFillColor(color)
    if char is None:
        char = track * size
    for ch in text:
        c.drawString(x, y, ch)
        x += c.stringWidth(ch, font, size) + char


def tracked_right(c, x, y, text, font, size, color, track=0.6, char=None):
    c.setFont(font, size)
    c.setFillColor(color)
    if char is None:
        char = track * size
    total = sum(c.stringWidth(ch, font, size) for ch in text) + char * (len(text) - 1)
    cx = x - total
    for ch in text:
        c.drawString(cx, y, ch)
        cx += c.stringWidth(ch, font, size) + char


def wrap(c, text, font, size, maxw):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if c.stringWidth(trial, font, size) <= maxw:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit_size(c, text, font, size, maxw, floor=14.5):
    while size > floor and c.stringWidth(text, font, size) > maxw:
        size -= 0.5
    return size


def dashed(c, x1, y, x2, color=FAINT, width=0.8, dash=(2.5, 3)):
    c.setStrokeColor(color)
    c.setLineWidth(width)
    c.setDash(dash)
    c.line(x1, y, x2, y)
    c.setDash()


def gold_rule(c, cx, y, halfw, color=GOLD):
    c.setStrokeColor(color)
    c.setLineWidth(0.9)
    c.line(cx - halfw, y, cx - 8, y)
    c.line(cx + 8, y, cx + halfw, y)
    c.setFont("Sans", 9)
    c.setFillColor(color)
    c.drawCentredString(cx, y - 3.2, "\u2726")  # ✦


# --------------------------------------------------------------------------
# panel decoration
# --------------------------------------------------------------------------
def panel_base(c, x, y, w, h, t, seed):
    """White card + pastel washes + rainbow edge + confetti + corner doodles.
    All decoration is clipped inside the card. Returns the panel top y."""
    rng = random.Random(seed * 7919 + 13)

    # white card first
    c.setFillColor(WHITE)
    c.setStrokeColor(t["c1"])
    c.setLineWidth(1.3)
    c.roundRect(x, y, w, h, 16, stroke=1, fill=1)

    # everything decorative stays inside the rounded card
    c.saveState()
    p = c.beginPath()
    p.roundRect(x, y, w, h, 16)
    c.clipPath(p, stroke=0, fill=0)

    # soft pastel washes on the card
    blob_cols = [t["c1"], t["c2"],
                 HexColor("#f9a8d4"), HexColor("#fcd34d"),
                 HexColor("#93c5fd"), HexColor("#a7f3d0")]
    for _ in range(5):
        bx = x + rng.random() * w
        by = y + rng.random() * h
        br = 55 + rng.random() * 85
        c.setFillColor(blob_cols[rng.randrange(len(blob_cols))])
        c.setFillAlpha(0.07)
        c.circle(bx, by, br, stroke=0, fill=1)
    c.setFillAlpha(1)

    # rainbow edge: skinny rainbow bars on top & bottom inside the card
    bar = 4.2
    n = len(RAINBOW)
    seg = w / n
    for i, col in enumerate(RAINBOW):
        c.setFillColor(HexColor(col))
        c.setFillAlpha(0.92)
        c.rect(x + i * seg, y + h - bar, seg + 1, bar, stroke=0, fill=1)
        c.rect(x + i * seg, y, seg + 1, bar, stroke=0, fill=1)
    c.setFillAlpha(1)

    # confetti speckles (edges only, so text stays clear)
    for _ in range(30):
        sx = x + 16 + rng.random() * (w - 32)
        sy = y + 16 + rng.random() * (h - 32)
        fx, fy = (sx - x) / w, (sy - y) / h
        if 0.16 < fx < 0.84 and 0.10 < fy < 0.90:
            continue
        c.setFillColor(HexColor(RAINBOW[rng.randrange(n)]))
        c.setFillAlpha(0.6)
        r = rng.random()
        if r < 0.55:
            c.circle(sx, sy, 1.0 + rng.random() * 1.1, stroke=0, fill=1)
        elif r < 0.8:
            s = 1.9
            c.saveState()
            c.translate(sx, sy)
            c.rotate(rng.random() * 180)
            c.rect(-s / 2, -s / 2, s, s * 0.55, stroke=0, fill=1)
            c.restoreState()
        else:
            c.setFont("Sans", 6)
            c.drawCentredString(sx, sy - 2, "\u2726")
    c.setFillAlpha(1)

    # flower vine along the bottom (also clipped inside the card)
    vine(c, x + 30, x + w - 30, y + 29, t, rng)
    c.restoreState()   # end clip

    # corner doodles on the white border
    c.setStrokeColor(t["c2"])
    c.setLineWidth(1.4)
    for (cx0, cy0, dx, dy) in [
        (x + 14, y + h - 30, 15, -13), (x + w - 14, y + h - 30, -15, -13),
        (x + 14, y + 30, 15, 13), (x + w - 14, y + 30, -15, 13)]:
        c.line(cx0, cy0, cx0 + dx, cy0 + dy)
    c.setFillColor(t["c1"])
    for (cx0, cy0) in [(x + 32, y + h - 20), (x + w - 32, y + h - 20),
                       (x + 32, y + 20), (x + w - 32, y + 20)]:
        c.circle(cx0, cy0, 1.7, stroke=0, fill=1)
    return y + h


def vine(c, x0, x1, y, t, rng):
    c.setStrokeColor(HexColor("#c9b458"))
    c.setLineWidth(0.9)
    p = c.beginPath()
    p.moveTo(x0, y)
    steps = 6
    for i in range(steps):
        xa = x0 + (x1 - x0) * (i + 0.33) / steps
        xb = x0 + (x1 - x0) * (i + 0.66) / steps
        xc = x0 + (x1 - x0) * (i + 1) / steps
        up = 5.5 if i % 2 == 0 else -5.5
        p.curveTo(xa, y + up, xb, y - up, xc, y)
    c.drawPath(p, stroke=1, fill=0)
    # leaves
    for i in range(steps):
        lx = x0 + (x1 - x0) * (i + 0.5) / steps
        ly = y + (4 if i % 2 == 0 else -4)
        c.setFillColor(LEAF)
        c.saveState()
        c.translate(lx, ly)
        c.rotate(25 if i % 2 == 0 else -25)
        c.ellipse(-4, -1.8, 4, 1.8, stroke=0, fill=1)
        c.restoreState()
    # flowers
    c.setFont("Sans", 12.5)
    spots = [0.12, 0.5, 0.88]
    for j, s in enumerate(spots):
        fx = x0 + (x1 - x0) * s
        fy = y + (6 if j % 2 == 0 else -7)
        c.setFillColor(FLOWER_COLS[j % len(FLOWER_COLS)])
        c.drawCentredString(fx, fy - 4, "\u273f")  # ✿
    c.setFillColor(INK)


# --------------------------------------------------------------------------
# shared widgets
# --------------------------------------------------------------------------
def badge(c, cx, cy, num, c2, c1):
    # serrated rosette
    pts = []
    teeth = 26
    for i in range(teeth * 2):
        ang = math.pi * i / teeth
        r = 27 if i % 2 == 0 else 23.5
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    p = c.beginPath()
    p.moveTo(*pts[0])
    for px, py in pts[1:]:
        p.lineTo(px, py)
    p.close()
    c.setFillColor(c2)
    c.setStrokeColor(WHITE)
    c.setLineWidth(1.6)
    c.drawPath(p, stroke=1, fill=1)
    c.setFillColor(WHITE)
    c.circle(cx, cy, 17.5, stroke=0, fill=1)
    c.setFillColor(c1)
    c.setFont("Sans-B", 12.5)
    c.drawCentredString(cx, cy - 4.4, f"{num:02d}")
    c.setFont("Sans-B", 5.6)
    c.drawCentredString(cx, cy - 11.5, "OF 83")


def ribbon(c, cx, cy, text, c2):
    c.setFont("Sans-B", 9.5)
    tw = c.stringWidth(text, "Sans-B", 9.5)
    rw = tw + 30
    rh = 19
    # tails
    for sgn in (-1, 1):
        ex = cx + sgn * rw / 2
        p = c.beginPath()
        p.moveTo(ex, cy + rh / 2)
        p.lineTo(ex + sgn * 13, cy)
        p.lineTo(ex, cy - rh / 2)
        p.close()
        c.setFillColor(c2)
        c.drawPath(p, stroke=0, fill=1)
    c.setFillColor(c2)
    c.roundRect(cx - rw / 2, cy - rh / 2, rw, rh, 3, stroke=0, fill=1)
    c.setFillColor(WHITE)
    c.drawCentredString(cx, cy - 3.2, text)


def pill(c, cx, cy, text, font, size, fill, txtcol, padx=12, h=20,
         stroke=None):
    c.setFont(font, size)
    tw = c.stringWidth(text, font, size)
    w = tw + 2 * padx
    if stroke is not None:
        c.setFillColor(WHITE)
        c.setStrokeColor(stroke)
        c.setLineWidth(1.1)
    else:
        c.setFillColor(fill)
        c.setStrokeColor(fill)
    c.roundRect(cx - w / 2, cy - h / 2, w, h, h / 2, stroke=1 if stroke else 0,
                fill=1)
    c.setFillColor(txtcol)
    c.drawCentredString(cx, cy - size * 0.35, text)
    return h


def circle_photo(c, cx, cy, r, img, t):
    # soft halo
    c.setFillColor(t["soft"])
    c.setFillAlpha(0.9)
    c.circle(cx, cy, r + 15, stroke=0, fill=1)
    c.setFillAlpha(1)
    c.setFillColor(t["c1"])
    c.setFillAlpha(0.12)
    c.circle(cx + 8, cy - 8, r + 9, stroke=0, fill=1)
    c.setFillAlpha(1)
    # photo clipped to circle
    c.saveState()
    p = c.beginPath()
    p.circle(cx, cy, r)
    c.clipPath(p, stroke=0, fill=0)
    c.drawImage(ImageReader(img), cx - r, cy - r, 2 * r, 2 * r, mask=None)
    c.restoreState()
    # ring
    c.setStrokeColor(t["c1"])
    c.setLineWidth(2.2)
    c.circle(cx, cy, r, stroke=1, fill=0)
    c.setStrokeColor(t["c2"])
    c.setLineWidth(0.8)
    c.circle(cx, cy, r + 3.2, stroke=1, fill=0)


def qr_card(c, cx, cy, size, qr_path, t, url):
    """White rounded card with a QR inside + soft shadow."""
    s = size
    # shadow
    c.setFillColor(HexColor("#3a2f55"))
    c.setFillAlpha(0.12)
    c.roundRect(cx - s / 2 + 2.5, cy - s / 2 - 2.5, s, s, 12, stroke=0, fill=1)
    c.setFillAlpha(1)
    # card
    c.setFillColor(WHITE)
    c.setStrokeColor(t["c1"])
    c.setLineWidth(1.3)
    c.roundRect(cx - s / 2, cy - s / 2, s, s, 12, stroke=1, fill=1)
    q = s - 26
    c.drawImage(ImageReader(qr_path), cx - q / 2, cy - q / 2, q, q,
                mask="auto")
    c.linkURL(url, (cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2),
              relative=0)


def fold_line(c, W, H):
    x = W / 2
    c.setStrokeColor(HexColor("#b9b3c9"))
    c.setLineWidth(0.8)
    c.setDash(2.5, 3.5)
    c.line(x, 46, x, H - 46)
    c.setDash()
    c.setFont("Sans", 12)
    c.setFillColor(HexColor("#b9b3c9"))
    for fy in (H - 62, 62):
        c.saveState()
        c.translate(x, fy)
        c.rotate(90)
        c.drawCentredString(0, -4, "\u2702")  # ✂
        c.restoreState()
    c.saveState()
    c.translate(x - 7, H / 2)
    c.rotate(90)
    tracked(c, 0, -3, "FOLD", "Sans-B", 7.5, HexColor("#b9b3c9"),
            track=2.2, char=4)
    c.restoreState()


# --------------------------------------------------------------------------
# panels
# --------------------------------------------------------------------------
def back_panel(c, x, ytop, w, h, t):
    """OUTER-LEFT: school identity + maker + small QR."""
    cx = x + w / 2
    url = f"{SITE}/teacher.html?t={t['id']}"
    qr = make_qr(url, f"qr_small_{t['num']:03d}.png")

    y = ytop - 46
    tracked(c, cx, y, "ST. MARY\u2019S ACADEMY", "Serif-B", 16.5, INK,
            track=0.9, char=1.7)
    y -= 19
    tracked(c, cx, y, "SAHARANPUR  \u00b7  TEACHERS\u2019 DAY 2019-20",
            "Sans-B", 8, GOLD, track=0.5, char=1.1)
    y -= 22
    gold_rule(c, cx, y, 120)

    # logo
    logo = prep_logo()
    ls = 82
    c.drawImage(ImageReader(logo), cx - ls / 2 - 4, y - 118, ls + 8, ls + 8,
                mask="auto")
    c.setStrokeColor(t["c2"])
    c.setLineWidth(1.4)
    c.roundRect(cx - ls / 2 - 4, y - 118, ls + 8, ls + 8, 12, stroke=1, fill=0)
    y -= 132

    tracked(c, cx, y, "MADE FOR ONE TEACHER", "Sans-B", 9.5, INK,
            track=1.4, char=2.1)
    y -= 17
    for ln in wrap(c, f"This is card {t['num']} of 83 \u2014 the other 82 "
                      f"each carry somebody else\u2019s name.",
                   ITALIC, 9.5, w - 90):
        c.setFont(ITALIC, 9.5)
        c.setFillColor(MUTED)
        c.drawCentredString(cx, y, ln)
        y -= 13.5
    y -= 12
    dashed(c, x + 60, y, x + w - 60)
    y -= 20
    tracked(c, cx, y, "MADE BY", "Sans-B", 7.5, GOLD, track=2, char=2.6)
    y -= 20
    c.setFont(ITALIC, 17)
    c.setFillColor(INK)
    c.drawCentredString(cx, y, "Pavit Singh")
    y -= 17
    tracked(c, cx, y, "CLASS IX-B  \u00b7  ROLL NO. 9231", "Sans", 7.5,
            MUTED, track=0.4, char=0.9)
    y -= 30

    qr_card(c, cx, y - 59, 118, qr, t, url)
    y -= 128
    tracked(c, cx, y, "SCAN: MY PAGE FOR YOU", "Sans-B", 8, t["c1"],
            track=1.2, char=1.8)
    y -= 15
    c.setFont(ITALIC, 8.5)
    c.setFillColor(MUTED)
    c.drawCentredString(cx, y, "open the card for the message and a bigger "
                               "code to scan")


def front_panel(c, x, ytop, w, h, t):
    """OUTER-RIGHT: photo, name, badges."""
    cx = x + w / 2

    # number rosette (top-left) + maker credits (top-right)
    badge(c, x + 37, ytop - 30, t["num"], t["c2"], t["c1"])
    tracked_right(c, x + w - 24, ytop - 27, "FROM PAVIT SINGH",
                  "Sans-B", 7.5, GOLD, track=1.2, char=1.7)
    tracked_right(c, x + w - 24, ytop - 40, "ONE CARD, ONE TEACHER",
                  "Sans", 6.5, MUTED, track=0.8, char=1.2)

    y = ytop - 62
    c.setFont(ITALIC, 27)
    c.setFillColor(t["c1"])
    c.drawCentredString(cx, y, "Happy Teachers\u2019 Day")
    y -= 22
    forwho = f"FOR YOU, {t['title'].upper()}" if t["title"] else "FOR YOU"
    tracked(c, cx, y, forwho, "Sans-B", 9, GOLD, track=1.6, char=2.4)
    y -= 27
    ribbon(c, cx, y, "5TH SEPTEMBER", t["c2"])

    # photo
    pr = 90
    pcy = y - pr - 22
    photo = prep_photo(t["photo"], t["num"])
    circle_photo(c, cx, pcy, pr, photo, t)

    # name
    ny = pcy - pr - 30
    nsize = fit_size(c, t["name"], "Serif-B", 23, w - 40)
    c.setFont("Serif-B", nsize)
    c.setFillColor(INK)
    c.drawCentredString(cx, ny, t["name"])

    # designation pill
    py = ny - 30
    pill(c, cx, py, t["designation"], "Sans-B", 10.5, t["c1"], WHITE,
         padx=13, h=21)
    py -= 27
    if t["subject"]:
        pill(c, cx, py, t["subject"], "Sans-B", 9, WHITE, t["c2"],
             padx=11, h=19, stroke=t["c2"])
        py -= 24
    if t["qual"] and t["qual"] != "." and t["group"] != "Supporting Staff":
        c.setFont(ITALIC, 10.5)
        c.setFillColor(MUTED)
        c.drawCentredString(cx, py, t["qual"])
        py -= 20

    py -= 14
    c.setFont("Sans-B", 10)
    c.setFillColor(t["c1"])
    c.drawCentredString(cx, py, "\u2665   OPEN ME   \u2665")
    py -= 15
    c.setFont(ITALIC, 9)
    c.setFillColor(MUTED)
    c.drawCentredString(cx, py, "your message and a page made for you are "
                                "inside")


def message_panel(c, x, ytop, w, h, t, msg):
    """INSIDE-LEFT: the letter."""
    x0 = x + 27
    cw = w - 54
    y = ytop - 32
    tracked_left(c, x0, y, "THE MESSAGE", "Sans-B", 9, GOLD,
                 track=1.4, char=2.1)

    y -= 44
    c.setFont("Serif-B", 17.5)
    c.setFillColor(INK)
    c.drawString(x0, y, msg["greeting"])

    y -= 24
    body = msg["body"]
    para = " ".join(body[:-1]) if len(body) > 1 else body[0]
    blessing = body[-1] if len(body) > 1 else ""
    c.setFont("Serif", 11.5)
    c.setFillColor(HexColor("#3d3754"))
    for ln in wrap(c, para, "Serif", 11.5, cw):
        c.drawString(x0, y, ln)
        y -= 16
    if blessing:
        y -= 4
        c.setFont(ITALIC, 11.8)
        c.setFillColor(HexColor("#57506e"))
        for ln in wrap(c, blessing, ITALIC, 11.8, cw):
            c.drawString(x0, y, ln)
            y -= 16
    y -= 16
    gold_rule(c, x + w / 2, y, cw / 2 - 4)
    y -= 22

    c.setFont(ITALIC, 11.5)
    c.setFillColor(HexColor("#57506e"))
    c.drawString(x0, y, "With love and gratitude,")
    y -= 22
    c.setFont(ITALIC_B, 16)
    c.setFillColor(INK)
    c.drawString(x0, y, "Pavit Singh")
    c.setFont("Sans", 13)
    c.setFillColor(HexColor("#f59e0b"))
    c.drawString(x0 + c.stringWidth("Pavit Singh", ITALIC_B, 16) + 6, y - 1,
                 "\u273f")
    y -= 18
    tracked_left(c, x0, y,
                 "CLASS IX-B  \u00b7  ROLL NO. 9231  \u00b7  ST. MARY\u2019S "
                 "ACADEMY",
                 "Sans", 7.2, MUTED, track=0.4, char=0.8)
    y -= 26
    dashed(c, x0, y, x + w - 27)
    y -= 24

    tracked_left(c, x0, y, "THREE THINGS I REMEMBER", "Sans-B", 9,
                 t["c1"], track=1.2, char=1.8)
    y -= 20
    for thing in msg["things"]:
        c.setFont("Sans", 9)
        c.setFillColor(t["c2"])
        c.drawString(x0 + 2, y, "\u2665")
        c.setFont(ITALIC, 11.5)
        c.setFillColor(HexColor("#3d3754"))
        c.drawString(x0 + 16, y, thing)
        y -= 17.5


def qr_panel(c, x, ytop, w, h, t):
    """INSIDE-RIGHT: big QR + the four secrets."""
    cx = x + w / 2
    url = f"{SITE}/teacher.html?t={t['id']}"
    y = ytop - 32
    tracked(c, cx, y, "AND A WHOLE PAGE, MADE FOR YOU", "Sans-B", 9,
            GOLD, track=1.0, char=1.6)

    qr = make_qr(url, f"qr_big_{t['num']:03d}.png")
    qcy = y - 108
    qr_card(c, cx, qcy, 176, qr, t, url)

    y = qcy - 108
    c.setFont(ITALIC, 10.5)
    c.setFillColor(MUTED)
    c.drawCentredString(cx, y, "point a camera at this")
    y -= 16
    dom = "teachers-day-rosy.vercel.app"
    rest = f"/teacher.html?t={t['id']}"
    c.setFont("Sans-B", 8.6)
    wd = c.stringWidth(dom, "Sans-B", 8.6)
    c.setFont("Sans", 8.6)
    wr = c.stringWidth(rest, "Sans", 8.6)
    ux = cx - (wd + wr) / 2
    c.setFont("Sans-B", 8.6)
    c.setFillColor(t["c1"])
    c.drawString(ux, y, dom)
    c.setFont("Sans", 8.6)
    c.setFillColor(HexColor("#4a4460"))
    c.drawString(ux + wd, y, rest)

    y -= 26
    dashed(c, x + 40, y, x + w - 40)
    y -= 26
    tracked(c, cx, y, "FOUR THINGS ARE HIDING ON THAT PAGE", "Sans-B", 9,
            t["c1"], track=0.8, char=1.3)
    y -= 24

    secrets = [
        "Tap your photo five times",
        "The gift box, hiding in the footer",
        "One line written in invisible ink",
        "The secret key: up up down down left right left right B A",
    ]
    c.setFont("Sans", 9.5)
    block_w = max(c.stringWidth(s, "Sans", 9.5) for s in secrets) + 26
    bx = cx - block_w / 2
    for i, s in enumerate(secrets):
        c.setFont("Sans", 10)
        c.setFillColor(FLOWER_COLS[i])
        c.drawString(bx, y, "\u273f")
        c.setFont("Sans", 9.5)
        c.setFillColor(HexColor("#3d3754"))
        c.drawString(bx + 18, y, s)
        y -= 17.5
    y -= 4
    c.setFont(ITALIC, 9.5)
    c.setFillColor(MUTED)
    c.drawCentredString(cx, y, "find all four and the page turns gold")


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------
def main():
    if "--extract" in sys.argv or not os.path.exists(MESSAGES_JSON):
        extract_messages()
    messages = json.load(open(MESSAGES_JSON, encoding="utf-8"))
    teachers = load_teachers()
    assert len(teachers) == 83, len(teachers)

    W, H = A4[1], A4[0]          # landscape
    MARGIN, GAP = 13, 9
    PW = (W - 2 * MARGIN - GAP) / 2
    PH = H - 2 * MARGIN
    LX, RX = MARGIN, MARGIN + PW + GAP
    PY = MARGIN

    c = canvas.Canvas(OUT_PDF, pagesize=(W, H))
    c.setTitle("St. Mary's Academy \u2014 Teachers' Day Cards (A4 fold)")
    c.setAuthor("Pavit Singh, Class IX-B")
    c.setSubject("83 foldable Teachers' Day cards \u2014 print A4 LANDSCAPE, "
                 "double-sided, FLIP ON SHORT EDGE, then fold on the dashed "
                 "centre line")

    for t in teachers:
        msg = messages[t["id"]]

        # ---- sheet side 1: OUTER (back | front) ----------------------
        c.setFillColor(PAPER)
        c.rect(0, 0, W, H, stroke=0, fill=1)
        ytop = panel_base(c, LX, PY, PW, PH, t, t["num"] * 2)
        panel_base(c, RX, PY, PW, PH, t, t["num"] * 2 + 1)
        back_panel(c, LX, ytop, PW, PH, t)
        front_panel(c, RX, ytop, PW, PH, t)
        fold_line(c, W, H)
        c.showPage()

        # ---- sheet side 2: INSIDE (message | QR) ---------------------
        # (same panel order — long-edge duplex flip keeps alignment)
        c.setFillColor(PAPER)
        c.rect(0, 0, W, H, stroke=0, fill=1)
        ytop = panel_base(c, LX, PY, PW, PH, t, t["num"] * 2 + 100)
        panel_base(c, RX, PY, PW, PH, t, t["num"] * 2 + 101)
        message_panel(c, LX, ytop, PW, PH, t, msg)
        qr_panel(c, RX, ytop, PW, PH, t)
        fold_line(c, W, H)
        c.showPage()

    c.save()
    print(f"wrote {OUT_PDF} ({os.path.getsize(OUT_PDF)/1e6:.1f} MB, "
          f"{len(teachers) * 2} pages)")
    print("Print: A4 LANDSCAPE, double-sided, FLIP ON SHORT EDGE, "
          "then fold on the dashed line (front cover on the outside).")


if __name__ == "__main__":
    main()
