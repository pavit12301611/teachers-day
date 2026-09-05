#!/usr/bin/env python3
"""
make_5cards.py — quick set of 5 Teachers' Day cards (same card format),
using photo PLACEHOLDERS (initials) instead of real photos.

Teachers:
  1. Biology  — Gaurav Sir
  2. Chemistry — Harshita Ma'am
  3. Physics  — Rahul Sir
  4. SST & English — Wajid Sir
  5. Maths    — Shivam Sir

Output: Teachers_Day_Cards_5.pdf  (A4 LANDSCAPE, double-sided, FLIP ON
LONG EDGE — inside pages are pre-rotated 180° so the fold reads upright).
"""

import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor

import make_cards as mc

OUT = os.path.join(mc.ROOT, "Teachers_Day_Cards_5.pdf")
# QR opens the tribute site (no per-teacher page exists for these names)
QR_URL = "https://teachers-day-rosy.vercel.app/"

TEACHERS = [
    {
        "num": 1, "id": "gaurav", "name": "Gaurav Sir", "title": "Sir",
        "designation": "Biology Teacher", "group": "P.G.T.",
        "qual": "M.Sc., B.Ed.", "subject": "Biology",
        "initial": "GS", "placeholder_label": "PHOTO",
        "c1": HexColor("#059669"), "c2": HexColor("#d97706"),
        "soft": HexColor("#e7f6ee"),
        "greeting": "Dear Sir,",
        "body": ["You made every cell, every leaf and every living thing feel",
                 "like a small miracle worth noticing.",
                 "May your day grow as warm and full of life as the labs you teach in."],
        "things": ["the diagrams on the board", "the lab-day excitement",
                   "the way you said 'observe carefully'"],
    },
    {
        "num": 2, "id": "harshita", "name": "Harshita Ma'am", "title": "Ma'am",
        "designation": "Chemistry Teacher", "group": "P.G.T.",
        "qual": "M.Sc., B.Ed.", "subject": "Chemistry",
        "initial": "HM", "placeholder_label": "PHOTO",
        "c1": HexColor("#7c3aed"), "c2": HexColor("#db2777"),
        "soft": HexColor("#f3efff"),
        "greeting": "Dear Ma'am,",
        "body": ["You turned equations and experiments into something I actually",
                 "looked forward to, and never let a doubt feel silly.",
                 "May your day sparkle like the prettiest reaction in the lab."],
        "things": ["the colour-changing tests", "your patience with my doubts",
                   "the 'one more reaction' days"],
    },
    {
        "num": 3, "id": "rahul", "name": "Rahul Sir", "title": "Sir",
        "designation": "Physics Teacher", "group": "P.G.T.",
        "qual": "M.Sc., B.Ed.", "subject": "Physics",
        "initial": "RS", "placeholder_label": "PHOTO",
        "c1": HexColor("#2563eb"), "c2": HexColor("#0891b2"),
        "soft": HexColor("#e9f1fe"),
        "greeting": "Dear Sir,",
        "body": ["You showed us that the whole world is just forces, motion and",
                 "curiosity \u2014 and that every question is allowed.",
                 "May your day be as bright and unstoppable as the ideas you spark."],
        "things": ["the pendulum demos", "the 'why does that happen?' talks",
                   "your calm during every hard sum"],
    },
    {
        "num": 4, "id": "wajid", "name": "Wajid Sir", "title": "Sir",
        "designation": "SST & English Teacher", "group": "T.G.T.",
        "qual": "M.A., B.Ed.", "subject": "SST & English",
        "initial": "WS", "placeholder_label": "PHOTO",
        "c1": HexColor("#b45309"), "c2": HexColor("#dc2626"),
        "soft": HexColor("#fdf3e2"),
        "greeting": "Dear Sir,",
        "body": ["Between maps, dates and stories, you taught us that history and",
                 "words are just two ways of understanding people.",
                 "May your day be as rich and memorable as the lessons you tell."],
        "things": ["the stories behind the dates", "the poems read aloud",
                   "the mark on the map quizzes"],
    },
    {
        "num": 5, "id": "shivam", "name": "Shivam Sir", "title": "Sir",
        "designation": "Maths Teacher", "group": "P.G.T.",
        "qual": "M.Sc., B.Ed.", "subject": "Mathematics",
        "initial": "SS", "placeholder_label": "PHOTO",
        "c1": HexColor("#dc2626"), "c2": HexColor("#7c3aed"),
        "soft": HexColor("#fdeaea"),
        "greeting": "Dear Sir,",
        "body": ["You made numbers feel like puzzles instead of fears, and proved",
                 "that every wrong step is just part of working it out.",
                 "May your day add up to joy, multiplied by everything you deserve."],
        "things": ["the shortcuts that worked", "the sums done on the board",
                   "the 'try it one more time' faith"],
    },
]

TOTAL = len(TEACHERS)


def main():
    for t in TEACHERS:
        t["url"] = QR_URL
        t["total"] = TOTAL
        t["photo"] = None  # -> placeholder circle

    W, H = A4[1], A4[0]
    MARGIN, GAP = 13, 9
    PW = (W - 2 * MARGIN - GAP) / 2
    PH = H - 2 * MARGIN
    LX, RX = MARGIN, MARGIN + PW + GAP
    PY = MARGIN

    c = canvas.Canvas(OUT, pagesize=(W, H))
    c.setTitle("Teachers' Day Cards \u2014 set of 5 (A4 fold)")
    c.setAuthor("Pavit Singh")
    c.setSubject("A4 LANDSCAPE, double-sided, FLIP ON LONG EDGE, then fold "
                 "on the dashed centre line")

    for t in TEACHERS:
        msg = {"greeting": t["greeting"], "body": t["body"],
               "things": t["things"]}

        # side 1 — OUTER (back | front)
        c.setFillColor(mc.PAPER)
        c.rect(0, 0, W, H, stroke=0, fill=1)
        ytop = mc.panel_base(c, LX, PY, PW, PH, t, t["num"] * 2)
        mc.panel_base(c, RX, PY, PW, PH, t, t["num"] * 2 + 1)
        mc.back_panel(c, LX, ytop, PW, PH, t, total=TOTAL)
        mc.front_panel(c, RX, ytop, PW, PH, t)
        mc.fold_line(c, W, H)
        c.showPage()

        # side 2 — INSIDE, pre-rotated 180° for long-edge duplex
        c.saveState()
        c.translate(W, H)
        c.rotate(180)
        c.setFillColor(mc.PAPER)
        c.rect(0, 0, W, H, stroke=0, fill=1)
        ytop = mc.panel_base(c, LX, PY, PW, PH, t, t["num"] * 2 + 100)
        mc.panel_base(c, RX, PY, PW, PH, t, t["num"] * 2 + 101)
        mc.message_panel(c, LX, ytop, PW, PH, t, msg)
        mc.qr_panel(c, RX, ytop, PW, PH, t)
        mc.fold_line(c, W, H)
        c.restoreState()
        c.showPage()

    c.save()
    print(f"wrote {OUT} ({os.path.getsize(OUT)/1e6:.1f} MB, {TOTAL*2} pages)")
    print("Print: A4 LANDSCAPE, double-sided, FLIP ON LONG EDGE, then fold.")


if __name__ == "__main__":
    main()
