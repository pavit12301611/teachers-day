#!/usr/bin/env python3
"""Build a print-ready ODT containing two fold-and-give Teachers' Day cards per A4 page.

The document is deliberately self-contained: every watercolour portrait and every QR
code lives inside the ODT, so it can be copied to another computer before printing.

Usage:
    python3 tools/generate_teachers_day_fold_cards.py

The first run briefly installs the small `qrcode` npm package in a temporary directory
(outside this repository) in order to generate standards-compliant QR vectors.  No
node_modules directory is added to the project.
"""

from __future__ import annotations

import argparse
import base64
import csv
import html
import json
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import zipfile
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "deliverables" / "Teachers_Day_Fold_Cards_83_Teachers.odt"
SITE_BASE = "https://teachers-day-rosy.vercel.app"

# A bright but print-friendly rotation.  Each pair is used for the cover and inside panel.
PALETTES = [
    {"ink": "#3B4D73", "accent": "#E96E58", "wash": "#FFF0E9", "wash2": "#DCEFF4", "gold": "#F6C95E", "leaf": "#41917A"},
    {"ink": "#4F3E76", "accent": "#D95E91", "wash": "#FCEBF3", "wash2": "#E3E5FB", "gold": "#F5C85F", "leaf": "#548A72"},
    {"ink": "#2F5A5B", "accent": "#DF7751", "wash": "#E8F5F0", "wash2": "#FFF0D7", "gold": "#EFC35F", "leaf": "#3C9077"},
    {"ink": "#56455E", "accent": "#C85D58", "wash": "#F9EEE0", "wash2": "#E6EFF7", "gold": "#E7B44D", "leaf": "#5E9E8E"},
    {"ink": "#3D5075", "accent": "#D66747", "wash": "#EAF3FE", "wash2": "#FCEBDD", "gold": "#F2C85D", "leaf": "#4C987E"},
    {"ink": "#5B4962", "accent": "#C4637C", "wash": "#F7ECF5", "wash2": "#E5F4F3", "gold": "#EFC55E", "leaf": "#4A927F"},
]


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def pretty_name(name: str) -> str:
    """Make names consistently readable while preserving initials and honorifics."""
    name = " ".join(name.strip().split())
    # The source list mixes upper case, lower case, and title case.  Title case is
    # easier to read in a greeting-card treatment and doesn't affect QR destinations.
    return name.title().replace("'S", "'s")


def lines_for(text: str, max_chars: int, max_lines: int = 2) -> list[str]:
    """Soft-wrap text for SVG (which does not wrap text nodes itself)."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        proposed = (current + " " + word).strip()
        if current and len(proposed) > max_chars:
            lines.append(current)
            current = word
        else:
            current = proposed
    if current:
        lines.append(current)
    if len(lines) <= max_lines:
        return lines
    # Keep the first max_lines-1 lines and compact the remainder without truncating a name.
    kept = lines[: max_lines - 1]
    kept.append(" ".join(lines[max_lines - 1 :]))
    return kept


def svg_text_lines(lines: list[str], x: float, y: float, line_height: float, **attrs: str) -> str:
    attr_text = " ".join(f'{key}="{esc(value)}"' for key, value in attrs.items())
    tspans = "".join(
        f'<tspan x="{x}" dy="{0 if i == 0 else line_height}">{esc(line)}</tspan>'
        for i, line in enumerate(lines)
    )
    return f'<text x="{x}" y="{y}" {attr_text}>{tspans}</text>'


def qr_payloads(urls: list[str]) -> dict[str, str]:
    """Generate SVG QR content with qrcode in an isolated, temporary npm prefix."""
    node_program = r'''
const QRCode = require('qrcode');
const readline = require('readline');
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', c => input += c);
process.stdin.on('end', async () => {
  const urls = JSON.parse(input);
  const result = {};
  for (const url of urls) {
    result[url] = await QRCode.toString(url, {
      type: 'svg',
      errorCorrectionLevel: 'M',
      margin: 3,
      color: { dark: '#24364C', light: '#FFFDF7' }
    });
  }
  process.stdout.write(JSON.stringify(result));
});
'''
    with tempfile.TemporaryDirectory(prefix="teachers-day-qr-") as temp_dir:
        temp = Path(temp_dir)
        # Cache is normally reused by npm, so this does not usually need a network fetch.
        subprocess.run(
            ["npm", "install", "--prefix", str(temp), "qrcode@1.5.4", "--no-audit", "--no-fund", "--silent"],
            check=True,
            cwd=ROOT,
        )
        qr_file = temp / "make-qrs.cjs"
        qr_file.write_text(node_program, encoding="utf-8")
        completed = subprocess.run(
            ["node", str(qr_file)],
            check=True,
            input=json.dumps(urls),
            text=True,
            stdout=subprocess.PIPE,
            cwd=ROOT,
            env={**os.environ, "NODE_PATH": str(temp / "node_modules")},
        )
    return json.loads(completed.stdout)


def qr_fragment(qr_svg: str, x: float, y: float, size: float) -> str:
    """Place the QR's vector paths in the page SVG, rather than rasterising them."""
    inner = qr_svg[qr_svg.find(">") + 1 : qr_svg.rfind("</svg>")]
    return (
        f'<svg x="{x}" y="{y}" width="{size}" height="{size}" '
        f'viewBox="0 0 39 39" shape-rendering="crispEdges">{inner}</svg>'
    )


