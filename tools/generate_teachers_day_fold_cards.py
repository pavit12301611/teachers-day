#!/usr/bin/env python3
"""Build a print-ready, double-sided ODT with two cards on each vertical A4 side.

Each card has a portrait-and-greeting front and a QR-focused back. There are exactly
83 named cards, so the final front/back sheet intentionally contains the final card
only rather than an unrelated duplicate or filler.

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
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "deliverables" / "Teachers_Day_Folded_Cards_83_Teachers.odt"
SITE_BASE = "https://teachers-day-rosy.vercel.app"

# A bright but print-friendly rotation.  Each pair is used for the cover and inside panel.
PALETTES = [
    {"ink": "#314D6D", "accent": "#C76050", "wash": "#F2F6FA", "line": "#D7E1EA"},
    {"ink": "#5A466D", "accent": "#B95F7B", "wash": "#F8F2F6", "line": "#E5D9E2"},
    {"ink": "#315E5D", "accent": "#B96B4F", "wash": "#F0F7F5", "line": "#D6E7E2"},
    {"ink": "#5A4C55", "accent": "#A95D53", "wash": "#F8F5F1", "line": "#E9DED4"},
]

# These are the real details supplied in teacher_context.md, edited only for clarity
# and length so they fit comfortably inside a printed card.  The remaining staff get
# a subject- or role-specific note from personal_note().
PERSONAL_NOTES = {
    1: "Your motivation for the whole school has always encouraged me.",
    2: "Your kindness and motivation have always felt warm and friendly.",
    7: "Thank you for guiding me as I learned more about computers and IT.",
    8: "Thank you for guiding us in fitness, march past, and every activity.",
    9: "Your anchoring and motivation have guided me in many parts of life.",
    16: "You made Social Science interesting, easy, and never boring for me.",
    18: "Thank you for teaching IT, moral values, and leading our class so well.",
    19: "Thank you for strengthening my Maths and Economics foundation.",
    22: "You made Science feel simple, clear, and easy to understand.",
    24: "You made Hindi and Sanskrit feel easy, simple, and fun to learn.",
    25: "Thank you for your language lessons and for teaching us moral values.",
    27: "Thank you for helping me learn Hindi with patience and care.",
    28: "You taught me to understand Science and use it in everyday life.",
    29: "You helped me see how simple and easy English grammar can be.",
    30: "Thank you for making Maths, tables, and calculations easy to remember.",
    31: "Thank you for your kind English lessons and encouragement.",
    32: "You made Social Science feel easy, simple, and interesting.",
    33: "Thank you for training us in exercise and healthy physical practices.",
    34: "Thank you for teaching us computers and computer languages.",
    35: "Thank you for teaching me computers and their many useful applications.",
    36: "Thank you for your patient guidance in Science and Maths.",
    37: "Thank you for teaching Hindi and Sanskrit with kindness and support.",
    39: "Thank you for English, moral values, and being my Class 5 teacher.",
    41: "Thank you for helping us study Science and General Knowledge.",
    42: "Your guidance has helped me in many parts of life and learning.",
    43: "Thank you for making dance lessons enjoyable and memorable.",
    44: "You helped us understand music and how beautiful it can be.",
    45: "Thank you for making Maths formulas easier to understand and use.",
    47: "Thank you for English, moral values, laughter, and memorable grammar lessons.",
    48: "Your Maths methods are lessons I still remember and use every day.",
    49: "Thank you for your kind guidance in drawing and art.",
    50: "Thank you for your supportive English and Social Science lessons.",
    51: "Thank you for being such a kind and cooperative Class 6 teacher.",
    52: "Thank you for being a wonderful teacher and making GK enjoyable.",
    54: "Thank you for teaching me Hindi and Sanskrit.",
    56: "Thank you for explaining Maths formulas and patiently clearing our doubts.",
    57: "Thank you for my Hindi and Sanskrit lessons in Class 7.",
    59: "Thank you for your encouraging PT guidance and support.",
}


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


def personal_note(record: dict[str, str]) -> str:
    """Use the student's real note where available, otherwise make a respectful unique note."""
    number = int(record["number"])
    if number in PERSONAL_NOTES:
        return PERSONAL_NOTES[number]

    subject = " ".join(record["subject_or_role"].strip().split())
    designation = record["designation"].strip()
    name = pretty_name(record["name"])
    if designation.lower() == "supporting staff":
        options = [
            f"{name}, thank you for the care and hard work you bring to our school every day.",
            f"{name}, your work helps make our school a better place every single day.",
            f"{name}, thank you for all the support and care you give our school community.",
        ]
    elif subject and subject != ".":
        subject = subject.lower()
        options = [
            f"Thank you for making {subject} easier to understand and for always encouraging us.",
            f"Your guidance in {subject} makes learning clearer, kinder, and more enjoyable.",
            f"Thank you for the patience, support, and dedication you bring to {subject}.",
        ]
    else:
        options = [
            "Thank you for your guidance, dedication, and the care you bring to St. Mary's.",
            "Your support and hard work make a lasting difference to every student.",
            "Thank you for the patience, encouragement, and kindness you share each day.",
        ]
    return options[number % len(options)]


