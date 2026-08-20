#!/usr/bin/env python3
"""
Teachers' Day — Context Collector (single-file, data baked in)
--------------------------------------------------------------
Walks through every teacher in SITE ORDER and asks about YOUR experience
with each one. Saves answers to teacher_context.md so the site can be
updated per teacher.

Run:  python collect_context.py

At each teacher's first prompt:
    ENTER  -> include this teacher (then answer the questions)
    s      -> skip this teacher
    q      -> quit & save what you've done so far
At any question:  ENTER = leave blank / skip that question.

Progress auto-saves after every teacher (.context_progress.json),
so you can stop and rerun to resume. Delete that file to start fresh.
"""

import os
import json
from datetime import datetime

OUTPUT_MD     = "teacher_context.md"
PROGRESS_FILE = ".context_progress.json"

# ---------------------------------------------------------------------------
# The questions asked for EACH teacher. Edit freely (key, prompt).
# ---------------------------------------------------------------------------
QUESTIONS = [
    ("who",         "Who were they to you? (who this teacher is in your eyes)"),
    ("taught_me",   "Did they ever teach you, even once? (yes / no / not sure)"),
    ("subjects",    "Which subject(s) did they teach you?"),
    ("how_to_me",   "How were they towards you? (how they treated / behaved with you)"),
    ("study_base",  "How did they help build your study base / foundation?"),
    ("extra",       "Anything else you want to add about them (optional)"),
]