def watercolour_blob(cx: float, cy: float, colour: str, second_colour: str) -> str:
    """A few translucent, imperfect marks make the paper feel hand-painted."""
    return f'''<g opacity="0.45">
      <path d="M {cx-22} {cy+2} C {cx-26} {cy-14}, {cx-9} {cy-25}, {cx+7} {cy-20}
               C {cx+23} {cy-28}, {cx+36} {cy-11}, {cx+28} {cy+3}
               C {cx+39} {cy+19}, {cx+14} {cy+25}, {cx-5} {cy+19}
               C {cx-20} {cy+25}, {cx-29} {cy+13}, {cx-22} {cy+2}Z" fill="{colour}"/>
      <path d="M {cx-8} {cy-24} C {cx+7} {cy-34}, {cx+25} {cy-23}, {cx+19} {cy-8}
               C {cx+35} {cy+2}, {cx+19} {cy+20}, {cx+3} {cy+10}
               C {cx-14} {cy+18}, {cx-23} {cy-5}, {cx-8} {cy-24}Z" fill="{second_colour}" opacity="0.7"/>
    </g>'''


def doodle(x: float, y: float, colour: str, kind: str = "star") -> str:
    if kind == "heart":
        return f'<path d="M {x} {y+4} C {x-9} {y-4}, {x-13} {y+7}, {x} {y+16} C {x+13} {y+7}, {x+9} {y-4}, {x} {y+4}Z" fill="none" stroke="{colour}" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round"/>'
    if kind == "leaf":
        return f'<path d="M {x-8} {y+10} C {x-5} {y-6}, {x+12} {y-9}, {x+10} {y+8} C {x+7} {y+14}, {x} {y+16}, {x-8} {y+10}Z M {x-6} {y+11} L {x+7} {y-3}" fill="none" stroke="{colour}" stroke-width="1.15" stroke-linecap="round" stroke-linejoin="round"/>'
    if kind == "pencil":
        return f'<g transform="rotate(-23 {x} {y})"><path d="M {x-13} {y-3} L {x+11} {y-3} L {x+16} {y} L {x+11} {y+3} L {x-13} {y+3}Z" fill="none" stroke="{colour}" stroke-width="1.15" stroke-linejoin="round"/><path d="M {x-13} {y-3} L {x-18} {y} L {x-13} {y+3}" fill="none" stroke="{colour}" stroke-width="1.15" stroke-linejoin="round"/></g>'
    return f'<path d="M {x} {y-8} L {x+2} {y-2} L {x+8} {y} L {x+2} {y+2} L {x} {y+8} L {x-2} {y+2} L {x-8} {y} L {x-2} {y-2}Z" fill="none" stroke="{colour}" stroke-width="1.15" stroke-linejoin="round"/>'


