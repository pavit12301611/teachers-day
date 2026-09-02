#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_staff_pdf.py — turns the Teachers' Day data into a decorated, print-ready PDF.
------------------------------------------------------------------------------------
The site (index.html / teachers.html / teacher.html) is the source of truth; this script
reads the very same data and lays the whole staff out on A4 pages, so the tribute can be
printed, mailed or handed out on Teachers' Day.

    python3 tools/build_staff_pdf.py                     # → St_Marys_Staff_Book_2019-20.pdf
    python3 tools/build_staff_pdf.py --out /tmp/x.pdf --dpi 210 --quality 80

Layout of the book
    1  cover (watercolour frame, ribbon, count seals)
    2  a note of thanks + what's inside (real page numbers, computed by build_plan)
    3  leadership spotlight (Principal & Manager, full-page profiles)
    …  one divider per section (roster + subject chips), then 6 decorated cards per page
    n-2 the sealed letter from Pavit
    n-1 the gratitude wall (sticky notes)
    n   credits

Data used (nothing is hard-coded about the school beyond the copy):
    js/data.js          → 83 staff records: name, designation, group, theme colours, photo
    staff.csv           → fallback if data.js is missing
    teacher_context.md  → Pavit's real personal notes (used whenever they say something)
    assets/staff-cards/ → square watercolour portraits (cropped to circles at build time)
    assets/wc-hero-splash.webp → the painted frame on the cover / dividers

All ornament is vector (washes, ribbons, seals, laurels, confetti, gold rules) so the file
stays small and every page prints crisp at any size.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance
from reportlab.lib.colors import Color, HexColor as _RLHexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import EmbeddedType1Face, Font as RLFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------- layout
PW, PH = A4                            # 595.28 x 841.89 pt
MARGIN = 40.0
BAND_H = 3.2                           # rainbow strip at the page edge
COLS, ROWS = 2, 3                      # staff cards per page
CARD_GAP = 14.0
HEADER_Y = PH - 52.0
FOOTER_Y = 46.0

# Watercolour palette — mirrors the --wc-* tokens in css/style.css (§25).
WC = {
    "rose": "#ff5f8d", "berry": "#d6337c", "tangerine": "#ff8a3d", "sun": "#ffc93c",
    "lime": "#7bd44a", "mint": "#22c39a", "teal": "#17b6c7", "sky": "#3ea6f5",
    "violet": "#8a5cf6", "grape": "#6b3fd4", "ink": "#2b2140", "slate": "#5b5168",
    "paper": "#fffdf8", "desk": "#fdf5ea", "gold": "#b99423", "bronze": "#8a6d1f",
}
RAINBOW = ["berry", "rose", "tangerine", "sun", "lime", "mint", "sky", "violet"]
RAINBOW_HEX = [WC[k] for k in RAINBOW]
PAPER, INK, SLATE, GOLD = WC["paper"], WC["ink"], WC["slate"], WC["gold"]

# ----------------------------------------------------------------------------- fonts
F = {}


def setup_fonts() -> None:
    """Embed the machine's DejaVu faces; borrow reportlab's script face if present."""
    fd = "/usr/share/fonts/truetype/dejavu/"
    for name, fname in (("serif", "DejaVuSerif.ttf"), ("serifb", "DejaVuSerif-Bold.ttf"),
                        ("sans", "DejaVuSans.ttf"), ("sansb", "DejaVuSans-Bold.ttf"),
                        ("mono", "DejaVuSansMono.ttf")):
        if (Path(fd) / fname).exists():
            pdfmetrics.registerFont(TTFont(name, fd + fname))
            F[name] = name
    # Base-14 faces: real italics, not embedded, present in every PDF reader.
    for name, base in (("serifi", "Times-Italic"), ("serifbi", "Times-BoldItalic")):
        F[name] = base
    # A genuine calligraphic script (ships inside reportlab) for the flourishes.
    F["script"] = F.get("serifbi", "Times-BoldItalic")
    try:
        face = EmbeddedType1Face("callig15.afm", "callig15.pfb")
        pdfmetrics.registerTypeFace(face)
        pdfmetrics.registerFont(RLFont("Callig15", face.name, "WinAnsiEncoding"))
        F["script"] = "Callig15"
    except Exception:
        pass
    F.setdefault("serif", F.get("serifb", "Helvetica"))
    F.setdefault("sans", F.get("sansb", "Helvetica"))


def HexColor(value):  # noqa: N802 — tolerant wrapper: '#rrggbb' or a Color instance
    return _RLHexColor(value) if isinstance(value, str) else value


def _with_alpha(color, alpha):
    """Multiply a colour's own alpha by the group alpha (reportlab ignores one of them)."""
    if color is None or alpha is None or alpha >= 1.0:
        return color
    col = HexColor(color)
    a = alpha * (col.alpha if col.alpha is not None else 1.0)
    return col if a >= 1.0 else Color(col.red, col.green, col.blue, min(a, 1.0))


def patch_canvas_alpha():
    """Make `setFillAlpha()/setStrokeAlpha()` win over a later `set*Color()`.

    ReportLab writes the ExtGState alpha from the *colour object*, so "set alpha, then set
    colour" silently drops the alpha and paints solid. Every decorative wash in this book is
    built that way, so the canvas is patched once at startup: the remembered group alpha is
    re-applied to each colour that follows, and save/restoreState keep it in sync.
    """
    C = rl_canvas.Canvas
    for kind in ("fill", "stroke"):
        K = kind.capitalize()
        set_color, set_alpha = getattr(C, f"set{K}Color"), getattr(C, f"set{K}Alpha")
        attr = f"_ag_{kind}_alpha"

        def new_color(set_color=set_color, attr=attr):
            def f(self, color, *a, **kw):
                return set_color(self, _with_alpha(color, getattr(self, attr, None)), *a, **kw)
            return f

        def new_alpha(set_alpha=set_alpha, attr=attr):
            def f(self, alpha):
                setattr(self, attr, alpha)
                return set_alpha(self, alpha)
            return f

        setattr(C, f"set{K}Color", new_color())
        setattr(C, f"set{K}Alpha", new_alpha())

    save, restore = C.saveState, C.restoreState

    def new_save(self, save=save):
        st = getattr(self, "_ag_stack", None)
        if st is None:
            st = self._ag_stack = []
        st.append((getattr(self, "_ag_fill_alpha", None), getattr(self, "_ag_stroke_alpha", None)))
        return save(self)

    def new_restore(self, restore=restore):
        st = getattr(self, "_ag_stack", None)
        if st:
            f_, s_ = st.pop()
            self._ag_fill_alpha, self._ag_stroke_alpha = f_, s_
        return restore(self)

    C.saveState, C.restoreState = new_save, new_restore


patch_canvas_alpha()


# ------------------------------------------------------------------------ text utils
EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0E\uFE0F\u200D\u20E3]")


def clean(s) -> str:
    """Drop emoji / selectors / control characters our fonts cannot draw."""
    if not s:
        return ""
    s = re.sub(r"[\u200b\u200c\u200d\u200e\u200f\ufeff]", "",
               str(s).replace("\r", " ").replace("\n", " "))
    s = EMOJI.sub("", s)
    s = "".join(ch for ch in s if ord(ch) >= 32)
    return re.sub(r"\s+", " ", s).strip()


def tidy_sentence(s: str) -> str:
    """Turn a raw answer from teacher_context.md into a line fit for a book."""
    s = clean(s)
    s = re.sub(r"^[^A-Za-z0-9]+", "", s)
    s = re.sub(r"[.,;!?\s]+$", "", s)
    if len(s) < 26 or s.lower() in {"no", "none", "na", "n/a", "nil", "nope"}:
        return ""
    return (s[0].upper() + s[1:] + ".").replace("  ", " ")


def word_pad(font: str) -> float:
    """Callig15's space glyph is far too narrow — pad words when script-setting."""
    return 0.34 if F.get("script") == "Callig15" and font == "script" else 0.0


def sw(text_str: str, font: str, size: float, tracking: float = 0.0) -> float:
    f = F.get(font, font)
    return pdfmetrics.stringWidth(text_str, f, size) + tracking * max(len(text_str) - 1, 0)


def wrap(text_str: str, font: str, size: float, maxw: float, tracking: float = 0.0):
    pad = word_pad(font) * size
    lines, cur = [], ""
    for word in text_str.split():
        trial = (cur + " " + word) if cur else word
        if sw(cur, font, size, tracking) + (pad if cur else 0) + sw(word, font, size, tracking) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def text(c, s, x, y, font="sans", size=9, color=INK, tracking=0.0, align="l", alpha=None):
    """One line, optionally letter-tracked (reportlab has no tracking), with word padding."""
    s = clean(s)
    if not s:
        return 0
    f = F.get(font, font)
    c.setFont(f, size)
    c.setFillColor(HexColor(color))
    if alpha is not None:
        c.saveState()
        c.setFillAlpha(alpha)
    pad = word_pad(font) * size
    if not tracking and not pad:
        w = pdfmetrics.stringWidth(s, f, size)
        if align == "c":
            c.drawCentredString(x, y, s)
        elif align == "r":
            c.drawRightString(x, y, s)
        else:
            c.drawString(x, y, s)
    else:
        w = pdfmetrics.stringWidth(s, f, size) + tracking * max(len(s) - 1, 0) \
            + pad * max(len(s.split()) - 1, 0)
        x0 = x - w / 2 if align == "c" else (x - w if align == "r" else x)
        for ch in s:
            c.drawString(x0, y, ch)
            x0 += pdfmetrics.stringWidth(ch, f, size) + tracking + (pad if ch == " " else 0)
    if alpha is not None:
        c.restoreState()
    return w


def para(c, s, x, y, maxw, font="serif", size=9, leading=None, color=INK,
         align="l", tracking=0.0, max_lines=None, alpha=None):
    """Wrapped paragraph drawn top-down from y. Returns the y below the last line."""
    f = F.get(font, font)
    leading = leading or size * 1.45
    lines = wrap(clean(s), f, size, maxw, tracking)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = re.sub(r"[,;:\s]+$", "", lines[-1]) + "…"
    ax = x + maxw / 2 if align == "c" else (x + maxw if align == "r" else x)
    yy = y
    for ln in lines:
        text(c, ln, ax, yy, font, size, color, tracking, align, alpha)
        yy -= leading
    return yy                                  # cursor: baseline the next block should start at


# --------------------------------------------------------------------------- colours
def tint(hexc, mix=0.65, towards=PAPER):
    """Mix a colour towards the paper — used to keep washes pale and print-friendly."""
    a, b = HexColor(hexc), HexColor(towards)
    return Color(a.red + (b.red - a.red) * mix, a.green + (b.green - a.green) * mix,
                 a.blue + (b.blue - a.blue) * mix)


def lerp(a, b, t):
    ca, cb = HexColor(a), HexColor(b)
    return Color(ca.red + (cb.red - ca.red) * t, ca.green + (cb.green - ca.green) * t,
                 ca.blue + (cb.blue - ca.blue) * t)


def hband(c, x, y, w, h, colors, steps=80, alpha=1.0):
    """Smooth horizontal gradient band."""
    n = len(colors)
    c.saveState()
    c.setFillAlpha(alpha)
    swp = w / steps
    for i in range(steps):
        t = i / max(steps - 1, 1) * (n - 1)
        k = min(int(t), n - 2)
        c.setFillColor(lerp(colors[k], colors[k + 1], t - k))
        c.rect(x + i * swp - 0.25, y, swp + 0.5, h, stroke=0, fill=1)
    c.restoreState()


def vband(c, x, y, w, h, colors, steps=70, alpha=1.0):
    n = len(colors)
    c.saveState()
    c.setFillAlpha(alpha)
    sh = h / steps
    for i in range(steps):
        t = i / max(steps - 1, 1) * (n - 1)
        k = min(int(t), n - 2)
        c.setFillColor(lerp(colors[k], colors[k + 1], t - k))
        c.rect(x, y + i * sh - 0.25, w, sh + 0.5, stroke=0, fill=1)
    c.restoreState()


def wash(c, cx, cy, r, colors, alpha=0.055, blobs=5, seed=0, spread=0.34, squash=0.9):
    """Pale, layered watercolour bloom (tinted, so text never fights with it)."""
    rnd = random.Random(seed * 977 + int(cx) + int(cy))
    c.saveState()
    c.setFillAlpha(alpha)
    for i in range(blobs):
        base = HexColor(colors[i % len(colors)])
        col = Color(base.red, base.green, base.blue, 0.55 if i % 3 == 2 else 1.0)
        c.setFillColor(tint(col, 0.15 if i % 2 else 0.30))
        ox = cx + rnd.uniform(-spread, spread) * r
        oy = cy + rnd.uniform(-spread, spread) * r
        s = rnd.uniform(0.62, 1.0)
        c.ellipse(ox - r * s / 2, oy - r * s * squash / 2, ox + r * s / 2, oy + r * s * squash / 2,
                  stroke=0, fill=1)
    c.restoreState()


def speckle(c, x, y, w, h, colors, n=40, seed=7, rmin=0.35, rmax=1.2, alpha=0.35):
    rnd = random.Random(seed)
    c.saveState()
    c.setFillAlpha(alpha)
    for i in range(n):
        c.setFillColor(HexColor(colors[rnd.randrange(len(colors))]))
        c.circle(x + rnd.random() * w, y + rnd.random() * h, rnd.uniform(rmin, rmax), stroke=0, fill=1)
    c.restoreState()


def confetti(c, x, y, w, h, n=28, seed=3, alpha=0.7):
    rnd = random.Random(seed)
    c.saveState()
    c.setFillAlpha(alpha)
    c.setStrokeAlpha(alpha)
    for i in range(n):
        col = HexColor(RAINBOW_HEX[rnd.randrange(len(RAINBOW_HEX))])
        cx, cy = x + rnd.random() * w, y + rnd.random() * h
        kind, s = rnd.random(), rnd.uniform(2.0, 4.4)
        c.saveState()
        c.translate(cx, cy)
        c.rotate(rnd.uniform(0, 360))
        if kind < 0.42:
            c.setFillColor(col)
            c.rect(-s / 2, -s / 4, s, s / 2, stroke=0, fill=1)
        elif kind < 0.72:
            c.setFillColor(col)
            c.circle(0, 0, s / 2.3, stroke=0, fill=1)
        else:
            c.setStrokeColor(col)
            c.setLineWidth(0.85)
            p = c.beginPath()
            p.moveTo(-s, 0)
            p.curveTo(-s / 3, s, s / 3, -s, s, 0)
            c.drawPath(p, stroke=1, fill=0)
        c.restoreState()
    c.restoreState()


# ------------------------------------------------------------------------- ornaments
def star_path(c, cx, cy, r, points=5, inner=0.45, rot=-90):
    p = c.beginPath()
    for i in range(points * 2):
        ang = math.radians(rot + i * 180.0 / points)
        rad = r if i % 2 == 0 else r * inner
        x, y = cx + rad * math.cos(ang), cy + rad * math.sin(ang)
        (p.moveTo if i == 0 else p.lineTo)(x, y)
    p.close()
    return p


def star(c, cx, cy, r, color=WC["sun"], alpha=1.0, points=5, rot=-90):
    c.saveState()
    c.setFillAlpha(alpha)
    c.setFillColor(HexColor(color))
    c.drawPath(star_path(c, cx, cy, r, points, rot=rot), stroke=0, fill=1)
    c.restoreState()


def heart(c, cx, cy, s, color=WC["rose"], alpha=1.0):
    c.saveState()
    c.setFillAlpha(alpha)
    c.setFillColor(HexColor(color))
    p = c.beginPath()
    p.moveTo(cx, cy - s * 0.62)
    p.curveTo(cx + s * 1.05, cy + s * 0.28, cx + s * 0.55, cy + s * 1.05, cx, cy + s * 0.34)
    p.curveTo(cx - s * 0.55, cy + s * 1.05, cx - s * 1.05, cy + s * 0.28, cx, cy - s * 0.62)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    c.restoreState()


def sparkle(c, cx, cy, r, color=WC["teal"], alpha=0.9):
    c.saveState()
    c.setFillAlpha(alpha)
    c.setFillColor(HexColor(color))
    k = r * 0.22
    pts = [(0, r), (k, k), (r, 0), (k, -k), (0, -r), (-k, -k), (-r, 0), (-k, k)]
    p = c.beginPath()
    p.moveTo(cx + pts[0][0], cy + pts[0][1])
    for x, y in pts[1:]:
        p.lineTo(cx + x, cy + y)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    c.restoreState()


def flower(c, cx, cy, r, petal=WC["rose"], center=WC["sun"], alpha=0.95, petals=6):
    c.saveState()
    c.setFillAlpha(alpha)
    c.setFillColor(tint(petal, 0.06))
    for i in range(petals):
        a = math.radians(i * 360.0 / petals)
        px, py = cx + r * 0.62 * math.cos(a), cy + r * 0.62 * math.sin(a)
        c.saveState()
        c.translate(px, py)
        c.rotate(math.degrees(a))
        c.ellipse(-r * 0.48, -r * 0.30, r * 0.48, r * 0.30, stroke=0, fill=1)
        c.restoreState()
    c.setFillColor(HexColor(center))
    c.circle(cx, cy, r * 0.32, stroke=0, fill=1)
    c.restoreState()


def garland(c, y, height=34, color=GOLD, n=None, seed=2, x1=None, x2=None):
    """A painted garland strip (leaves + blossoms) used to finish off pages."""
    rnd = random.Random(seed)
    x1 = MARGIN if x1 is None else x1
    x2 = PW - MARGIN if x2 is None else x2
    c.saveState()
    c.setStrokeColor(HexColor(color))
    c.setLineWidth(0.8)
    c.setStrokeAlpha(0.75)
    p = c.beginPath()
    p.moveTo(x1, y)
    for x in range(int(x1), int(x2), 8):
        p.lineTo(x, y + math.sin((x - x1) / 26.0) * height * 0.16)
    c.drawPath(p, stroke=1, fill=0)
    step = (x2 - x1) / (n or 13)
    for i in range(n or 13):
        x = x1 + step * (i + 0.5)
        yy = y + math.sin((x - x1) / 26.0) * height * 0.16
        col = RAINBOW_HEX[i % 8]
        if i % 3 == 0:
            flower(c, x, yy + 5, 4.6 + (i % 4) * 0.5, col, WC["sun"], 0.9)
        elif i % 3 == 1:
            c.saveState()
            c.translate(x, yy + 2)
            c.rotate(rnd.uniform(-18, 18))
            c.setFillColor(tint(WC["lime"], 0.12))
            c.setFillAlpha(0.85)
            q = c.beginPath()
            q.moveTo(0, 0)
            q.curveTo(3.2, 4.4, 8.6, 3.4, 10.6, 0)
            q.curveTo(8.6, -3.0, 3.2, -4.0, 0, 0)
            q.close()
            c.drawPath(q, stroke=0, fill=1)
            c.restoreState()
        else:
            star(c, x, yy + 4, 2.6, col, 0.85, rot=rnd.uniform(-40, 40))
    c.restoreState()


def gem_rule(c, x1, x2, y, color=GOLD, half=2.6, gems=3):
    """Thin rule with a cluster of diamonds in the middle."""
    c.saveState()
    mid = (x1 + x2) / 2
    gap = half * 2.7 * (gems - 1) + half * 2.6
    c.setStrokeColor(HexColor(color))
    c.setLineWidth(0.7)
    c.line(x1, y, mid - gap / 2, y)
    c.line(mid + gap / 2, y, x2, y)
    c.setFillColor(HexColor(color))
    c.setFillAlpha(0.9)
    for i in range(gems):
        gx = mid + (i - (gems - 1) / 2) * half * 2.7
        hh = half if i % 2 == 0 else half * 0.72
        p = c.beginPath()
        p.moveTo(gx, y + hh)
        p.lineTo(gx + hh, y)
        p.lineTo(gx, y - hh)
        p.lineTo(gx - hh, y)
        p.close()
        c.drawPath(p, stroke=0, fill=1)
    c.restoreState()