# ---------------------------------------------------------------------------
# All 83 staff, in the exact order they appear on the site (from staff.csv).
# ---------------------------------------------------------------------------
TEACHERS = [
    {"number": "1",  "name": "Sr. Sheela Solanki",   "designation": "Principal",           "subject": "ENGLISH"},
    {"number": "2",  "name": "Rev. Fr. John Chiman", "designation": "Manager",             "subject": ""},
    {"number": "3",  "name": "Athar Umar",           "designation": "P.G.T.",              "subject": "Business,Accounts"},
    {"number": "4",  "name": "Prabha Sharma",        "designation": "P.G.T.",              "subject": "English"},
    {"number": "5",  "name": "Arvind Kumar",         "designation": "P.G.T.",              "subject": "Mathematics,U.G.C NET"},
    {"number": "6",  "name": "Vijay Sharma",         "designation": "P.G.T.",              "subject": "Mathematics"},
    {"number": "7",  "name": "Vivek Duneja",         "designation": "P.G.T.",              "subject": "Computer"},
    {"number": "8",  "name": "Tejaswi",              "designation": "P.G.T.",              "subject": "Physical Education"},
    {"number": "9",  "name": "Anuj Sharma",          "designation": "P.G.T.",              "subject": "English, Sociology, Education"},
    {"number": "10", "name": "Amit kumar",           "designation": "P.G.T.",              "subject": "Physics"},
    {"number": "11", "name": "Hemant Kumar Sharma",  "designation": "P.G.T.",              "subject": "Chemistry"},
    {"number": "12", "name": "Vivek Kapoor",         "designation": "P.G.T.",              "subject": "ECONOMICS"},
    {"number": "13", "name": "ARSHDEEP SINGH",       "designation": "P.G.T.",              "subject": ""},
    {"number": "14", "name": "VIVEK CHAUDHARY",      "designation": "P.G.T.",              "subject": "Biology"},
    {"number": "15", "name": "Edna R. Theophilus",   "designation": "T.G.T.",              "subject": "Social Studies"},
    {"number": "16", "name": "Anvesha Cornelius",    "designation": "T.G.T.",              "subject": "Social Studies"},
    {"number": "17", "name": "Kamini Choudhary",     "designation": "T.G.T.",              "subject": ""},
    {"number": "18", "name": "Amit Mittal",          "designation": "T.G.T.",              "subject": "Computer"},
    {"number": "19", "name": "Sudhir Aggarwal",      "designation": "T.G.T.",              "subject": "Mathematics,Economics"},
    {"number": "20", "name": "Sushil Kumar",         "designation": "T.G.T.",              "subject": "Mathematics"},
    {"number": "21", "name": "Ruby Jain",            "designation": "T.G.T.",              "subject": "Hindi"},
    {"number": "22", "name": "RUCHI SHARPE",         "designation": "T.G.T.",              "subject": "Science"},
    {"number": "23", "name": "RISHU WADHERA",        "designation": "T.G.T.",              "subject": ""},
    {"number": "24", "name": "KAMAL JAIN",           "designation": "T.G.T.",              "subject": ""},
    {"number": "25", "name": "Kanika Goyal",         "designation": "T.G.T.",              "subject": ""},
    {"number": "26", "name": "SR. MARYKUTTY",        "designation": "P.R.T.",              "subject": ""},
    {"number": "27", "name": "J. R. Bacon",          "designation": "P.R.T.",              "subject": ""},
    {"number": "28", "name": "HENRIETTA RAJ ANTONY", "designation": "P.R.T.",              "subject": ""},
    {"number": "29", "name": "Olga John",            "designation": "P.R.T.",              "subject": ""},
    {"number": "30", "name": "Tony Atmaram",         "designation": "P.R.T.",              "subject": ""},
    {"number": "31", "name": "Michelle Scott",       "designation": "P.R.T.",              "subject": ""},
    {"number": "32", "name": "Madhu Malini Agarwal", "designation": "P.R.T.",              "subject": ""},
    {"number": "33", "name": "Anupam Francis",       "designation": "P.R.T.",              "subject": ""},
    {"number": "34", "name": "Parul Gera",           "designation": "P.R.T.",              "subject": ""},
    {"number": "35", "name": "Mehjabin",             "designation": "P.R.T.",              "subject": ""},
    {"number": "36", "name": "Priyanka A Luke",      "designation": "P.R.T.",              "subject": ""},
    {"number": "37", "name": "Mayuri Tyagi",         "designation": "P.R.T.",              "subject": ""},
    {"number": "38", "name": "Madhu Christopher",    "designation": "P.R.T.",              "subject": ""},
    {"number": "39", "name": "Meetu Taneja",         "designation": "P.R.T.",              "subject": ""},
    {"number": "40", "name": "Konika Mehta",         "designation": "P.R.T.",              "subject": ""},
    {"number": "41", "name": "Garima Sakhuja",       "designation": "P.R.T.",              "subject": ""},
    {"number": "42", "name": "Dipanta Sharma",       "designation": "P.R.T.",              "subject": ""},
    {"number": "43", "name": "Shilpa Lal",           "designation": "P.R.T.",              "subject": ""},
    {"number": "44", "name": "Lalit Kumar Rai",      "designation": "P.R.T.",              "subject": ""},
    {"number": "45", "name": "Isha Miglani",         "designation": "P.R.T.",              "subject": ""},
    {"number": "46", "name": "NEERU TYAGI",          "designation": "P.R.T.",              "subject": ""},
    {"number": "47", "name": "Salma Naz",            "designation": "P.R.T.",              "subject": ""},
    {"number": "48", "name": "SUHANI ARORA",         "designation": "P.R.T.",              "subject": ""},
    {"number": "49", "name": "PRIYANKA RAWAT",       "designation": "P.R.T.",              "subject": ""},
    {"number": "50", "name": "PAVNEET KAUR",         "designation": "P.R.T.",              "subject": ""},
    {"number": "51", "name": "KIRTI RASWANT",        "designation": "P.R.T.",              "subject": ""},
    {"number": "52", "name": "URVASHI GOSWAMI",      "designation": "P.R.T.",              "subject": ""},
    {"number": "53", "name": "SHEETAL GROVER",       "designation": "P.R.T.",              "subject": ""},
    {"number": "54", "name": "POONAM CHHABRA",       "designation": "P.R.T.",              "subject": ""},
    {"number": "55", "name": "ANU JOHN",             "designation": "P.R.T.",              "subject": ""},
    {"number": "56", "name": "MEENU DHINGRA",        "designation": "P.R.T.",              "subject": ""},
    {"number": "57", "name": "ROOPMALA",             "designation": "P.R.T.",              "subject": "SANSKRIT"},
    {"number": "58", "name": "BHAWNA CHAUHAN",       "designation": "P.R.T.",              "subject": ""},
    {"number": "59", "name": "JATIN BHURIA",         "designation": "P.R.T.",              "subject": ""},
    {"number": "60", "name": "YASHIKA VERMA",        "designation": "P.R.T.",              "subject": ""},
    {"number": "61", "name": "DEEPALI SHARMA",       "designation": "PRE-PRIMARY",         "subject": ""},
    {"number": "62", "name": "NITHA CIBICHN",        "designation": "PRE-PRIMARY",         "subject": ""},
    {"number": "63", "name": "POOJA MAINI",          "designation": "PRE-PRIMARY",         "subject": ""},
    {"number": "64", "name": "VAISHALI BAVEJA",      "designation": "PRE-PRIMARY",         "subject": ""},
    {"number": "65", "name": "SHWETA TAKKAR",        "designation": "PRE-PRIMARY",         "subject": ""},
    {"number": "66", "name": "Nikunj K Jain",        "designation": "Office Staff",        "subject": "Superintendent, Sr. Acc."},
    {"number": "67", "name": "Rose Dias",            "designation": "Office Staff",        "subject": "Clerk"},
    {"number": "68", "name": "Shubham Bhardwaj",     "designation": "Office Staff",        "subject": "Clerk"},
    {"number": "69", "name": "SHIVANI LOUIS",        "designation": "Office Staff",        "subject": "Clerk"},
    {"number": "70", "name": "Catherin Moses",       "designation": "Assistant Librarian", "subject": "Library"},
    {"number": "71", "name": "Christopher Joseph",   "designation": "Supporting Staff",    "subject": ""},
    {"number": "72", "name": "Virender Kumar",       "designation": "Supporting Staff",    "subject": ""},
    {"number": "73", "name": "Shiv Charan",          "designation": "Supporting Staff",    "subject": ""},
    {"number": "74", "name": "Roxwell John",         "designation": "Supporting Staff",    "subject": ""},
    {"number": "75", "name": "Sonu",                 "designation": "Supporting Staff",    "subject": ""},
    {"number": "76", "name": "Sumit Jacob",          "designation": "Supporting Staff",    "subject": ""},
    {"number": "77", "name": "Rajiv Kumar",          "designation": "Supporting Staff",    "subject": ""},
    {"number": "78", "name": "AJIT SINGH",           "designation": "Supporting Staff",    "subject": ""},
    {"number": "79", "name": "Savina Daniel",        "designation": "Supporting Staff",    "subject": ""},
    {"number": "80", "name": "Beena Charles",        "designation": "Supporting Staff",    "subject": ""},
    {"number": "81", "name": "Naveen Kumar",         "designation": "Supporting Staff",    "subject": ""},
    {"number": "82", "name": "LILY SHERRING",        "designation": "Supporting Staff",    "subject": ""},
    {"number": "83", "name": "GABRIAL",              "designation": "Supporting Staff",    "subject": ""},
]


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_progress(data):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def ask(prompt):
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\n(Interrupted — saving.)")
        return "__QUIT__"