def appreciation_line(record: dict[str, str]) -> list[str]:
    subject = " ".join(record["subject_or_role"].strip().split())
    if subject and subject != ".":
        if len(subject) <= 31:
            line = f"Thank you for making {subject.lower()} feel possible."
        else:
            line = "Thank you for making every lesson feel possible."
    elif record["designation"].lower() == "supporting staff":
        line = "Thank you for the care that keeps our school shining."
    else:
        line = "Thank you for the care, guidance, and encouragement you give."
    return lines_for(line, 37, 2)


def photo_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return "data:image/jpeg;base64," + encoded


def teacher_card_svg(record: dict[str, str], qr_svg: str, palette: dict[str, str], generic: bool = False) -> str:
    """Return a 194 mm × 133 mm two-panel folded card as an SVG group.

    The left panel is the inside message; the right panel is the cover.  After cutting
    the sheet in half, fold on the vertical dotted line with the cover facing out.
    """
    card_w, card_h, half = 194.0, 133.0, 97.0
    name = pretty_name(record["name"])
    designation = record["designation"].strip()
    teacher_id = f"p{int(record['number']):03d}"
    url = f"{SITE_BASE}/teacher.html?t={teacher_id}"
    portrait = ROOT / "assets" / "staff-cards" / Path(record["image_file"]).name
    if not portrait.exists():
        portrait = ROOT / record["image_file"]
    portrait_uri = photo_data_uri(portrait)

    # Compose sensible name sizing for long names while keeping the cover airy.
    name_lines = lines_for(name, 15 if len(name) > 18 else 18, 2)
    name_size = "6.1" if len(name) <= 16 else ("5.0" if len(name) <= 20 else "4.7")
    # Names that wrap get a taller ribbon, so the second line remains comfortably clear.
    long_name = len(name_lines) > 1
    ribbon_y = 102.8 if long_name else 104.2
    ribbon_height = 11.9 if long_name else 8.1
    name_y = 107.2 if long_name else 109.1
    name_line_height = 4.35 if long_name else 4.6
    role_y = 120.3 if long_name else 118.2
    tagline_y = 126.3 if long_name else 124.5
    ornament_y = 123.0 if long_name else 121.0
    message_lines = appreciation_line(record)
    subject_label = record["subject_or_role"].strip()
    role_label = subject_label if subject_label and subject_label != "." else designation
    if len(role_label) > 30:
        role_label = designation
    role_label = role_label.title() if role_label.isupper() else role_label

    inner_message = [
        "You helped build more than lessons —",
        "you helped build confidence.",
        "This little page was made especially",
        "for you, with gratitude.",
    ]
    # Card group starts at 0,0 and is positioned by its parent page SVG.
    return f'''<g>
      <defs>
        <clipPath id="portrait-{teacher_id}"><rect x="116" y="34" width="76" height="67" rx="10"/></clipPath>
      </defs>
      <!-- full card + the two independently coloured panels -->
      <rect x="0.8" y="0.8" width="192.4" height="131.4" rx="5" fill="#FFFDF7" stroke="{palette['ink']}" stroke-width="1.45"/>
      <rect x="2" y="2" width="93.8" height="129" rx="4" fill="{palette['wash']}"/>
      <rect x="98.2" y="2" width="93.8" height="129" rx="4" fill="#FFFDF7"/>
      {watercolour_blob(35, 25, palette['wash2'], palette['gold'])}
      {watercolour_blob(164, 25, palette['wash'], palette['wash2'])}
      {watercolour_blob(172, 97, palette['wash2'], palette['gold'])}
      <!-- inside / invitation panel -->
      <path d="M 8 11 C 23 7, 46 14, 74 9 C 83 7, 89 8, 91 8" fill="none" stroke="{palette['accent']}" stroke-width="1.4" stroke-linecap="round" opacity=".7"/>
      {doodle(14, 18, palette['leaf'], 'leaf')}
      {doodle(82, 17, palette['accent'], 'heart')}
      <text x="48.5" y="19" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="3.1" font-weight="700" letter-spacing=".75" fill="{palette['ink']}">A LITTLE INVITATION FOR</text>
      {svg_text_lines(["DEAR " + name.upper() + ","], 48.5, 31, 4.3, **{"text-anchor": "middle", "font-family": "Comic Sans MS, DejaVu Sans, cursive", "font-size": "5.0", "font-weight": "700", "fill": palette['ink']})}
      {svg_text_lines(message_lines, 48.5, 43, 4.2, **{"text-anchor": "middle", "font-family": "DejaVu Sans, sans-serif", "font-size": "3.6", "font-weight": "700", "fill": palette['accent']})}
      {svg_text_lines(inner_message, 48.5, 56, 4.2, **{"text-anchor": "middle", "font-family": "DejaVu Sans, sans-serif", "font-size": "3.25", "fill": palette['ink']})}
      <g transform="translate(13 76)">
        <rect x="-1.3" y="-1.3" width="37.6" height="37.6" rx="3.4" fill="#FFFDF7" stroke="{palette['ink']}" stroke-width=".8"/>
        {qr_fragment(qr_svg, 1, 1, 33)}
      </g>
      <text x="56" y="84" font-family="DejaVu Sans, sans-serif" font-size="3.05" font-weight="700" fill="{palette['ink']}">SCAN TO OPEN</text>
      <text x="56" y="89" font-family="DejaVu Sans, sans-serif" font-size="3.05" font-weight="700" fill="{palette['ink']}">YOUR PERSONAL</text>
      <text x="56" y="94" font-family="DejaVu Sans, sans-serif" font-size="3.05" font-weight="700" fill="{palette['ink']}">TRIBUTE PAGE</text>
      <path d="M 56 97.5 C 66 96.5, 75 99, 86 97.4" fill="none" stroke="{palette['gold']}" stroke-width="1.35" stroke-linecap="round"/>
      <text x="56" y="103" font-family="DejaVu Sans, sans-serif" font-size="2.22" fill="{palette['ink']}" opacity=".9">teachers-day-rosy.vercel.app</text>
      <text x="56" y="106.6" font-family="DejaVu Sans, sans-serif" font-size="2.22" fill="{palette['ink']}" opacity=".9">/teacher.html?t={teacher_id}</text>
      <text x="48.5" y="119" text-anchor="middle" font-family="Comic Sans MS, DejaVu Sans, cursive" font-size="3.45" font-weight="700" fill="{palette['ink']}">With gratitude, Pavit Singh • IX-B</text>
      <text x="48.5" y="125" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="2.6" letter-spacing=".35" fill="{palette['accent']}">ST. MARY'S ACADEMY • 5 SEPTEMBER</text>
      {doodle(10, 116, palette['gold'], 'star')}
      {doodle(88, 116, palette['leaf'], 'pencil')}
      <!-- cover panel -->
      <path d="M 104 13 C 121 6, 145 13, 161 9 C 176 5, 185 9, 188 11" fill="none" stroke="{palette['accent']}" stroke-width="1.6" stroke-linecap="round" opacity=".8"/>
      {doodle(108, 18, palette['leaf'], 'leaf')}
      {doodle(185, 18, palette['accent'], 'heart')}
      <text x="145.5" y="19.5" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="3.1" font-weight="700" letter-spacing="1.1" fill="{palette['ink']}">HAPPY</text>
      <text x="145.5" y="27.6" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="6.7" font-weight="800" letter-spacing=".3" fill="{palette['accent']}">TEACHERS' DAY</text>
      <path d="M 114 30.7 C 128 34.5, 158 27.2, 178 31.2" fill="none" stroke="{palette['gold']}" stroke-width="1.55" stroke-linecap="round"/>
      <rect x="114.5" y="32.5" width="79" height="70" rx="11" fill="#FFFDF7" stroke="{palette['ink']}" stroke-width=".95"/>
      <image x="116" y="34" width="76" height="67" preserveAspectRatio="xMidYMid slice" clip-path="url(#portrait-{teacher_id})" xlink:href="{portrait_uri}"/>
      <path d="M 111 56 C 106 59, 106 66, 112 68" fill="none" stroke="{palette['gold']}" stroke-width="1.3" stroke-linecap="round"/>
      <path d="M 180 79 C 188 75, 191 68, 188 61" fill="none" stroke="{palette['leaf']}" stroke-width="1.3" stroke-linecap="round"/>
      <rect x="106" y="{ribbon_y}" width="79" height="{ribbon_height}" rx="4.05" fill="{palette['ink']}"/>
      {svg_text_lines(name_lines, 145.5, name_y, name_line_height, **{"text-anchor": "middle", "font-family": "Comic Sans MS, DejaVu Sans, cursive", "font-size": name_size, "font-weight": "700", "fill": "#FFFDF7"})}
      <text x="145.5" y="{role_y}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="3.05" font-weight="700" fill="{palette['ink']}">{esc(role_label)}</text>
      <text x="145.5" y="{tagline_y}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="2.7" letter-spacing=".2" fill="{palette['accent']}">A THANK-YOU MADE WITH LOVE</text>
      {doodle(109, ornament_y, palette['gold'], 'star')}
      {doodle(184, ornament_y, palette['leaf'], 'star')}
      <!-- fold guide, intentionally visible so this can be printed without guesswork -->
      <path d="M 97 6 L 97 127" fill="none" stroke="{palette['ink']}" stroke-width=".65" stroke-dasharray="2.2 1.9" opacity=".72"/>
      <rect x="89.1" y="127.1" width="15.8" height="3.55" rx="1.7" fill="#FFFDF7" opacity=".96"/>
      <text x="97" y="129.65" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="1.8" font-weight="700" letter-spacing=".25" fill="{palette['ink']}">FOLD</text>
    </g>'''