def dashed_rule(c, x1, x2, y, color="#ddd0bb", dash=(3, 3), lw=0.7):
    c.saveState()
    c.setStrokeColor(HexColor(color))
    c.setLineWidth(lw)
    c.setDash(dash[0], dash[1])
    c.line(x1, y, x2, y)
    c.restoreState()


def corner_flourish(c, x, y, size=26, color=GOLD, fx=1, fy=1):
    c.saveState()
    c.translate(x, y)
    c.scale(fx, fy)
    c.setStrokeColor(HexColor(color))
    c.setLineWidth(1.1)
    p = c.beginPath()
    p.moveTo(0, size)
    p.curveTo(size * 0.30, size * 0.62, size * 0.62, size * 0.30, size, 0)
    c.drawPath(p, stroke=1, fill=0)
    c.setLineWidth(0.6)
    q = c.beginPath()
    q.moveTo(size * 0.14, size * 0.84)
    q.curveTo(size * 0.44, size * 0.58, size * 0.58, size * 0.44, size * 0.84, size * 0.14)
    c.drawPath(q, stroke=1, fill=0)
    c.setFillColor(HexColor(WC["rose"]))
    c.setFillAlpha(0.85)
    c.circle(size * 0.10, size * 0.10, 1.7, stroke=0, fill=1)
    c.setFillColor(HexColor(WC["teal"]))
    c.circle(size * 0.36, size * 0.30, 1.1, stroke=0, fill=1)
    c.restoreState()


def framed_panel(c, x, y, w, h, fill="#ffffff", stroke=GOLD, radius=9, lw=1.0,
                 shadow=True, shadow_alpha=0.12, double=False):
    if shadow:
        c.saveState()
        c.setFillColor(HexColor("#4a3a5e"))
        c.setFillAlpha(shadow_alpha)
        c.roundRect(x + 2.4, y - 2.8, w, h, radius, stroke=0, fill=1)
        c.restoreState()
    c.setFillColor(HexColor(fill))
    c.setStrokeColor(HexColor(stroke))
    c.setLineWidth(lw)
    c.roundRect(x, y, w, h, radius, stroke=1, fill=1)
    if double:
        c.saveState()
        c.setStrokeColor(HexColor(stroke))
        c.setLineWidth(0.4)
        c.setStrokeAlpha(0.7)
        c.roundRect(x + 3.4, y + 3.4, w - 6.8, h - 6.8, max(radius - 3, 1), stroke=1, fill=0)
        c.restoreState()


def ribbon(c, cx, cy, text_str, color=WC["berry"], fold=WC["grape"], size=8.4, font="sansb",
           tcol="#ffffff", tracking=1.5, pad=26):
    """Centre ribbon banner; width follows the text."""
    w = sw(text_str, F.get(font, font), size, tracking) + pad * 2
    h = size * 2.0
    tw = w / 2
    c.saveState()
    for sgn in (-1, 1):
        x0 = cx + sgn * tw
        p = c.beginPath()
        p.moveTo(x0, cy - h * 0.40)
        p.lineTo(x0 + sgn * h * 0.85, cy + h * 0.28)
        p.lineTo(x0 + sgn * h * 0.62, cy - h * 0.02)
        p.lineTo(x0 + sgn * h * 0.95, cy - h * 0.58)
        p.lineTo(x0, cy - h * 0.58)
        p.close()
        c.setFillColor(HexColor(fold))
        c.setFillAlpha(0.92)
        c.drawPath(p, stroke=0, fill=1)
    c.setFillColor(HexColor("#3a2b4d"))
    c.setFillAlpha(0.10)
    c.roundRect(cx - tw - h * 0.26, cy - h * 0.68, (tw + h * 0.26) * 2, h * 1.36, 3, stroke=0, fill=1)
    c.setFillAlpha(1)
    c.setFillColor(HexColor(color))
    p = c.beginPath()
    tl, tr = cx - tw, cx + tw
    p.moveTo(tl, cy - h / 2)
    p.lineTo(tr, cy - h / 2)
    p.lineTo(tr - h * 0.26, cy)
    p.lineTo(tr, cy + h / 2)
    p.lineTo(tl, cy + h / 2)
    p.lineTo(tl + h * 0.26, cy)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    c.restoreState()
    text(c, text_str, cx, cy - size * 0.36, font, size, tcol, tracking, "c")
    return w


def seal(c, cx, cy, r, label, sub="", ring=GOLD, face="#fffdf7", ink=INK, rot=0, star_ring=False):
    """Scalloped wax-seal medallion: page numbers, counts, badges."""
    c.saveState()
    c.translate(cx, cy)
    c.rotate(rot)
    c.setFillColor(HexColor("#4a3a5e"))
    c.setFillAlpha(0.11)
    c.circle(1.2, -1.6, r, stroke=0, fill=1)
    c.setFillAlpha(1)
    n = 24
    p = c.beginPath()
    for i in range(n * 2):
        ang = math.radians(i * 180.0 / n)
        rad = r if i % 2 == 0 else r * 0.90
        (p.moveTo if i == 0 else p.lineTo)(rad * math.cos(ang), rad * math.sin(ang))
    p.close()
    c.setFillColor(HexColor(ring))
    c.drawPath(p, stroke=0, fill=1)
    c.setFillColor(HexColor(face))
    c.circle(0, 0, r * 0.79, stroke=0, fill=1)
    c.setStrokeColor(HexColor(ring))
    c.setLineWidth(0.55)
    c.circle(0, 0, r * 0.65, stroke=1, fill=0)
    if star_ring:
        for i in range(6):
            a = math.radians(i * 60 + 12)
            star(c, r * 0.72 * math.cos(a), r * 0.72 * math.sin(a), r * 0.10, RAINBOW_HEX[i], 0.9)
    fs = r * 0.46 if len(str(label)) <= 3 else r * 0.34
    text(c, str(label), 0, r * (0.10 if sub else -0.10), "serifb", fs, ink, 0, "c")
    if sub:
        sub = clean(sub)
        avail = r * 1.18
        rows, cur = [], ""
        for word in sub.split():
            trial = (cur + " " + word).strip()
            if sw(trial, F["sansb"], r * 0.19, 0.4) <= avail or not cur:
                cur = trial
            else:
                rows.append(cur)
                cur = word
        if cur:
            rows.append(cur)
        rows = rows[:2]
        for i, ln in enumerate(rows):
            text(c, ln, 0, -r * (0.26 + i * 0.23), "sansb", r * 0.185, ink, 0.35, "c")
    c.restoreState()


