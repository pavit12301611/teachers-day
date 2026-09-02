# teachers-day 💐

A heartfelt, **fully data-driven** Teachers' Day tribute site — made by **Pavit Singh**
(Class **IX-B**, roll **9231**) for the teachers and staff of **St. Mary's Academy** (83 members).
No frameworks, no build step, no paid services: just HTML, CSS and a little JavaScript. Host it anywhere.

## Pages

| Page | What's on it |
| --- | --- |
| `index.html` | Home — hero collage of staff, a **daily wish** (fresh every day), thank-you marquee, animated stats (83 staff), staff preview, treasure-hunt guide, **randomised quotes** and a 🎉 **Celebrate** button |
| `teachers.html` | **All 83 staff members**, grouped by designation (Principal, Manager, P.G.T., T.G.T., P.R.T., Pre-Primary, Office, Librarian, Supporting) — each with their own theme colour, message and secret-hunt progress |
| `teacher.html?t=p001` (etc.) | **One dynamic template** for every staff member: themed profile, sealed letter that types itself out (with a time-of-day greeting), subject minigames, a **message library** (a new message every time you ask), notes from Pavit, and 4 hidden secrets |
| `memories.html` | "The Faces We'll Keep Forever" — an album of every staff member with an accessible lightbox |
| `message.html` | The special message from Pavit + a 🎲 random thank-you-note shuffle |
| `wall.html` | Interactive Gratitude Wall of sticky notes (add/remove your own, saved in your browser) |

## The content engine — `js/data.js` 🧠

`js/data.js` is **generated from `staff.csv`** (`python3 /tmp/gen_staff.py` regenerates it — see below).
Every staff member is one record: name, designation, qualification, subject, theme colours,
`photo` (path inside `images/`) and `avatar` (initial avatar in `assets/staff-avatars/`).

- **Adding photos**: drop the real photos into the `images/` folder using the exact filenames from
  the CSV (`images/001_sr-sheela-solanki.jpg`, …). The site **automatically** uses them — until then
  it gracefully falls back to the initial avatars. No code changes needed.
- **Adding/removing staff**: edit `staff.csv`, re-run the generator, done.
- Per-person content (sealed letter, P.S. lines, message library, minigames) is built from
  subject/designation templates in `js/app.js` — personalised with each person's name.

No two visits are identical: quotes reshuffle, the P.S. line rotates, the daily wish changes with
the day of the week, and the letter greeting matches the time of day.

## Personalisation

Every staff member gets their **own** colour theme, **own** sealed letter, **own** P.S., **own**
minigame buttons (subject-flavoured: poems for English, proofs for Maths, elements for Science,
whistle for PE…) and **own** message library.

## Hidden surprises (4 per staff page 🕵️)

1. Tap the photo **5 times** → stickers + secret reveal
2. Find the **🎁 gift box** hiding in the footer
3. Select the **invisible ink** line in the footer
4. Enter the **Konami code** (↑ ↑ ↓ ↓ ← → ← → B A) → party mode + secret #4

Find all 4 on a page for the golden banner celebration. 🏆 Progress is saved per person in your
browser and shown on the staff index.

## The colour theme 🎨

The palette is tuned to the hand-drawn watercolour portraits: rainbow washes in the page
background, gradient headings, a rainbow navbar strip and marquee, colour-cycled card tints and
shadows, a painted halo behind profile photos and a colourful footer. It all lives in
**section 25 of `css/style.css`** (`--wc-*` tokens), so the whole scheme can be retuned from
one block of variables.

## The printable cards — `St_Marys_Teacher_Cards_A4-fold.pdf` 🖨️

83 **foldable A4 cards**, one per staff member — a printed companion to the
site. Each card is a single **A4 landscape** sheet printed on **both sides**:

| Sheet side | Left half | Right half |
| --- | --- | --- |
| **Side 1 (outer)** | back of card (PS logo, *made by Pavit*) | front cover (photo, name, badges) |
| **Side 2 (inner)** | the handwritten-style message | big QR + the four secret hints |

**Print settings (important — taaki page ulte na aayein):**

1. Paper **A4**, orientation **Landscape**
2. **Double-sided / two-sided printing** → **Flip on LONG edge**
   (the common Windows default). The inside pages are drawn **pre-rotated
   180°** in the PDF on purpose — they look upside down if you view page 2
   on screen, but after the long-edge duplex tumble and folding they read
   perfectly upright.
3. **Scale: 100% / Actual size** (do *not* use "fit to page")
4. Fold along the dashed centre line marked **✂ FOLD**

After printing, fold the sheet in half with the **front cover (photo) on the
outside** and the message facing you inside — it stands like a greeting card.

> The generator (`make_cards.py`) pre-rotates even pages for long-edge
> duplexing. If your printer uses *flip on short edge* instead, remove the
> `c.translate(W, H); c.rotate(180)` block around the inside-page draw.

Every QR code opens that teacher's **own live page** on the deployed site,
e.g. `https://teachers-day-rosy.vercel.app/teacher.html?t=p001` (…`p002`,
… up to `p083`) — and the QR areas are clickable links in the PDF too.

Regenerate the PDF any time with:

```bash
pip install reportlab pillow qrcode pymupdf
python3 make_cards.py          # rebuilds the PDF from js/data.js + staff photos
```

## Regenerating data from staff.csv

```bash
# after editing staff.csv
python3 /tmp/gen_staff.py   # regenerates js/data.js + assets/staff-avatars/
```

## Run locally

Any static server works, e.g.

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

## Accessibility & performance notes

- Semantic landmarks, skip link, labelled form fields and visible focus states.
- `prefers-reduced-motion` is respected (animations & confetti calm down automatically).
- Confetti only appears when *you* click something — nothing auto-sprays on load.
- Fonts load from Google Fonts with graceful fallbacks; everything else is dependency-free.
- With JavaScript disabled, pages degrade gracefully.