def folded_outer_card_svg(record: dict[str, str], qr_svg: str, palette: dict[str, str]) -> str:
    """Outside of a folded card: QR-focused back on the left, portrait cover on the right."""
    name = pretty_name(record["name"])
    designation = record["designation"].strip()
    teacher_id = f"p{int(record['number']):03d}"
    name_lines = lines_for(name, 18, 2)
    name_size = "5.6" if len(name) <= 17 else "4.8"
    # 72 × 70 mm is deliberately sized to be the visual centre of the cover: large
    # enough to honour each portrait, while leaving clear breathing room for the name.
    name_y = 107.5 if len(name_lines) == 1 else 105.0
    role_y = 116.3 if len(name_lines) == 1 else 116.6

    return f'''<g>
      <rect x="0.8" y="0.8" width="192.4" height="131.4" rx="3.4" fill="#FFFFFF" stroke="{palette['ink']}" stroke-width="1.05"/>
      <rect x="1.8" y="1.8" width="94.3" height="129.4" rx="2.6" fill="{palette['wash']}"/>
      <rect x="1.5" y="1.5" width="191" height="5.5" rx="2.5" fill="{palette['accent']}"/>

      <!-- Outside back: deliberately short, impactful text and a large QR -->
      <text x="48.5" y="17" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="3.05" font-weight="700" letter-spacing=".65" fill="{palette['accent']}">A PERSONAL TEACHERS' DAY PAGE</text>
      <text x="48.5" y="26.5" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="3.95" font-weight="700" fill="{palette['ink']}">YOUR GUIDANCE STAYS</text>
      <text x="48.5" y="31.5" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="3.95" font-weight="700" fill="{palette['ink']}">WITH ME BEYOND THE CLASSROOM.</text>
      <g transform="translate(20 36)">
        <rect x="0" y="0" width="57" height="57" rx="3.2" fill="#FFFFFF" stroke="{palette['ink']}" stroke-width=".85"/>
        {qr_fragment(qr_svg, 2, 2, 53)}
      </g>
      <text x="48.5" y="102" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="3.25" font-weight="700" letter-spacing=".45" fill="{palette['accent']}">SCAN TO OPEN YOUR PAGE</text>
      <text x="48.5" y="107" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="2.2" fill="{palette['ink']}">teachers-day-rosy.vercel.app</text>
      <text x="48.5" y="110.8" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="2.2" fill="{palette['ink']}">/teacher.html?t={teacher_id}</text>
      <path d="M 10 117 H 87" stroke="{palette['line']}" stroke-width=".65"/>
      <text x="48.5" y="123.3" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="2.65" fill="{palette['ink']}">With gratitude, Pavit Singh • IX-B</text>
      <text x="48.5" y="128.1" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="2.25" letter-spacing=".25" fill="{palette['accent']}">ST. MARY'S ACADEMY</text>

      <!-- Outside cover -->
      <text x="145" y="16" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="3.05" font-weight="700" letter-spacing="1.2" fill="{palette['accent']}">HAPPY</text>
      <text x="145" y="23.2" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="5.65" font-weight="800" fill="{palette['ink']}">TEACHERS' DAY</text>
      <path d="M 112 26.5 H 178" stroke="{palette['accent']}" stroke-width=".85"/>
      <rect x="109.2" y="29.2" width="73.6" height="71.6" rx="4.2" fill="#FFFFFF" stroke="{palette['ink']}" stroke-width=".8"/>
      <!-- The portrait is an actual ODT image frame, positioned above this card layer. -->
      {svg_text_lines(name_lines, 145, name_y, 4.6, **{"text-anchor": "middle", "font-family": "DejaVu Sans, sans-serif", "font-size": name_size, "font-weight": "700", "fill": palette['ink']})}
      <text x="145" y="{role_y}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="3.15" fill="{palette['accent']}">{esc(designation)}</text>
      <path d="M 111 121 H 179" stroke="{palette['line']}" stroke-width=".6"/>
      <text x="145" y="126.2" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="2.5" letter-spacing=".35" fill="{palette['ink']}">5 SEPTEMBER</text>
      <text x="145" y="130" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="2.25" letter-spacing=".2" fill="{palette['accent']}">ST. MARY'S ACADEMY</text>

      <path d="M 97 7 V 126" stroke="{palette['ink']}" stroke-width=".55" stroke-dasharray="2 1.8" opacity=".8"/>
      <rect x="90.3" y="127.1" width="13.4" height="3.3" rx="1.5" fill="#FFFFFF"/>
      <text x="97" y="129.45" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="1.7" font-weight="700" letter-spacing=".25" fill="{palette['ink']}">FOLD</text>
    </g>'''


