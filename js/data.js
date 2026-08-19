/* ==========================================================================
   Teachers' Day — Content Engine
   --------------------------------------------------------------------------
   Every word on this site lives here. Add a new teacher, a new message or a
   new quote by editing this one file — every page updates automatically.

   How to add a teacher:
     1. Add an object to SITE_DATA.teachers (copy an existing one).
     2. Drop their photo into assets/ and an audio note into assets/audio/.
     3. Done — the home page, teachers page and teacher.html?t=<id> all
        pick them up automatically.
   ========================================================================== */
window.SITE_DATA = {

  /* ------------------------------------------------------------------ teachers */
  teachers: [

    /* ---------------- Mrs. Anjali Sharma · English ---------------- */
    {
      id: 'sharma',
      name: 'Mrs. Anjali Sharma',
      shortName: "Sharma Ma'am",
      subject: 'English · Class Teacher',
      tagline: "You made Shakespeare feel like gossip between friends, and every margin note a tiny letter back to us.",
      emoji: '📖',
      theme: { c1: '#b7196b', c2: '#d97706', soft: '#fdf1f7' },
      photo: 'assets/teacher1.jpg',
      audio: 'assets/audio/sharma.mp3',
      floats: ['📖', '✍️', '💐'],
      stickers: ['💐', '⭐', '📖', '❤️', '✨'],
      goldBanner: "🏆 You found all 4 secrets! Sharma Ma'am whispers: \"You were always my favourite chapter.\" 📖",
      giftJoke: "🎁 Inside the box: one (1) coupon for an error-free essay, hand-delivered by the class. Terms & conditions: we will try very, very hard.",
      ink: "psst… invisible ink says: Ma'am's favourite bookmark is the class register. 🤫",

      letter: [
        "Dear Sharma Ma'am, the board still says 'Welcome Students' in your handwriting, and honestly, that one line is the reason half of us walk in smiling on Monday mornings. You don't just teach English — you read it aloud like the whole classroom is holding its breath for a story.",
        "We know your red pen by heart. But those little notes in our margins — 'nice thought!', 'try again, you can do better' — were never corrections. They were tiny letters from you to us, and we kept every single one of them.",
        "Thank you for the poems that became adventures, for the grammar that became games, and for believing in our words before we did. This page, this letter, this whole corner of the internet — it is yours, Ma'am. Only yours.",
        "And on the days we were quiet, you asked if we were okay instead of asking for homework. That is not teaching. That is magic. And today, the magic gets celebrated — loudly, the way you always taught us to speak up. 💐"
      ],

      psLines: [
        "P.S. — Yes, we noticed you read the last line of our essays first. Your secret is safe with us. 😄",
        "P.S. — We still say 'the show must go on' before every speech. It's basically your watermark now. 🎭",
        "P.S. — The bookmark you lost last year? Found it. Keeping it. It's a treasure now. 📖",
        "P.S. — One day we'll write an essay long enough to make you smile for an entire period. We're training. ✍️"
      ],

      /* New messages — the library every teacher gets on their page. */
      moreMessages: [
        "Ma'am, you once said our words have power. So today our words are: thank you, thank you, thank you. We hope that was loud enough. 💛",
        "Every time we read a poem now, we hear it in your voice — the pauses, the drama, the little gasp at the good lines. You ruined poems for us in the best way possible. 📜",
        "Remember the day you read our answers aloud and said 'this is beautiful'? We still replay that moment before every exam. It never fails. ⭐",
        "You taught us that a story can change someone's day. So here is ours: a girl who was scared of English became a girl who loves stories. Thank you for being chapter one. 📚",
        "We promise to keep writing — essays, poems, letters, anything. And we promise the margins will always be as kind as yours. ✉️",
        "The classroom smelled like chalk and flowers that one morning, and you said it reminded you of your mother's garden. We never forgot. Happy Teachers' Day, Ma'am. 🌸",
        "You said there are no silly questions, only unasked ones. So here's ours: how does one teacher fit so much love in one heart? (Asking for the whole class.) ❤️",
        "If gratitude were a language, Ma'am, you'd be the reason we're fluent. Happy Teachers' Day from all of us — in every tense. 💐"
      ],

      classNotes: [
        { note: "The first time you returned our notebooks, the margins had more kindness than corrections. I kept mine.", by: "Pavit Singh" },
        { note: "You made us act out Shakespeare and I got to be Juliet. Best. Day. Ever.", by: "Pavit Singh" },
        { note: "'Try again, you can do better' — the most famous quote in our class group. We even made a sticker of it.", by: "Pavit Singh" },
        { note: "Ma'am, you remembered my birthday when I forgot mine. That's when I knew you were magic.", by: "Pavit Singh" },
        { note: "Your 'one more paragraph' during writing practice is why I finish every exam paper early. Thank you for the stretch.", by: "Pavit Singh" },
        { note: "She corrects our grammar in WhatsApp messages too. And honestly? We love her for it.", by: "Pavit Singh" }
      ],

      fun: [
        { label: '📜 A Poem, Just For You', kind: 'poem' },
        { label: '✨ Compliment Shuffle', kind: 'shuffle' },
        { label: '🖋️ One More Line', kind: 'wisdom' }
      ],
      poem: [
        "A — Always the first smile at the classroom door,",
        "N — Never a doubt left unanswered,",
        "J — Joy, quietly hidden in every single period,",
        "A — All our margins full of your little letters,",
        "L — Literature that came alive in your voice,",
        "I — Incredible, Ma'am. Simply incredible. 💐"
      ],
      shuffleLines: [
        "Your board handwriting is officially better than our entire notebooks. ✍️",
        "You make Shakespeare feel like gossip between friends. 🎭",
        "The maroon saree with the gold border? Iconic. Always. 💛",
        "One 'well done' from you = a whole week of motivation. ⭐",
        "You're the only person who can make a full stop sound dramatic. 📖",
        "Our favourite subject is English. That sentence is the biggest compliment we can give you. 😄"
      ],
      wisdom: [
        "A book is a dream you hold in your hands — and you handed us a whole library. 📚",
        "The best way to know a person? Read what they wrote in the margins. 🖋️",
        "Every great story has a brave beginning. Today's begins: 'Happy Teachers' Day'. 🎬",
        "Words are one of the few things that get better with age. Like you, Ma'am. ✨",
        "An ordinary teacher tells, a good teacher explains, a great teacher inspires. You read aloud. 👑",
        "When in doubt, write it down. When in doubt about your teacher? Never. 💌"
      ]
    },

    /* ---------------- Mr. Rajesh Verma · Mathematics ---------------- */
    {
      id: 'verma',
      name: 'Mr. Rajesh Verma',
      shortName: 'Verma Sir',
      subject: 'Mathematics',
      tagline: "You turned the scariest subject in school into the one we secretly look forward to.",
      emoji: '➗',
      theme: { c1: '#1d4ed8', c2: '#0ea5e9', soft: '#eef5ff' },
      photo: 'assets/teacher2.jpg',
      audio: 'assets/audio/verma.mp3',
      floats: ['➗', '📐', '🧮'],
      stickers: ['🧮', '📐', '🧮', '❤️', '✨'],
      goldBanner: "🏆 All 4 secrets found! Verma Sir calculates: probability of a better class = exactly 0. 📐",
      giftJoke: "🎁 Inside the box: one (1) protractor, pre-apologised for being used as a cake cutter in the canteen.",
      ink: "psst… invisible ink says: Sir secretly keeps our best test papers. He will never admit it. 🤫",

      letter: [
        "Dear Verma Sir, we still remember the day you carried that whole stack of puzzle books into the library and said maths is just a mystery that likes company. You turned the scariest subject in school into the one we secretly look forward to.",
        "Your glasses do that little flash right before you say 'observe carefully' — and we've started saying it to each other before every single test. That's not a habit, Sir. That's a legacy.",
        "Thank you for never letting us say 'I can't do maths' in your class. You made us show our steps in equations and in life: be patient, be honest, and always check your work.",
        "And thank you for the after-school doubts, and the 'let's try it one more time' that always meant 'I'm not giving up on you'. We solved it, Sir — the problem, the fear, all of it. This page is proved. Q.E.D., just for you. 🙌"
      ],

      psLines: [
        "P.S. — Fine. We admit it. We should have shown ALL the steps. Every single time. 😅",
        "P.S. — We still can't find x. But we did find out you're the best teacher, and that equation balances perfectly. ⚖️",
        "P.S. — The chalk you gently tossed at sleepy students? Perfect aim. We're still impressed. 🎯",
        "P.S. — Your probability lessons were right: the probability of us forgetting you = 0. 📊"
      ],

      moreMessages: [
        "Sir, 'x' never stood a chance once you walked into class. Thank you for making every problem feel solvable. 🧮",
        "You said maths is everywhere — and you were right. It's in the way we count our blessings every day, and you are number one. 1️⃣",
        "The day you explained a hard problem three times without rolling your eyes, we decided to become patient people too. Not teachers. Just patient. ✨",
        "Our class once calculated: 1 teacher + 1 board + 45 students = 0 fears. Maths confirmed, Sir. ✔️",
        "You made 'observe carefully' our exam mantra. We now notice things nobody else does — like how your tea is always the same perfect shade. ☕",
        "Thank you for the extra sheets, the patient 'no, start from here', and for never making us feel silly for asking. That's infinity in our hearts. ∞",
        "If kindness were a subject, Sir, you'd have scored beyond the syllabus. 📈",
        "We promise to check our work, show our steps, and carry your logic through life — at least where it counts. And it always counts. 😄"
      ],

      classNotes: [
        { note: "Sir once asked who found the problem hard and half the class raised their hands. He smiled and said: 'Perfect. Now I know where to begin.'", by: "Pavit Singh" },
        { note: "His 'one more time' is the most patient sentence in the history of sentences.", by: "Pavit Singh" },
        { note: "We solved 100 problems in one period as a challenge. Sir got emotional — he hid it behind the board, but we saw.", by: "Pavit Singh" },
        { note: "He hands out 'star of the day' stickers for good steps. I have 12. Yes, I count.", by: "Pavit Singh" },
        { note: "His Pi Day stories are 3.14 times longer than anyone else's. We wouldn't trade a digit of them.", by: "Pavit Singh" },
        { note: "Nobody in our class fears maths anymore. That's the biggest proof of all. Q.E.D.", by: "Pavit Singh" }
      ],

      fun: [
        { label: '🧮 Solve For Joy', kind: 'equation' },
        { label: '🥧 The Pi Button', kind: 'pi' },
        { label: '📐 The Theorem of Us', kind: 'theorem' }
      ],
      equation: [
        "Let x = your patience",
        "Let y = our silliest mistakes",
        "Given: y → ∞",
        "To prove: x > y, always",
        "Proof: you smiled again today. ∎",
        "Q.E.D. — Thank you, Sir! 🙌"
      ],
      piNote: "…still shorter than the list of steps you make us write. 😄",
      theorem: [
        "Theorem: A class taught with patience → a class that never stops trying. ∎",
        "Lemma: Every mistake corrected kindly = one fear removed. ∎",
        "Corollary: Doubt + your explanation → understanding, in at most 3 tries. ∎",
        "Conjecture, proven today: you are the best part of the timetable. ∎",
        "Identity: Our gratitude = your effort × our smiles. No division allowed. ∎",
        "Proof by induction: Base case — you believed in us. Step — we believed in ourselves. Forever. Q.E.D. ∎"
      ]
    },

    /* ---------------- Ms. Simran Kaur · Science ---------------- */
    {
      id: 'kaur',
      name: 'Ms. Simran Kaur',
      shortName: "Kaur Ma'am",
      subject: 'Science',
      tagline: "You celebrated every 'what happens if…?' and turned curiosity into our favourite habit.",
      emoji: '🔬',
      theme: { c1: '#0f766e', c2: '#ea580c', soft: '#ecfbf7' },
      photo: 'assets/teacher3.jpg',
      audio: 'assets/audio/kaur.mp3',
      floats: ['🔬', '⚗️', '🧬'],
      stickers: ['🧪', '⭐', '🔬', '❤️', '✨'],
      goldBanner: "🏆 All 4 secrets found! Kaur Ma'am's final result: curiosity — 100/100, passed with distinction! 🧪",
      giftJoke: "🎁 Inside the box: one (1) extra-safe beaker, certified mess-friendly by the entire class.",
      ink: "psst… invisible ink says: Ma'am's favourite element is the one we haven't discovered yet. 🤫",

      letter: [
        "Dear Kaur Ma'am, your lab is the only place in school where 'what happens if…?' is celebrated instead of scolded. You turned curiosity into our favourite habit and the periodic table into our treasure map.",
        "We still hear you say 'hypothesis first, then the fun' before every experiment. And yes, Ma'am, our hypothesis for today is this: you will smile while reading this page. (Conclusion: confirmed. ✅)",
        "Thank you for the fizz, the flames (the safe ones!), the diagrams we actually remember, and for showing us that science is not a subject — it's a way of looking at the world.",
        "You stayed back with us for the science fair, fixed our volcano five times, and still called it 'the best eruption we've ever made'. That's not science, Ma'am. That's love. And today we measure it: infinity units. ⚗️💛"
      ],

      psLines: [
        "P.S. — That \"small mess\" in the lab was 100% intentional science. We stand by it. 🧪",
        "P.S. — Our hypothesis: this page will make you smile. Conclusion: confirmed in advance. ✅",
        "P.S. — We will never, ever forget that the mitochondria is the powerhouse of the cell. Or you. 🧬",
        "P.S. — The beaker 'borrowed' for the class plant was returned. Eventually. We have receipts. 🌱"
      ],

      moreMessages: [
        "Ma'am, you made us believe that asking 'why' is a superpower. We've been asking ever since. Why do you teach so well? Answer pending. 🔬",
        "The periodic table has 118 elements, but only one Kaurium — and it lives in Lab 2. Happy Teachers' Day, Ma'am. 🧪",
        "Every time we see a rainbow, we think of your light experiments. Every time we see a rainbow, we think of you. That's a lot of rainbows. 🌈",
        "You taught us that failures are just data. So today our data says: 100% of our favourite teacher memories include you. 📊",
        "Thank you for the day you let us mix everything 'just to see'. The lab survived. Our curiosity didn't just survive — it thrived. ⚗️",
        "You said the universe is made of atoms, and atoms are mostly empty space. But somehow you filled ours completely. 🌌",
        "Our class project on 'reactions' was secretly a project on your kindness — the one reaction we wanted to study forever. 💞",
        "Hypothesis: teachers like you are rare. Experiment: one school, one Lab 2, one you. Result: confirmed — the rarest element of all. 🏅"
      ],

      classNotes: [
        { note: "Kaur Ma'am let me redo the experiment after our group's volcano flooded the table. I got it right the second time. She said that's how science works.", by: "Pavit Singh" },
        { note: "She knows every student's name in every class she teaches. We tested. It's true.", by: "Pavit Singh" },
        { note: "Her 'one more observation' before we write the conclusion changed how I see everything.", by: "Pavit Singh" },
        { note: "Ma'am brought her telescope to school for the night-sky session. We saw Saturn's ring — and her smile, which was bigger.", by: "Pavit Singh" },
        { note: "The class garden was her idea, her seeds, her weekends. The plants grow because of her. So do we.", by: "Pavit Singh" },
        { note: "Lab 2 is the loudest, happiest, most 'dangerous' (safe) place in school. We love it.", by: "Pavit Singh" }
      ],

      fun: [
        { label: '🧪 Your Element', kind: 'element' },
        { label: '⚗️ Mix A Reaction', kind: 'bubbles' },
        { label: '🧬 Class Processes', kind: 'process' }
      ],
      element: {
        num: '1',
        sym: 'Ku',
        name: 'Kaurium',
        mass: '∞',
        note: 'Discovered in Lab 2. Property: turns curiosity into confidence. Highly stable in our hearts. No known side effects except excessive smiling.'
      },
      reactions: [
        "curiosity + courage → a confident you! (and a little foam) 🫧",
        "doubt + your patience → clarity, every single time ✨",
        "one spark of 'why?' → a lifetime of questions worth asking 🔥",
        "boredom + your demo → wonder, with mild fizzing 🧪"
      ],
      processes: [
        "Photosynthesis: we absorb your lessons all day and release gratitude. 🌱",
        "Evaporation: our tears at the farewell slowly disappear as we grow — but the salt stays. 🧂",
        "Combustion: your energy during a practical demo → complete burning of our boredom. 🔥",
        "Respiration: breathe in courage, breathe out 'I can't do it'. You taught us that exchange. 🫁",
        "Osmosis: your kindness moves from high concentration (you) to low (us) until we're all equal. ⚖️",
        "Evolution: we entered your class as students and evolved into curious humans. Natural selection chose you. 🧬"
      ]
    },

    /* ---------------- Mr. Arjun Singh · Physical Education ---------------- */
    {
      id: 'singh',
      name: 'Mr. Arjun Singh',
      shortName: 'Singh Sir',
      subject: 'Physical Education',
      tagline: "You taught us that 'one more lap' was never about the track — it was about never giving up.",
      emoji: '🏆',
      theme: { c1: '#15803d', c2: '#f97316', soft: '#effaf1' },
      photo: 'assets/teacher4.jpg',
      audio: 'assets/audio/singh.mp3',
      floats: ['🏆', '🏃', '🥇'],
      stickers: ['🏅', '⭐', '🏆', '❤️', '✨'],
      goldBanner: "🏆 All 4 secrets found! Coach Singh blows the final whistle: full-time score — Class 1, Doubts 0! 📣",
      giftJoke: "🎁 Inside the box: one (1) golden whistle, for the coach who never needed one to lead.",
      ink: "psst… invisible ink says: Sir still remembers every student's personal best. Every. Single. One. 🤫",

      letter: [
        "Dear Singh Sir, your whistle is the most honest alarm clock in this school. One blast and we know: it's time to run, time to try, time to become a little stronger than yesterday.",
        "You taught us that 'one more lap' was never about the track. It was about the little voice in our head that says quit — and how to politely show it the exit. We hear your pep talks in every hard moment now.",
        "Thank you for the sunset drills, the water breaks that felt like victory parades, and for celebrating our smallest wins like world cups.",
        "You remember every student's personal best. Every. Single. One. Somewhere between the relay races and the rain-cancelled practices, you became the coach of our whole lives, not just our games. This page is your home ground, Sir. Home ground only. 🏅"
      ],

      psLines: [
        "P.S. — That one lap we complained about? It's the reason we never give up now. Please don't tell anyone we admitted it. 🤫",
        "P.S. — Your whistle belongs in a museum. We'd settle for hearing it one more time. 📣",
        "P.S. — We still blame you for our love of morning runs. It's a disease and we're not looking for a cure. 🏃",
        "P.S. — Team A vs Team B will never be that intense again. You refereed it like a world final. 🏀"
      ],

      moreMessages: [
        "Sir, you once said your only competition is yesterday's you. Yesterday's us couldn't do a single push-up. Today's us can't stop thanking you. 💪",
        "The day you ran the relay with us because we were one short? We still talk about it like a championship final. For us, it was. 🏆",
        "You made losing feel like learning and winning feel like gratitude. That's a coach. That's you. 🏅",
        "Rain didn't cancel our period — you moved practice indoors and turned the corridor into a stadium. Legend behaviour only. 🌧️",
        "Thank you for teaching us that rest is part of training, and asking for help is part of strength. Some lessons had nothing to do with sports. All of them had everything to do with you. 🎽",
        "Your 'five more minutes' became the longest, most loved five minutes of our week. ⏱️",
        "We measured the school ground once. It's exactly one Singh Sir wide in memories. 📏",
        "If life is a match, you're the captain who never sits out. Happy Teachers' Day, Coach. 📣"
      ],

      classNotes: [
        { note: "Sir knew I was nervous before inter-school tryouts and just said: 'Breathe. You've done this a hundred times.' I made the team.", by: "Pavit Singh" },
        { note: "He high-fives everyone at the gate on sports day mornings. Everyone. For an hour.", by: "Pavit Singh" },
        { note: "'One more lap' is now a class inside joke. We say it before every hard thing. And it works.", by: "Pavit Singh" },
        { note: "Coach made me captain when I wasn't the fastest. He said leaders aren't the fastest — they're the ones who turn back to check on the team.", by: "Pavit Singh" },
        { note: "He remembers our personal bests from two years ago. I don't remember what I ate yesterday.", by: "Pavit Singh" },
        { note: "Our sports-day trophy shelf? His legacy. Our legs? Also his legacy.", by: "Pavit Singh" }
      ],

      fun: [
        { label: '📣 Blow The Whistle', kind: 'whistle' },
        { label: '💪 Pep Talk', kind: 'pep' },
        { label: '🏟️ The Scoreboard', kind: 'score' }
      ],
      pepTalks: [
        "Champions are made in practice — but today, the champion is YOU, Coach. 🏆",
        "Rest if you must, but never quit. (You said that. We lived it.) 💪",
        "The whole class runs behind you, Sir. Always. 🏃",
        "Gold medal for the teacher who made us unbreakable. 🥇",
        "No pain, no gain? More like: no Sir, no champion. We'll take the laps. 🏁",
        "You don't blow the whistle for us, Sir. You blow it for the version of us that's still warming up. 🔥"
      ],
      scoreboard: [
        "Final score — Class: 10/10 courage · Doubts: 0/10. Referee: Singh Sir. 🏟️",
        "Half-time pep talk: 'You're doing better than you think.' — Coach Singh, every single time. 📣",
        "Points table: You 100 · Everyone else 99. (There is no debate.) 🏆",
        "Stamina: unlimited · Smiles: unlimited · Laps: 'one more, just one more'. 🏃",
        "Assists: 1 coach who believed in us first → goals: our whole future. ⚽",
        "Red card for anyone who says they can't. Yellow card for anyone who won't try. Gold card for our coach. 🟥🟨🥇"
      ]
    }
  ],

  /* --------------------------------------------------- quotes (home page) */
  quotes: [
    { text: "A teacher takes a hand, opens a mind, and touches a heart.", who: "Unknown" },
    { text: "The best teachers teach from the heart, not from the book.", who: "Unknown" },
    { text: "Teaching is the one profession that creates all other professions.", who: "Unknown" },
    { text: "The art of teaching is the art of assisting discovery.", who: "Mark Van Doren" },
    { text: "What the teacher is, is more important than what he teaches.", who: "Karl Menninger" },
    { text: "It is the supreme art of the teacher to awaken joy in creative expression and knowledge.", who: "Albert Einstein" },
    { text: "A teacher affects eternity; he can never tell where his influence stops.", who: "Henry Adams" },
    { text: "One book, one pen, one child, and one teacher can change the world.", who: "Malala Yousafzai" },
    { text: "Everyone who remembers his own education remembers teachers, not methods.", who: "Sidney Hook" },
    { text: "A good teacher is like a candle — it consumes itself to light the way for others.", who: "Mustafa Kemal Atatürk" },
    { text: "Teachers plant seeds of knowledge that grow forever.", who: "Our class" },
    { text: "In a world where you can be anything, be kind. Teachers chose kind first.", who: "From all of us" }
  ],

  /* ---------------------------------------- thank-you notes (message page) */
  wishNotes: [
    { note: "Thank you for believing in us before we ever believed in ourselves.", by: "Pavit Singh" },
    { note: "You didn't just teach a subject — you taught us how to keep trying.", by: "Pavit Singh" },
    { note: "One 'well done' from you is worth a whole week of motivation.", by: "Pavit Singh" },
    { note: "Thank you for the extra minutes after the bell. We noticed every one.", by: "Pavit Singh" },
    { note: "Because of you, the classroom felt like a second home.", by: "Pavit Singh" },
    { note: "Teachers plant seeds that grow forever. Thank you for ours.", by: "Pavit Singh" },
    { note: "Thank you for seeing the potential in us that we couldn't see ourselves.", by: "Pavit Singh" },
    { note: "Every mark you corrected, every doubt you cleared — thank you for all of it.", by: "Pavit Singh" },
    { note: "You made Monday mornings something we actually look forward to.", by: "Pavit Singh" },
    { note: "You saw the best in us even on our worst days. That's a superpower.", by: "Pavit Singh" },
    { note: "Every doubt you cleared still echoes in our heads as confidence.", by: "Pavit Singh" },
    { note: "Thank you for the laughter — half our school memories are your jokes.", by: "Pavit Singh" },
    { note: "You didn't give us answers; you gave us the courage to find them.", by: "Pavit Singh" },
    { note: "The day you said 'I'm proud of you' still plays on repeat. Thank you.", by: "Pavit Singh" },
    { note: "You taught us that mistakes are just first attempts at learning. Now we're fearless.", by: "Pavit Singh" },
    { note: "If thank-you notes were homework, we'd still be writing them for you.", by: "Pavit Singh" }
  ],

  /* -------------------------------------------------- sticky notes (wall) */
  wallNotes: [
    { note: "Sharma Ma'am, your margin notes were the real love letters. We kept every single one.", by: "Pavit Singh" },
    { note: "Verma Sir proved that patience is a superpower. Q.E.D.", by: "Pavit Singh" },
    { note: "Kaur Ma'am, Lab 2 was officially the best place in the whole school.", by: "Pavit Singh" },
    { note: "Singh Sir, 'one more lap' quietly changed my life. I'll never admit it out loud though.", by: "Pavit Singh" },
    { note: "Thank you for believing in us before we ever believed in ourselves.", by: "Pavit Singh" },
    { note: "Best. Teachers. Ever. There is no debate and there never will be.", by: "Pavit Singh" },
    { note: "The way you explain things twice without sighing should be studied by scientists.", by: "Pavit Singh" },
    { note: "Our class is basically a family now — and it's because of how you treat us.", by: "Pavit Singh" },
    { note: "Thank you for staying after the bell when you didn't have to. We noticed, always.", by: "Pavit Singh" },
    { note: "You celebrate our small wins like they're world records. We love you for it.", by: "Pavit Singh" },
    { note: "Your 'you can do this' is the strongest sentence in the English language.", by: "Pavit Singh" },
    { note: "Happy Teachers' Day to the people who shaped us — every single one of you. 💛", by: "Pavit Singh" }
  ],

  /* ---------------------------------------- daily wish (home page, per day) */
  dailyWishes: [
    "Dear teachers, may this week begin the way you make every class begin — with a smile. 💛",
    "Somewhere a teacher is explaining something for the third time with endless patience. We salute you. 🫡",
    "Halfway through the week and you're still the best part of our school days. 🌟",
    "Thank you for turning 'I can't' into 'I'll try' — one lesson at a time. 💪",
    "You made it to Friday, and so did we — thanks to you. 🎉",
    "Even on weekends, we carry your lessons with us. That's how powerful you are. 📚",
    "Rest well today, teachers. You've earned every minute of it. 💐"
  ]
};
