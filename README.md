# teachers-day 💐

A polished, emotional, fully static Teachers' Day tribute site — made by **Pavit Singh and the
Whole Cabinet Members**. No frameworks, no build step, no paid services: just HTML, CSS and a
little JavaScript. Host it anywhere.

## Pages

| Page | What's on it |
| --- | --- |
| `index.html` | Home — split hero with a photo collage, thank-you marquee, animated stats, teacher preview, treasure-hunt guide, quotes and a 🎉 **Celebrate** button |
| `teachers.html` | The four teachers, each with their own theme colour, appreciation message + secret-hunt progress |
| `teacher-sharma.html` | Mrs. Anjali Sharma (English): sealed letter, ANJALI acrostic poem, compliment shuffle, voice note |
| `teacher-verma.html` | Mr. Rajesh Verma (Maths): sealed letter, "Solve For Joy" proof, the Pi button, voice note |
| `teacher-kaur.html` | Ms. Simran Kaur (Science): sealed letter, Kaurium element tile, reaction mixer, voice note |
| `teacher-singh.html` | Mr. Arjun Singh (PE): sealed letter, whistle button (real sound!), pep talks, voice note |
| `memories.html` | Photo gallery with an accessible lightbox — existing photos + clearly-marked, easy-to-replace placeholders |
| `message.html` | The special message from everyone + a 🎲 random thank-you-note shuffle |
| `wall.html` | Interactive Gratitude Wall of sticky notes (add/remove your own, saved in your browser) |

## Personalisation

Every teacher page has its **own** colour theme, its **own** sealed letter that types itself out,
its **own** P.S., its **own** fun buttons and its **own** recorded voice note (`assets/audio/*.mp3`).
No two teachers see the same message.

## Hidden surprises (4 per teacher page 🕵️)

1. Tap the teacher's photo **5 times** → stickers + secret reveal
2. Find the **🎁 gift box** hiding in the footer
3. Enter the **Konami code** (↑ ↑ ↓ ↓ ← → ← → B A) → party mode
4. Select the **invisible ink** line in the footer

Find all 4 on a page for the golden banner celebration. 🏆

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