def folded_inside_card_svg(record: dict[str, str], palette: dict[str, str]) -> str:
    """Inside of a folded card: a true personal note plus a restrained thank-you panel."""
    name = pretty_name(record["name"])
    inside_name_lines = lines_for("DEAR " + name.upper() + ",", 19, 2)
    inside_name_size = "4.9" if len(inside_name_lines) == 1 else "4.35"
    inside_name_y = 27 if len(inside_name_lines) == 1 else 24.3
    inside_name_line_height = 4.45
    inside_divider_y = 31.4 if len(inside_name_lines) == 1 else 33.2
    note_lines = lines_for(personal_note(record), 37, 4)
    return f'''<g>
      <rect x="0.8" y="0.8" width="192.4" height="131.4" rx="3.4" fill="#FFFFFF" stroke="{palette['ink']}" stroke-width="1.05"/>
      <rect x="1.8" y="1.8" width="94.3" height="129.4" rx="2.6" fill="{palette['wash']}"/>
      <rect x="1.5" y="1.5" width="191" height="5.5" rx="2.5" fill="{palette['accent']}"/>
      <path d="M 97 7 V 126" stroke="{palette['ink']}" stroke-width=".55" stroke-dasharray="2 1.8" opacity=".8"/>

      <!-- Inside left: the genuinely personal note -->
      <text x="10" y="17" font-family="DejaVu Sans, sans-serif" font-size="2.85" font-weight="700" letter-spacing=".7" fill="{palette['accent']}">A NOTE JUST FOR YOU</text>
      {svg_text_lines(inside_name_lines, 10, inside_name_y, inside_name_line_height, **{"font-family": "DejaVu Sans, sans-serif", "font-size": inside_name_size, "font-weight": "700", "fill": palette['ink']})}
      <path d="M 10 {inside_divider_y} H 87" stroke="{palette['accent']}" stroke-width=".8"/>
      {svg_text_lines(note_lines, 10, 42, 5.05, **{"font-family": "DejaVu Sans, sans-serif", "font-size": "3.78", "fill": palette['ink']})}
      <text x="10" y="72" font-family="DejaVu Sans, sans-serif" font-size="3.5" fill="{palette['ink']}">Thank you for the difference you make,</text>
      <text x="10" y="77.2" font-family="DejaVu Sans, sans-serif" font-size="3.5" fill="{palette['ink']}">in class and far beyond it.</text>
      <path d="M 10 113 H 87" stroke="{palette['line']}" stroke-width=".65"/>
      <text x="10" y="120" font-family="DejaVu Sans, sans-serif" font-size="3.4" font-weight="700" fill="{palette['accent']}">With respect and gratitude,</text>
      <text x="10" y="126" font-family="DejaVu Sans, sans-serif" font-size="3.45" font-weight="700" fill="{palette['ink']}">Pavit Singh • Class IX-B</text>

      <!-- Inside right: uncluttered closing panel -->
      <text x="145" y="36" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="3.2" font-weight="700" letter-spacing="1" fill="{palette['accent']}">THANK YOU</text>
      <path d="M 116 42 H 174" stroke="{palette['line']}" stroke-width=".75"/>
      <text x="145" y="57" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="4.2" font-weight="700" fill="{palette['ink']}">THE BEST TEACHERS</text>
      <text x="145" y="63" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="4.2" font-weight="700" fill="{palette['ink']}">HELP US BELIEVE</text>
      <text x="145" y="69" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="4.2" font-weight="700" fill="{palette['ink']}">IN OURSELVES.</text>
      <path d="M 116 78 H 174" stroke="{palette['accent']}" stroke-width=".9"/>
      <text x="145" y="94" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="3.4" fill="{palette['ink']}">Happy Teachers' Day</text>
      <text x="145" y="100" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="3.4" fill="{palette['ink']}">with warm appreciation.</text>
      <text x="145" y="119" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="2.6" letter-spacing=".45" fill="{palette['accent']}">ST. MARY'S ACADEMY</text>
      <text x="145" y="124" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="2.5" letter-spacing=".25" fill="{palette['ink']}">5 SEPTEMBER</text>
    </g>'''


