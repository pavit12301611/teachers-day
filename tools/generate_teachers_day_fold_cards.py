#!/usr/bin/env python3
"""Build a print-ready ODT with two fold-and-give cards on each vertical A4 page.

There are exactly 83 named cards, so the final page intentionally contains the final
card only rather than an unrelated duplicate or filler.

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
DEFAULT_OUTPUT = ROOT / "deliverables" / "Teachers_Day_Fold_Cards_83_Teachers.odt"
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


def photo_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return "data:image/jpeg;base64," + encoded


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


def teacher_card_svg(record: dict[str, str], qr_svg: str, palette: dict[str, str]) -> str:
    """A deliberately clean, personal two-panel folded card (194 × 133 mm)."""
    name = pretty_name(record["name"])
    designation = record["designation"].strip()
    teacher_id = f"p{int(record['number']):03d}"
    portrait = ROOT / "assets" / "staff-cards" / Path(record["image_file"]).name
    if not portrait.exists():
        portrait = ROOT / record["image_file"]
    portrait_uri = photo_data_uri(portrait)

    name_lines = lines_for(name, 18, 2)
    cover_name_size = "5.6" if len(name) <= 17 else "4.8"
    cover_name_y = 106 if len(name_lines) == 1 else 103.8
    cover_line_height = 4.6
    role_y = 114.5 if len(name_lines) == 1 else 115.5
    note_lines = lines_for(personal_note(record), 37, 4)
    note_y = 39.5
    note_line_height = 5.0

    return f'''<g>
      <defs>
        <clipPath id="portrait-{teacher_id}"><rect x="114" y="30" width="68" height="67" rx="3.5"/></clipPath>
      </defs>
      <rect x="0.8" y="0.8" width="192.4" height="131.4" rx="3.4" fill="#FFFFFF" stroke="{palette['ink']}" stroke-width="1.05"/>
      <rect x="1.8" y="1.8" width="94.3" height="129.4" rx="2.6" fill="{palette['wash']}"/>
      <path d="M 97 7 V 126" stroke="{palette['line']}" stroke-width=".65"/>
      <rect x="1.5" y="1.5" width="191" height="5.5" rx="2.5" fill="{palette['accent']}"/>

      <!-- Personal message panel -->
      <text x="10" y="16" font-family="DejaVu Sans, sans-serif" font-size="2.8" font-weight="700" letter-spacing=".8" fill="{palette['accent']}">A PERSONAL NOTE FOR</text>
      {svg_text_lines(["DEAR " + name.upper() + ","], 10, 25.3, 4.5, **{"font-family": "DejaVu Sans, sans-serif", "font-size": "4.75", "font-weight": "700", "fill": palette['ink']})}
      <path d="M 10 29.5 H 87" stroke="{palette['accent']}" stroke-width=".8"/>
      {svg_text_lines(note_lines, 10, note_y, note_line_height, **{"font-family": "DejaVu Sans, sans-serif", "font-size": "3.72", "fill": palette['ink']})}
      <text x="10" y="65.5" font-family="DejaVu Sans, sans-serif" font-size="3.05" fill="{palette['ink']}">I made this small page just to say thank you.</text>
      <text x="10" y="70.2" font-family="DejaVu Sans, sans-serif" font-size="3.05" fill="{palette['ink']}">Please scan the QR code to open it.</text>
      <g transform="translate(10 79)">
        <rect x="0" y="0" width="34" height="34" rx="2.5" fill="#FFFFFF" stroke="{palette['ink']}" stroke-width=".7"/>
        {qr_fragment(qr_svg, .5, .5, 33)}
      </g>
      <text x="51" y="88" font-family="DejaVu Sans, sans-serif" font-size="3.1" font-weight="700" fill="{palette['ink']}">SCAN FOR YOUR</text>
      <text x="51" y="93" font-family="DejaVu Sans, sans-serif" font-size="3.1" font-weight="700" fill="{palette['ink']}">PERSONAL PAGE</text>
      <text x="51" y="101" font-family="DejaVu Sans, sans-serif" font-size="2.35" fill="{palette['accent']}">teachers-day-rosy.vercel.app</text>
      <text x="51" y="104.8" font-family="DejaVu Sans, sans-serif" font-size="2.35" fill="{palette['accent']}">/teacher.html?t={teacher_id}</text>
      <path d="M 10 119 H 87" stroke="{palette['line']}" stroke-width=".6"/>
      <text x="10" y="124.7" font-family="DejaVu Sans, sans-serif" font-size="3.1" font-weight="700" fill="{palette['ink']}">With gratitude, Pavit Singh</text>
      <text x="10" y="129" font-family="DejaVu Sans, sans-serif" font-size="2.45" letter-spacing=".25" fill="{palette['accent']}">CLASS IX-B • ST. MARY'S ACADEMY</text>

      <!-- Clean cover panel -->
      <text x="145" y="16" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="3" font-weight="700" letter-spacing="1" fill="{palette['accent']}">HAPPY</text>
      <text x="145" y="23.3" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="5.6" font-weight="800" fill="{palette['ink']}">TEACHERS' DAY</text>
      <path d="M 112 26.5 H 178" stroke="{palette['accent']}" stroke-width=".85"/>
      <rect x="113.2" y="29.2" width="69.6" height="68.6" rx="4.2" fill="#FFFFFF" stroke="{palette['ink']}" stroke-width=".8"/>
      <image x="114" y="30" width="68" height="67" preserveAspectRatio="xMidYMid slice" clip-path="url(#portrait-{teacher_id})" xlink:href="{portrait_uri}"/>
      {svg_text_lines(name_lines, 145, cover_name_y, cover_line_height, **{"text-anchor": "middle", "font-family": "DejaVu Sans, sans-serif", "font-size": cover_name_size, "font-weight": "700", "fill": palette['ink']})}
      <text x="145" y="{role_y}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="3.15" fill="{palette['accent']}">{esc(designation)}</text>
      <path d="M 113 119 H 177" stroke="{palette['line']}" stroke-width=".6"/>
      <text x="145" y="125" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="2.5" letter-spacing=".35" fill="{palette['ink']}">5 SEPTEMBER</text>
      <text x="145" y="129" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="2.25" letter-spacing=".2" fill="{palette['accent']}">ST. MARY'S ACADEMY</text>

      <!-- Simple, practical fold guide -->
      <path d="M 97 7 V 126" stroke="{palette['ink']}" stroke-width=".55" stroke-dasharray="2 1.8" opacity=".8"/>
      <rect x="90.3" y="127.1" width="13.4" height="3.3" rx="1.5" fill="#FFFFFF"/>
      <text x="97" y="129.45" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="1.7" font-weight="700" letter-spacing=".25" fill="{palette['ink']}">FOLD</text>
    </g>'''


def page_svg(top_card: str, bottom_card: str | None, page_number: int) -> str:
    """Place two 194×133 mm cards on an A4 portrait sheet, with a clear cut guide."""
    lower = f'<g transform="translate(8 155)">{bottom_card}</g>' if bottom_card else ""
    page_card_count = "2 cards per page" if bottom_card else "Final card • 83 of 83"
    cut_guide = '''<g opacity=".9">
    <path d="M 8 148.5 H 202" stroke="#8491A0" stroke-width=".45" stroke-dasharray="2.1 1.4"/>
    <circle cx="12" cy="148.5" r="1.35" fill="#FFFFFF" stroke="#8491A0" stroke-width=".45"/>
    <path d="M 11.35 147.85 L 12.65 149.15 M 12.65 147.85 L 11.35 149.15" stroke="#8491A0" stroke-width=".45"/>
    <rect x="72" y="145.35" width="66" height="6.25" rx="3.1" fill="#FFFFFF"/>
    <text x="105" y="149.4" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="2.5" font-weight="700" letter-spacing=".22" fill="#667482">CUT HERE • THEN FOLD EACH CARD ON THE DOTTED CENTRE LINE</text>
    <circle cx="198" cy="148.5" r="1.35" fill="#FFFFFF" stroke="#8491A0" stroke-width=".45"/>
    <path d="M 197.35 147.85 L 198.65 149.15 M 198.65 147.85 L 197.35 149.15" stroke="#8491A0" stroke-width=".45"/>
  </g>''' if bottom_card else ""
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="210mm" height="297mm" viewBox="0 0 210 297">
  <rect width="210" height="297" fill="#FFFFFF"/>
  <g transform="translate(8 9)">{top_card}</g>
  {lower}
  <!-- Printed trim guide appears only on the two-card sheets. -->
  {cut_guide}
  <text x="8" y="294" font-family="DejaVu Sans, sans-serif" font-size="1.8" fill="#92A0AB">Teachers' Day Fold Cards • Page {page_number} • Print at 100% on A4 paper</text>
  <text x="202" y="294" text-anchor="end" font-family="DejaVu Sans, sans-serif" font-size="1.8" fill="#92A0AB">{page_card_count}</text>
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
    qrs = qr_payloads(urls)

    cards = []
    manifest_rows: list[tuple[str, str]] = []
    for index, teacher in enumerate(teachers):
        url = f"{SITE_BASE}/teacher.html?t=p{int(teacher['number']):03d}"
        cards.append(teacher_card_svg(teacher, qrs[url], PALETTES[index % len(PALETTES)]))
        manifest_rows.append((pretty_name(teacher["name"]), url))
    # There are exactly 83 named cards. The final page contains the last card only,
    # rather than adding an unrelated filler card.
    pages = [
        page_svg(cards[i], cards[i + 1] if i + 1 < len(cards) else None, i // 2 + 1)
        for i in range(0, len(cards), 2)
    ]
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
        "Every card points to that person's personal tribute page.",
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
    print(f"Created {args.output.resolve()} ({pages} A4 pages; exactly 83 personalised cards).")


if __name__ == "__main__":
    main()