def generic_card_svg(qr_svg: str, palette: dict[str, str]) -> str:
    """The 84th slot keeps the final (odd-numbered) sheet two-up and is a useful spare."""
    record = {
        "number": "0",
        "name": "St. Mary's Family",
        "designation": "A Little Extra Thank-You",
        "subject_or_role": "",
        "image_file": "assets/logo-crest.png",
    }
    # Build a standard card, then substitute its legacy person URL/image with a home-page version.
    # The logo receives the same framed treatment as the portraits.
    card = teacher_card_svg(record, qr_svg, palette, generic=True)
    logo_uri = "data:image/png;base64," + base64.b64encode((ROOT / "assets" / "logo-crest.png").read_bytes()).decode("ascii")
    card = card.replace(
        f"{SITE_BASE}/teacher.html?t=p000", f"{SITE_BASE}/"
    ).replace("/teacher.html?t=p000", "/")
    # The raw image is not elsewhere in the SVG (portrait URI is only used once).
    old_portrait = photo_data_uri(ROOT / "assets" / "logo-crest.png")
    # If the designated logo has actually been selected already, no-op replacement is harmless.
    return card.replace(old_portrait, logo_uri)


def page_svg(top_card: str, bottom_card: str | None, page_number: int) -> str:
    """Place two 194×133 mm cards on an A4 portrait sheet, with a clear cut guide."""
    lower = f'<g transform="translate(8 155)">{bottom_card}</g>' if bottom_card else ""
    empty_label = "" if bottom_card else ""
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="210mm" height="297mm" viewBox="0 0 210 297">
  <rect width="210" height="297" fill="#FFFFFF"/>
  <g transform="translate(8 9)">{top_card}</g>
  {lower}
  <!-- Printed trim guide: cut here, then fold the dotted centre of each card. -->
  <g opacity=".9">
    <path d="M 8 148.5 H 202" stroke="#8491A0" stroke-width=".45" stroke-dasharray="2.1 1.4"/>
    <circle cx="12" cy="148.5" r="1.35" fill="#FFFFFF" stroke="#8491A0" stroke-width=".45"/>
    <path d="M 11.35 147.85 L 12.65 149.15 M 12.65 147.85 L 11.35 149.15" stroke="#8491A0" stroke-width=".45"/>
    <rect x="72" y="145.35" width="66" height="6.25" rx="3.1" fill="#FFFFFF"/>
    <text x="105" y="149.4" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="2.5" font-weight="700" letter-spacing=".22" fill="#667482">CUT HERE • THEN FOLD EACH CARD ON THE DOTTED CENTRE LINE</text>
    <circle cx="198" cy="148.5" r="1.35" fill="#FFFFFF" stroke="#8491A0" stroke-width=".45"/>
    <path d="M 197.35 147.85 L 198.65 149.15 M 198.65 147.85 L 197.35 149.15" stroke="#8491A0" stroke-width=".45"/>
  </g>
  <text x="8" y="294" font-family="DejaVu Sans, sans-serif" font-size="1.8" fill="#92A0AB">Teachers' Day Fold Cards • Page {page_number} • Print at 100% on A4 paper</text>
  <text x="202" y="294" text-anchor="end" font-family="DejaVu Sans, sans-serif" font-size="1.8" fill="#92A0AB">2 cards per page</text>
  {empty_label}