def page_svg(top_card: str, bottom_card: str | None, sheet_number: int, side: str) -> str:
    """Place the outside or inside of two folded cards on a vertical A4 sheet."""
    lower = f'<g transform="translate(8 155)">{bottom_card}</g>' if bottom_card else ""
    cut_guide = '''<g opacity=".9">
    <path d="M 8 148.5 H 202" stroke="#8491A0" stroke-width=".45" stroke-dasharray="2.1 1.4"/>
    <circle cx="12" cy="148.5" r="1.35" fill="#FFFFFF" stroke="#8491A0" stroke-width=".45"/>
    <path d="M 11.35 147.85 L 12.65 149.15 M 12.65 147.85 L 11.35 149.15" stroke="#8491A0" stroke-width=".45"/>
    <rect x="72" y="145.35" width="66" height="6.25" rx="3.1" fill="#FFFFFF"/>
    <text x="105" y="149.4" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="2.5" font-weight="700" letter-spacing=".22" fill="#667482">CUT HERE AFTER TWO-SIDED PRINTING</text>
    <circle cx="198" cy="148.5" r="1.35" fill="#FFFFFF" stroke="#8491A0" stroke-width=".45"/>
    <path d="M 197.35 147.85 L 198.65 149.15 M 198.65 147.85 L 197.35 149.15" stroke="#8491A0" stroke-width=".45"/>
  </g>''' if bottom_card else ""
    suffix = "2 cards" if bottom_card else "final card"
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="210mm" height="297mm" viewBox="0 0 210 297">
  <rect width="210" height="297" fill="#FFFFFF"/>
  <g transform="translate(8 9)">{top_card}</g>
  {lower}
  {cut_guide}
  <text x="8" y="294" font-family="DejaVu Sans, sans-serif" font-size="1.8" fill="#92A0AB">Teachers' Day Folded Cards • Sheet {sheet_number} • {side} • Print at 100% on A4</text>
  <text x="202" y="294" text-anchor="end" font-family="DejaVu Sans, sans-serif" font-size="1.8" fill="#92A0AB">{suffix}</text>
