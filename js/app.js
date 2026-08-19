/* ==========================================================================
   Teachers' Day — application engine
   --------------------------------------------------------------------------
   The site is DATA-DRIVEN: every staff member lives in js/data.js (SITE_DATA,
   generated from staff.csv). This file renders the pages and builds each
   person's personalised content (letter, messages, minigames) from templates.
   Modules:
     1. helpers          — toast + reduced-motion detection
     2. content builder  — personalised letter/messages/minigames per person
     3. dynamic render   — grids (grouped), quotes, daily wish, collage, memories
     4. mobileNav        — hamburger menu
     5. revealOnScroll   — fade-in sections
     6. countUp          — animated stats
     7. lightbox         — gallery preview (native <dialog>)
     8. noteShuffle      — random thank-you note generator
     9. celebrate        — "Celebrate" button → confetti
    10. teacherPage      — sealed letter, minigames, message library, secrets
    11. konami           — hidden party-mode easter egg (secret #4)
    12. secretBadges     — progress on the teachers index
    13. gratitudeWall    — sticky-note wall (localStorage) with delete
   ========================================================================== */
(function () {
  'use strict';

  // Enable JS-only enhancements (e.g. scroll-reveal) now that scripts have run.
  document.documentElement.classList.add('js');

  var reducedMotion = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ------------------------------------------------------------------ 1. helpers */
  var toastWrap = null;
  function toast(msg, ms) {
    if (!toastWrap) {
      toastWrap = document.createElement('div');
      toastWrap.className = 'toast-wrap';
      toastWrap.setAttribute('role', 'status');
      toastWrap.setAttribute('aria-live', 'polite');
      document.body.appendChild(toastWrap);
    }
    var t = document.createElement('div');
    t.className = 'toast';
    t.textContent = msg;
    toastWrap.appendChild(t);
    setTimeout(function () {
      t.classList.add('out');
      setTimeout(function () { t.remove(); }, 450);
    }, ms || 2800);
  }
  window.showToast = toast;

  var DATA = window.SITE_DATA || {
    teachers: [], quotes: [], wishNotes: [], wallNotes: [], dailyWishes: []
  };

  function el(tag, cls, html) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html !== undefined) n.innerHTML = html;
    return n;
  }

  function imgSrc(t) {
    // Watercolor AI avatars are used everywhere for a consistent, premium look.
    return t.avatar;
  }

  /* ------------------------------------------------------------------ 2. content builder
     Every staff member gets a personalised page built from templates. */
  var POOL = {
    compliments: [
      'Your smile makes the whole corridor brighter. \u2600\uFE0F',
      'One "well done" from you = a whole week of motivation. \u2B50',
      'You make even the hardest topic feel doable. \uD83D\uDCAA',
      'Your patience deserves a national award. \uD83C\uDFC5',
      'You notice the students nobody else notices \u2014 that\u2019s real magic. \u2728',
      'You are proof that kindness is the best subject. \uD83D\uDC9B'
    ],
    wisdom: [
      'Education is the most powerful weapon, and you are the ones who hand it to us. \uD83D\uDDDD\uFE0F',
      'A teacher\u2019s influence never ends \u2014 it echoes forever. \uD83C\uDF0A',
      'The best teachers teach from the heart, not from the book. \u2764\uFE0F',
      'Every great student had a teacher who refused to give up on them. \uD83D\uDE4F',
      'Knowledge shared is knowledge multiplied. Thank you for multiplying ours. \u2716\uFE0F',
      'A school is only as great as its people \u2014 and ours is great because of you. \uD83C\uDFEB'
    ],
    reactions: [
      'curiosity + courage \u2192 a confident you! (and a little foam) \uD83E\uDEE7',
      'doubt + your patience \u2192 clarity, every single time \u2728',
      'one spark of "why?" \u2192 a lifetime of questions worth asking \uD83D\uDD25',
      'boredom + your demo \u2192 wonder, with mild fizzing \uD83E\uDDEA'
    ],
    processes: [
      'Photosynthesis: we absorb your lessons all day and release gratitude. \uD83C\uDF31',
      'Evaporation: our doubts slowly disappear as we grow \u2014 but the gratitude stays. \uD83D\uDCA7',
      'Combustion: your energy during a lesson \u2192 complete burning of our boredom. \uD83D\uDD25',
      'Respiration: breathe in courage, breathe out "I can\u2019t do it". You taught me that exchange. \uD83E\uDEC2',
      'Osmosis: your kindness moves from high concentration (you) to low (me) until we\u2019re all equal. \u2696\uFE0F',
      'Evolution: I entered your class as a student and evolved into a curious human. Natural selection chose you. \uD83E\uDDEC'
    ],
    pep: [
      'Champions are made in practice \u2014 but today, the champion is YOU. \uD83C\uDFC6',
      'Rest if you must, but never quit. (You said that. I lived it.) \uD83D\uDCAA',
      'Every student who ever trained with you runs behind you, always. \uD83C\uDFC3',
      'Gold medal for the staff member who made us unbreakable. \uD83E\uDD47',
      'No pain, no gain? More like: no you, no champion. \uD83C\uDFC1',
      'You don\u2019t blow the whistle for us \u2014 you blow it for the version of us that\u2019s still warming up. \uD83D\uDD25'
    ],
    score: [
      'Final score \u2014 Class: 10/10 courage \u00B7 Doubts: 0/10. \uD83C\uDFDF\uFE0F',
      'Half-time pep talk: "You\u2019re doing better than you think." \uD83D\uDCE3',
      'Points table: You 100 \u00B7 Everyone else 99. (There is no debate.) \uD83C\uDFC6',
      'Stamina: unlimited \u00B7 Smiles: unlimited \u00B7 Laps: "one more, just one more". \uD83C\uDFC3',
      'Assists: 1 teacher who believed first \u2192 goals: our whole future. \u26BD',
      'Red card for anyone who says they can\u2019t. Gold card for our teacher. \uD83D\uDFE5\uD83D\uDFE8\uD83E\uDD47'
    ],
    eq: [
      'Let x = your patience',
      'Let y = our silliest mistakes',
      'Given: y \u2192 \u221E',
      'To prove: x > y, always',
      'Proof: you smiled again today. \u221E',
      'Q.E.D. \u2014 Thank you! \uD83D\uDE4C'
    ],
    theorem: [
      'Theorem: a class taught with patience \u2192 a class that never stops trying. \u221E',
      'Lemma: every mistake corrected kindly = one fear removed. \u221E',
      'Corollary: doubt + your explanation \u2192 clarity, in at most 3 tries. \u221E',
      'Conjecture, proven today: you are the best part of the timetable. \u221E',
      'Identity: our gratitude = your effort \u00D7 our smiles. No division allowed. \u221E',
      'Proof by induction: base case \u2014 you believed in us. Step \u2014 we believed in ourselves. Forever. Q.E.D. \u221E'
    ],
    ps: [
      'P.S. \u2014 I promise to keep trying, keep learning, and keep saying thank you. \uD83D\uDE04',
      'P.S. \u2014 You are appreciated more than you will ever know. \uD83E\uDD2B',
      'P.S. \u2014 If this page made you smile even a little, my job here is done. \uD83D\uDE0A'
    ],
    extra: [
      '{first}, you make every day at school a little brighter. Thank you for being you. \u2728',
      'Some people become teachers; you became the reason a student loves school. Thank you. \uD83D\uDC9B',
      'I hope this Teachers\u2019 Day brings you even half the joy you have given us. You deserve it all. \uD83D\uDC90',
      'Every lesson you taught, every doubt you cleared, every extra minute you stayed \u2014 I noticed, and I am grateful. \uD83D\uDE4F',
      'If gratitude could be measured, our school would overflow with it \u2014 and a large part of that would be for you. \uD83C\uDFC6',
      'Thank you for making our school feel like a second home. You are a huge part of that feeling. \uD83C\uDFE0'
    ],
    notes: [
      'You probably don\u2019t remember every small kindness, but I remember all of mine. Thank you for every single one.',
      'The way you explain things twice without ever sighing is a superpower. I admire it.',
      'You saw potential in me before I saw it myself. That changed everything.'
    ],
    poem: [
      'T \u2014 To {first}, who makes learning a joy,',
      'E \u2014 Every lesson taught with love and care,',
      'A \u2014 Always the first to believe in us,',
      'C \u2014 Caring in ways that words can\u2019t share,',
      'H \u2014 Helping us grow, day after day,',
      'E \u2014 Every moment with you is a gift,',
      'R \u2014 Remember: you are appreciated, always. \uD83D\uDC90'
    ]
  };

  var ROLE = {
    'Principal': 'as the heart of our whole school, you are the reason every morning here begins with a smile. From the gate to the last classroom, your presence is felt everywhere',
    'Manager': 'as our respected Manager, you quietly make sure every single part of this school runs like a well-oiled machine',
    'P.G.T.': 'as one of our senior teachers, you have taught generations of students, and every one of us carries a little piece of your wisdom',
    'T.G.T.': 'as one of our middle-school teachers, you were there at exactly the age when we needed someone to believe in us',
    'P.R.T.': 'as one of our primary teachers, you were among the first people who made school feel safe and fun',
    'PRE-PRIMARY': 'as one of our pre-primary teachers, you taught the littlest ones \u2014 including the very first letters and numbers we ever learned',
    'Office Staff': 'as part of our office staff, you keep the whole school running behind the scenes \u2014 records, routines, everything',
    'Assistant Librarian': 'as our assistant librarian, you guard the shelves of stories that so many of us escaped into',
    'Supporting Staff': 'as part of our supporting staff, you do the quiet, tireless work that keeps our school clean, safe and cheerful'
  };

  var SUBJECT = {
    english: 'Thank you for the poems that became adventures and the stories that made us fall in love with words. You taught us that a well-written sentence can change a mood, and a well-read book can change a life.',
    maths: 'Thank you for making numbers feel less scary and more like puzzles waiting to be solved. You taught us to show our steps, check our work, and never give up until the answer appears.',
    science: 'Thank you for celebrating every "what happens if\u2026?" and turning curiosity into a habit. You showed us that the world is one big experiment and questions are the best equipment.',
    computer: 'Thank you for teaching us the language of machines. You showed us that with logic and a little patience, we can build almost anything.',
    social: 'Thank you for taking us around the world and back through time. You taught us that history is full of stories, and geography is full of reasons to be curious.',
    hindi: 'Thank you for teaching us our mother tongue with so much love. You made every poem and every story in Hindi feel like home.',
    sanskrit: 'Thank you for sharing the oldest language of our land. You taught us that some words carry thousands of years of wisdom.',
    music: 'Thank you for filling our school with music. You taught us that a song can say what words alone cannot.',
    pe: 'Thank you for the whistle, the laps, and the pep talks. You taught us that the body and the mind grow stronger together \u2014 and that quitting is never an option.',
    'default': 'Thank you for the lessons that went beyond the textbook. You taught us patience, kindness and the courage to keep trying \u2014 and that is something no exam can ever measure.'
  };

  var SUBJECT_LABEL = {
    english: 'English', maths: 'Mathematics', science: 'Science', computer: 'Computer',
    social: 'Social Studies', hindi: 'Hindi', sanskrit: 'Sanskrit', music: 'Music',
    pe: 'Physical Education'
  };

  function cleanSubjectRaw(t) {
    var s = (t.subjectRaw || '').replace(/[()]/g, '').trim();
    if (!s || s === '.') return '';
    if (s.length > 28) s = s.split(',')[0];
    return s;
  }

  function fill(tmpl, t) {
    return tmpl.replace(/\{first\}/g, t.shortName).replace(/\{name\}/g, t.name);
  }

  function surname(t) {
    var parts = t.name.replace(/^Sr\.\s*/, '').replace(/^Rev\.\s*Fr\.\s*/, '').split(' ');
    return parts.length > 1 ? parts[parts.length - 1] : t.shortName;
  }

  function buildContent(t) {
    var roleLine = ROLE[t.designation] || ROLE['P.G.T.'];
    var subjLine = SUBJECT[t.subject] || SUBJECT['default'];
    t.letter = [
      'Dear ' + t.name + ', ' + roleLine + '. Today is the day this whole school says thank you \u2014 loudly and from the heart.',
      subjLine,
      'This little page is my way of saying thank you, ' + t.shortName + '. From Pavit Singh \u2014 happy Teachers\u2019 Day, and may you always know how much you mean to this school. \uD83D\uDC90'
    ];
    t.psLines = POOL.ps.slice();
    t.moreMessages = POOL.extra.map(function (m) { return fill(m, t); });
    t.classNotes = POOL.notes.map(function (n) { return fill(n, t); });
    t.goldBanner = '\uD83C\uDFC6 All 4 secrets found! ' + t.name + ' is officially the most appreciated member of this school! \uD83C\uDF89';
    t.giftJoke = '\uD83C\uDF81 Inside the box: a tiny token of gratitude for ' + t.shortName + ' \u2014 valid for unlimited smiles. No returns, no refunds, only feelings.';
    t.ink = 'psst\u2026 invisible ink says: ' + t.shortName + ' is one of the reasons this school feels like home. \uD83E\uDD2B';

    var shuffleFn = [
      { label: '\u2728 Compliment Shuffle', kind: 'shuffle' },
      { label: '\uD83D\uDD8B\uFE0F One More Line', kind: 'wisdom' }
    ];
    t.shuffleLines = POOL.compliments.slice();
    t.wisdom = POOL.wisdom.slice();

    switch (t.subject) {
      case 'english':
        t.fun = [
          { label: '\uD83D\uDCDC A Poem For You', kind: 'poem' },
          { label: '\u2728 Compliment Shuffle', kind: 'shuffle' },
          { label: '\uD83D\uDD8B\uFE0F One More Line', kind: 'wisdom' }
        ];
        t.poem = POOL.poem.map(function (l) { return fill(l, t); });
        break;
      case 'maths':
        t.fun = [
          { label: '\uD83E\uDDEE Solve For Joy', kind: 'equation' },
          { label: '\uD83E\uDD57 The Pi Button', kind: 'pi' },
          { label: '\uD83D\uDCD0 The Theorem', kind: 'theorem' }
        ];
        t.equation = POOL.eq.slice();
        t.piNote = '\u2026and still not as infinite as our gratitude for you. \uD83D\uDE04';
        t.theorem = POOL.theorem.slice();
        break;
      case 'science':
        t.fun = [
          { label: '\uD83E\uDDEA Your Element', kind: 'element' },
          { label: '\u2697\uFE0F Mix A Reaction', kind: 'bubbles' },
          { label: '\uD83E\uDDEC Class Processes', kind: 'process' }
        ];
        t.element = {
          num: String(t.num),
          sym: (t.name.replace(/^Sr\.\s*/, '').split(/\s+/).map(function (w) { return w[0]; }).join('').slice(0, 2)).toUpperCase(),
          name: surname(t) + 'ium',
          mass: '\u221E',
          note: 'Discovered in this school. Property: turns doubt into confidence. Highly stable in our hearts. No known side effects except excessive smiling.'
        };
        t.reactions = POOL.reactions.slice();
        t.processes = POOL.processes.slice();
        break;
      case 'pe':
        t.fun = [
          { label: '\uD83D\uDCE3 Blow The Whistle', kind: 'whistle' },
          { label: '\uD83D\uDCAA Pep Talk', kind: 'pep' },
          { label: '\uD83C\uDFDF\uFE0F The Scoreboard', kind: 'score' }
        ];
        t.pepTalks = POOL.pep.slice();
        t.scoreboard = POOL.score.slice();
        break;
      case 'computer':
        t.fun = [
          { label: '\uD83D\uDDA5\uFE0F Debug Gratitude', kind: 'wisdom' },
          { label: '\u2728 Compliment Shuffle', kind: 'shuffle' }
        ];
        break;
      default:
        t.fun = shuffleFn;
    }
    return t;
  }

  /* ------------------------------------------------------------------ 3. dynamic render */
  var revealObserver = null;
  function initReveals() {
    var items = document.querySelectorAll('.reveal:not(.in)');
    if (reducedMotion) {
      items.forEach(function (n) { n.classList.add('in'); });
    } else if ('IntersectionObserver' in window) {
      if (!revealObserver) {
        revealObserver = new IntersectionObserver(function (entries) {
          entries.forEach(function (e) {
            if (e.isIntersecting) {
              e.target.classList.add('in');
              revealObserver.unobserve(e.target);
            }
          });
        }, { threshold: 0.12 });
      }
      items.forEach(function (n) { revealObserver.observe(n); });
    } else {
      items.forEach(function (n) { n.classList.add('in'); });
    }
  }

  function teacherHref(t) { return 'teacher.html?t=' + t.id; }

  function cardHtml(t, opts) {
    var subj = cleanSubjectRaw(t);
    var subjText = subj && SUBJECT_LABEL[t.subject] ? SUBJECT_LABEL[t.subject] : subj;
    var subjectLine = subjText ? t.designation + ' \u00B7 ' + subjText : t.designation;
    var note = subjText
      ? 'You make ' + subjText.toLowerCase() + ' something we look forward to.'
      : 'You make our school feel like home. Thank you.';
    return '' +
      '<div class="photo-wrap">' +
        '<img src="' + imgSrc(t) + '" data-avatar="' + t.avatar + '" alt="' + t.name + '" loading="lazy" />' +
        '<span class="theme-emoji">' + t.emoji + '</span>' +
      '</div>' +
      '<div class="info">' +
        '<h3>' + t.name + '</h3>' +
        '<p class="subject">' + subjectLine + '</p>' +
        '<p class="note">"' + note + '"</p>' +
        (opts.badges
          ? '<p class="tap">Tap to open their personal page \u2192</p>' +
            '<span class="secret-badge" data-badge="' + t.id + '">\uD83D\uDD75\uFE0F Secrets found: 0/4</span>'
          : '') +
      '</div>';
  }

  function renderTeacherGrid(container, opts) {
    if (!container) return;
    opts = opts || {};
    var list = DATA.teachers.slice();
    if (opts.limit) list = list.slice(0, opts.limit);
    list.forEach(function (t) {
      var card = el('a', 'teacher-card reveal' + (opts.mini ? ' mini' : ''), '');
      card.href = teacherHref(t);
      card.style.setProperty('--c1', t.theme.c1);
      card.style.setProperty('--c2', t.theme.c2);
      card.innerHTML = cardHtml(t, opts);
      container.appendChild(card);
    });
    initReveals();
  }

  /* Grouped staff index (teachers.html): headers per designation. */
  var GROUP_ORDER = [
    'Principal', 'Manager', 'P.G.T.', 'T.G.T.', 'P.R.T.', 'PRE-PRIMARY',
    'Office Staff', 'Assistant Librarian', 'Supporting Staff'
  ];
  function renderGroupedGrid(container) {
    if (!container) return;
    container.innerHTML = '';
    GROUP_ORDER.forEach(function (g) {
      var members = DATA.teachers.filter(function (t) { return t.designation === g; });
      if (!members.length) return;
      var count = members.length;
      container.appendChild(el('h3', 'staff-group-head', g + ' \u00B7 ' + count));
      var grid = el('div', 'teacher-grid');
      members.forEach(function (t) {
        var card = el('a', 'teacher-card reveal', '');
        card.href = teacherHref(t);
        card.style.setProperty('--c1', t.theme.c1);
        card.style.setProperty('--c2', t.theme.c2);
        card.innerHTML = cardHtml(t, { badges: true });
        grid.appendChild(card);
      });
      container.appendChild(grid);
    });
    initReveals();
  }

  /* Quote strip — three random quotes on every visit. */
  function renderQuotes() {
    var strip = document.getElementById('quotesStrip');
    if (!strip) return;
    strip.innerHTML = '';
    var pool = DATA.quotes.slice();
    for (var i = pool.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = pool[i]; pool[i] = pool[j]; pool[j] = tmp;
    }
    pool.slice(0, 3).forEach(function (q) {
      var card = el('div', 'quote-card reveal');
      card.innerHTML = '"' + q.text + '"<span class="who">\u2014 ' + q.who + '</span>';
      strip.appendChild(card);
    });
    initReveals();
  }

  var shuffleQuotesBtn = document.getElementById('shuffleQuotes');
  if (shuffleQuotesBtn) {
    shuffleQuotesBtn.addEventListener('click', function () {
      renderQuotes();
      var r = shuffleQuotesBtn.getBoundingClientRect();
      window.confettiBurst(r.left + r.width / 2, r.top, 22);
    });
  }

  /* Today's wish — one message per day of the week. */
  function renderTodayWish() {
    var box = document.getElementById('todayWish');
    if (!box) return;
    var wishes = DATA.dailyWishes.length ? DATA.dailyWishes : ['Happy Teachers\' Day! \uD83D\uDC90'];
    var day = (new Date().getDay() + 6) % 7; // Monday = 0 … Sunday = 6
    box.innerHTML =
      '<span class="tw-label">\uD83D\uDCAB Today\'s Wish For Our Teachers</span>' +
      '<p class="tw-text">' + wishes[day % wishes.length] + '</p>';
  }

  /* Hero collage — first four staff members. */
  function renderCollage() {
    var frame = document.getElementById('heroCollage');
    if (!frame) return;
    frame.innerHTML = '';
    DATA.teachers.slice(0, 4).forEach(function (t) {
      var d = el('div', 'collage-img');
      d.innerHTML = '<img src="' + imgSrc(t) + '" data-avatar="' + t.avatar + '" alt="" loading="lazy" />';
      frame.appendChild(d);
    });
  }

  /* Memories page — every staff member as a memory card. */
  function renderMemories() {
    var grid = document.getElementById('memoriesGrid');
    if (!grid) return;
    DATA.teachers.forEach(function (t, i) {
      var btn = el('button', 'memory-card reveal', '');
      btn.type = 'button';
      btn.setAttribute('data-lightbox', '');
      btn.setAttribute('data-lightbox-img', imgSrc(t, true));
      btn.setAttribute('data-lightbox-avatar', t.avatar);
      btn.setAttribute('data-lightbox-title', t.name);
      var subj = SUBJECT_LABEL[t.subject] || cleanSubjectRaw(t);
      btn.setAttribute('data-lightbox-sub', t.designation + (subj ? ' \u2014 ' + subj : ''));
      btn.innerHTML =
        '<span class="thumb"><img src="' + imgSrc(t) + '" data-avatar="' + t.avatar + '" alt="' + t.name + '" loading="lazy" /></span>' +
        '<span class="cap">' +
          '<span class="cap-title">' + t.name + '</span>' +
          '<span class="cap-sub">' + t.designation + (subj ? ' \u00B7 ' + subj : '') + '</span>' +
        '</span>';
      grid.appendChild(btn);
    });
    initReveals();
  }

  renderTeacherGrid(document.getElementById('homeTeacherGrid'), { mini: true, limit: 6 });
  renderGroupedGrid(document.getElementById('teacherGrid'));
  renderQuotes();
  renderTodayWish();
  renderCollage();
  renderMemories();

  /* Global image fallback chain: watercolor avatar jpg -> initial SVG -> hide. */
  document.addEventListener('error', function (e) {
    var target = e.target;
    if (!target || target.tagName !== 'IMG' || !target.dataset.avatar) return;
    var cur = target.src;
    var nxt = cur.replace('assets/avatars/', 'assets/staff-avatars/').replace(/\.jpg$/, '.svg');
    if (nxt === cur) { target.removeAttribute('data-avatar'); return; }
    target.dataset.avatar = nxt;
    target.src = nxt;
  }, true);

  /* ------------------------------------------------------------------ 4. mobile nav */
  var toggle = document.getElementById('navToggle');
  var navList = document.querySelector('.nav-links');
  if (toggle && navList) {
    function setNav(open) {
      navList.classList.toggle('open', open);
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    }
    toggle.addEventListener('click', function () {
      setNav(!navList.classList.contains('open'));
    });
    navList.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () { setNav(false); });
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') setNav(false);
    });
    document.addEventListener('click', function (e) {
      if (navList.classList.contains('open') &&
          !navList.contains(e.target) && !toggle.contains(e.target)) {
        setNav(false);
      }
    });
  }

  /* ------------------------------------------------------------------ 5. reveal on scroll */
  initReveals();

  /* ------------------------------------------------------------------ 6. count-up stats */
  var counters = document.querySelectorAll('[data-count]');
  if (reducedMotion) {
    counters.forEach(function (el) { el.textContent = el.dataset.count; });
  } else if ('IntersectionObserver' in window) {
    var cio = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        cio.unobserve(e.target);
        var target = parseInt(e.target.dataset.count, 10);
        var start = performance.now();
        var dur = 1200;
        function tick(now) {
          var p = Math.min(1, (now - start) / dur);
          e.target.textContent = Math.round(target * (1 - Math.pow(1 - p, 3)));
          if (p < 1) requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
      });
    }, { threshold: 0.5 });
    counters.forEach(function (el) { cio.observe(el); });
  }

  /* ------------------------------------------------------------------ 7. lightbox */
  var lightboxTriggers = document.querySelectorAll('[data-lightbox]');
  if (lightboxTriggers.length) {
    var dialog = document.createElement('dialog');
    dialog.className = 'lightbox';
    dialog.setAttribute('aria-label', 'Photo preview');
    dialog.innerHTML =
      '<div class="lightbox-box">' +
        '<button type="button" class="lightbox-close" aria-label="Close preview">&times;</button>' +
        '<img class="lightbox-img" alt="" />' +
        '<div class="lightbox-cap">' +
          '<div class="cap-title"></div>' +
          '<div class="cap-sub"></div>' +
        '</div>' +
      '</div>';
    document.body.appendChild(dialog);

    var img = dialog.querySelector('.lightbox-img');
    var capTitle = dialog.querySelector('.lightbox-cap .cap-title');
    var capSub = dialog.querySelector('.lightbox-cap .cap-sub');
    var closeBtn = dialog.querySelector('.lightbox-close');

    function openLightbox(trigger) {
      img.src = trigger.dataset.lightboxImg;
      img.dataset.avatar = trigger.dataset.lightboxAvatar || '';
      img.alt = trigger.dataset.lightboxTitle || '';
      capTitle.textContent = trigger.dataset.lightboxTitle || '';
      capSub.textContent = trigger.dataset.lightboxSub || '';
      if (typeof dialog.showModal === 'function') dialog.showModal();
      else dialog.setAttribute('open', '');
    }

    lightboxTriggers.forEach(function (t) {
      t.addEventListener('click', function () { openLightbox(t); });
    });

    function closeLightbox() {
      if (typeof dialog.close === 'function') dialog.close();
      else dialog.removeAttribute('open');
    }

    closeBtn.addEventListener('click', closeLightbox);
    dialog.addEventListener('click', function (e) {
      if (e.target === dialog) closeLightbox();
    });
  }

  /* ------------------------------------------------------------------ 8. random thank-you note */
  var shuffleBtn = document.querySelector('[data-note-shuffle]');
  var noteOutput = document.querySelector('[data-note-output]');
  if (shuffleBtn && noteOutput) {
    var notes = (window.WISH_NOTES || DATA.wishNotes || []).slice();
    var lastIndex = -1;
    function showNote() {
      if (!notes.length) { noteOutput.textContent = 'No notes yet \u2014 be the first to write one!'; return; }
      var i;
      do { i = Math.floor(Math.random() * notes.length); } while (i === lastIndex && notes.length > 1);
      lastIndex = i;
      var n = notes[i];
      noteOutput.innerHTML = '';
      var text = document.createElement('span');
      text.textContent = n.note;
      noteOutput.appendChild(text);
      var who = document.createElement('span');
      who.className = 'who';
      who.textContent = '\u2014 ' + n.by;
      noteOutput.appendChild(who);
    }
    shuffleBtn.addEventListener('click', function () {
      showNote();
      var r = shuffleBtn.getBoundingClientRect();
      window.confettiBurst(r.left + r.width / 2, r.top, 24);
    });
    showNote();
  }

  /* ------------------------------------------------------------------ 9. celebrate button */
  document.querySelectorAll('[data-celebrate]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      window.confettiRain(160);
      var msg = btn.dataset.celebrate || '\uD83C\uDF89 Happy Teachers\u2019 Day!';
      toast(msg, 3600);
    });
  });

  /* ------------------------------------------------------------------ 10. teacher page */
  var T = null;
  if (DATA.teachers.length) {
    var tid = (new URLSearchParams(window.location.search)).get('t');
    T = DATA.teachers.filter(function (t) { return t.id === tid; })[0] || null;
    if (tid && !T) { window.location.replace('teachers.html'); }
  }
  var teacherDiscover = null;
  if (T) initTeacherPage(T);

  function initTeacherPage(T) {
    buildContent(T);

    document.body.setAttribute('data-theme', T.id);
    // Per-person theme colours (data.js), applied inline.
    document.body.style.setProperty('--p1', T.theme.c1);
    document.body.style.setProperty('--p2', T.theme.c2);
    document.body.style.setProperty('--psoft', T.theme.soft);
    document.title = T.name + ' \uD83D\uDC90 | Teachers\' Day';

    var photo = document.getElementById('teacherPhoto');
    if (photo) { photo.src = imgSrc(T, true); photo.alt = T.name; }
    var name = document.getElementById('teacherName');
    if (name) name.textContent = T.name;
    var subject = document.getElementById('subjectTag');
    var subjLabel = SUBJECT_LABEL[T.subject] || cleanSubjectRaw(T);
    if (subject) subject.textContent = T.emoji + ' ' + T.designation + (subjLabel ? ' \u00B7 ' + subjLabel : '');
    var only = document.getElementById('onlyFor');
    if (only) only.textContent = 'This page, its letter and its messages were made only for ' + T.name + '. Nobody else\u2019s message lives here. \uD83D\uDC9D';
    var openBtn = document.getElementById('openLetter');
    if (openBtn) openBtn.textContent = '\uD83D\uDC8C Open Your Sealed Letter' + (T.title ? ', ' + T.title : '');

    var floats = document.querySelectorAll('.float-emoji');
    ['\uD83C\uDF93', '\uD83D\uDCDA', '\uD83D\uDC90'].forEach(function (f, i) { if (floats[i]) floats[i].textContent = f; });
    var stickers = document.querySelectorAll('.sticker');
    ['\u2B50', '\uD83C\uDFC6', '\uD83D\uDCD6', '\u2764\uFE0F', '\u2728'].forEach(function (s, i) { if (stickers[i]) stickers[i].textContent = s; });

    var gold = document.getElementById('goldBanner');
    if (gold) gold.textContent = T.goldBanner;

    var gift = document.querySelector('.giftbox');
    if (gift) gift.setAttribute('aria-label', T.shortName + '\u2019s mysterious little gift');
    var ink = document.querySelector('.hidden-ink');
    if (ink) ink.textContent = T.ink;

    var funWrap = document.getElementById('funButtons');
    if (funWrap) {
      T.fun.forEach(function (f) {
        var b = el('button', 'btn btn-ghost');
        b.type = 'button';
        b.setAttribute('data-fun', f.kind);
        b.textContent = f.label;
        funWrap.appendChild(b);
      });
    }

    /* ---- Message library ---- */
    var msgIdx = -1;
    var msgCard = document.getElementById('msgCard');
    var msgBtn = document.getElementById('nextMsg');
    function showMsg(forward) {
      if (!msgCard || !T.moreMessages.length) return;
      msgIdx = forward
        ? (msgIdx + 1) % T.moreMessages.length
        : Math.floor(Math.random() * T.moreMessages.length);
      msgCard.innerHTML =
        '<span class="msg-count">Message ' + (msgIdx + 1) + ' of ' + T.moreMessages.length + ' \u00B7 written only for ' + T.shortName + '</span>' +
        '<p class="msg-body">' + T.moreMessages[msgIdx] + '</p>' +
        '<span class="msg-by">\u2014 from Pavit Singh, with love \uD83D\uDC8C</span>';
      msgCard.classList.remove('pop'); void msgCard.offsetWidth;
      msgCard.classList.add('pop');
    }
    if (msgBtn) msgBtn.addEventListener('click', function () {
      showMsg(true);
      var r = msgBtn.getBoundingClientRect();
      window.confettiBurst(r.left + r.width / 2, r.top, 20);
    });
    showMsg(false);

    /* ---- A few notes from Pavit ---- */
    var notesWrap = document.getElementById('classNotes');
    if (notesWrap) {
      T.classNotes.forEach(function (n) {
        var d = el('div', 'class-note');
        d.innerHTML = '<p>' + n + '</p><span class="who">\u2014 Pavit Singh</span>';
        notesWrap.appendChild(d);
      });
      initReveals();
    }

    /* ---- Secrets progress (persisted per staff member) ---- */
    var secretFound = [];
    var storageKey = 'td-secrets-' + T.id;
    try { secretFound = JSON.parse(localStorage.getItem(storageKey)) || []; } catch (e) { secretFound = []; }

    function saveSecrets() {
      try { localStorage.setItem(storageKey, JSON.stringify(secretFound)); } catch (e) { /* private mode */ }
    }

    function updateChip(pop) {
      var chip = document.getElementById('secretChip');
      var count = document.getElementById('secretCount');
      if (!chip || !count) return;
      count.textContent = secretFound.length;
      if (pop) {
        chip.classList.remove('pop');
        void chip.offsetWidth;
        chip.classList.add('pop');
      }
    }

    function celebrateAll(quiet) {
      var banner = document.getElementById('goldBanner');
      if (banner) banner.classList.add('show');
      if (!quiet) {
        window.confettiRain(160);
        toast('\uD83C\uDFC6 ALL 4 SECRETS FOUND! You are officially ' + T.shortName + '\u2019s favourite detective!', 4200);
      }
    }

    function discover(id, label) {
      if (secretFound.indexOf(id) !== -1) { toast('\uD83D\uDE04 You already found that one!'); return; }
      secretFound.push(id);
      saveSecrets();
      updateChip(true);
      toast('\uD83D\uDD75\uFE0F Secret found (' + secretFound.length + '/4): ' + label, 3200);
      window.confettiBurst(window.innerWidth / 2, window.innerHeight / 3, 60);
      if (secretFound.length >= 4) setTimeout(function () { celebrateAll(false); }, 700);
    }
    teacherDiscover = discover;

    updateChip(false);
    if (secretFound.length >= 4) celebrateAll(true);

    /* ---- Secret 1: tap the photo five times ---- */
    var taps = 0;
    var frame = document.getElementById('photoFrame');
    if (frame) {
      frame.setAttribute('role', 'button');
      frame.setAttribute('tabindex', '0');
      frame.setAttribute('aria-label', T.shortName + '\u2019s photo. A little bird says it enjoys being tapped five times.');
      function tapPhoto() {
        taps++;
        frame.classList.remove('wiggle');
        void frame.offsetWidth;
        frame.classList.add('wiggle');
        if (taps === 2) toast('\uD83D\uDCF8 The photo likes the attention\u2026');
        if (taps === 4) toast('\uD83D\uDC40 One more tap, maybe?');
        if (taps >= 5) {
          document.querySelector('.photo-side').classList.add('stickered');
          discover('photo', 'The photo winked back!');
        }
      }
      frame.addEventListener('click', tapPhoto);
      frame.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); tapPhoto(); }
      });
    }

    /* ---- Secret 2: hidden gift box ---- */
    if (gift) {
      gift.addEventListener('click', function () {
        discover('gift', 'The hidden gift box!');
        var r = gift.getBoundingClientRect();
        window.confettiBurst(r.left + r.width / 2, r.top, 40);
        toast(T.giftJoke, 5000);
      });
    }

    /* ---- Secret 3: invisible ink ---- */
    if (ink) {
      var checkInk = function () {
        var sel = window.getSelection();
        if (sel && sel.toString().trim().length > 4 && ink.contains(sel.anchorNode)) {
          discover('ink', 'The invisible ink!');
        }
      };
      ink.addEventListener('mouseup', checkInk);
      ink.addEventListener('keyup', checkInk);
    }

    /* ---- Sealed letter ---- */
    var letter = document.getElementById('letter');
    var skipTyping = reducedMotion;
    if (letter) letter.addEventListener('click', function () { skipTyping = true; });

    function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

    function greeting() {
      var h = new Date().getHours();
      var time;
      if (h < 5) time = 'Working late';
      else if (h < 12) time = 'Good morning';
      else if (h < 17) time = 'Good afternoon';
      else time = 'Good evening';
      return time + ', ' + (T.title || T.shortName) + ' \u2014 and welcome to your page. This letter types itself out because even I couldn\u2019t write it fast enough. \u2728';
    }

    async function typeParagraphs(paras) {
      for (var pIndex = 0; pIndex < paras.length; pIndex++) {
        var text = paras[pIndex];
        var p = document.createElement('p');
        p.className = 'typing';
        letter.insertBefore(p, letter.querySelector('.ps'));
        for (var i = 0; i <= text.length; i++) {
          if (skipTyping) { p.textContent = text; break; }
          p.textContent = text.slice(0, i);
          if (i % 3 === 0) await sleep(18);
        }
        p.textContent = text;
        p.classList.remove('typing');
        await sleep(250);
      }
      var ps = letter.querySelector('.ps');
      if (ps) ps.classList.add('show');
      toast('\uD83D\uDC8C Letter fully opened. Every word, only for ' + T.shortName + '.', 3400);
    }

    if (openBtn && letter) {
      var psEl = letter.querySelector('.ps');
      if (psEl && T.psLines.length) {
        psEl.textContent = T.psLines[Math.floor(Math.random() * T.psLines.length)];
      }
      openBtn.addEventListener('click', function () {
        openBtn.classList.add('gone');
        letter.classList.add('open');
        window.confettiBurst(window.innerWidth / 2, 220, 40);
        setTimeout(function () {
          if (letter.scrollIntoView) {
            letter.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'center' });
          }
          typeParagraphs([greeting()].concat(T.letter));
        }, 750);
      });
    }

    /* ---- Voice note (only when an audio file exists) ---- */
    var voiceBtn = document.getElementById('voiceNote');
    if (voiceBtn) {
      if (T.audio) {
        var audio = new Audio(T.audio);
        voiceBtn.addEventListener('click', function () {
          if (audio.paused) {
            audio.play().then(function () {
              voiceBtn.textContent = '\u23F8\uFE0F Playing your voice note\u2026';
              toast('\uD83C\uDFA7 A voice note recorded just for ' + T.shortName + '. Turn the volume up!', 3400);
            }).catch(function () {
              toast('\uD83D\uDD07 Hmm, audio needs a moment \u2014 try again!');
            });
          } else {
            audio.pause();
            voiceBtn.textContent = '\uD83C\uDFA7 Play Your Voice Note';
          }
        });
        audio.addEventListener('ended', function () {
          voiceBtn.textContent = '\uD83C\uDFA7 Play Your Voice Note (again!)';
        });
      } else {
        voiceBtn.style.display = 'none';
      }
    }

    /* ---- Subject minigames ---- */
    var stage = document.getElementById('funStage');
    if (stage) stage.setAttribute('aria-live', 'polite');
    var shuffleIdx = -1;

    function render(html) {
      if (!stage) return;
      stage.classList.add('show');
      stage.innerHTML = html;
    }

    function nextLine(arr) {
      if (!arr || !arr.length) return '';
      shuffleIdx = (shuffleIdx + 1) % arr.length;
      return arr[shuffleIdx];
    }

    function playWhistle() {
      try {
        var Ctx = window.AudioContext || window.webkitAudioContext;
        var ctx = new Ctx();
        var t = ctx.currentTime;
        for (var i = 0; i < 2; i++) {
          var o = ctx.createOscillator();
          var g = ctx.createGain();
          var lfo = ctx.createOscillator();
          var lg = ctx.createGain();
          o.type = 'sine';
          o.frequency.value = 2350;
          lfo.type = 'square';
          lfo.frequency.value = 34;
          lg.gain.value = 0.25;
          lfo.connect(lg); lg.connect(g.gain);
          g.gain.setValueAtTime(0.0001, t + i * 0.55);
          g.gain.exponentialRampToValueAtTime(0.35, t + i * 0.55 + 0.03);
          g.gain.setValueAtTime(0.35, t + i * 0.55 + 0.4);
          g.gain.exponentialRampToValueAtTime(0.0001, t + i * 0.55 + 0.5);
          o.connect(g); g.connect(ctx.destination);
          o.start(t + i * 0.55); o.stop(t + i * 0.55 + 0.52);
          lfo.start(t + i * 0.55); lfo.stop(t + i * 0.55 + 0.52);
        }
      } catch (e) { /* audio unavailable */ }
    }

    var actions = {
      poem: function () {
        render(T.poem.map(function (l, i) {
          return '<div class="poem-line" style="animation-delay:' + (i * 0.35) + 's">' + l + '</div>';
        }).join(''));
      },
      shuffle: function () {
        render('<div class="pop-line">' + nextLine(T.shuffleLines) + '</div>');
      },
      wisdom: function () {
        render('<div class="pop-line">' + nextLine(T.wisdom) + '</div>');
      },
      equation: function () {
        render(T.equation.map(function (l, i) {
          return '<div class="eq-line" style="animation-delay:' + (i * 0.5) + 's">' + l + '</div>';
        }).join(''));
      },
      theorem: function () {
        render(T.theorem.map(function (l, i) {
          return '<div class="eq-line" style="animation-delay:' + (i * 0.5) + 's">' + l + '</div>';
        }).join(''));
      },
      pi: function () {
        render('<div class="eq-line">\u03C0 = <span id="piDigits"></span></div><div class="reaction-line"></div>');
        var digits = '3.14159265358979323846264338327950288419716939937510582';
        var elp = document.getElementById('piDigits');
        var i = 0;
        var iv = setInterval(function () {
          if (!elp || !stage.isConnected) { clearInterval(iv); return; }
          elp.textContent = digits.slice(0, ++i);
          if (i >= digits.length) {
            clearInterval(iv);
            var rl = stage.querySelector('.reaction-line');
            if (rl) rl.textContent = T.piNote;
          }
        }, 45);
      },
      element: function () {
        render(
          '<div class="element-tile">' +
            '<div class="num">' + T.element.num + '</div>' +
            '<div class="sym">' + T.element.sym + '</div>' +
            '<div class="name">' + T.element.name + '</div>' +
            '<div class="mass">' + T.element.mass + '</div>' +
          '</div><span class="element-note">' + T.element.note + '</span>'
        );
      },
      bubbles: function () {
        render('<div class="bubble-wrap" id="bubbleWrap"></div><div class="reaction-line"></div>');
        var wrap = document.getElementById('bubbleWrap');
        var bcolors = ['#0f766e', '#ea580c', '#f472b6', '#38bdf8', '#a3e635'];
        var n = 0;
        var iv = setInterval(function () {
          var b = document.createElement('div');
          b.className = 'bubble';
          var s = 12 + Math.random() * 26;
          b.style.width = s + 'px'; b.style.height = s + 'px';
          b.style.left = Math.random() * 90 + '%';
          b.style.background = bcolors[Math.floor(Math.random() * bcolors.length)];
          b.style.animationDuration = 1.4 + Math.random() * 1.4 + 's';
          if (wrap && wrap.isConnected) wrap.appendChild(b);
          setTimeout(function () { if (b.isConnected) b.remove(); }, 3000);
          if (++n > 26) clearInterval(iv);
        }, 90);
        setTimeout(function () {
          if (!stage.isConnected) return;
          var rl = stage.querySelector('.reaction-line');
          if (rl) rl.textContent = '\u2697\uFE0F ' + T.reactions[Math.floor(Math.random() * T.reactions.length)];
        }, 900);
      },
      process: function () {
        render('<div class="pop-line">\uD83E\uDDEC ' + nextLine(T.processes) + '</div>');
      },
      whistle: function () {
        playWhistle();
        render('<div class="pop-line">\uD83D\uDCE3 PEEP-PEEP! Everyone gather round \u2014 it\u2019s ' + T.shortName + '\u2019s day!</div>');
        window.confettiBurst(window.innerWidth / 2, window.innerHeight / 2, 70);
      },
      pep: function () {
        render('<div class="pop-line">\uD83D\uDCAA ' + nextLine(T.pepTalks) + '</div>');
      },
      score: function () {
        render('<div class="eq-line">\uD83C\uDFDF\uFE0F ' + nextLine(T.scoreboard) + '</div>');
      }
    };

    document.querySelectorAll('[data-fun]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var kind = btn.dataset.fun;
        if (actions[kind]) actions[kind]();
        if (kind !== 'whistle' && kind !== 'bubbles') {
          var r = btn.getBoundingClientRect();
          window.confettiBurst(r.left + r.width / 2, r.top, 18);
        }
      });
    });
  }

  /* ------------------------------------------------------------------ 11. konami code */
  var seq = ['arrowup', 'arrowup', 'arrowdown', 'arrowdown', 'arrowleft', 'arrowright', 'arrowleft', 'arrowright', 'b', 'a'];
  var ki = 0;
  document.addEventListener('keydown', function (e) {
    var k = (e.key || '').toLowerCase();
    ki = (k === seq[ki]) ? ki + 1 : (k === seq[0] ? 1 : 0);
    if (ki === seq.length) {
      ki = 0;
      document.body.classList.add('party');
      window.confettiRain(140);
      toast('\uD83C\uDF08 PARTY MODE UNLOCKED! (Old-school cheat codes still work here)', 4000);
      if (teacherDiscover) teacherDiscover('konami', 'The old-school cheat code!');
    }
  });

  /* ------------------------------------------------------------------ 12. secret badges (staff index) */
  document.querySelectorAll('[data-badge]').forEach(function (el) {
    var n = 0;
    try { n = (JSON.parse(localStorage.getItem('td-secrets-' + el.dataset.badge)) || []).length; } catch (e) { /* noop */ }
    el.textContent = '\uD83D\uDD75\uFE0F Secrets found: ' + Math.min(n, 4) + '/4';
  });

  /* ------------------------------------------------------------------ 13. gratitude wall */
  var wallGrid = document.getElementById('wallGrid');
  if (wallGrid) {
    var preset = window.WALL_NOTES || DATA.wallNotes || [];
    var extra = [];
    try { extra = JSON.parse(localStorage.getItem('td-wall')) || []; } catch (e) { /* noop */ }
    var noteColors = ['#fef08a', '#fbcfe8', '#bbf7d0', '#bfdbfe', '#fed7aa', '#e9d5ff'];

    function saveWall() {
      try { localStorage.setItem('td-wall', JSON.stringify(extra)); } catch (e) { /* private mode */ }
    }

    function addNote(item, i, removable) {
      var d = document.createElement('div');
      d.className = 'sticky-note reveal in';
      d.style.background = noteColors[i % noteColors.length];
      d.style.setProperty('--rot', ((i % 5) - 2) * 1.4 + 'deg');

      var text = document.createElement('span');
      text.textContent = item.note;
      d.appendChild(text);

      var s = document.createElement('span');
      s.className = 'by';
      s.textContent = '\u2014 ' + item.by;
      d.appendChild(s);

      if (removable) {
        var rm = document.createElement('button');
        rm.type = 'button';
        rm.className = 'remove';
        rm.setAttribute('aria-label', 'Remove this note');
        rm.textContent = '\u00D7';
        rm.addEventListener('click', function () {
          extra = extra.filter(function (n) { return n !== item; });
          saveWall();
          d.remove();
          toast('\uD83D\uDDD1\uFE0F Note removed.');
        });
        d.appendChild(rm);
      }

      wallGrid.appendChild(d);
    }

    preset.forEach(function (n, i) { addNote(n, i, false); });
    extra.forEach(function (n, i) { addNote(n, i + preset.length, true); });

    var form = document.getElementById('wallForm');
    if (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var nameInput = form.querySelector('#wallName');
        var noteInput = form.querySelector('#wallNote');
        var by = (nameInput.value || 'A secret admirer').trim();
        var note = (noteInput.value || '').trim();
        if (!note) { toast('\u270D\uFE0F Write a little note first!'); return; }
        var item = { note: note, by: by };
        extra.push(item);
        saveWall();
        addNote(item, preset.length + extra.length - 1, true);
        form.reset();
        window.confettiBurst(window.innerWidth / 2, window.innerHeight / 2, 40);
        toast('\uD83D\uDC9B Your note is on the wall! Thank you!');
      });
    }
  }
})();