def write_markdown(answers):
    lines = []
    lines.append("# Teachers' Day — Context Notes\n")
    lines.append(f"_Generated: {datetime.now():%Y-%m-%d %H:%M}_\n")
    done = [t for t in TEACHERS if answers.get(t["number"], {}).get("_done")]
    lines.append(f"**Filled: {len(done)} / {len(TEACHERS)} teachers**\n")
    lines.append("\n---\n")

    for t in TEACHERS:
        a = answers.get(t["number"], {})
        if a.get("_skipped"):
            continue
        meta = " · ".join(x for x in [t["designation"], t["subject"]] if x)
        lines.append(f"## {t['number']}. {t['name']}")
        if meta:
            lines.append(f"_{meta}_")
        lines.append("")
        if not a.get("_done"):
            lines.append("> _Not filled yet._\n")
            lines.append("\n---\n")
            continue
        for key, prompt in QUESTIONS:
            val = (a.get(key) or "").strip()
            label = prompt.split("(")[0].strip().rstrip("?")
            if val:
                lines.append(f"- **{label}:** {val}")
        lines.append("\n---\n")

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    answers = load_progress()

    print("=" * 60)
    print("  TEACHERS' DAY — CONTEXT COLLECTOR")
    print("=" * 60)
    print(f"{len(TEACHERS)} teachers loaded (site order).")
    print("Per teacher:  ENTER=include | s=skip | q=quit & save")
    print("Per question: ENTER = leave blank")
    print("Progress auto-saves — rerun anytime to resume.\n")

    for idx, t in enumerate(TEACHERS, start=1):
        rec = answers.get(t["number"], {})
        if rec.get("_done") or rec.get("_skipped"):
            continue  # already handled earlier

        meta = " · ".join(x for x in [t["designation"], t["subject"]] if x)
        print("\n" + "-" * 60)
        print(f"[{idx}/{len(TEACHERS)}]  #{t['number']}  {t['name']}")
        if meta:
            print(f"          {meta}")
        print("-" * 60)

        first = ask("Include this teacher? (ENTER=yes / s=skip / q=quit): ").lower()
        if first in ("q", "__quit__"):
            break
        if first == "s":
            answers[t["number"]] = {"_skipped": True}
            save_progress(answers)
            continue

        rec, quit_now = {}, False
        for key, prompt in QUESTIONS:
            ans = ask(f"  • {prompt}: ")
            if ans == "__QUIT__":
                quit_now = True
                break
            rec[key] = ans
        rec["_done"] = True
        answers[t["number"]] = rec
        save_progress(answers)
        if quit_now:
            break

    write_markdown(answers)
    save_progress(answers)
    print("\n" + "=" * 60)
    print(f"Saved Markdown  -> {OUTPUT_MD}")
    print(f"Progress saved  -> {PROGRESS_FILE}  (delete to start fresh)")
    print("=" * 60)


if __name__ == "__main__":
    main()