</svg>'''


def portrait_asset_path(record: dict[str, str]) -> Path:
    """Use the pre-rendered hand-drawn portrait if available, otherwise the source photo."""
    filename = Path(record["image_file"]).name
    painted = ROOT / "assets" / "staff-cards" / filename
    return painted if painted.exists() else ROOT / record["image_file"]


def portrait_frames_for(teachers: list[dict[str, str]]) -> dict[int, list[str]]:
    """Create direct ODT image frames so Writer displays every portrait reliably."""
    frames: dict[int, list[str]] = {}
    for index, teacher in enumerate(teachers):
        page_number = (index // 2) * 2 + 1  # OUTSIDE pages are 1, 3, 5, ...
        y = 39 if index % 2 == 0 else 185
        image_name = Path(teacher["image_file"]).name
        frame = f'''<draw:frame draw:style-name="PortraitImage" draw:name="Portrait {int(teacher['number']):03d}"
                   text:anchor-type="page" draw:page-number="{page_number}" svg:x="118mm" svg:y="{y}mm"
                   svg:width="72mm" svg:height="70mm" draw:z-index="1">
                <draw:image xlink:href="Pictures/portraits/{image_name}" xlink:type="simple"
                            xlink:show="embed" xlink:actuate="onLoad"/>
              </draw:frame>'''
        frames.setdefault(page_number, []).append(frame)
    return frames


def content_xml(page_count: int, portrait_frames: dict[int, list[str]]) -> str:
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
              {''.join(portrait_frames.get(n, []))}
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
   <style:style style:name="PortraitImage" style:family="graphic"><style:graphic-properties draw:stroke="none" draw:fill="none" style:wrap="run-through" style:run-through="foreground"/></style:style>
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
   <dc:title>Teachers' Day Folded Cards — St. Mary's Academy</dc:title>
   <dc:description>Printable folded Teachers' Day cards: portrait covers, large QR back covers, and personal inside notes, two cards per vertical A4 sheet.</dc:description>
   <dc:creator>Pavit Singh</dc:creator>
   <meta:generator>Teachers' Day card builder</meta:generator>
   <meta:document-statistic meta:page-count="{page_count}"/>
 </office:meta>
</office:document-meta>'''