</svg>'''


def content_xml(page_count: int) -> str:
    # A page-anchored frame is placed *inside* its corresponding paragraph.  This is
    # the portable ODT representation: the paragraph creates each physical page and
    # the frame is absolutely positioned at that page's top-left corner.
    page_paragraphs = []
    for n in range(1, page_count + 1):
        paragraph_style = "PFirst" if n == 1 else "PBreak"
        page_paragraphs.append(
            f'''<text:p text:style-name="{paragraph_style}">&#160;
              <draw:frame draw:style-name="PageImage" draw:name="Invitation Cards Page {n}"
                   text:anchor-type="page" draw:page-number="{n}" svg:x="0mm" svg:y="0mm"
                   svg:width="210mm" svg:height="297mm" draw:z-index="0">
                <draw:image xlink:href="Pictures/page_{n:02d}.svg" xlink:type="simple"
                            xlink:show="embed" xlink:actuate="onLoad"/>
              </draw:frame>
            </text:p>'''
        )
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
 xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
 xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"
 xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
 xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"
 xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
 xmlns:xlink="http://www.w3.org/1999/xlink"
 xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0"
 office:version="1.3">
 <office:automatic-styles>
   <style:style style:name="PFirst" style:family="paragraph" style:master-page-name="CardPages"><style:paragraph-properties fo:margin-top="0mm" fo:margin-bottom="0mm" fo:line-height="1%"/></style:style>
   <style:style style:name="PBreak" style:family="paragraph" style:master-page-name="CardPages"><style:paragraph-properties fo:break-before="page" fo:margin-top="0mm" fo:margin-bottom="0mm" fo:line-height="1%"/></style:style>
   <style:style style:name="PageImage" style:family="graphic"><style:graphic-properties draw:stroke="none" draw:fill="none" style:wrap="run-through" style:run-through="foreground"/></style:style>
 </office:automatic-styles>
 <office:body><office:text>
   {''.join(page_paragraphs)}
 </office:text></office:body>
</office:document-content>'''