# ---------------------------------------------------------------------------- images
def circle_portrait(path: Path, dia_pt: float, dpi: float, bg: str, ring: str,
                    ring2=None, quality=82) -> bytes | None:
    """Crop the square watercolour portrait to a circle, baking in the card colour so the
    image needs no alpha channel (tiny JPEG, clean anti-aliased edge)."""
    px = max(int(round(dia_pt / 72.0 * dpi)), 110)
    ss = 3
    try:
        im = Image.open(path).convert("RGB")
    except Exception:
        return None
    w, h = im.size
    side = min(w, h)
    top = int((h - side) * 0.40)               # faces sit a touch above centre
    im = im.crop(((w - side) // 2, top, (w - side) // 2 + side, top + side))
    im = im.resize((px * ss, px * ss), Image.LANCZOS)
    im = ImageEnhance.Color(im).enhance(1.04)
    mask = Image.new("L", (px * ss, px * ss), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, px * ss, px * ss), fill=255)
    out = Image.new("RGB", (px * ss, px * ss), bg)
    out.paste(im, (0, 0), mask)
    d = ImageDraw.Draw(out)
    lw = max(int(2.6 * ss), 4)
    d.ellipse((lw * 0.5, lw * 0.5, px * ss - lw * 0.5, px * ss - lw * 0.5), outline="#ffffff", width=lw)
    lw2 = max(int(0.9 * ss), 2)
    off = lw + lw2 * 0.5
    d.ellipse((off, off, px * ss - off, px * ss - off), outline=ring, width=lw2)
    if ring2:
        off2 = lw + lw2 * 1.9
        d.ellipse((off2, off2, px * ss - off2, px * ss - off2), outline=ring2,
                  width=max(int(0.5 * ss), 1))
    out = out.resize((px, px), Image.LANCZOS)
    buf = BytesIO()
    out.save(buf, "JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def _jpeg_blob(im: Image.Image, quality: int = 84) -> bytes:
    buf = BytesIO()
    im.save(buf, "JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def load_splash():
    """The painted watercolour frame from assets/, encoded once so every placement in the
    book re-uses one embedded copy (ReportLab de-duplicates identical streams)."""
    for cand in ("assets/wc-hero-splash.webp", "assets/wc-hero-splash.png"):
        fp = ROOT / cand
        if fp.exists():
            try:
                im = Image.open(fp).convert("RGB")
            except Exception:
                continue
            if im.size[0] > 1600:
                im = im.resize((1600, int(im.size[1] * 1600 / im.size[0])), Image.LANCZOS)
            rgb = im.getpixel((3, 3))[:3]
            return _jpeg_blob(im), "#%02x%02x%02x" % tuple(rgb)
    return None, PAPER


# ------------------------------------------------------------------------------ data
SUBJECT_TEMPLATES = {
    "english": ["Thank you for every story you made us read twice — and for every new word that stuck.",
                "Thank you for red-penning my essays with patience and never with sarcasm.",
                "Thank you for the dictations we groaned at and the poems we ended up remembering.",
                "Thank you for teaching us that a sentence can be kind and correct at the same time."],
    "maths": ["Thank you for never giving up on my algebra, even on the third attempt at the board.",
              "Thank you for teaching me that a wrong answer is still a step forward.",
              "Thank you for the theorems, the proofs and the extra sums you checked after class.",
              "Thank you for making maths feel like a puzzle instead of a punishment."],
    "science": ["Thank you for making the laboratory the most exciting room in school.",
                "Thank you for the elements, the experiments and the extra 'why?' answers.",
                "Thank you for the diagrams we still half-remember while cooking dinner.",
                "Thank you for treating every wild question as a real one."],
    "computer": ["Thank you for teaching me to think in steps — and to save my work before the demo.",
                 "Thank you for every bug we found together, one line at a time.",
                 "Thank you for the lab, the log books and the patience with frozen screens.",
                 "Thank you for showing us that computing is mostly careful thinking."],
    "social": ["Thank you for making dates, maps and dynasties feel alive.",
               "Thank you for turning history into a story I actually wanted to hear.",
               "Thank you for the civics debates that made school feel like a democracy.",
               "Thank you for teaching us where we are, and how we got here."],
    "hindi": ["Thank you for the language, the literature and the endless patience.",
              "Thank you for making shlokas and grammar feel simple and fun.",
              "Thank you for the dictations, the diaries and the love of good stories.",
              "Thank you for keeping our languages proud and alive in this school."],
    "pe": ["Thank you for the drills, the discipline and the sports-day spirit.",
           "Thank you for the march-past practice we groaned at — and then nailed.",
           "Thank you for the whistles, the warm-ups and the 'one more lap' we survived.",
           "Thank you for teaching us that losing well is a skill too."],
    "art": ["Thank you for the colour, the craft and the courage to make something.",
            "Thank you for treating every doodle like a masterpiece in progress.",
            "Thank you for the chart paper, the brushes and the beautifully messy classrooms.",
            "Thank you for teaching us to look properly at things."],
    "music": ["Thank you for the harmony, the choir practice and the confidence to sing out loud.",
              "Thank you for teaching me that every voice deserves its own part.",
              "Thank you for the assemblies that sounded better because you insisted.",
              "Thank you for the rhythm you gave to school functions."],
    "primary": ["Thank you for the little hands, the tied laces and the wiped tears.",
                "Thank you for making the first years of school feel safe and happy.",
                "Thank you for the sound of a whole class reading together, loudly and wrongly.",
                "Thank you for teaching us to share, to wait and to try again."],
    "preprimary": ["Thank you for the storytime voices and the very first 'A B C'.",
                   "Thank you for loving the littlest kids of St. Mary's without fail.",
                   "Thank you for the nudge to the washroom, the packed snack checked twice.",
                   "Thank you for making the first classroom feel like a second home."],
    "office": ["Thank you for the files, the forms and the smile at the counter.",
               "Thank you for keeping our school running — one receipt at a time.",
               "Thank you for the transfer certificates, the ledgers and the lost registers found.",
               "Thank you for answering the same question kindly, every single time."],
    "library": ["Thank you for the quiet, and for always finding the exact right book.",
                "Thank you for storytime, stamped due dates and second chances on overdue ones.",
                "Thank you for keeping the shelves, the silence and the stories in order.",
                "Thank you for making the library the best refuge in the building."],
    "support": ["Thank you for keeping our school bright and safe — seen and unseen.",
                "Thank you for the work nobody applauds and everybody depends on.",
                "Thank you for the clean corridors, the working gates and the early mornings.",
                "Thank you for carrying, fixing and sweeping so that we could learn."],
    "default": ["Thank you for everything you do for our school, every single day.",
                "Thank you for showing up for us — even on the difficult days.",
                "Thank you for the work that happens quietly and never gets counted.",
                "Thank you for being part of what makes this school feel like home."],
    "principal": ["Thank you for leading this school with a firm hand and a kind word, and for motivating "
                  "us long before we could motivate ourselves.",
                  "Thank you for being the steadiest presence in the whole building.",
                  "Thank you for the assemblies that somehow made Monday feel like a fresh start.",
                  "Thank you for saying 'you can' before we believed it ourselves."],
    "manager": ["Thank you for looking after the entire school family, one careful decision at a time.",
                "Thank you for steering St. Mary's so that teaching feels easy.",
                "Thank you for the doors that open because someone decided they should.",
                "Thank you for a friendship that never forgot who was in charge."],
}


def subject_key(t):
    sl = " ".join([(t.get("subjectRaw") or ""), (t.get("subject") or ""), t.get("group", "")]).lower()
    d = (t.get("designation") or "").lower()
    g = (t.get("group") or "").lower()
    if "principal" in d:
        return "principal"
    if "manager" in d:
        return "manager"
    if "librar" in sl or "librar" in d:
        return "library"
    if "pre-primary" in g:
        return "preprimary"
    if "office" in g:
        return "office"
    if "supporting" in g:
        return "support"
    if "english" in sl:
        return "english"
    if any(k in sl for k in ("math", "commerce", "account", "economic", "b.com")):
        return "maths"
    if any(k in sl for k in ("science", "physics", "chemistry", "biology", " bio")):
        return "science"
    if any(k in sl for k in ("computer", "informatics", " m.sce", "it ")) or sl.strip() == "it":
        return "computer"
    if any(k in sl for k in ("social", "history", "geograph", "civics", "sst")):
        return "social"
    if any(k in sl for k in ("hindi", "sanskrit", "urdu")):
        return "hindi"
    if any(k in sl for k in ("physical", "pti", "sport", "yoga", " pe")):
        return "pe"
    if "art" in sl or "craft" in sl:
        return "art"
    if "music" in sl or "dance" in sl:
        return "music"
    if "p.r.t." in d or "primary" in g:
        return "primary"
    return "default"


# `subject_or_role` in the CSV sometimes carries degrees as well, so the token list below is
# filtered against this blocklist plus the person's own qualification string.
DEGREE_WORDS = {
    "ba", "ma", "bca", "mca", "bcom", "mcom", "bsc", "msc", "bed", "med", "b.ed", "m.ed", "llb",
    "mbbs", "phd", "dled", "b.lib", "m.lib", "blib", "dmlib", "ncc", "net", "ugc", "ugcnet",
    "diploma", "certificate", "bhm", "bsw", "msw", "bfa", "mfa", "pgd", "pgdd", "mphil", "b.a",
    "m.a", "b.sc", "m.sc", "b.com", "m.com", "b.ed", "m.ed", "b.lib.sc", "10th", "12th", "graduation",
    "post", "graduation", "hons", "passed", "in", "and", "or", "of", "the", "education", "science",
}
DEGREE_SHAPE = re.compile(r"^[bmd](\.?\s)?[a-z]{1,5}(\.?\s)?(sc|com|a|ed|phd|phil|lib|tech|sw|fa)$", re.I)


def _norm(tok: str) -> str:
    return re.sub(r"[^a-z0-9]", "", tok.lower())


def subject_tokens(t):
    """Clean, display-ready subject list for a teacher (degrees and '.' noise filtered out)."""
    raw = clean(t.get("subjectRaw") or "")
    qual = _norm(clean(t.get("qualification") or ""))
    out = []
    for part in re.split(r"[,/]| and | & ", re.sub(r"[().]", " ", raw)):
        tok = re.sub(r"\s+", " ", part).strip(" .-")
        key = _norm(tok)
        if len(key) < 3 or key in DEGREE_WORDS:
            continue
        if DEGREE_SHAPE.match(tok):
            continue
        if len(key) <= 9 and qual and key in qual:      # a qualification wearing a subject's clothes
            continue
        tok = re.sub(r"\b[mb]\s?[a-z]{0,2}\.?\s?(ed|sc|com|phil|lib|tech|sw|phd)\b", " ", tok,
                     flags=re.I)                        # "Education B Ed" → "Education"
        tok = re.sub(r"\s{2,}", " ", tok).strip(" .,-/")
        if len(_norm(tok)) < 3 or _norm(tok) in DEGREE_WORDS:
            continue
        if tok.upper().replace(" ", "") in {"PE", "PTI", "IT", "SST", "CS", "NET", "UGC"}:
            tok = tok.upper().replace(" ", "")
        elif tok.isupper() and len(tok) > 4:
            tok = tok.title()
        out.append(tok)
    seen, uniq = set(), []
    for tok in out:
        key = _norm(tok)
        if key not in seen:
            seen.add(key)
            uniq.append(tok)
    return uniq


def pretty_subjects(t, maxlen=54):
    toks = subject_tokens(t)
    s = ", ".join(toks)
    if len(s) > maxlen and toks:
        s = ", ".join(toks[:max(1, len(toks) // 2)]) + "…"
    return s


# whole-string degrees and certificates that never parse as "B + A" pairs
FLAT_DEG = {"mca": "M.C.A.", "bca": "B.C.A.", "bped": "B.P.Ed.", "mped": "M.P.Ed.", "bpes": "B.P.E.S.",
            "ttc": "T.T.C.", "ctet": "C-TET", "stet": "S-TET", "net": "N.E.T.", "ugc": "U.G.C.",
            "bed": "B.Ed.", "med": "M.Ed.", "bmlib": "B.M.Lib.", "dmlib": "D.M.Lib.", "ncc": "N.C.C.",
            "mbbs": "M.B.B.S.", "bhm": "B.H.M.", "llb": "LL.B.", "pgt": "P.G.T.", "tgt": "T.G.T.",
            "prt": "P.R.T.", "gdt": "G.D.T.", "diploma": "Diploma", "graduation": "Graduation"}
DEG_CANON = {("b", "a"): "B.A.", ("m", "a"): "M.A.", ("b", "sc"): "B.Sc.", ("m", "sc"): "M.Sc.",
             ("b", "com"): "B.Com.", ("m", "com"): "M.Com.", ("b", "ed"): "B.Ed.",
             ("m", "ed"): "M.Ed.", ("b", "lib"): "B.Lib.", ("m", "lib"): "M.Lib.",
             ("m", "phil"): "M.Phil.", ("ph", "d"): "Ph.D.", ("b", "tech"): "B.Tech.",
             ("m", "tech"): "M.Tech.", ("l", "lb"): "LL.B.", ("b", "sw"): "B.S.W.",
             ("m", "sw"): "M.S.W.", ("d", "ed"): "D.Ed.", ("n", "tt"): "N.T.T.",
             ("b", "fa"): "B.F.A.", ("m", "fa"): "M.F.A.", ("u", "gc"): "U.G.C.",
             ("b", "hm"): "B.H.M.", ("b", "ca"): "B.C.A.", ("m", "ca"): "M.C.A.",
             ("b", "pharm"): "B.Pharm.", ("d", "el"): "D.El.Ed.", ("b", "optometry"): "B.Optom.",
             ("b", "jmc"): "B.J.M.C.", ("m", "jmc"): "M.J.M.C.", ("b", "bed"): "B.Ed.",
             ("ll", "b"): "LL.B.", ("b", "aed"): "B.A.Ed.", ("b", "ar"): "B.A.R."}


def pretty_qual(q, maxlen=48):
    """Normalise degree strings from the school's own mixed-case CSV."""
    q = clean(q).strip(" .")
    if q.lower() in {"", "-", ".", "n a", "na", "none"}:
        return ""
    out = []
    for seg in re.split(r"[,/]| and ", q):
        seg = re.sub(r"\s+", " ", seg).strip(" .-")
        if not seg:
            continue
        def canon(piece):
            flat = re.sub(r"[^a-z]", "", piece.lower())
            if flat in FLAT_DEG:
                return FLAT_DEG[flat]
            m = re.match(r"^([a-z]{1,2})\.?\s?([a-z]{1,9})\.?$", piece.strip().lower())
            return DEG_CANON.get((m.group(1), m.group(2))) if m else None

        if canon(seg):
            seg = canon(seg)
        elif len(seg.split()) > 1 and all(canon(x) for x in seg.split()):
            seg = ", ".join(canon(x) for x in seg.split())
        elif seg.isupper():
            # title-case, but keep numerals and initials shouting: "IV CLASS STAFF" stays "IV Class Staff"
            seg = " ".join(w if re.fullmatch(r"[IVX]{1,4}|[A-Z]", w) else w.title()
                           for w in seg.split())
        out.append(seg)
    s = ", ".join(out)
    return s if len(s) <= maxlen else s[:maxlen].rsplit(" ", 1)[0] + "…"


def meta_line(t, maxlen=76):
    qual = pretty_qual(t.get("qualification", ""))
    subj = pretty_subjects(t)
    bits = [b for b in (qual, subj) if b]
    out = "   ·   ".join(bits)
    if len(out) > maxlen:
        out = out[:maxlen].rsplit(" ", 1)[0] + "…"
    return out or "St. Mary's Academy"


def load_notes():
    """Parse teacher_context.md into {staff number: best personal sentence}."""
    fp = ROOT / "teacher_context.md"
    notes = {}
    if not fp.exists():
        return notes
    txt = fp.read_text(encoding="utf-8", errors="replace")
    for blk in re.split(r"\n---\s*\n", txt):
        m = re.match(r"\s*##\s*(\d+)\.\s*(.+)", blk)
        if not m:
            continue
        fields = dict(re.findall(r"\*\*(.+?):\*\*\s*(.+)", blk))
        cands = []
        for key in ("How did they help build your study base / foundation", "Who were they to you",
                    "Anything else you want to add about them", "How were they towards you"):
            v = tidy_sentence(fields.get(key, ""))
            if v:
                cands.append(v)
        cands.sort(key=len, reverse=True)
        if cands:
            notes[int(m.group(1))] = cands[0]
    return notes


RESTATE = re.compile(r"^(he|she|they) (is|was) the [a-z]{3,14} of( the)? school\.?$", re.I)
WARM = re.compile(r"(taught|helped|guided|explain|motivat|encourag|support|advis|inspire|showed|"
                  r"made |gave us|gave me|kind|patient|strict|sweet|best|fun|interesting|care)", re.I)


def thank_you_for(t, notes, position=0):
    """Pavit's own words when they carry feeling; a subject-flavoured line otherwise — and
    never a bare job description standing on its own. `position` rotates the pool so that
    two cards on the same page never say the same thing."""
    real = notes.get(t["num"])
    pool = SUBJECT_TEMPLATES[subject_key(t)]
    filler = pool[position % len(pool)]
    if not real:
        return filler
    if RESTATE.match(real):                       # "She is the principal of the school" tells us nothing
        return filler
    if len(real) >= 62 or WARM.search(real):
        return real
    return real.rstrip(".") + ". " + filler.rstrip(".") + "."      # his words first, then ours


def load_data():
    """Teachers + quotes + wall notes from js/data.js (falls back to staff.csv)."""
    dj = ROOT / "js" / "data.js"
    if dj.exists():
        s = dj.read_text(encoding="utf-8")
        d = json.loads(s[s.index("{"): s.rindex("}") + 1])
    else:
        d = {"teachers": [], "quotes": [], "wallNotes": [], "wishNotes": []}
        for row in csv.DictReader(open(ROOT / "staff.csv", encoding="utf-8-sig")):
            d["teachers"].append({"num": int(row["number"]), "name": row["name"],
                                  "shortName": row["name"].split()[-1], "designation": row["designation"],
                                  "group": row["designation"], "qualification": row["qualification"],
                                  "subjectRaw": row["subject_or_role"], "photo": row["image_file"],
                                  "theme": {"c1": WC["violet"], "c2": WC["tangerine"], "soft": "#fff6f9"}})
    for t in d["teachers"]:
        th = t.setdefault("theme", {})
        th.setdefault("c1", WC["violet"])
        th.setdefault("c2", WC["tangerine"])
        th.setdefault("soft", "#fff6f9")
        t.setdefault("shortName", t["name"].split()[-1])
    return d


def photo_for(t):
    """Prefer the ready-made square crops, fall back to the raw photo in images/."""
    stem = Path(t.get("photo", "")).name
    for rel in ("assets/staff-cards/" + stem, t.get("photo", "")):
        if rel:
            p = ROOT / rel
            if p.exists():
                return p
    hits = sorted((ROOT / "images").glob(f"{t['num']:03d}_*"))
    return hits[0] if hits else None


GROUP_ORDER = ["Principal", "Manager", "P.G.T. (Senior Teachers)", "T.G.T. (Middle School)",
               "P.R.T. (Primary)", "Pre-Primary", "Office Staff", "Assistant Librarian",
               "Supporting Staff"]
GROUP_BLURB = {
    "Principal": "The head of our school family — the first name on the list and the last light to go out at the end of the day.",
    "Manager": "The manager who steers St. Mary's so that every class, corridor and sports day runs the way it should.",
    "P.G.T. (Senior Teachers)": "Senior teachers of the senior classes: the subject experts who get us ready for boards — and, more quietly, for life.",
    "T.G.T. (Middle School)": "The middle-school team: the bridge between the little years and the big ones, and the ones who notice everything.",
    "P.R.T. (Primary)": "The primary teachers — the biggest team in school and the one that decides how a child feels about learning for years afterwards.",
    "Pre-Primary": "Pre-primary: where the very first day of school stops being frightening and starts being fun.",
    "Office Staff": "The office team: admissions, files, fee counters, attendance registers and the busiest in-boxes in the building.",
    "Assistant Librarian": "The library — the quietest room in school and, somehow, the one with the most worlds inside it.",
    "Supporting Staff": "The supporting staff: the gardeners, caretakers, drivers and helpers who keep St. Mary's running before we arrive and after we leave.",
}
GROUP_SHORT = {"Principal": "Principal", "Manager": "Manager", "P.G.T. (Senior Teachers)": "P.G.T.",
               "T.G.T. (Middle School)": "T.G.T.", "P.R.T. (Primary)": "P.R.T.",
               "Pre-Primary": "Pre-Primary", "Office Staff": "Office", "Assistant Librarian": "Library",
               "Supporting Staff": "Support"}

# ------------------------------------------------------------------------------ the doc
class Doc:
    """Canvas wrapper: page furniture, portrait cache, running section label."""

    def __init__(self, out: Path, dpi: float, quality: int, splash, meta=None):
        self.out = out
        self.dpi, self.quality = dpi, quality
        self.splash, self.splash_bg = splash
        m = meta or {}
        c = rl_canvas.Canvas(str(out), pagesize=(PW, PH), pageCompression=1)
        c.setTitle(m.get("title", "St. Mary's Academy — Teachers' Day Staff Book 2019-20"))
        c.setAuthor("Pavit Singh (Class IX-B, Roll 9231)")
        c.setSubject(m.get("subject", "A decorated thank-you book for all 83 teachers and staff"))
        c.setKeywords(m.get("keywords", "Teachers' Day, St. Mary's Academy, staff directory, "
                                        "thank-you book, 2019-20"))
        c.setCreator("tools/build_staff_pdf.py")
        self.c = c
        self.page = 0
        self.section_title, self.section_color = "", WC["berry"]
        self._pcache = {}

    # ---- pages -------------------------------------------------------------------
    def new_page(self, kind="content", washes=True):
        self.page += 1
        c = self.c
        c.setFillColor(HexColor(self.splash_bg or PAPER))
        c.rect(0, 0, PW, PH, stroke=0, fill=1)
        vband(c, 0, 0, PW, PH, [PAPER, WC["desk"]], 26, 0.55)
        if washes:
            self.page_washes()
        if kind != "cover":
            self.footer()
        if kind in ("grid", "letter", "wall"):
            self.header()
        return c

    def page_washes(self):
        """Very pale painted corners — decoration that never fights with the type."""
        c = self.c
        r = random.Random(self.page * 131)
        a = RAINBOW_HEX[(self.page * 3) % 8]
        b = RAINBOW_HEX[(self.page * 3 + 3) % 8]
        d = RAINBOW_HEX[(self.page * 5 + 5) % 8]
        kw = dict(alpha=0.06, spread=0.30)
        wash(c, 24 + r.uniform(-14, 14), PH - 16, 250, [a, b], blobs=4, seed=self.page,
             squash=0.5, **kw)
        wash(c, PW - 20, PH - 10, 210, [b, d], blobs=4, seed=self.page + 3, squash=0.5, **kw)
        wash(c, PW - 12, 26 + r.uniform(0, 10), 220, [d, a], blobs=4, seed=self.page + 7,
             squash=0.55, **kw)
        wash(c, 18, 20, 190, [a, b], blobs=3, seed=self.page + 11, squash=0.5, **kw)
        speckle(c, MARGIN, PH - 46, PW - 2 * MARGIN, 22, [a, b, d], 14, self.page, 0.35, 0.9, 0.3)

    def header(self):
        c = self.c
        text(c, "ST. MARY'S ACADEMY · TEACHERS' DAY BOOK 2019-20", MARGIN, HEADER_Y, "sansb", 6.3,
             SLATE, 1.15, "l", 0.7)
        text(c, self.section_title, PW - MARGIN, HEADER_Y, "sansb", 6.6,
             HexColor(self.section_color), 1.05, "r", 0.85)
        gem_rule(c, MARGIN, PW - MARGIN, HEADER_Y - 8, GOLD, 2.2, 3)

    def footer(self):
        c = self.c
        hband(c, 0, 0, PW, BAND_H, RAINBOW_HEX, 70, 0.9)
        dashed_rule(c, MARGIN, PW - MARGIN - 26, FOOTER_Y + 12, "#e0d3bd", (2.4, 3.4), 0.6)
        text(c, "Made with love by Pavit Singh · Class IX-B · Roll 9231", MARGIN, FOOTER_Y, "sans",
             6.1, SLATE, 0.3, "l", 0.75)
        flower(c, MARGIN + sw("Made with love by Pavit Singh · Class IX-B · Roll 9231", F["sans"], 6.1, 0.3) + 10,
               FOOTER_Y + 2.4, 3.2, WC["violet"], WC["sun"], 0.7)
        seal(c, PW - MARGIN - 2, FOOTER_Y + 4, 10.6, f"{self.page:02d}", "", GOLD, "#fffdf6", INK,
             rot=random.Random(self.page).uniform(-5, 5))

    def section(self, title, color):
        self.section_title, self.section_color = title, color

    def show(self):
        self.c.showPage()

    def save(self):
        self.c.save()

    # ---- portraits ----------------------------------------------------------------
    def portrait(self, t, dia_pt, raster=None):
        key = (t["num"], round(dia_pt), round(raster or dia_pt))
        if key not in self._pcache:
            p = photo_for(t)
            self._pcache[key] = None
            if p is not None and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                base = self.portrait_bg
                self._pcache[key] = circle_portrait(p, raster or dia_pt, self.dpi, base,
                                                     t["theme"]["c1"], t["theme"]["c2"], self.quality)
        return self._pcache[key]

    portrait_bg = "#fffdf9"        # must match CARD_FILL

    def portrait_on(self, t, cx, cy, dia, plate=True, halo=True, raster=None):
        """A photo inside a pale painted plate; degrades to an initial medallion if missing."""
        c = self.c
        c1, c2 = t["theme"]["c1"], t["theme"]["c2"]
        if halo:
            wash(c, cx, cy, dia * 1.10, [c1, c2, WC["sun"]], alpha=0.085, blobs=5,
                 seed=t["num"], spread=0.24, squash=0.95)
        if plate:
            pad = 6.5
            framed_panel(c, cx - dia / 2 - pad, cy - dia / 2 - pad, dia + pad * 2, dia + pad * 2,
                         self.portrait_bg, tint(c1, 0.45), 11, 0.7, False)
        blob = self.portrait(t, dia, raster)
        if blob:
            c.drawImage(ImageReader(BytesIO(blob)), cx - dia / 2, cy - dia / 2, dia, dia)
        else:
            r = dia / 2
            c.setFillColor(tint(c1, 0.25))
            c.circle(cx, cy, r, stroke=0, fill=1)
            text(c, (t.get("shortName") or t["name"])[0].upper(), cx, cy - r * 0.34, "serifb",
                 r * 0.9, "#ffffff", 0, "c")


CARD_FILL = Doc.portrait_bg


# --------------------------------------------------------------------------- the pages
def page_cover(doc: Doc, d, notes, plan):
    c = doc.c
    c = doc.new_page("cover", washes=False)
    band_h = 0
    if doc.splash:
        iw, ih = Image.open(BytesIO(doc.splash)).size
        bw = PW - 6.0
        band_h = min(bw * ih / iw, PH * 0.375)
        c.drawImage(ImageReader(BytesIO(doc.splash)), 3, PH - band_h - 4, bw, band_h)
    else:
        hband(c, 0, PH - 30, PW, 30, RAINBOW_HEX, 80)
        band_h = 30
    top = PH - band_h - 24

    # ---- title block
    text(c, "FAITH  ·  KNOWLEDGE  ·  SERVICE", PW / 2, top - 8, "sansb", 6.4, WC["bronze"], 3.1, "c", 0.92)
    text(c, "St. Mary's Academy", PW / 2, top - 52, "serifb", 38, INK, 0.4, "c")
    text(c, "SAHARANPUR", PW / 2, top - 68, "serifb", 10.6, HexColor(WC["violet"]), 6.6, "c")
    gem_rule(c, PW / 2 - 120, PW / 2 + 120, top - 80, GOLD, 2.6, 3)
    text(c, "Teachers' Day Book", PW / 2, top - 116, "script", 40, HexColor(WC["berry"]), 0, "c")
    text(c, "STAFF DIRECTORY & A BOOK OF THANKS", PW / 2, top - 134, "sansb", 8.4, SLATE, 2.1, "c")
    w = ribbon(c, PW / 2, top - 162, "83 TEACHERS & STAFF · SESSION 2019-20", WC["berry"], WC["grape"],
               8.2)
    confetti(c, PW / 2 - w / 2, top - 176, w, 10, 12, 21, 0.55)

    # ---- painted middle: sparkles + a light wash so the cream never looks empty
    wash(c, PW * 0.2, top - 208, 150, [WC["sun"], WC["rose"]], alpha=0.05, blobs=4, seed=3,
         spread=0.3, squash=0.7)
    wash(c, PW * 0.82, top - 216, 140, [WC["teal"], WC["violet"]], alpha=0.05, blobs=4, seed=5,
         spread=0.3, squash=0.7)
    for i, fx in enumerate((64, 128, PW - 64, PW - 128)):
        sparkle(c, fx, top - 200 - (i % 2) * 16, 4.0 - (i % 3) * 0.7, RAINBOW_HEX[i * 2 % 8], 0.85)

    # ---- count seals
    stats = [(len(d["teachers"]), "STAFF"), (len(plan["order"]), "SECTIONS"),
              (len(notes), "NOTES"), (plan["total"], "PAGES")]
    for i, (big, small) in enumerate(stats):
        cx = PW / 2 + (i - 1.5) * 62
        seal(c, cx, top - 252, 24, big, small, RAINBOW_HEX[i], "#fffdf8", INK,
             rot=(-5, 4, -3, 5)[i], star_ring=(i == 0))
    text(c, "Every name in this school — and every one of them thanked, by name.",
         PW / 2, top - 288, "serif", 10.2, "#5b4a68", 0.2, "c")

    # ---- bottom: garland + the maker's credit, all on clean paper
    garland(c, 148, 30, GOLD, 15, 4)
    text(c, "Compiled, illustrated & printed with love by", PW / 2, 124, "serif", 8.6, SLATE, 0.2, "c")
    text(c, "Pavit Singh", PW / 2, 96, "script", 28, HexColor(WC["grape"]), 0, "c")
    text(c, "CLASS IX-B  ·  ROLL NO. 9231  ·  ST. MARY'S ACADEMY", PW / 2, 80, "sansb", 6.4, SLATE,
         1.7, "c", 0.9)
    heart(c, PW / 2 - 116, 88, 3.4, WC["rose"], 0.8)
    heart(c, PW / 2 + 116, 88, 3.4, WC["rose"], 0.8)
    confetti(c, 60, 158, PW - 120, 16, 16, 8, 0.5)

    # ---- double frame on top of everything
    c.saveState()
    c.setStrokeColor(HexColor(GOLD))
    c.setLineWidth(1.1)
    c.roundRect(18, 20, PW - 36, PH - 40, 10, stroke=1, fill=0)
    c.setLineWidth(0.4)
    c.setStrokeAlpha(0.75)
    c.roundRect(23, 25, PW - 46, PH - 50, 8, stroke=1, fill=0)
    c.restoreState()
    for (cx, cy, fx, fy) in [(23, PH - 25, 1, -1), (PW - 23, PH - 25, -1, -1),
                             (23, 25, 1, 1), (PW - 23, 25, -1, 1)]:
        corner_flourish(c, cx, cy, 28, GOLD, fx, fy)
    doc.show()


def page_intro(doc: Doc, d, notes, plan):
    c = doc.c
    doc.section("A NOTE OF THANKS · WHAT'S INSIDE", WC["violet"])
    doc.new_page("letter")
    top = PH - 84
    text(c, "Before the names begin", PW / 2, top, "script", 30, HexColor(WC["berry"]), 0, "c")
    top -= 24
    text(c, "A LETTER TO THE WHOLE SCHOOL", PW / 2, top, "sansb", 7.4, SLATE, 2.6, "c")
    gem_rule(c, MARGIN + 6, PW - MARGIN - 6, top - 9, GOLD)
    top -= 34

    body = ("Dear teachers and staff of St. Mary's Academy — this little book is my thank-you card to all "
            "of you. It began as a website, but a website cannot be handed across a desk, so here it is on "
            "paper too: all 83 members of our school, group by group, each with a thank-you written for them "
            "personally. Where you taught me, I have tried to say exactly what you did; where you did not, I "
            "have said it anyway, because the work you do reaches every corridor in this building.")
    lead = 13.8
    dh = 34
    c.setFillColor(tint(WC["violet"], 0.82))
    c.roundRect(MARGIN + 6, top - dh + 8, dh - 4, dh - 4, 7, stroke=0, fill=1)
    text(c, body[0], MARGIN + 6 + (dh - 4) / 2, top - dh + 17, "serifb", 24, HexColor(WC["grape"]), 0, "c")
    y = para(c, body[1:], MARGIN + 46, top - 6, PW - 2 * MARGIN - 52, "serif", 9.4, lead, INK)
    top = y - 2
    top = para(c, (f"{len(notes)} of the cards that follow carry a note written from memory rather than "
                   "from a template — those are the truest lines in this book."), MARGIN + 6, top,
               PW - 2 * MARGIN - 12, "serifi", 8.9, 12.6, "#5b4a68")
    top -= 16

    # ---- quote panel
    q = (d.get("quotes") or [{"text": "A teacher takes a hand, opens a mind and touches a heart.",
                              "who": "Unknown"}])[0]
    qh = 56
    framed_panel(c, MARGIN + 6, top - qh, PW - 2 * MARGIN - 12, qh, "#fff9e9", WC["sun"], 9, 0.8, True,
                 0.10, True)
    heart(c, MARGIN + 24, top - qh / 2 - 2, 5.0, WC["rose"], 0.85)
    para(c, "“" + clean(q["text"]) + "”", MARGIN + 46, top - 22, PW - 2 * MARGIN - 104, "serifi", 10.4,
         14.2, INK, "c")
    text(c, "— " + clean(q.get("who", "Unknown")), PW - MARGIN - 22, top - qh + 13, "sansb", 6.5,
         WC["bronze"], 1.2, "r", 0.85)
    top -= qh + 26

    # ---- contents
    text(c, "WHAT'S INSIDE", MARGIN + 6, top, "sansb", 8.6, INK, 3.0, "l")
    text(c, "PAGE", PW - MARGIN - 6, top, "sansb", 7.0, SLATE, 1.6, "r", 0.8)
    dashed_rule(c, MARGIN + 6, PW - MARGIN - 6, top - 7, "#cbb99e", (2, 3), 0.9)
    top -= 17
    for i, g in enumerate(plan["order"]):
        p, n = plan["pages"][g], plan["counts"][g]
        accent = RAINBOW_HEX[i % 8]
        c.setFillColor(HexColor(accent))
        c.setFillAlpha(0.9)
        c.roundRect(MARGIN + 6, top - 3, 3.4, 12.6, 1.7, stroke=0, fill=1)
        c.setFillAlpha(1)
        label = g if sw(g, F["serifb"], 9.6, 0.2) < 250 else GROUP_SHORT.get(g, g)
        text(c, label, MARGIN + 16, top, "serifb", 9.6, INK, 0.2, "l")
        lw_ = sw(label, F["serifb"], 9.6, 0.2)
        dots = max(1, int((PW - 2 * MARGIN - 86 - lw_) / 5.0))
        text(c, ("·" * dots), MARGIN + 22 + lw_, top + 0.4, "sans", 6.4, SLATE, 0, "l", 0.45)
        text(c, f"{n} {'member' if n == 1 else 'members'}", PW - MARGIN - 34, top, "sans", 6.2, SLATE,
             0.4, "r", 0.72)
        text(c, f"{p:02d}", PW - MARGIN - 6, top, "sansb", 9.4, HexColor(accent), 0.4, "r")
        top -= 20.2
    top -= 10

    # ---- how to read the book (fills the foot of the page with something worth knowing)
    steps = [("01", "Find the section", "Nine sections, in the order of the staff list — the ribbon on "
                                        "each divider carries its number and colour."),
             ("02", "Read a card", "Name, role, qualification and subjects, then the thank-you written "
                                   "for that one person — nobody shares a card."),
             ("03", "Keep to the end", "The sealed letter and the gratitude wall close the book, and the "
                                        "last page says how it was made.")]
    box_top = min(top - 4, FOOTER_Y + 128)
    bw = (PW - 2 * MARGIN - 20) / 3
    text(c, "HOW TO READ THIS BOOK", MARGIN + 6, box_top + 18, "sansb", 7.2, INK, 2.6, "l")
    gem_rule(c, MARGIN + 6, PW - MARGIN - 6, box_top + 8, "#ddd0bb", 2.0, 3)
    for i, (num, head, body) in enumerate(steps):
        x = MARGIN + i * (bw + 10)
        accent = RAINBOW_HEX[(i * 2 + 1) % 8]
        c.setFillColor(HexColor(accent))
        c.setFillAlpha(0.92)
        c.circle(x + 14, box_top - 14, 12, stroke=0, fill=1)
        c.setFillAlpha(1)
        text(c, num, x + 14, box_top - 17.5, "sansb", 8.2, "#ffffff", 0.2, "c")
        text(c, head, x + 32, box_top - 17, "serifb", 9.6, INK, 0.2, "l")
        para(c, body, x + 2, box_top - 34, bw - 8, "serif", 7.6, 10.8, SLATE, max_lines=4)
    for i in range(5):                      # the page's own tail ornament, clear of the boxes
        star(c, PW / 2 + (i - 2) * 13, FOOTER_Y + 34, 2.8, RAINBOW_HEX[(i + 4) % 8], 0.85, rot=i * 21)
    doc.show()


def page_divider(doc: Doc, g, gi, members, plan):
    c = doc.c
    accent = RAINBOW_HEX[gi % 8]
    doc.section(f"SECTION {gi + 1:02d} · {g.upper()}", accent)
    doc.new_page("content")
    band_h = 0
    if doc.splash:
        iw, ih = Image.open(BytesIO(doc.splash)).size
        bw = PW - 4.0
        band_h = min(bw * ih / iw, PH * 0.24)
        c.drawImage(ImageReader(BytesIO(doc.splash)), 2, PH - band_h - 3, bw, band_h)
    top = PH - band_h - 44

    ribbon(c, PW / 2, top - 6, f"SECTION {gi + 1:02d}", accent, WC["grape"], 7.4)
    ty = top - 46
    text(c, g.split(" (")[0], PW / 2, ty, "serifb", 32, INK, 0.5, "c")
    if " (" in g:
        text(c, g.split(" (")[1].rstrip(")"), PW / 2, ty - 15, "sansb", 9.4, HexColor(accent), 3.0, "c")
    gem_rule(c, PW / 2 - 112, PW / 2 + 112, ty - 27, GOLD)
    top = para(c, GROUP_BLURB.get(g, "The people of St. Mary's Academy."), MARGIN + 46, ty - 46,
               PW - 2 * MARGIN - 92, "serif", 9.8, 14.6, SLATE, "c")
    top -= 6

    # ---- subject chips
    chips = []
    for t in members:
        for tk in subject_tokens(t):
            if tk not in chips:
                chips.append(tk)
    chips = chips[:12]
    if chips:
        rows, cur, wcur = [], [], 0
        for ch in chips:
            wid = sw(ch, F["sansb"], 6.8, 0.8) + 17
            if wcur + wid > 360 and cur:
                rows.append(cur)
                cur, wcur = [], 0
            cur.append((ch, wid))
            wcur += wid + 8
        if cur:
            rows.append(cur)
        for row in rows:
            rw = sum(w for _, w in row) + 8 * (len(row) - 1)
            xx = PW / 2 - rw / 2
            for ch, wid in row:
                c.setFillColor(tint(accent, 0.85))
                c.roundRect(xx, top - 4.5, wid, 13.5, 6.7, stroke=0, fill=1)
                c.setStrokeColor(HexColor(accent))
                c.setStrokeAlpha(0.45)
                c.setLineWidth(0.5)
                c.roundRect(xx, top - 4.5, wid, 13.5, 6.7, stroke=1, fill=0)
                c.setStrokeAlpha(1)
                text(c, ch, xx + wid / 2, top, "sansb", 6.8, INK, 0.8, "c")
                xx += wid + 8
            top -= 20.5
    top -= 6

    # ---- roster of the section: numbered, two columns, dot leaders
    list_top = top - 8
    text(c, "IN THIS SECTION", MARGIN + 6, list_top, "sansb", 7.4, INK, 2.4, "l")
    dashed_rule(c, MARGIN + 6, PW - MARGIN - 6, list_top - 7, "#ddd0bb", (2, 3), 0.8)
    names = list_top - 22
    per_col = math.ceil(len(members) / 2)
    colw = (PW - 2 * MARGIN - 16) / 2
    yy = names
    lh = 13.2
    room = int((yy - (FOOTER_Y + 96)) / lh)
    strip_h = 64
    rows_used = min(max(per_col, len(members) - per_col), room)
    spare = (yy - rows_used * lh) - (FOOTER_Y + strip_h + 26)
    if spare > 60:                      # painted numeral (+ quote when there is room) fills the foot
        cyy = FOOTER_Y + strip_h + 34 + spare / 2
        text(c, f"{gi + 1:02d}", PW / 2, cyy, "serifb", min(132, 60 + spare * 0.5),
             tint(accent, 0.9), 0, "c")
        if spare > 150:
            qq = d_quotes(doc)[gi % len(d_quotes(doc))]
            para(c, "“" + clean(qq["text"]) + "”", MARGIN + 96, cyy + 18, PW - 2 * MARGIN - 192,
                 "serifi", 9.4, 13.6, tint(accent, 0.05, towards=INK), "c")
            text(c, "— " + clean(qq.get("who", "Unknown")), PW / 2, cyy - 22, "sansb", 6.4,
                 WC["bronze"], 1.2, "c", 0.85)
    left, right = members[:per_col], members[per_col:]
    for ci, col in enumerate((left, right)):
        y0 = yy
        for j, t in enumerate(col):
            if j >= room:
                break
            x0 = MARGIN + 6 + ci * (colw + 16)
            c1 = t["theme"]["c1"]
            c.setFillColor(HexColor(c1))
            c.setFillAlpha(0.85)
            c.circle(x0 + 4.4, y0 + 2.6, 4.4, stroke=0, fill=1)
            c.setFillAlpha(1)
            text(c, f"{t['num']}", x0 + 4.4, y0 + 0.9, "sansb", 4.6, "#ffffff", 0, "c")
            nm = clean(t["name"])
            maxnm = colw - 34
            while sw(nm, F["serif"], 8.4, 0.1) > maxnm and len(nm) > 4:
                nm = nm[:-2].rstrip() + "."
            text(c, nm, x0 + 13, y0, "serif", 8.4, INK, 0.1, "l")
            lab = pretty_subjects(t, 22)
            if lab:
                while sw(lab, F["sans"], 6.0, 0.1) > maxnm - sw(nm, F["serif"], 8.4, 0.1) - 16:
                    lab = lab[:-1].rstrip(" ,.")
                text(c, lab, x0 + 13 + sw(nm, F["serif"], 8.4, 0.1) + 7, y0 + 0.3, "sans", 6.0,
                     SLATE, 0.1, "l", 0.8)
            y0 -= lh
        if len(col) > room:
            text(c, f"… and {len(col) - room} more on the pages that follow", x0, y0 - 2, "serifi",
                 8.0, HexColor(accent), 0.1, "l", 0.9)

    # ---- avatar strip along the foot
    n = min(len(members), 12)
    dia = min(42.0, (PW - 2 * MARGIN - 30) / max(n, 1) - 7)
    total = n * (dia + 7) - 7
    x = PW / 2 - total / 2
    yy = FOOTER_Y + 46
    for t in members[:n]:
        doc.portrait_on(t, x + dia / 2, yy + dia / 2, dia, plate=False, halo=True)
        x += dia + 7
    text(c, f"{len(members)} {'member' if len(members) == 1 else 'members'} in this section", PW / 2,
         yy + dia + 14, "sansb", 7.0, HexColor(accent), 2.2, "c", 0.9)
    if len(members) > n:
        text(c, f"+ {len(members) - n} more portraits on the following pages", PW / 2, yy - 15, "serif",
             8.2, SLATE, 0.2, "c")
    confetti(c, MARGIN, yy + dia + 26, PW - 2 * MARGIN, 18, 12, gi + 2, 0.45)
    doc.show()


def end_of_section_panel(doc: Doc, x, y, w, h, g, gi, total, quote=None, recap=None, recap_label=""):
    """Fills whatever the last grid page of a section leaves open — never a blank hole."""
    c = doc.c
    accent = RAINBOW_HEX[gi % 8]
    framed_panel(c, x, y, w, h, tint(accent, 0.93, towards=CARD_FILL), tint(accent, 0.55), 10, 0.8,
                 shadow=False)
    c.saveState()
    pp = c.beginPath()
    pp.roundRect(x, y, w, h, 10)
    c.clipPath(pp, stroke=0, fill=0)
    c.setLineWidth(0.8)
    c.setStrokeColor(tint(accent, 0.45))
    c.setDash(4, 4)
    c.roundRect(x, y, w, h, 10, stroke=1, fill=0)
    c.setDash()
    wash(c, x + 12, y + h - 12, w * 0.5, [accent, WC["sun"]], alpha=0.05, blobs=4, seed=gi + 1,
         spread=0.35, squash=0.5)
    c.restoreState()

    cx = x + w / 2
    qlines = wrap("“" + clean(quote.get("text", "")) + "”", F["serifi"], 8.8, w - 56) if quote else []
    qlines = qlines[:4]
    rec = recap or []
    rows_used = math.ceil(len(rec) / 2) if rec else 0
    bh = 52 + (len(qlines) * 13.0 + 22 if qlines else 0) + (16 + rows_used * 12.6 if rec else 0)
    cy = y + h / 2 + bh / 2 - 10

    text(c, f"END OF SECTION {gi + 1:02d}", cx, cy, "sansb", 7.2, HexColor(accent), 2.4, "c")
    gem_rule(c, cx - min(70, w / 2 - 18), cx + min(70, w / 2 - 18), cy - 11, tint(accent, 0.15), 2.2, 3)
    text(c, f"{total} {'name' if total == 1 else 'names'} thanked in “{GROUP_SHORT.get(g, g)}”",
         cx, cy - 26, "serif", 8.6, SLATE, 0.2, "c")
    yy = cy - 46
    if qlines and h > 130:
        yy = para(c, "“" + clean(quote.get("text", "")) + "”", x + 28, yy, w - 56, "serifi", 8.8, 13.0,
                  "#5b4a68", "c") - 8
        text(c, "— " + clean(quote.get("who", "Unknown")), cx, yy, "sansb", 6.2, WC["bronze"], 1.0, "c",
             0.85)
        yy -= 20
    if rec and rows_used:
        text(c, recap_label.upper(), cx, yy, "sansb", 6.2, HexColor(accent), 2.2, "c", 0.9)
        yy -= 15
        colw = (w - 60) / 2
        for ci in range(2):
            col = rec[ci::2]
            y0 = yy
            for nm in col:
                text(c, nm, x + 30 + ci * colw, y0, "serif", 7.6, SLATE, 0.1, "l", 0.95)
                y0 -= 12.6
        yy = yy - rows_used * 12.6
    if h > 260:
        seal(c, cx, y + 46, 20, GROUP_SHORT.get(g, g)[:11], "", accent, "#fffdf7", INK, rot=-4)
        for i in range(4):
            sparkle(c, cx + (i - 1.5) * 26, y + 78, 2.8, RAINBOW_HEX[(gi + i) % 8], 0.8)
    elif h > 96:
        garland(c, y + 40, 20, tint(accent, 0.25), 7, gi)
    else:
        confetti(c, x + 24, y + 26, w - 48, 22, 8, gi + 5, 0.45)


def page_profiles_or_grid(doc: Doc, g, gi, members, notes, plan, total_len, page_no, section_members):
    """Six cards per page, last row centred; any whole empty row becomes a section-end panel."""
    accent = RAINBOW_HEX[gi % 8]
    doc.section(f"SECTION {gi + 1:02d} · {g.upper()}", accent)
    doc.new_page("grid")
    area_top, area_bottom = HEADER_Y - 18, FOOTER_Y + 22
    ch = (area_top - area_bottom - (ROWS - 1) * CARD_GAP) / ROWS
    cw = (PW - 2 * MARGIN - (COLS - 1) * CARD_GAP) / COLS
    n = len(members)
    for i, t in enumerate(members):
        r, col = divmod(i, COLS)
        in_row = min(COLS, n - r * COLS)
        row_w = in_row * cw + (in_row - 1) * CARD_GAP
        x = MARGIN + ((PW - 2 * MARGIN) - row_w) / 2 + col * (cw + CARD_GAP)
        y = area_top - ch - r * (ch + CARD_GAP)
        staff_card(doc, t, x, y, cw, ch, thank_you_for(t, notes, page_no * 6 + i))
    rows_used = math.ceil(n / COLS)
    if rows_used < ROWS:
        on_page = {t["num"] for t in members}
        recap = [f"{t['num']:02d}  {clean(t['name'])}" for t in (section_members or members)
                 if t["num"] not in on_page]
        quotes = d_quotes(doc)
        py = area_top - ch - rows_used * (ch + CARD_GAP) + ch
        end_of_section_panel(doc, MARGIN, area_bottom, PW - 2 * MARGIN, py - area_bottom, g, gi,
                             total_len, quotes[(gi + page_no) % len(quotes)] if quotes else None,
                             recap[:40], "the rest of this section")
    doc.show()


def staff_card(doc: Doc, t, x, y, w, h, thank):
    c = doc.c
    c1, c2, soft = t["theme"]["c1"], t["theme"]["c2"], t["theme"]["soft"]
    framed_panel(c, x, y, w, h, CARD_FILL, tint(c1, 0.55), 10, 0.8)
    c.saveState()
    p = c.beginPath()
    p.roundRect(x, y, w, h, 10)
    c.clipPath(p, stroke=0, fill=0)
    c.setFillColor(tint(soft, 0.42, towards=CARD_FILL))
    c.rect(x, y, w, h, stroke=0, fill=1)
    hband(c, x, y + h - 4.4, w, 4.4, [c1, c2, WC["sun"], c1], 54)
    wash(c, x + 6, y + h - 26, w * 0.44, [c1, c2], alpha=0.05, blobs=3, seed=t["num"] + 3,
         spread=0.4, squash=0.6)
    wash(c, x + w - 6, y + 20, w * 0.42, [c2, c1], alpha=0.045, blobs=3, seed=t["num"] + 9,
         spread=0.4, squash=0.6)
    c.restoreState()

    # header row: courtesy title tab + numbered seal
    # the tab reads "Sir"/"Ma'am" when we know it, otherwise the first subject — never a
    # boring repeat of the designation pill below
    tab = clean(t.get("title") or "") or (subject_tokens(t) or [GROUP_SHORT.get(t.get("group", ""), "Staff")])[0]
    tw_ = min(w * 0.42, sw(tab, F["sansb"], 5.6, 1.1) + 20)
    c.setFillColor(HexColor(c1))
    c.setFillAlpha(0.92)
    c.roundRect(x + 9, y + h - 24.5, tw_, 12.5, 6.2, stroke=0, fill=1)
    c.setFillAlpha(1)
    text(c, tab, x + 9 + tw_ / 2, y + h - 20.4, "sansb", 5.6, "#ffffff", 1.1, "c")
    seal(c, x + w - 17, y + h - 18, 9.4, f"{t['num']:02d}", "", c2, "#fffdf6", INK, rot=6)

    cx = x + w / 2
    dia = 68.0
    pcy = y + h - 30 - dia / 2
    doc.portrait_on(t, cx, pcy, dia, plate=True, halo=True)
    star(c, cx - 34, pcy - dia / 2 - 4, 2.6, c1, 0.85, rot=-10)
    star(c, cx, pcy - dia / 2 - 6.5, 2.9, WC["sun"], 0.9, rot=8)
    star(c, cx + 34, pcy - dia / 2 - 4, 2.6, c2, 0.85, rot=20)

    ny = pcy - dia / 2 - 20
    size = 12.2
    if sw(t["name"], F["serifb"], size, 0.2) > w - 20:
        size = 11.0
    lines = wrap(t["name"], F["serifb"], size, w - 20)
    if len(lines) > 2:
        size = 10.0
        lines = wrap(t["name"], F["serifb"], size, w - 20)[:2]
    for ln in lines[:2]:
        text(c, ln, cx, ny, "serifb", size, INK, 0.2, "c")
        ny -= size * 1.18

    des = clean(t.get("designation", ""))
    pw = min(w - 34, sw(des, F["sansb"], 6.0, 1.0) + 18)
    ny -= 2
    c.setFillColor(HexColor(c1))
    c.setFillAlpha(0.93)
    c.roundRect(cx - pw / 2, ny - 4, pw, 12.4, 6.2, stroke=0, fill=1)
    c.setFillAlpha(1)
    text(c, des, cx, ny - 0.6, "sansb", 6.0, "#ffffff", 1.0, "c")
    ny -= 15.4
    text(c, meta_line(t), cx, ny, "sans", 6.5, SLATE, 0.25, "c")
    ny -= 10.5
    gem_rule(c, x + 22, x + w - 22, ny, "#d9c9ae", 2.0, 3)
    ny -= 11.5
    avail = ny - (y + 13)
    maxl = max(1, int((avail + 4) / (7.4 * 1.44)))
    para(c, thank, x + 13, ny, w - 26, "serifi", 7.4, 7.4 * 1.44, "#54465c", "c", 0.0, maxl)
    heart(c, x + 13, y + 8, 2.4, c2, 0.55)
    heart(c, x + w - 13, y + 8, 2.4, c1, 0.55)


def spotlight_card(doc: Doc, t, x, y, w, h, thank):
    c = doc.c
    c1, c2 = t["theme"]["c1"], t["theme"]["c2"]
    framed_panel(c, x, y, w, h, CARD_FILL, tint(GOLD, 0.35), 13, 1.0, True, 0.14, True)
    band = 56.0
    c.saveState()
    p = c.beginPath()
    p.roundRect(x, y, w, h, 13)
    c.clipPath(p, stroke=0, fill=0)
    vband(c, x, y + h - band, w, band, [c1, c2], 46, 0.94)
    speckle(c, x, y + h - band, w, band, ["#ffffff"], 26, t["num"], 0.5, 1.5, 0.3)
    wash(c, x + 10, y + h - band + 6, w * 0.5, [c2, WC["sun"]], alpha=0.06, blobs=3,
         seed=t["num"], spread=0.4, squash=0.5)
    c.restoreState()
    text(c, "A PERSONAL THANK-YOU", x + w / 2, y + h - 20, "sansb", 6.6, "#ffffff", 2.4, "c", 0.95)
    text(c, GROUP_SHORT.get(t.get("group", ""), t.get("designation", "")), x + w / 2, y + h - 32,
         "sansb", 6.0, "#ffffff", 1.4, "c", 0.8)
    seal(c, x + w - 22, y + h - 26, 13, f"№ {t['num']:02d}", "", GOLD, "#fffdf6", INK, rot=8)

    dia = 124.0
    cx = x + w / 2
    cy = y + h - band - dia / 2 - 16
    # slack between the profile table and the signature, shared out so nothing looks stranded
    slack = max(0.0, (cy - dia / 2 - 20 - 190) - (y + 108))
    pad = min(26.0, slack / 5.0)
    doc.portrait_on(t, cx, cy, dia, plate=True, halo=True)
    ny = cy - dia / 2 - 26 - pad * 0.6
    text(c, t["name"], cx, ny, "serifb", 17, INK, 0.3, "c")
    ny -= 15.5 + pad * 0.3
    subj = pretty_subjects(t)
    text(c, clean(t.get("designation", "")) + (("   ·   " + subj) if subj else ""), cx, ny, "sansb",
         8.2, HexColor(c1), 0.8, "c")
    ny -= 17
    # little profile table with dotted leaders
    rows = [("Role", clean(t.get("designation", "")) or "—"),
            ("Qualification", re.sub(r"\s*,\s*", ", ", clean(t.get("qualification", "")).strip(" .")) or "—"),
            ("Subjects", subj or "—"),
            ("Section", t.get("group", "") or "—")]
    for lab, val in rows:
        text(c, lab.upper(), x + 22, ny, "sansb", 5.8, SLATE, 1.4, "l", 0.85)
        vx = x + 22 + sw(lab.upper(), F["sansb"], 5.8, 1.4) + 10
        vv = val
        while sw(vv, F["serif"], 8.2, 0.1) > (x + w - 24) - vx - 6 and len(vv) > 4:
            vv = vv[:-2].rstrip() + "."
        text(c, vv, x + w - 24, ny, "serif", 8.2, INK, 0.1, "r")
        dashed_rule(c, vx, x + w - 24 - sw(vv, F["serif"], 8.2, 0.1) - 6, ny + 2.2, "#e4d8c4", (1.3, 2.6), 0.5)
        ny -= 14.2
    ny -= 4 + pad * 0.6
    gem_rule(c, x + 26, x + w - 26, ny, GOLD)
    sparkle(c, x + 20, ny + 2, 3.2, c2, 0.85)
    sparkle(c, x + w - 20, ny + 2, 3.2, c1, 0.85)
    ny -= 20 + pad * 0.6
    lead = 8.9 * 1.52
    room = max(2, int((ny - (y + 92)) / lead))
    after = para(c, thank, x + 26, ny, w - 52, "serifi", 8.9, lead, "#4b3c55", "c", 0.0, room)
    spare = after - (y + 92)
    if spare > 44:                      # painted fillers so a short note never leaves the card gaping
        yy = after - 16 - pad * 0.5
        fillers = ["For the patience, the corrections and the extra minutes.",
                   "For the way you make this school feel like a home.",
                   "For the standards you keep even when nobody is watching.",
                   "For every good word said about us when we weren't there."]
        for line in [fillers[(t["num"] + k) % 4] for k in range(1 if spare < 96 else 2)]:
            text(c, line, x + w / 2, yy, "serif", 8.2, "#6b5c74", 0.2, "c", 0.9)
            yy -= 13.4
        for i in range(5):
            star(c, x + w / 2 + (i - 2) * 12, yy + 2, 2.7, RAINBOW_HEX[(i + t["num"]) % 8], 0.85,
                 rot=i * 18)
    dashed_rule(c, x + 26, x + w - 26, y + 62, "#e6dac6", (2, 3), 0.7)
    text(c, "With gratitude,", x + 26, y + 46, "serif", 8.2, SLATE, 0.2, "l", 0.9)
    text(c, "Pavit", x + 24, y + 21, "script", 23, HexColor(c1), 0, "l")
    heart(c, x + w - 34, y + 38, 4.2, WC["rose"], 0.9)
    star(c, x + w - 52, y + 48, 2.6, WC["sun"], 0.85)
    text(c, f"{t['name']} · page {doc.page:02d}", x + w - 26, y + 15, "sans", 6.0, SLATE, 0.6, "r", 0.7)


def page_leadership(doc: Doc, groups, notes):
    c = doc.c
    doc.section("SECTIONS 01 & 02 · PRINCIPAL & MANAGER", WC["grape"])
    doc.new_page("content")
    top = PH - 76
    text(c, "The people at the front of the assembly", PW / 2, top, "script", 26,
         HexColor(WC["berry"]), 0, "c")
    text(c, "PRINCIPAL  ·  MANAGER", PW / 2, top - 16, "sansb", 7.6, SLATE, 3.0, "c", 0.95)
    gem_rule(c, PW / 2 - 88, PW / 2 + 88, top - 27, GOLD)
    lead = [t for g in ("Principal", "Manager") for t in groups.get(g, [])][:2]
    if not lead:
        doc.show()
        return
    gap = 14.0
    w = (PW - 2 * MARGIN - gap) / 2
    y0, h = FOOTER_Y + 26, (top - 38) - (FOOTER_Y + 26)
    for i, t in enumerate(lead):
        spotlight_card(doc, t, MARGIN + i * (w + gap), y0, w, h, thank_you_for(t, notes, i * 2))
    doc.show()


def d_quotes(doc: Doc):
    """Quotes carried over from the site, for the section-ending panels."""
    q = getattr(doc, "_quotes", None)
    if q is None:
        q = [{"text": "A teacher takes a hand, opens a mind and touches a heart.", "who": "Unknown"}]
        try:
            dj = ROOT / "js" / "data.js"
            src = dj.read_text(encoding="utf-8")
            q = json.loads(src[src.index("{"): src.rindex("}") + 1]).get("quotes") or q
        except Exception:
            pass
        doc._quotes = q
    return q


def page_profiles(doc: Doc, g, gi, members, notes, d):
    """Small teams (1–2 people) deserve the big layout, not one card lost on a page."""
    c = doc.c
    accent = RAINBOW_HEX[gi % 8]
    doc.section(f"SECTION {gi + 1:02d} · {g.upper()}", accent)
    doc.new_page("content")
    top = PH - 74
    text(c, GROUP_SHORT.get(g, g), PW / 2, top, "script", 27, HexColor(accent), 0, "c")
    text(c, f"SECTION {gi + 1:02d}  ·  {clean(GROUP_BLURB.get(g, ''))[:0]}THE PEOPLE OF THIS TEAM".strip(),
         PW / 2, top - 17, "sansb", 7.0, SLATE, 2.6, "c", 0.9)
    gem_rule(c, PW / 2 - 90, PW / 2 + 90, top - 28, GOLD)
    gap = 14.0
    n = len(members)
    w = (PW - 2 * MARGIN - gap * (n - 1)) / n if n > 1 else (PW - 2 * MARGIN) * 0.56
    h = top - 40 - (FOOTER_Y + 26)
    for i, t in enumerate(members):
        if n > 1:
            x = MARGIN + i * (w + gap)
        else:
            x = MARGIN
        thanks = thank_you_for(t, notes, i * 3)
        if n == 1:
            thanks += "  " + SUBJECT_TEMPLATES[subject_key(t)][(t["num"] + 1) % 4]
        spotlight_card(doc, t, x, FOOTER_Y + 26, w, h, thanks)
    if n == 1:                                # a decorated panel balances the single profile
        px = MARGIN + w + gap
        pw_ = PW - MARGIN - px
        framed_panel(c, px, FOOTER_Y + 26, pw_, h, tint(accent, 0.94, towards=CARD_FILL),
                     tint(accent, 0.5), 13, 0.9, True, 0.12, True)
        block = 150 + 20 * 4 + 60 + len(clean(GROUP_BLURB.get(g, ""))) / 9
        yy = min(FOOTER_Y + 26 + h - 34, FOOTER_Y + 26 + h / 2 + block / 2)
        text(c, "IN THIS TEAM", px + pw_ / 2, yy, "sansb", 7.0, HexColor(accent), 2.6, "c")
        yy -= 12
        gem_rule(c, px + 20, px + pw_ - 20, yy, tint(accent, 0.2))
        yy -= 22
        text(c, GROUP_SHORT.get(g, g), px + pw_ / 2, yy, "serifb", 15, INK, 0.4, "c")
        yy -= 22
        yy = para(c, GROUP_BLURB.get(g, ""), px + 20, yy, pw_ - 40, "serif", 9.0, 13.4, SLATE, "c") - 16
        chips = []
        for tk in subject_tokens(members[0]):
            if tk not in chips:
                chips.append(tk)
        for ch in (chips[:4] or [GROUP_SHORT.get(g, "Staff")]):
            wid = min(pw_ - 44, sw(ch, F["sansb"], 7.4, 1.0) + 18)
            c.setFillColor(tint(accent, 0.82))
            c.roundRect(px + pw_ / 2 - wid / 2, yy - 4.5, wid, 14.5, 7, stroke=0, fill=1)
            text(c, ch, px + pw_ / 2, yy, "sansb", 7.4, INK, 1.0, "c")
            yy -= 20
        quotes = d_quotes(doc)
        if quotes:
            qq = quotes[gi % len(quotes)]
            yy -= 8
            gem_rule(c, px + 24, px + pw_ - 24, yy, tint(accent, 0.25))
            para(c, "“" + clean(qq["text"]) + "”", px + 18, yy - 20, pw_ - 36, "serifi", 9.4, 13.6,
                 "#5b4a68", "c")
        text(c, f"{len(members)} member", px + pw_ / 2, FOOTER_Y + 78, "sansb", 6.8,
             HexColor(accent), 2.2, "c", 0.9)
        seal(c, px + pw_ / 2, FOOTER_Y + 48, 18, "01", "OF 01", accent, "#fffdf7", INK, rot=-4)
    confetti(c, MARGIN, FOOTER_Y + h + 40, PW - 2 * MARGIN, 16, 12, gi + 3, 0.4)
    doc.show()


def plan_pages(doc: Doc):
    return getattr(doc, "_pages", 29)


def page_letter(doc: Doc, d):
    c = doc.c
    doc.section("THE SEALED LETTER", WC["rose"])
    doc.new_page("letter")
    top = PH - 92
    sheet_x, sheet_w = MARGIN + 12, PW - 2 * MARGIN - 24
    sheet_bottom = FOOTER_Y + 30
    framed_panel(c, sheet_x, sheet_bottom, sheet_w, top - sheet_bottom + 18, "#fffdf8", "#e8d8c0", 12,
                 1.0, True, 0.15, True)
    c.saveState()
    p = c.beginPath()
    p.roundRect(sheet_x, sheet_bottom, sheet_w, top - sheet_bottom + 18, 12)
    c.clipPath(p, stroke=0, fill=0)
    wash(c, sheet_x + 24, top + 6, 210, [WC["rose"], WC["sun"]], alpha=0.08, blobs=4, seed=5,
         spread=0.3, squash=0.5)
    wash(c, sheet_x + sheet_w - 24, sheet_bottom + 10, 210, [WC["teal"], WC["violet"]], alpha=0.07,
         blobs=4, seed=6, spread=0.3, squash=0.5)
    for yy in range(int(sheet_bottom + 26), int(top - 30), 17):
        dashed_rule(c, sheet_x + 24, sheet_x + sheet_w - 24, yy, "#efe4d2", (1.6, 3.6), 0.5)
    c.restoreState()
    text(c, "For every teacher of St. Mary's Academy", sheet_x + sheet_w / 2, top - 6, "script", 25,
         HexColor(WC["berry"]), 0, "c")
    dashed_rule(c, sheet_x + 52, sheet_x + sheet_w - 52, top - 20, WC["rose"], (4, 4), 0.8)

    body = [
        "Dear Teachers,",
        "Today isn't just another date on the calendar — it's the day we finally get to say what we feel "
        "all year round. Thank you. Thank you for every lesson that went beyond the textbook, for every "
        "“one more time, let me explain” when we just weren't getting it, and for every smile that made a "
        "tough day easier.",
        "You didn't just teach us subjects — you taught us patience, kindness, discipline, and the courage "
        "to raise our hands even when we weren't sure of the answer. You saw potential in us before we "
        "could see it in ourselves.",
        "The chalk dust settles, the bell rings, the classes end — but what you have given us stays forever. "
        "Wherever life takes us, a part of every success will always belong to you.",
        "Happy Teachers' Day! May your day be as wonderful as you make ours, every single day.",
    ]
    y = top - 46
    for i, blk in enumerate(body):
        if i == 0:
            text(c, blk, sheet_x + 44, y, "serifb", 11, INK, 0.2, "l")
            y -= 20
            continue
        y = para(c, blk, sheet_x + 44, y, sheet_w - 100, "serif", 9.9, 14.6, INK) - 11
    text(c, "With love and gratitude,", sheet_x + 44, y - 14, "serif", 9.0, SLATE, 0.2, "l", 0.9)
    text(c, "Pavit Singh", sheet_x + 40, y - 44, "script", 30, HexColor(WC["grape"]), 0, "l")
    flower(c, sheet_x + 40 + sw("Pavit Singh", F["script"], 30) + 22, y - 38, 6.0, WC["rose"], WC["sun"], 0.9)
    py = y - 74
    para(c, "P.S. — Every card in this book was written for one person only. If your card is missing a "
            "line, it is because I could not decide which of the many things you did was the one worth "
            "printing.", sheet_x + 44, py, sheet_w - 100, "serifi", 8.8, 12.8, "#5b4a68")
    py -= 24
    dashed_rule(c, sheet_x + 44, sheet_x + sheet_w - 44, py, "#e6dac6", (2, 3), 0.7)
    text(c, "WRITTEN ON 5TH SEPTEMBER · CLASS IX-B · ST. MARY'S ACADEMY", sheet_x + 44, py - 13,
         "sansb", 5.8, SLATE, 1.5, "l", 0.85)
    seal(c, sheet_x + sheet_w - 66, py - 12, 27, "5 Sept", "TEACHERS' DAY", WC["berry"], "#fffdf6",
         HexColor(WC["berry"]), rot=9, star_ring=True)
    for i in range(4):
        star(c, sheet_x + 44 + i * 11, py - 30, 2.6, RAINBOW_HEX[i * 2 % 8], 0.8, rot=i * 24)
    fy = sheet_bottom + 46
    dashed_rule(c, sheet_x + 44, sheet_x + sheet_w - 44, fy + 26, "#e6dac6", (2, 3), 0.7)
    text(c, f"{len(d['teachers'])} names · {plan_pages(doc)} pages · one thank-you for every one of them",
         sheet_x + 44, fy + 10, "serif", 9.6, "#5b4a68", 0.2, "l", 0.9)
    text(c, "— A LETTER THAT LIVES ON message.html, TOO", sheet_x + 44, fy - 6, "sansb", 6.0, SLATE,
         1.6, "l", 0.8)
    garland(c, fy - 30, 22, GOLD, 11, 3)
    flower(c, sheet_x + sheet_w - 70, fy + 4, 6.4, WC["rose"], WC["sun"], 0.9)
    flower(c, sheet_x + sheet_w - 46, fy + 16, 5.2, WC["violet"], WC["tangerine"], 0.9)
    doc.show()


def page_wall(doc: Doc, d):
    c = doc.c
    doc.section("THE GRATITUDE WALL", WC["teal"])
    doc.new_page("wall")
    top = PH - 84
    text(c, "The Gratitude Wall", PW / 2, top, "script", 31, HexColor(WC["grape"]), 0, "c")
    text(c, "STICKY NOTES FROM PAVIT — THE SAME ONES THAT LIVE ON WALL.HTML", PW / 2, top - 18,
         "sansb", 7.0, SLATE, 2.3, "c", 0.9)
    gem_rule(c, PW / 2 - 116, PW / 2 + 116, top - 30, GOLD)
    notes = [n for n in (d.get("wallNotes", []) + d.get("wishNotes", []))
             if isinstance(n, dict) and n.get("note")]
    notes = notes[:9] or [{"note": "Thank you, teachers.", "by": "Pavit Singh"}]
    rnd = random.Random(19)
    cols = 3
    gw = (PW - 2 * MARGIN - 24) / cols
    gh = 138.0
    tints = [(WC["sun"], "#7a4a00"), ("#c9f2d8", "#1f5a3a"), ("#ffd6e8", "#7a2048"),
             ("#cdeef2", "#0d5560"), ("#e6dcff", "#3d2670"), ("#ffe0c2", "#7a3d10"),
             ("#d7ecff", "#1c4570"), ("#f2ffc2", "#4d5a00"), ("#ffd9d9", "#7a1f1f")]
    area_top = top - 52
    for i, n in enumerate(notes):
        r, col = divmod(i, cols)
        x = MARGIN + 8 + col * (gw + 8)
        y = area_top - (r + 1) * (gh + 14)
        bg, inkc = tints[i % len(tints)]
        rot = rnd.uniform(-3.0, 3.0)
        c.saveState()
        c.translate(x + gw / 2, y + gh / 2)
        c.rotate(rot)
        cx, cy = -gw / 2, -gh / 2
        c.setFillColor(HexColor("#4a3a5e"))
        c.setFillAlpha(0.12)
        c.rect(cx + 2.6, cy - 2.6, gw, gh, stroke=0, fill=1)
        c.setFillAlpha(1)
        c.setFillColor(HexColor(bg))
        c.rect(cx, cy, gw, gh, stroke=0, fill=1)
        vband(c, cx, cy, gw, gh * 0.28, ["#ffffff", "#ffffff"], 4, 0.12)
        c.setFillColor(HexColor("#000000"))
        c.setFillAlpha(0.07)
        p = c.beginPath()
        p.moveTo(cx + gw - 14, cy)
        p.lineTo(cx + gw, cy + 14)
        p.lineTo(cx + gw, cy)
        p.close()
        c.drawPath(p, stroke=0, fill=1)
        c.setFillAlpha(1)
        c.saveState()
        c.translate(0, gh / 2 - 5)
        c.rotate(-4)
        c.setFillColor(HexColor("#ffffff"))
        c.setFillAlpha(0.6)
        c.rect(-21, -5.5, 42, 11, stroke=0, fill=1)
        c.setStrokeColor(HexColor("#c9b48f"))
        c.setLineWidth(0.4)
        c.setDash(2, 2)
        c.rect(-21, -5.5, 42, 11, stroke=1, fill=0)
        c.restoreState()
        text(c, f"№ {i + 1:02d}", cx + gw - 12, cy + 12, "sansb", 6.2, inkc, 0.8, "r", 0.55)
        para(c, "“" + clean(n["note"]) + "”", cx + 13, cy + gh - 28, gw - 30, "serif", 9.5, 13.4, inkc)
        dashed_rule(c, cx + 13, cx + gw - 14, cy + 26, HexColor(inkc), (2, 3), 0.4)
        text(c, "— " + clean(n.get("by", "Pavit Singh")), cx + 13, cy + 15, "sansb", 6.5, inkc, 0.6, "l", 0.9)
        c.restoreState()
    used = len(notes) * (gh + 14)
    y_after = area_top - used - 6
    if y_after > FOOTER_Y + 40:
        text(c, "Add your own note on wall.html — the site keeps every one, and prints none of them until you ask.",
             PW / 2, y_after, "serif", 8.6, SLATE, 0.2, "c", 0.9)
    doc.show()


def page_credits(doc: Doc, d, plan, notes):
    c = doc.c
    doc.section("MADE WITH LOVE", WC["violet"])
    doc.new_page("content")
    top = PH - 92
    text(c, "The last page (so far)", PW / 2, top, "script", 30, HexColor(WC["berry"]), 0, "c")
    text(c, "ONE BOOK · 83 PEOPLE · ZERO FORGETTING", PW / 2, top - 18, "sansb", 7.2, SLATE, 2.5, "c", 0.9)
    gem_rule(c, PW / 2 - 124, PW / 2 + 124, top - 30, GOLD)
    top -= 66
    stats = [(len(d["teachers"]), "names, all in print"), (len(plan["order"]), "sections, one per team"),
             (len(notes), "notes written from memory"), ("4", "secrets per web page")]
    for i, (big, small) in enumerate(stats):
        cx = PW / 2 + (i - 1.5) * 66
        seal(c, cx, top, 27, big, small, RAINBOW_HEX[(i * 2) % 8], "#fffdf7", INK, rot=(-5, 4, -3, 5)[i],
             star_ring=(i == 1))
    top -= 54
    lines = [
        "This book is printed from the same data as the website: js/data.js, generated from staff.csv. "
        "Add a name to the CSV, re-run the site generator, then run tools/build_staff_pdf.py again — "
        "sections, page numbers and the contents list all re-flow themselves.",
        "Portraits are the watercolour paintings in images/ and assets/staff-cards/, cropped into circles "
        "at build time. Every wash, ribbon, seal and piece of confetti is drawn as a vector, so all "
        f"{plan['total']} pages stay crisp at any print size.",
        "On the website each teacher's page hides four surprises; here the secret is simpler — every single "
        "person in this list was thought about while their page was being laid out.",
    ]
    for ln in lines:
        top = para(c, ln, MARGIN + 42, top, PW - 2 * MARGIN - 84, "serif", 9.2, 13.8, SLATE, "c") - 13
    top -= 10
    y = para(c, "Thank you for everything.", MARGIN, top, PW - 2 * MARGIN, "serifi", 12, 15, INK, "c")
    text(c, "Pavit", PW / 2, y - 26, "script", 32, HexColor(WC["grape"]), 0, "c")
    garland(c, y - 46, 26, GOLD, 13, 5)

    # the marquee from the site, printed: thank-you in every language our corridors hear
    marquee = "THANK YOU  ·  DHANYAVAAD  ·  SHUKRIYA  ·  NANDRI  ·  GURU VANDANA  ·  THANK YOU"
    mh = 22
    my = 152
    hband(c, MARGIN + 40, my, PW - 2 * MARGIN - 80, mh, [WC["berry"], WC["violet"], WC["teal"]], 60, 0.95)
    text(c, marquee, PW / 2, my + 8.6, "sansb", 7.6, "#ffffff", 1.7, "c")
    by = 96
    c.saveState()
    c.setFillColor(HexColor("#141c30"))
    c.setFillAlpha(0.96)
    c.roundRect(MARGIN + 40, by, PW - 2 * MARGIN - 80, 48, 10, stroke=0, fill=1)
    c.restoreState()
    logo = ROOT / "assets" / "logo.png"
    if logo.exists():
        try:
            im = Image.open(logo).convert("RGB").resize((180, 180), Image.LANCZOS)
            c.drawImage(ImageReader(BytesIO(_jpeg_blob(im, 86))), MARGIN + 54, by + 6, 36, 36)
        except Exception:
            pass
    text(c, "MADE BY", MARGIN + 102, by + 31, "sansb", 5.8, "#9fb3d9", 2.2, "l", 0.9)
    text(c, "Pavit Singh · Class IX-B · Roll 9231", MARGIN + 102, by + 18, "serifb", 9.6, "#ffffff", 0.2, "l")
    text(c, "St. Mary's Academy · Teachers' Day 2019-20 · site + this book", MARGIN + 102, by + 8,
         "sans", 6.2, "#9fb3d9", 0.4, "l", 0.9)
    for i in range(7):
        star(c, PW - MARGIN - 58 - i * 9, by + 36, 2.6, RAINBOW_HEX[i % 8], 1, rot=i * 22)
    doc.show()


# ===================================================================== printable gift cards
# One hand-out card per teacher, in his/her own colours, with his/her own message.
CARD_W, CARD_H = 595.28, 420.96            # A5 landscape (210 x 148.5 mm) — two of these tile an A4
LAYOUTS = ("fold", "cut", "a5", "a4")


# third-person -> second-person rewrites for Pavit's own notes (cards speak TO the teacher)
YOU_VERBS = {"teaches": "teach", "helps": "help", "gives": "give", "makes": "make",
             "does": "do", "says": "say", "takes": "take", "explains": "explain",
             "writes": "write", "reads": "read", "knows": "know", "thinks": "think",
             "brings": "bring", "sends": "send", "tells": "tell", "asks": "ask",
             "wants": "want", "keeps": "keep", "shows": "show", "treats": "treat",
             "guides": "guide", "encourages": "encourage", "prepares": "prepare",
             "shares": "share", "solves": "solve", "praises": "praise", "checks": "check",
             "fixes": "fix", "loves": "love", "hopes": "hope", "smiles": "smile"}
TYPOS = {"formulaes": "formulae", "grammer": "grammar", "becuase": "because",
         "recieved": "received", "alot": "a lot", "teached": "taught",
         "maam": "Ma'am", "smily": "smile", "thier": "their", "wi": "will"}


def _cap(self_word, out, i):
    """"You" at the start of a sentence, "you" in the middle of one."""
    j = i - 1
    while j >= 0 and out[j] == " ":
        j -= 1
    return self_word if (j < 0 or out[j] in ".!?:") else self_word.lower()


def to_direct(s: str) -> str:
    """Rewrite Pavit's third-person notes into the second person, so a card addressed to
    "Dear Ma'am" can quote them back at the teacher without sounding like a report."""
    if not s:
        return ""
    out = s
    # his notes are written as one long line: put the missing full stops in first, while the
    # capitals that mark a new sentence are still where he left them
    out = re.sub(SENT_SPLIT, lambda m: m.group(1) + ". " + m.group(2), out)
    for a, b_ in TYPOS.items():
        out = re.sub(r"\b" + a + r"\b", b_, out, flags=re.I)
    # name a school subject the way the timetable does — but only when it reads as one
    SUBJ = r"(hindi|english|maths|science|computer|sanskrit|urdu|gk|sst)"
    out = re.sub(r"\b(my )?(" + SUBJ + r")\b",
                 lambda m: (m.group(1) or "") + (m.group(2).upper() if m.group(2) in ("gk", "sst")
                                                 else m.group(2).capitalize()), out)
    out = re.sub(r"\b(She|she|They|they|He|he|Him|him)\b",
                 lambda m: _cap("You", out, m.start()), out)
    out = re.sub(r"\b(Her|her|His|his|Their|their)\b",
                 lambda m: _cap("Your", out, m.start()), out)
    for a, b in (("You was", "You were"), ("You is", "You are"), ("You has", "You have"),
                 ("You are being", "You are"), ("You had been", "You were"),
                 ("you was", "you were"), ("you is", "you are"), ("you has", "you have")):
        out = re.sub(r"\b" + a + r"\b", b, out)
    out = re.sub(r"\bYou (%s)\b" % "|".join(YOU_VERBS),
                 lambda m: "You " + YOU_VERBS[m.group(1)], out)
    out = re.sub(r"\byou (%s)\b" % "|".join(YOU_VERBS),
                 lambda m: "you " + YOU_VERBS[m.group(1)], out)
    out = re.sub(r"(?<=\. )([a-z])(?=\w)", lambda m: m.group(1).upper(), out)
    out = re.sub(r"(?<=[.!?]\s)([a-z])", lambda m: m.group(1).upper(), out)
    out = out[0].upper() + out[1:] if out else ""
    return re.sub(r"\s+", " ", out).strip()


CARD_WISHES = {
    "english": "May your day be full of good books and easier grading.",
    "maths": "May your day be as satisfying as a proof that finally works.",
    "science": "May your day have all the right reactions and none of the fumes.",
    "computer": "May your day run bug-free, with everything saved on the first try.",
    "social": "May your day be remembered for years, the way you make history.",
    "hindi": "May your day be as sweet as the stories you tell us.",
    "pe": "May your day be a good run with no extra laps for anybody.",
    "art": "May your day be bright, and may nobody smudge what you made.",
    "music": "May your day land on the high note you always aim for.",
    "primary": "May your day be loud in the nicest possible way.",
    "preprimary": "May your day be full of the little hands holding flowers.",
    "office": "May your day have an in-box that is actually empty.",
    "library": "May your day be quiet, kind and overdue-free.",
    "support": "May your day be as dependable as you always are for us.",
    "default": "May your day be as wonderful as you make ours.",
    "principal": "May your day be as steady and generous as the school you run.",
    "manager": "May your day be as kind to you as you are to this whole school family.",
}

CARD_OPENERS = {
    "english": "You made paragraphs feel like stories and mistakes feel fixable.",
    "maths": "You never let a student leave the board without understanding it once.",
    "science": "You made this school curious — even the lab tables felt like discoveries.",
    "computer": "You taught us to think in steps, and to be careful before we press Enter.",
    "social": "You gave dates and maps a heartbeat, and made us care about both.",
    "hindi": "You kept our languages proud, and made grammar feel gentle.",
    "pe": "You gave this school its posture — literally — and its sports-day courage.",
    "art": "You treated everything we made as if it mattered, so we started to believe it did.",
    "music": "You gave every voice a part, and every assembly a soul.",
    "primary": "You built the foundation everyone else is standing on, and rarely get thanked for.",
    "preprimary": "You made the very first day of school feel safe, and that is everything.",
    "office": "This school runs on you — the files, the counters, the patience.",
    "library": "You kept the quiet, the shelves and every one of us in good order.",
    "support": "You are the reason this place is clean, running and welcoming before we arrive.",
    "default": "Your work reaches further than the room you do it in.",
    "principal": "You lead a whole school family, and still find time for one student at a time.",
    "manager": "You steer this school so that teaching feels easy and learning feels safe.",
}


NOTE_SUBJECTS = (
    ("english", ("english", "grammar", "literature", "poem", "essay")),
    ("hindi", ("hindi", "sanskrit", "urdu")),
    ("computer", ("computer", "coding", "programming", "it lab")),
    ("maths", ("maths", "math ", "algebra", "geometry", "commerce", "accounts", "economics")),
    ("science", ("science", "physics", "chemistry", "biology")),
    ("social", ("social", "history", "geography", "civics", "sst", "gk")),
    ("pe", ("pti", "sports", "physical education", "yoga", "march past")),
    ("art", ("drawing", "painting", "art work")),
    ("music", ("music", "choir", "singing")),
)
WEAK_KEYS = ("primary", "default")

# Pavit's notes are mostly one long sentence; a capital that follows a lower-case word in the
# middle of a line is a sentence break he simply forgot to type. Only trusted sentence-starters
# are split, so a name in the middle of a clause is never cut in two.
SENT_START = ("You", "Your", "He", "She", "They", "It", "And", "But", "So", "This", "That",
              "There", "Then", "Also", "Even", "Because", "When", "With", "For", "In", "On",
              "At", "Now", "Today", "Sometimes", "We", "My", "Our", "I", "Ma'am", "Sir")
SENT_SPLIT = re.compile(r"([a-z,]) (" + "|".join(SENT_START) + r")(?=[ ,A-Za-z])")


def prep_card_keys(teachers, notes):
    """data.js leaves subjectRaw blank for a lot of primary teachers, so when a card would
    otherwise say only 'primary', read what Pavit wrote about them and pick that subject."""
    for t in teachers:
        key = subject_key(t)
        real = notes.get(t["num"], "")
        if key in WEAK_KEYS and real:
            low = " " + to_direct(real).lower() + " "
            for k, words in NOTE_SUBJECTS:
                if any(w in low for w in words):
                    key = k
                    break
        t["_ckey"] = key


def card_key(t):
    return t.get("_ckey") or subject_key(t)


def card_message(t, notes):
    """The card's letter: an opener for the subject, then Pavit's own words about this teacher.
    The closing wish is set separately (in a band), so it is deliberately not here."""
    key = subject_key(t)
    real = notes.get(t["num"])
    if real and not RESTATE.match(real):
        return CARD_OPENERS[key] + " " + to_direct(real)
    return CARD_OPENERS[key]


def card_wish(t):
    return CARD_WISHES[card_key(t)]


SUBJECT_POINTS = {
    "english": ["the stories", "the red pen", "the new words"],
    "maths": ["the extra sums", "the patience at the board", "the 'show your steps'"],
    "science": ["the lab mornings", "the diagrams", "the answered 'why?'s"],
    "computer": ["the shortcuts", "the saved files", "the calm during crashes"],
    "social": ["the maps", "the dates that stuck", "the debates"],
    "hindi": ["the shlokas", "the dictations", "the love of language"],
    "pe": ["the whistles", "the march past", "the sports-day courage"],
    "art": ["the colours", "the chart paper", "the bold ideas"],
    "music": ["the choir notes", "the assemblies", "the confidence"],
    "primary": ["the tied laces", "the first letters", "the wiped tears"],
    "preprimary": ["the storytime voices", "the name tags", "the brave first day"],
    "office": ["the files in order", "the smile at the counter", "the found registers"],
    "library": ["the quiet", "the right book", "the stamped cards"],
    "support": ["the clean corridors", "the early mornings", "the fixed things"],
    "default": ["the small kindnesses", "the firm rules", "the extra minutes"],
    "principal": ["the morning assembly", "the firm decisions", "the kind word"],
    "manager": ["the steady hand", "the open door", "the school family"],
}


def fit(text_str, font, size, maxw, tracking=0.0, min_size=None):
    """Shrink a single line until it fits the space it has."""
    size = float(size)
    floor = min_size or size * 0.62
    while sw(text_str, F.get(font, font), size, tracking) > maxw and size > floor:
        size -= 0.25
    return size


def card_face(doc: Doc, t, notes, sc=1.0, x=0.0, y=0.0):
    """One complete hand-out card, designed at A5 landscape and scaled by `sc`."""
    c = doc.c
    c1, c2, soft = t["theme"]["c1"], t["theme"]["c2"], t["theme"]["soft"]
    c.saveState()
    c.translate(x, y)
    c.scale(sc, sc)
    W, H = CARD_W, CARD_H
    LX, RX = 262.0, 288.0                 # the two columns, split by the gold rule at 275
    RULE = 275.0

    # ---- paper, tint and painted washes
    c.setFillColor(HexColor(doc.splash_bg or PAPER))
    c.rect(0, 0, W, H, stroke=0, fill=1)
    c.setFillColor(tint(soft, 0.58, towards=PAPER))
    c.rect(0, 0, W, H, stroke=0, fill=1)
    wash(c, 10, H - 8, 220, [c1, c2], alpha=0.075, blobs=5, seed=t["num"], spread=0.3, squash=0.6)
    wash(c, W - 12, 10, 210, [c2, WC["sun"]], alpha=0.07, blobs=4, seed=t["num"] + 2, spread=0.3, squash=0.6)
    wash(c, RX + 120, H - 150, 190, [c1, WC["teal"]], alpha=0.045, blobs=3, seed=t["num"] + 5,
         spread=0.35, squash=0.5)
    speckle(c, 0, H - 44, W, 44, [c1, c2, WC["sun"]], 24, t["num"] + 7, 0.35, 1.1, 0.35)

    # ---- double frame + corner sprigs + rainbow strip
    c.setStrokeColor(HexColor(c1))
    c.setLineWidth(1.6)
    c.roundRect(11, 11, W - 22, H - 22, 8, stroke=1, fill=0)
    c.saveState()
    c.setStrokeColor(HexColor(GOLD))
    c.setLineWidth(0.5)
    c.setStrokeAlpha(0.85)
    c.roundRect(16, 16, W - 32, H - 32, 6, stroke=1, fill=0)
    c.restoreState()
    corner_flourish(c, 20, 20, 22, c2, 1, 1)
    corner_flourish(c, W - 20, 20, 22, c1, -1, 1)
    corner_flourish(c, 20, H - 20, 22, c1, 1, -1)
    corner_flourish(c, W - 20, H - 20, 22, c2, -1, -1)
    hband(c, 16, H - 15.5, W - 32, 3.0, RAINBOW_HEX, 60, 0.9)

    # ================================================ LEFT: who this card belongs to
    cx = 132.0
    dia = 118.0
    FOOT = 56.0                                      # room kept for the garland along the foot
    seal(c, 44, H - 42, 13.5, f"{t['num']:02d}", "OF 83", c2, "#fffdf6", INK, rot=-7)
    text(c, "FROM PAVIT SINGH", LX - 10, H - 40, "sansb", 5.6, WC["bronze"], 1.7, "r", 0.85)
    text(c, "ONE CARD, ONE TEACHER", LX - 10, H - 49, "sansb", 5.0, SLATE, 1.3, "r", 0.7)

    doc.portrait_on(t, cx, H - 100 - dia / 2, dia, plate=True, halo=True, raster=dia * sc)
    ny = H - 100 - dia - 24
    nsize = 17.5
    namew = LX - 46
    lines = wrap(t["name"], F["serifb"], nsize, namew)
    if len(lines) > 2:
        nsize = fit(t["name"].split()[0], "serifb", 15.4, namew)
        lines = wrap(t["name"], F["serifb"], nsize, namew)[:2]
    for ln in lines:
        text(c, ln, cx, ny, "serifb", nsize, INK, 0.3, "c")
        ny -= nsize * 1.16
    des = clean(t.get("designation", ""))
    dsize = fit(des, "sansb", 7.4, LX - 60, 1.4)
    pw = min(LX - 40, sw(des, F["sansb"], dsize, 1.4) + 22)
    ny -= 3
    c.setFillColor(HexColor(c1))
    c.setFillAlpha(0.95)
    c.roundRect(cx - pw / 2, ny - 4.4, pw, 14.5, 7.2, stroke=0, fill=1)
    c.setFillAlpha(1)
    text(c, des, cx, ny - 0.6, "sansb", dsize, "#ffffff", 1.4, "c")
    ny -= 18
    chips = subject_tokens(t)[:3]
    if chips:
        widths = [min(120, sw(ch, F["sansb"], 6.2, 0.8) + 14) for ch in chips]
        chips_w = sum(widths) + 6 * (len(chips) - 1)
        x0 = cx - chips_w / 2
        for ch, wid in zip(chips, widths):
            c.setFillColor(tint(c2, 0.80, towards=PAPER))
            c.roundRect(x0, ny - 4.5, wid, 13, 6.5, stroke=0, fill=1)
            c.setStrokeColor(HexColor(c2))
            c.setStrokeAlpha(0.5)
            c.setLineWidth(0.5)
            c.roundRect(x0, ny - 4.5, wid, 13, 6.5, stroke=1, fill=0)
            c.setStrokeAlpha(1)
            text(c, ch, x0 + wid / 2, ny, "sansb", 6.2, INK, 0.8, "c")
            x0 += wid + 6
        ny -= 16
    qual = pretty_qual(t.get("qualification", ""))
    if qual:
        if len(qual) > 42:
            qual = qual[:42].rsplit(" ", 1)[0] + "…"
        text(c, qual, cx, ny, "serif", 7.4, SLATE, 0.3, "c", 0.9)
        ny -= 15

    # the three small things this card remembers — set on one line so the column never spills
    pts = SUBJECT_POINTS[card_key(t)]
    ny -= 5
    dashed_rule(c, 30, LX - 6, ny, "#dcccb0", (2.6, 3.2), 0.6)
    ny -= 13.5
    text(c, "THREE THINGS I REMEMBER", cx, ny, "sansb", 5.6, HexColor(c1), 1.9, "c", 0.9)
    ny -= 14
    line = "   ·   ".join(pts)
    psz = fit(line, "serif", 8.6, LX - 44)
    used = 0
    for pt_ in wrap(line, F["serif"], psz, LX - 44)[:2]:
        heart(c, 40, ny + 2.4, 2.2, [c1, c2, WC["sun"]][used % 3], 0.8)
        text(c, pt_, 50, ny, "serif", psz, "#4b3c55", 0.1, "l")
        ny -= 12.4
        used += 1
    confetti(c, 26, FOOT - 12, LX - 40, 22, 10, t["num"] + 3, 0.45)
    if ny > FOOT:            # only draw the garland if there is clean paper left for it
        garland(c, 30, 12, GOLD, 7, t["num"])

    # ================================================ the spine
    c.saveState()
    c.setStrokeColor(HexColor(GOLD))
    c.setLineWidth(0.6)
    c.setDash(3.4, 3.4)
    c.setStrokeAlpha(0.7)
    c.line(RULE, 28, RULE, H - 28)
    c.restoreState()
    spine = "ST. MARY'S ACADEMY · SAHARANPUR · TEACHERS' DAY 2019-20"
    spine_len = sw(spine, F["sansb"], 5.4, 2.4)
    span = (H - 28) - 28
    if spine_len > span - 10:                       # keep it inside the card, never past the frame
        spine = "ST. MARY'S ACADEMY · SAHARANPUR"
    c.saveState()
    c.translate(RULE, H / 2)
    c.rotate(90)
    text(c, spine, 0, -2.2, "sansb", 5.4, WC["bronze"], 2.4, "c", 0.8)
    c.restoreState()

    # ================================================ RIGHT: the letter, bottom-anchored
    rx = RX + 4
    rw_ = W - rx - 26
    sig_y = 78
    text(c, "Happy Teachers' Day", rx, H - 52, "script", 22, HexColor(c1), 0, "l")
    rtxt, rpad = "5TH SEPTEMBER", 13
    rwide = sw(rtxt, F["sansb"], 6.2, 1.3) + rpad * 2
    ribbon(c, W - 24 - rwide / 2, H - 44, rtxt, c2, WC["grape"], 6.2, "sansb", "#ffffff", 1.3, rpad)
    greet_name = clean(t.get("title") or "")
    greet = f"Dear {greet_name}," if greet_name else f"Dear {clean(t.get('designation','')) or 'Teacher'},"
    text(c, greet, rx, H - 84, "serifb", 12.8, INK, 0.2, "l")
    msg_top = H - 104
    room = msg_top - (sig_y + 52)
    msz, lead = 9.9, 14.2
    body = card_message(t, notes)
    lines = wrap(body, F["serif"], msz, rw_)
    while len(lines) * lead > room and msz > 8.2:
        msz -= 0.4
        lead = msz * 1.44
        lines = wrap(body, F["serif"], msz, rw_)
    y_end = msg_top
    for ln in lines[:max(2, int(room // lead))]:
        text(c, ln, rx, y_end, "serif", msz, "#3f3450", 0.0, "l")
        y_end -= lead
    y_end -= 8
    gem_rule(c, rx, rx + rw_, y_end, "#d9c9ae", 2.2, 3)

    # the signature block is pinned to the foot of the card; the space in between is ornamented
    wish = card_wish(t)
    if y_end - sig_y > 84:
        wsz = fit(wish, "serifi", 9.2, rw_ - 34)
        band_y = max(sig_y + 42, min((y_end + sig_y) / 2 - 14, y_end - 24))
        bw = min(rw_, sw(wish, F["serifi"], wsz) + 34)
        c.setFillColor(tint(c1, 0.88, towards=PAPER))
        c.roundRect(rx + (rw_ - bw) / 2, band_y - 4, bw, 24, 8, stroke=0, fill=1)
        c.setStrokeColor(HexColor(c1))
        c.setStrokeAlpha(0.35)
        c.setLineWidth(0.6)
        c.roundRect(rx + (rw_ - bw) / 2, band_y - 4, bw, 24, 8, stroke=1, fill=0)
        c.setStrokeAlpha(1)
        text(c, wish, rx + rw_ / 2, band_y + 3.6, "serifi", wsz, "#4b3c55", 0.1, "c")
        sparkle(c, rx + rw_ / 2 - bw / 2 - 12, band_y + 8, 3.0, WC["sun"], 0.85)
        sparkle(c, rx + rw_ / 2 + bw / 2 + 12, band_y + 8, 3.0, c2, 0.85)
    elif y_end - sig_y > 26:
        text(c, wish, rx, y_end - 12, "serifi", fit(wish, "serifi", 9.0, rw_), "#4b3c55", 0.1, "l")
    text(c, "With love and gratitude,", rx, sig_y + 26, "serif", 8.6, SLATE, 0.2, "l", 0.9)
    text(c, "Pavit Singh", rx - 3, sig_y, "script", 25, HexColor(WC["grape"]), 0, "l")
    sig_w = sw("Pavit Singh", F["script"], 25) + 25 * word_pad("script") * 2
    flower(c, rx + 12 + sig_w, sig_y + 6, 6.0, c2, WC["sun"], 0.9)
    cap = "CLASS IX-B · ROLL NO. 9231 · ST. MARY'S ACADEMY"
    csize = fit(cap, "sansb", 5.8, rw_ - 60, 1.5)
    text(c, cap, rx, sig_y - 22, "sansb", csize, SLATE, 1.5, "l", 0.8)
    for i in range(4):
        star(c, W - 34 - i * 11, sig_y + 22, 2.7, RAINBOW_HEX[(t["num"] + i) % 8], 0.9, rot=i * 20)
    c.restoreState()


def page_cards(doc: Doc, teachers, notes, layout="cut"):
    """One card per teacher. `cut` = two A5-landscape cards per A4 sheet with a cut line;
    `a5` = exact-size A5 page per card; `a4` = one big A4-landscape card per teacher."""
    c = doc.c
    if layout == "a5":
        c.setPageSize((CARD_W, CARD_H))
        for t in teachers:
            doc.page += 1
            card_face(doc, t, notes, sc=1.0)
            doc.show()
        return
    scale = 1.0 if layout == "cut" else (PW - 2 * 12) / CARD_W
    gap = PH - 2 * CARD_H * scale
    per = 1 if layout != "cut" else 2
    for i in range(0, len(teachers), per):
        batch = teachers[i:i + per]
        doc.page += 1
        c.setFillColor(HexColor(doc.splash_bg or PAPER))
        c.rect(0, 0, PW, PH, stroke=0, fill=1)
        x = (PW - CARD_W * scale) / 2
        if per == 1:
            ys = [(PH - CARD_H * scale) / 2]
        else:
            # top card and bottom card share the middle of the sheet, so one straight cut
            # along that line yields two exact A5-landscape cards
            ys = [PH - gap / 2 - CARD_H * scale, gap / 2]
        cut_y = ys[0]
        for k, t in enumerate(batch):
            y = ys[k]
            card_face(doc, t, notes, sc=scale, x=x, y=y)
        if per == 2 and len(batch) == 2:      # the two cards share an edge: score it for cutting
            dashed_rule(c, 0, PW, cut_y, "#a99a80", (5, 4), 0.9)
            for tx in (7, PW - 7):
                c.saveState()
                c.setStrokeColor(HexColor(SLATE))
                c.setLineWidth(0.5)
                c.setStrokeAlpha(0.8)
                c.circle(tx, cut_y, 3.0, stroke=1, fill=0)
                c.line(tx - 1.1, cut_y - 1.1, tx + 1.1, cut_y + 1.1)
                c.restoreState()
            text(c, "cut here", PW - 52, cut_y + 4.5, "sansb", 5.2, SLATE, 1.4, "l", 0.65)
        doc.show()


# ------------------------------------------------------------------- foldable gift cards
# One A4 landscape sheet per teacher, printed on BOTH sides and folded once in half.
#   outside page : [back cover | FRONT cover]   -> after folding, the greeting faces out
#   inside  page : [the letter  |  the QR page] -> what they find when they open it
# Each panel is A6 portrait (105 x 148.5 mm), the classic folded-card size.
PANEL_W, PANEL_H = 420.94, 595.28
FOLD_SHEET = (841.89, 595.28)
QR_BASE_DEFAULT = "https://pavit12301611.github.io/teachers-day/"
FOLD_SECRETS = [
    "Tap your photo five times",
    "The gift box, hiding in the footer",
    "One line written in invisible ink",
    "The secret key: up up down down left right left right B A",
]


def qr_matrix(data):
    """A QR matrix (tuple of rows of 0/1) — segno if present, then qrcode, else None."""
    cache = getattr(qr_matrix, "_cache", None)
    if cache is None:
        cache = {}
        qr_matrix._cache = cache
    if data in cache:
        return cache[data]
    m = None
    try:
        import segno
        m = [[int(bool(v)) for v in row] for row in segno.make(data, error="l").matrix]
    except Exception:
        try:
            import qrcode
            qr = qrcode.QRCode(border=0, box_size=1,
                               error=qrcode.constants.ERROR_CORRECT_L)
            qr.add_data(data)
            qr.make(fit=True)
            m = [[int(bool(v)) for v in row] for row in qr.get_matrix()]
        except Exception:
            m = None
    m = tuple(tuple(row) for row in m) if m else None
    cache[data] = m
    return m


def draw_qr(c, cx, cy, size, matrix, ink=INK, paper="#ffffff", pad=4.0):
    """Vector QR code: crisp at any print size and it costs nothing in file weight.
    Runs of dark modules are merged into single rectangles, so 166 pages stay light."""
    if not matrix:
        return 0
    n = len(matrix)
    quiet = 4                                   # spec-recommended clear space, in modules
    m = size / float(n)                         # `size` is the code itself; the card is bigger
    c.saveState()
    c.setFillColor(HexColor(paper))
    c.setFillAlpha(1)
    c.setStrokeColor(HexColor(paper))
    c.setLineWidth(1)
    # a solid white card under the code: phones need calm, bright clear space around it,
    # and the theme washes on these cards are not bright enough to trust
    card = size + (m * quiet + pad) * 2
    c.roundRect(cx - card / 2, cy - card / 2, card, card, 4.0, stroke=1, fill=1)
    c.setFillColor(HexColor(ink))
    x0, y0 = cx - size / 2, cy - size / 2 + (n - 1) * m
    for i, row in enumerate(matrix):
        yy = y0 - i * m
        j = 0
        while j < n:
            if row[j]:
                k = j
                while k + 1 < n and row[k + 1]:
                    k += 1
                c.rect(x0 + j * m, yy, (k - j + 1) * m + 0.06, m + 0.06, stroke=0, fill=1)
                j = k + 1
            else:
                j += 1
    c.restoreState()
    return size + m * quiet * 2


def logo_image():
    """The school logo as one shared ImageReader, so 83 back covers embed it exactly once."""
    got = getattr(logo_image, "_got", None)
    if got is not None:
        return got
    logo_image._got = False
    fp = ROOT / "assets" / "logo.png"
    if fp.exists():
        try:
            im = Image.open(fp).convert("RGB")
            if im.size[0] > 460:
                im = im.resize((460, int(im.size[1] * 460 / im.size[0])), Image.LANCZOS)
            logo_image._got = ImageReader(BytesIO(_jpeg_blob(im, 90)))
        except Exception:
            logo_image._got = False
    return logo_image._got


def qr_card_w(box, matrix):
    """Side of the white card draw_qr paints for a `box`-wide code, so frames can hug it."""
    if not matrix:
        return box + 40
    m = box / float(len(matrix))
    return box + (m * 4 + 4.0) * 2


def fold_url(t, base):
    return base.rstrip("/") + "/teacher.html?t=" + (t.get("id") or ("p%03d" % t["num"]))


def fold_skin(doc, t, w, h, gutter=0.0):
    """The shared card skin: paper, theme tint, painted washes, gilded double frame, rainbow."""
    c = doc.c
    c1, c2, soft = t["theme"]["c1"], t["theme"]["c2"], t["theme"]["soft"]
    c.setFillColor(HexColor(doc.splash_bg or PAPER))
    c.rect(0, 0, w + gutter, h, stroke=0, fill=1)
    c.setFillColor(tint(soft, 0.58, towards=PAPER))
    c.rect(0, 0, w + gutter, h, stroke=0, fill=1)
    wash(c, 12, h - 8, 170, [c1, c2], alpha=0.075, blobs=5, seed=t["num"], spread=0.3, squash=0.6)
    wash(c, (w + gutter) - 12, 10, 160, [c2, WC["sun"]], alpha=0.07, blobs=4, seed=t["num"] + 2,
         spread=0.3, squash=0.6)
    wash(c, w * 0.5, h * 0.42, 190, [c1, WC["teal"]], alpha=0.04, blobs=3, seed=t["num"] + 5,
         spread=0.35, squash=0.5)
    speckle(c, 0, h - 40, w + gutter, 40, [c1, c2, WC["sun"]], 24, t["num"] + 7, 0.35, 1.1,
            0.35)
    c.saveState()
    c.setStrokeColor(HexColor(c1))
    c.setLineWidth(1.5)
    fw = w + gutter
    c.roundRect(10, 10, fw - 20, h - 20, 8, stroke=1, fill=0)
    c.setStrokeColor(HexColor(GOLD))
    c.setLineWidth(0.5)
    c.setStrokeAlpha(0.85)
    c.roundRect(15, 15, fw - 30, h - 30, 6, stroke=1, fill=0)
    c.restoreState()
    hband(c, 15, h - 14.5, fw - 30, 2.8, RAINBOW_HEX, 60, 0.9)
    corner_flourish(c, 19, 19, 20, c2, 1, 1)
    corner_flourish(c, fw - 19, 19, 20, c1, -1, 1)
    corner_flourish(c, 19, h - 19, 20, c1, 1, -1)
    corner_flourish(c, fw - 19, h - 19, 20, c2, -1, -1)


def fold_ticks(c, x, h, label="fold", dashes=True):
    """Marks on the panel edge that becomes the crease, so the card is folded in the right place."""
    c.saveState()
    c.setStrokeColor(HexColor(SLATE))
    c.setLineWidth(0.5)
    c.setStrokeAlpha(0.7)
    for yy in (h - 22, 22):
        c.setDash(2.6, 2.4)
        c.line(x, yy - 7, x, yy + 7)
    if dashes:
        c.setDash(3.4, 3.0)
        c.setStrokeAlpha(0.4)
        c.line(x, 30, x, h - 30)
    c.restoreState()
    if label:
        c.saveState()
        c.translate(x, h / 2)
        c.rotate(-90)
        text(c, label.upper(), 0, -3.2, "sansb", 4.8, SLATE, 2.2, "c", 0.55)
        c.restoreState()


def fold_front(doc, t, notes, x, y, sc=1.0):
    """The face that shows once the card is folded: greeting, photo, name — nothing else."""
    c = doc.c
    c.saveState()
    c.translate(x, y)
    c.scale(sc, sc)
    W, H = PANEL_W, PANEL_H
    c1, c2 = t["theme"]["c1"], t["theme"]["c2"]
    fold_skin(doc, t, W, H)
    seal(c, 40, H - 40, 13.0, f"{t['num']:02d}", "OF 83", c2, "#fffdf6", INK, rot=-7)
    text(c, "FROM PAVIT SINGH", W - 30, H - 36, "sansb", 5.6, WC["bronze"], 1.7, "r", 0.85)
    text(c, "ONE CARD, ONE TEACHER", W - 30, H - 45, "sansb", 5.0, SLATE, 1.3, "r", 0.7)

    greet = "Happy Teachers\u2019 Day"
    gs = 31.0
    while sw(greet, F["script"], gs) > W - 64 and gs > 20:
        gs -= 0.5
    text(c, greet, W / 2, H - 92, "script", gs, HexColor(c1), 0, "c")
    who = {"Ma'am": "FOR YOU, MA'AM", "Sir": "FOR YOU, SIR"}.get(clean(t.get("title") or ""),
                                                                  "FOR YOU")
    text(c, who, W / 2, H - 107, "sansb", 5.4, c2, 2.4, "c", 0.8)
    ribbon(c, W / 2, H - 128, "5TH SEPTEMBER", c2, WC["grape"], 6.4, "sansb", "#ffffff", 1.3, 13)

    dia = 188.0
    doc.portrait_on(t, W / 2, H - 152 - dia / 2, dia, plate=True, halo=True, raster=dia * sc)
    ny = H - 152 - dia - 26
    name = clean(t["name"])
    nsize, namew = 22.0, W - 48
    lines = wrap(name, F["serifb"], nsize, namew)
    if len(lines) > 2:
        nsize = 18.5
        lines = wrap(name, F["serifb"], nsize, namew)[:2]
    for ln in lines:
        text(c, ln, W / 2, ny, "serifb", nsize, INK, 0.25, "c")
        ny -= nsize * 1.18
    des = clean(t.get("designation", ""))
    dsize = fit(des, "sansb", 7.6, namew - 40, 1.4)
    pwid = min(namew, sw(des, F["sansb"], dsize, 1.4) + 22)
    ny -= 2
    c.setFillColor(HexColor(c1))
    c.setFillAlpha(0.95)
    c.roundRect(W / 2 - pwid / 2, ny - 4.6, pwid, 15, 7.5, stroke=0, fill=1)
    c.setFillAlpha(1)
    text(c, des, W / 2, ny - 0.6, "sansb", dsize, "#ffffff", 1.4, "c")
    ny -= 19
    chips = subject_tokens(t)[:3]
    if chips:
        widths = [min(126, sw(ch, F["sansb"], 6.4, 0.8) + 14) for ch in chips]
        cw = sum(widths) + 6 * (len(chips) - 1)
        x0 = W / 2 - cw / 2
        for ch, wid in zip(chips, widths):
            c.setFillColor(tint(c2, 0.80, towards=PAPER))
            c.roundRect(x0, ny - 4.6, wid, 13.4, 6.7, stroke=0, fill=1)
            c.setStrokeColor(HexColor(c2))
            c.setStrokeAlpha(0.5)
            c.setLineWidth(0.5)
            c.roundRect(x0, ny - 4.6, wid, 13.4, 6.7, stroke=1, fill=0)
            c.setStrokeAlpha(1)
            text(c, ch, x0 + wid / 2, ny, "sansb", 6.4, INK, 0.8, "c")
            x0 += wid + 6
        ny -= 16
    qual = pretty_qual(t.get("qualification", ""))
    if qual:
        text(c, qual, W / 2, ny, "serif", 8.4, SLATE, 0.3, "c", 0.9)
    dashed_rule(c, 26, W - 26, 92, "#dcccb0", (2.6, 3.2), 0.6)
    ow = sw("OPEN ME", F["sansb"], 6.6, 3.0)
    text(c, "OPEN ME", W / 2, 76, "sansb", 6.6, HexColor(c1), 3.0, "c", 0.9)
    text(c, "your message and a page made for you are inside", W / 2, 64, "serifi", 8.6,
         "#4b3c55", 0.1, "c")
    heart(c, W / 2 - ow / 2 - 11, 78, 3.0, c2, 0.85)
    heart(c, W / 2 + ow / 2 + 11, 78, 3.0, c1, 0.85)
    confetti(c, 24, 36, W - 48, 20, 9, t["num"] + 3, 0.4)
    garland(c, 26, 12, GOLD, 8, t["num"], x1=22, x2=W - 22)
    fold_ticks(c, 0, H, "fold", dashes=False)
    c.restoreState()


def fold_back_cover(doc, t, x, y, url, qr_ok, sc=1.0):
    """The outside back of the folded card: the school, who made it, and a small scan line."""
    c = doc.c
    c.saveState()
    c.translate(x, y)
    c.scale(sc, sc)
    W, H = PANEL_W, PANEL_H
    c1 = t["theme"]["c1"]
    fold_skin(doc, t, W, H)
    text(c, "ST. MARY\u2019S ACADEMY", W / 2, H - 60, "serifb", 12.5, INK, 2.6, "c")
    text(c, "SAHARANPUR  \u00b7  TEACHERS\u2019 DAY 2019-20", W / 2, H - 74, "sansb", 5.6,
         SLATE, 1.9, "c", 0.9)
    lg = logo_image()
    if lg:
        lw_, lh_ = 76.0, 76.0 * 348 / 460
        framed_panel(c, W / 2 - lw_ / 2 - 7, H - 150 - lh_ / 2 - 7, lw_ + 14, lh_ + 14,
                     "#ffffff", GOLD, 7, 0.8, True, 0.10, True)
        c.drawImage(lg, W / 2 - lw_ / 2, H - 150 - lh_ / 2, lw_, lh_, mask=None)
    gem_rule(c, 60, W - 60, H - 202, GOLD, 2.2, 3)
    text(c, "MADE FOR ONE TEACHER", W / 2, H - 220, "serif", 9.6, "#3f3450", 0.2, "c")
    line = (f"This is card {t['num']:02d} of 83 \u2014 the other 82 each carry "
            "somebody else\u2019s name")
    text(c, line, W / 2, H - 235, "serifi", fit(line, "serifi", 8.0, W - 60, 0.1), SLATE, 0.1,
         "c")
    dashed_rule(c, 40, W - 40, H - 250, "#dcccb0", (2.6, 3.2), 0.6)
    text(c, "MADE BY", W / 2, H - 270, "sansb", 5.6, WC["bronze"], 2.0, "c", 0.9)
    text(c, "Pavit Singh", W / 2, H - 292, "script", 22, HexColor(WC["grape"]), 0, "c")
    text(c, "CLASS IX-B  \u00b7  ROLL NO. 9231", W / 2, H - 310, "sansb", 5.4, SLATE, 1.6, "c",
         0.85)
    if qr_ok:
        box = 104.0
        cy = H - 408
        cw = qr_card_w(box, qr_ok) + 12
        draw_qr(c, W / 2, cy, box, qr_ok)
        c.saveState()
        c.setStrokeColor(HexColor(c1))
        c.setLineWidth(0.6)
        c.setStrokeAlpha(0.5)
        c.roundRect(W / 2 - cw / 2, cy - cw / 2, cw, cw, 7, stroke=1, fill=0)
        c.restoreState()
        text(c, "SCAN: MY PAGE FOR YOU", W / 2, cy - cw / 2 - 14, "sansb", 5.4, WC["bronze"],
             1.8, "c", 0.9)
    else:
        addr = url.split("//")[-1]
        text(c, "MY PAGE FOR YOU", W / 2, H - 340, "sansb", 5.6, WC["bronze"], 1.9, "c", 0.9)
        text(c, addr, W / 2, H - 356, "serifi", fit(addr, "serifi", 8.4, W - 70, 0.2),
             "#3f3450", 0.1, "c")
    text(c, "open the card for the message and a bigger code to scan", W / 2, 62, "serifi",
         7.6, SLATE, 0.1, "c", 0.9)
    garland(c, 26, 12, GOLD, 8, t["num"], x1=22, x2=W - 22)
    fold_ticks(c, W, H, "fold", dashes=False)
    c.restoreState()


def fold_inside(doc, t, notes, url, qr_ok, sc=1.0):
    """The inside spread: Pavit's letter on the left, the QR and the 4 secrets on the right.
    Both halves are measured first, then set, so a three-line note and a six-line note both
    sit in the middle of their page instead of leaving a hole at the foot."""
    c = doc.c
    c.saveState()
    c.scale(sc, sc)
    W, H = PANEL_W, PANEL_H
    c1, c2 = t["theme"]["c1"], t["theme"]["c2"]
    fold_skin(doc, t, W, H, gutter=W)
    fold_ticks(c, W, H, "fold")

    # ---- left half: the letter, measured once and then drawn, so it sits in the middle
    # of the leaf whatever the length of Pavit's note. `desc` is the descent from the
    # greeting's baseline to the last line, and every step below costs exactly what it says.
    lx, lw = 34, W - 68
    body = card_message(t, notes)
    msz, lead = 11.4, 16.6
    lines = wrap(body, F["serif"], msz, lw)
    while len(lines) * lead > 250 and msz > 9.6:
        msz -= 0.3
        lead = msz * 1.46
        lines = wrap(body, F["serif"], msz, lw)
    wish = card_wish(t)
    wsz = fit(wish, "serifi", 10.6, lw)
    wl = wrap(wish, F["serifi"], wsz, lw)
    pts = SUBJECT_POINTS[card_key(t)]
    desc = (22 + len(lines) * lead + 26 + len(wl) * wsz * 1.4 + 14 + 40 + 20 + 16 + 14
            + 12.4 * len(pts) + 10)
    top = 52 + (H - 104 - desc - 18) / 2 + desc + 4
    top = max(desc + 58, min(H - 58, top))
    text(c, "THE MESSAGE", lx, H - 44, "sansb", 6.2, WC["bronze"], 2.2, "l", 0.9)
    yy = top
    greet_name = clean(t.get("title") or "")
    text(c, f"Dear {greet_name}," if greet_name else "Dear Teacher,", lx, yy, "serifb", 15.5,
         INK, 0.1, "l")
    yy -= 22
    for ln in lines:
        text(c, ln, lx, yy, "serif", msz, "#3f3450", 0.0, "l")
        yy -= lead
    yy -= 8
    gem_rule(c, lx, lx + lw, yy, GOLD, 2.2, 3)
    yy -= 18
    for ln in wl:
        text(c, ln, lx, yy, "serifi", wsz, "#4b3c55", 0.1, "l")
        yy -= wsz * 1.4
    yy -= 14
    text(c, "With love and gratitude,", lx, yy, "serif", 9.6, SLATE, 0.2, "l", 0.9)
    text(c, "Pavit Singh", lx - 3, yy - 22, "script", 26, HexColor(WC["grape"]), 0, "l")
    sig_w = sw("Pavit Singh", F["script"], 26) + 26 * word_pad("script") * 2
    flower(c, lx + 12 + sig_w, yy - 16, 6.2, c2, WC["sun"], 0.9)
    yy -= 40
    text(c, "CLASS IX-B  \u00b7  ROLL NO. 9231  \u00b7  ST. MARY\u2019S ACADEMY", lx, yy,
         "sansb", fit("CLASS IX-B  \u00b7  ROLL NO. 9231  \u00b7  ST. MARY\u2019S ACADEMY",
                      "sansb", 5.8, lw, 1.5), SLATE, 1.5, "l", 0.8)
    yy -= 20
    dashed_rule(c, lx, lx + lw, yy, "#dcccb0", (2.6, 3.2), 0.6)
    yy -= 16
    text(c, "THREE THINGS I REMEMBER", lx, yy, "sansb", 5.8, HexColor(c1), 2.0, "l", 0.9)
    yy -= 14
    for i, pt in enumerate(pts):
        heart(c, lx + 3, yy, 2.4, [c1, c2, WC["sun"]][i % 3], 0.85)
        text(c, pt, lx + 12, yy, "serif", 9.0, "#4b3c55", 0.1, "l")
        yy -= 12.4
    garland(c, 26, 12, GOLD, 8, t["num"], x1=24, x2=W - 24)

    # ---- right half: the page he made for them, also centred as one block
    rx, rw = W + 34, W - 68
    rblock = (132 + 28 + 46) if qr_ok else 40
    rblock += 24 + 16 + 13.4 * len(FOLD_SECRETS) + 16
    ry = 64 + ((H - 70 - 64) - rblock) / 2 + rblock
    text(c, "AND A WHOLE PAGE, MADE FOR YOU", rx, H - 44, "sansb", 6.2, WC["bronze"], 2.0, "l",
         0.9)
    if qr_ok:
        box = 132.0
        cw = qr_card_w(box, qr_ok) + 14
        cye = ry - cw / 2
        c.saveState()
        c.setStrokeColor(HexColor(c1))
        c.setLineWidth(0.7)
        c.setStrokeAlpha(0.5)
        c.roundRect(rx + rw / 2 - cw / 2, cye - cw / 2, cw, cw, 10, stroke=1, fill=0)
        c.restoreState()
        draw_qr(c, rx + rw / 2, cye, box, qr_ok)
        shown = url.split("//")[-1]
        text(c, "point a camera at this", rx + rw / 2, cye - cw / 2 - 16, "serifi", 9.0,
             "#4b3c55", 0.4, "c", 0.9)
        text(c, shown, rx + rw / 2, cye - cw / 2 - 30, "sansb",
             fit(shown, "sansb", 6.0, rw, 0.4), SLATE, 0.4, "c", 0.9)
        ty = cye - cw / 2 - 54
    else:
        text(c, url, rx, ry - 20, "serif", 9.4, INK, 0.1, "l")
        ty = ry - 40
    dashed_rule(c, rx, rx + rw, ty, "#dcccb0", (2.6, 3.2), 0.6)
    text(c, "FOUR THINGS ARE HIDING ON THAT PAGE", rx, ty - 16, "sansb", 5.8, HexColor(c1), 1.8,
         "l", 0.9)
    ty -= 32
    for i, secret in enumerate(FOLD_SECRETS):
        star(c, rx + 4, ty + 2.4, 2.8, RAINBOW_HEX[(t["num"] + i) % 8], 0.9, rot=i * 18)
        text(c, secret, rx + 14, ty, "serif", 9.0, "#4b3c55", 0.1, "l")
        ty -= 13.4
    text(c, "find all four and the page turns gold", rx, ty - 4, "serifi", 8.4, SLATE, 0.1, "l",
         0.9)
    confetti(c, rx, 44, rw, 20, 9, t["num"] + 5, 0.4)
    garland(c, 26, 12, GOLD, 8, t["num"], x1=W + 24, x2=2 * W - 24)
    c.restoreState()


def fold_geometry(edge_mm=3.5):
    """Scale + offset so both panels sit inside a real printer's unprintable margin.
    edge_mm=0 gives an exact half-of-A4 card, for a borderless-capable printer."""
    sw_, sh_ = FOLD_SHEET
    edge = max(0.0, float(edge_mm)) / 25.4 * 72
    sc = min((sw_ - 2 * edge) / (2 * PANEL_W), (sh_ - 2 * edge) / PANEL_H)
    return sc, (sw_ - 2 * PANEL_W * sc) / 2, (sh_ - PANEL_H * sc) / 2


def page_fold(doc, teachers, notes, base, edge_mm=3.5, side="both", qr=True):
    """Two pages per teacher (outside + inside) so one A4 sheet folds into one card."""
    c = doc.c
    sc, ox, oy = fold_geometry(edge_mm)
    for t in teachers:
        url = fold_url(t, base)
        mat = qr_matrix(url) if qr else None
        for kind in (("outside", "inside") if side == "both" else (side,)):
            doc.page += 1
            c.setPageSize(FOLD_SHEET)
            if kind == "outside":
                fold_back_cover(doc, t, ox, oy, url, mat, sc)
                fold_front(doc, t, notes, ox + PANEL_W * sc, oy, sc)
            else:
                c.saveState()
                c.translate(ox, oy)
                fold_inside(doc, t, notes, url, mat, sc)
                c.restoreState()
            doc.show()


# --------------------------------------------------------------------- page bookkeeping
def build_plan(groups, order):
    """Page numbers are deterministic, so work them out first for the contents list.
    Mirrors render() exactly: cover · intro · leadership · (divider + grids)* · letter ·
    wall · credits."""
    lead = [g for g in ("Principal", "Manager") if g in groups]
    rest = [g for g in order if g not in lead]
    per = COLS * ROWS
    page, pages, counts = 3, {}, {}       # cover(1) · intro(2) · leadership(3)
    for g in lead:
        pages[g], counts[g] = page, len(groups[g])
    for g in rest:
        counts[g] = len(groups[g])
        page += 1                         # divider
        pages[g] = page
        page += math.ceil(counts[g] / per)
    page += 3                             # letter, wall, credits
    return {"pages": pages, "counts": counts, "order": order, "lead": lead, "rest": rest,
            "per": per, "total": page}


def render_cards(teachers, notes, out: Path, layout: str, dpi: float, quality: int,
                 edge_mm: float = 3.5, base: str = QR_BASE_DEFAULT, side: str = "both",
                 qr: bool = True):
    """One personalised card per teacher; returns the number of PDF pages."""
    prep_card_keys(teachers, notes)
    if layout == "fold" and qr and qr_matrix(base) is None:
        raise SystemExit("QR codes need a QR library:  pip install segno   (or --no-qr)")
    splash, bg = load_splash()
    doc = Doc(out, dpi, quality, (splash, bg), meta={
        "title": "St. Mary's Academy — Teachers' Day Fold Cards 2019-20"
        if layout == "fold" else "St. Mary's Academy — Teachers' Day Cards 2019-20",
        "subject": "One printable, foldable thank-you card for every teacher, personalised one by one",
        "keywords": "Teachers' Day, thank-you cards, foldable, QR code, printable, personalised, "
                    "St. Mary's Academy"})
    if layout == "fold":
        page_fold(doc, teachers, notes, base, edge_mm, side, qr)
    else:
        page_cards(doc, teachers, notes, layout)
    doc.save()
    return doc.page


def render(groups, order, plan, d, notes, out: Path, dpi: float, quality: int):
    splash, bg = load_splash()
    doc = Doc(out, dpi, quality, (splash, bg))
    doc._pages = plan["total"]
    page_cover(doc, d, notes, plan)
    page_intro(doc, d, notes, plan)
    page_leadership(doc, groups, notes)
    numbers = {g: i for i, g in enumerate(plan["order"])}        # 01 = Principal … 09 = Support
    for g in plan["rest"]:
        gi = numbers[g]
        members = groups[g]
        page_divider(doc, g, gi, members, plan)
        if len(members) <= 2:                 # tiny teams get the big portrait treatment
            page_profiles(doc, g, gi, members, notes, d)
            continue
        chunks = [members[i:i + plan["per"]] for i in range(0, len(members), plan["per"])]
        for ci, chunk in enumerate(chunks):
            page_profiles_or_grid(doc, g, gi, chunk, notes, plan, len(members), ci, members)
    page_letter(doc, d)
    page_wall(doc, d)
    page_credits(doc, d, plan, notes)
    doc.save()
    return doc.page


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Print-ready PDFs for the Teachers' Day project: one personalised card per "
                    "teacher (default), or the full decorated staff book.")
    ap.add_argument("--mode", choices=("cards", "book"), default="cards",
                    help="cards = a hand-out card for every teacher; book = the 29-page staff book")
    ap.add_argument("--layout", choices=LAYOUTS, default="fold",
                    help="fold = A4 sheet per teacher, printed front and back, folded into one "
                         "card (default) · cut = 2 flat A5 cards per A4 with a cut line · "
                         "a5 = exact A5-landscape page per card · a4 = one big A4 card each")
    ap.add_argument("--edge-mm", type=float, default=3.5,
                    help="fold layout: blank margin kept clear on all four sides, so nothing is "
                         "clipped by the printer (0 = full bleed, exact half-A4)")
    ap.add_argument("--base-url", default=QR_BASE_DEFAULT,
                    help="where the QR codes point (your hosted site, no trailing slash needed)")
    ap.add_argument("--sides", choices=("both", "outside", "inside"), default="both",
                    help="fold layout: print both sides in one duplex PDF (default), or only one "
                         "side into its own file")
    ap.add_argument("--no-qr", action="store_true", help="fold layout: leave the QR codes out")
    ap.add_argument("--out", default=None, help="output PDF (default depends on --mode/--layout)")
    ap.add_argument("--only", default="", help="just these staff numbers, e.g. --only 1,4,59")
    ap.add_argument("--dpi", type=float, default=200.0, help="raster density for the portraits")
    ap.add_argument("--quality", type=int, default=80, help="JPEG quality for the portraits")
    args = ap.parse_args(argv)

    setup_fonts()
    d = load_data()
    notes = load_notes()
    grouped = {}
    for t in d["teachers"]:
        grouped.setdefault(t.get("group") or t.get("designation") or "Other", []).append(t)
    order = [g for g in GROUP_ORDER if g in grouped] + [g for g in grouped if g not in GROUP_ORDER]
    groups = {g: grouped[g] for g in order}
    if args.dpi < 140:
        print("warning: --dpi below 140 will look soft in print", file=sys.stderr)

    if args.only.strip():
        wanted = [int(x) for x in re.split(r"[,\s]+", args.only.strip()) if x]
        d["teachers"] = [t for t in d["teachers"] if t["num"] in wanted]

    size_name = {"fold": "A4-fold", "cut": "A5-cards-2-per-A4", "a5": "A5",
                 "a4": "A4"}[args.layout]
    stem = (f"St_Marys_Teacher_Cards_{size_name}" + ("" if args.sides == "both" or args.mode != "cards"
             else "_" + args.sides) + ".pdf")
    out = args.out or str(ROOT / (stem if args.mode == "cards"
                                  else "St_Marys_Staff_Book_2019-20.pdf"))

    if args.mode == "cards":
        pages = render_cards(d["teachers"], notes, Path(out), args.layout, args.dpi, args.quality,
                             args.edge_mm, args.base_url, args.sides, not args.no_qr)
        mb = Path(out).stat().st_size / 1e6
        mine = sum(1 for t in d["teachers"] if notes.get(t["num"]) and not RESTATE.match(notes[t["num"]]))
        if args.layout == "fold":
            sheets = pages // (1 if args.sides != "both" else 2)
            sc, _, _ = fold_geometry(args.edge_mm)
            card_mm = (PANEL_W * sc) / 72 * 25.4, (PANEL_H * sc) / 72 * 25.4
            n_cards = len(d["teachers"])
            plural = "card" if n_cards == 1 else "cards"
            sides_txt = ("printed front and back" if args.sides == "both"
                         else f"the {args.sides} side only")
            print(f"→ {out}\n   {n_cards} fold {plural} on {pages} page(s) = {sheets} "
                  f"A4 sheet(s), {sides_txt} · {mb:.2f} MB")
            print(f"   folded card size {card_mm[0]:.0f} × {card_mm[1]:.0f} mm · "
                  f"{mine} cards carry a note from memory")
            print(f"   QR codes point at: {args.base_url}")
            if args.sides == "both":
                print("   print: A4 LANDSCAPE · duplex = FLIP ON SHORT EDGE · 100% (actual size),"
                      " no duplex border/no scaling")
            else:
                other = "inside" if args.sides == "outside" else "outside"
                print(f"   single-sided: print this file, then re-feed the same sheets one at a "
                      f"time and print the {other} file on the back — run --only 41 first to check "
                      "which way your printer feeds")
            print("   then fold: crease on the marked middle line, printed OUTSIDE facing out")
        else:
            print(f"→ {out}\n   {len(d['teachers'])} personalised cards on {pages} page(s) "
                  f"({size_name}) · {mb:.2f} MB · {mine} cards carry a note from memory")
            if args.layout == "cut":
                print("   print at 100% (no scaling, duplex off), then cut each sheet once along "
                      "the dashed line")
        return 0

    plan = build_plan(groups, order)
    pages = render(groups, order, plan, d, notes, Path(out), args.dpi, args.quality)
    ok = "page plan OK" if pages == plan["total"] else f"page plan MISMATCH (planned {plan['total']})"
    size = Path(out).stat().st_size / 1e6
    print(f"→ {out}\n   {pages} pages · {ok} · {size:.2f} MB · {len(d['teachers'])} staff in "
          f"{len(order)} sections · {len(notes)} personal notes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
