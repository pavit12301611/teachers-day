# teachers-day 💐

A polished, emotional, **fully data-driven** Teachers' Day tribute site — made by **Pavit Singh**.
No frameworks, no build step, no paid services: just HTML, CSS and a little
JavaScript. Host it anywhere.

## Pages

| Page | What's on it |
| --- | --- |
| `index.html` | Home — hero with photo collage, a **daily wish** (fresh every day of the week), thank-you marquee, animated stats, teacher preview (generated from data), treasure-hunt guide, **randomised quotes** (shuffle button) and a 🎉 **Celebrate** button |
| `teachers.html` | All teachers (generated from data), each with their own theme colour, message + secret-hunt progress |
| `teacher.html?t=sharma` (etc.) | **One dynamic template** for every teacher: themed profile, sealed letter that types itself out (with a time-of-day greeting), subject minigames, voice note, a **message library** (a new message every time you ask), **notes from the class**, and 4 hidden secrets |
| `teacher-sharma.html` … `teacher-singh.html` | Short redirects to `teacher.html?t=…` so old links keep working |
| `memories.html` | Photo gallery with an accessible lightbox — existing photos + clearly-marked, easy-to-replace placeholders |
| `message.html` | The special message from everyone + a 🎲 random thank-you-note shuffle (16 notes in data) |
| `wall.html` | Interactive Gratitude Wall of sticky notes (12 seeded notes + add/remove your own, saved in your browser) |

## The content engine — `js/data.js` 🧠

**Every word on the site lives in one file.** The whole site renders from it, so it's now dynamic:

- **Add a teacher** → add one object to `SITE_DATA.teachers` (copy an existing one, drop a photo in
  `assets/` and an audio note in `assets/audio/`). The home page, teachers page and
  `teacher.html?t=<id>` pick them up automatically. No new HTML file needed.
- **Add messages** → each teacher has:
  - `letter` — 4 paragraphs, typed out word-by-word
  - `psLines` — 4 rotating P.S. lines (a random one each time)
  - `moreMessages` — a **library of 8 fresh messages** cycled by the "Next Message" button
  - `classNotes` — 6 notes from Pavit (memories about each teacher)
  - `fun` + themed minigame lines (poems, theorems, elements, pep talks…)
- **Quotes, wish notes, wall notes, daily wishes** all live in `SITE_DATA` too.

No two visits are identical: the quotes reshuffle, the P.S. line rotates, the daily wish changes with
the day of the week, and the greeting matches the time of day.

## Personalisation

Every teacher gets their **own** colour theme, **own** sealed letter, **own** P.S., **own** minigame
buttons, **own** message library and **own** recorded voice note (`assets/audio/*.mp3`).
No two teachers see the same message.

## Hidden surprises (4 per teacher page 🕵️)

1. Tap the teacher's photo **5 times** → stickers + secret reveal
2. Find the **🎁 gift box** hiding in the footer
3. Select the **invisible ink** line in the footer
4. Enter the **Konami code** (↑ ↑ ↓ ↓ ← → ← → B A) → party mode + secret #4

Find all 4 on a page for the golden banner celebration. 🏆 Progress is saved per teacher in your
browser and shown on the teachers page.

## Adding real photos to the Memories page

Drop your image into `assets/memories/`, then replace the placeholder `src` on any card in
`memories.html` (see the in-file comment). The caption and lightbox update from the card's
`data-lightbox-*` attributes.

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
- With JavaScript disabled, pages degrade gracefully and teacher links redirect sensibly.