def manifest_xml(page_count: int, portrait_files: list[str]) -> str:
    entries = "\n".join(
        f'  <manifest:file-entry manifest:full-path="Pictures/page_{n:02d}.svg" manifest:media-type="image/svg+xml"/>'
        for n in range(1, page_count + 1)
    )
    portrait_entries = "\n".join(
        f'  <manifest:file-entry manifest:full-path="Pictures/portraits/{name}" manifest:media-type="image/jpeg"/>'
        for name in portrait_files
    )
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.3">
  <manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.text"/>
  <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
  <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
  <manifest:file-entry manifest:full-path="meta.xml" manifest:media-type="text/xml"/>
  <manifest:file-entry manifest:full-path="settings.xml" manifest:media-type="text/xml"/>
  <manifest:file-entry manifest:full-path="Pictures/" manifest:media-type=""/>
  <manifest:file-entry manifest:full-path="Pictures/portraits/" manifest:media-type=""/>
{entries}
{portrait_entries}
</manifest:manifest>'''


def build(output: Path) -> tuple[int, list[tuple[str, str]]]:
    with (ROOT / "staff.csv").open("r", encoding="utf-8-sig", newline="") as source:
        teachers = list(csv.DictReader(source))
    if len(teachers) != 83:
        raise ValueError(f"Expected 83 staff rows in staff.csv, found {len(teachers)}.")

    urls = [f"{SITE_BASE}/teacher.html?t=p{int(t['number']):03d}" for t in teachers]
    qrs = qr_payloads(urls)

    outside_cards: list[str] = []
    inside_cards: list[str] = []
    manifest_rows: list[tuple[str, str]] = []
    for index, teacher in enumerate(teachers):
        url = f"{SITE_BASE}/teacher.html?t=p{int(teacher['number']):03d}"
        palette = PALETTES[index % len(PALETTES)]
        outside_cards.append(folded_outer_card_svg(teacher, qrs[url], palette))
        inside_cards.append(folded_inside_card_svg(teacher, palette))
        manifest_rows.append((pretty_name(teacher["name"]), url))

    # Each physical sheet is represented by two consecutive ODT pages. Its outside
    # has the QR back (left) and portrait cover (right); its inside holds the note.
    pages: list[str] = []
    for i in range(0, len(teachers), 2):
        second_outside = outside_cards[i + 1] if i + 1 < len(outside_cards) else None
        second_inside = inside_cards[i + 1] if i + 1 < len(inside_cards) else None
        sheet_number = i // 2 + 1
        pages.append(page_svg(outside_cards[i], second_outside, sheet_number, "OUTSIDE"))
        pages.append(page_svg(inside_cards[i], second_inside, sheet_number, "INSIDE"))
    portrait_frames = portrait_frames_for(teachers)
    portrait_assets = [(Path(teacher["image_file"]).name, portrait_asset_path(teacher)) for teacher in teachers]
    if len({name for name, _ in portrait_assets}) != len(teachers):
        raise ValueError("Portrait filenames must be unique inside the ODT package.")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as odt:
        # ODF requires this file to be first and uncompressed.
        odt.writestr("mimetype", "application/vnd.oasis.opendocument.text", compress_type=zipfile.ZIP_STORED)
        odt.writestr("content.xml", content_xml(len(pages), portrait_frames))
        odt.writestr("styles.xml", styles_xml())
        odt.writestr("meta.xml", meta_xml(len(pages)))
        odt.writestr("settings.xml", '<?xml version="1.0" encoding="UTF-8"?><office:document-settings xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" office:version="1.3"><office:settings/></office:document-settings>')
        for page_number, image in enumerate(pages, 1):
            odt.writestr(f"Pictures/page_{page_number:02d}.svg", image)
        # These are normal ODT image assets and frames, not browser-only data URIs.
        # LibreOffice/Writer can therefore display the portraits directly in the file.
        for image_name, image_path in portrait_assets:
            odt.write(image_path, f"Pictures/portraits/{image_name}")
        odt.writestr("META-INF/manifest.xml", manifest_xml(len(pages), [name for name, _ in portrait_assets]))

    # A plain-text manifest makes it easy to spot-check every encoded destination.
    manifest_path = output.with_name("Teachers_Day_Card_QR_Links.txt")
    manifest_lines = [
        "TEACHERS' DAY FOLDED CARDS — QR DESTINATIONS",
        "=" * 47,
        "Every card points to that person's personal tribute page.",
        "",
    ]
    manifest_lines.extend(f"{name}: {url}" for name, url in manifest_rows)
    manifest_path.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    return len(pages), manifest_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Create two-up, double-sided folded Teachers' Day cards as an ODT.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="ODT path to write")
    args = parser.parse_args()
    pages, _ = build(args.output.resolve())
    print(f"Created {args.output.resolve()} ({pages} ordered A4 sides / 42 duplex sheets; exactly 83 personalised cards).")


if __name__ == "__main__":
    main()