def styles_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles
 xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
 xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"
 xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
 office:version="1.3">
 <office:styles/>
 <office:automatic-styles>
   <style:page-layout style:name="A4FullBleed">
     <style:page-layout-properties fo:page-width="210mm" fo:page-height="297mm" style:print-orientation="portrait"
       fo:margin-top="0mm" fo:margin-bottom="0mm" fo:margin-left="0mm" fo:margin-right="0mm"
       style:writing-mode="lr-tb"/>
   </style:page-layout>
 </office:automatic-styles>
 <office:master-styles><style:master-page style:name="CardPages" style:page-layout-name="A4FullBleed"/></office:master-styles>
</office:document-styles>'''


def meta_xml(page_count: int) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-meta
 xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
 xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 office:version="1.3">
 <office:meta>
   <dc:title>Teachers' Day Fold Cards — St. Mary's Academy</dc:title>
   <dc:description>Printable Teachers' Day invitation cards: two fold-and-give cards per A4 page, each with a personalised QR tribute link.</dc:description>
   <dc:creator>Pavit Singh</dc:creator>
   <meta:generator>Teachers' Day card builder</meta:generator>
   <meta:document-statistic meta:page-count="{page_count}"/>
 </office:meta>
</office:document-meta>'''


def manifest_xml(page_count: int) -> str:
    entries = "\n".join(
        f'  <manifest:file-entry manifest:full-path="Pictures/page_{n:02d}.svg" manifest:media-type="image/svg+xml"/>'
        for n in range(1, page_count + 1)
    )
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.3">
  <manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.text"/>
  <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
  <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
  <manifest:file-entry manifest:full-path="meta.xml" manifest:media-type="text/xml"/>
  <manifest:file-entry manifest:full-path="settings.xml" manifest:media-type="text/xml"/>
  <manifest:file-entry manifest:full-path="Pictures/" manifest:media-type=""/>
{entries}
</manifest:manifest>'''


def build(output: Path) -> tuple[int, list[tuple[str, str]]]:
    with (ROOT / "staff.csv").open("r", encoding="utf-8-sig", newline="") as source:
        teachers = list(csv.DictReader(source))
    if len(teachers) != 83:
        raise ValueError(f"Expected 83 staff rows in staff.csv, found {len(teachers)}.")

    urls = [f"{SITE_BASE}/teacher.html?t=p{int(t['number']):03d}" for t in teachers]
    urls.append(f"{SITE_BASE}/")  # the extra card fills the final, otherwise odd, two-up sheet
    qrs = qr_payloads(urls)

    cards = []
    manifest_rows: list[tuple[str, str]] = []
    for index, teacher in enumerate(teachers):
        url = f"{SITE_BASE}/teacher.html?t=p{int(teacher['number']):03d}"
        cards.append(teacher_card_svg(teacher, qrs[url], PALETTES[index % len(PALETTES)]))
        manifest_rows.append((pretty_name(teacher["name"]), url))
    cards.append(generic_card_svg(qrs[f"{SITE_BASE}/"], PALETTES[len(teachers) % len(PALETTES)]))
    manifest_rows.append(("Spare — St. Mary's Family", f"{SITE_BASE}/"))

    pages = [page_svg(cards[i], cards[i + 1], i // 2 + 1) for i in range(0, len(cards), 2)]
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as odt:
        # ODF requires this file to be first and uncompressed.
        odt.writestr("mimetype", "application/vnd.oasis.opendocument.text", compress_type=zipfile.ZIP_STORED)
        odt.writestr("content.xml", content_xml(len(pages)))
        odt.writestr("styles.xml", styles_xml())
        odt.writestr("meta.xml", meta_xml(len(pages)))
        odt.writestr("settings.xml", '<?xml version="1.0" encoding="UTF-8"?><office:document-settings xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" office:version="1.3"><office:settings/></office:document-settings>')
        for page_number, image in enumerate(pages, 1):
            odt.writestr(f"Pictures/page_{page_number:02d}.svg", image)
        odt.writestr("META-INF/manifest.xml", manifest_xml(len(pages)))

    # A plain-text manifest makes it easy to spot-check every encoded destination.
    manifest_path = output.with_name("Teachers_Day_Card_QR_Links.txt")
    manifest_lines = [
        "TEACHERS' DAY FOLD CARDS — QR DESTINATIONS",
        "=" * 47,
        "Each named card points to that person's personal tribute page.",
        "The final spare card points to the Teachers' Day home page.",
        "",
    ]
    manifest_lines.extend(f"{name}: {url}" for name, url in manifest_rows)
    manifest_path.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    return len(pages), manifest_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Create two-up printable Teachers' Day fold cards as an ODT.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="ODT path to write")
    args = parser.parse_args()
    pages, _ = build(args.output.resolve())
    print(f"Created {args.output.resolve()} ({pages} A4 pages; 83 personalised cards plus 1 spare card).")


if __name__ == "__main__":
    main()
