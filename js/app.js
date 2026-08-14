/* ============ Teacher's Day — app engine ============ */
(function () {
  'use strict';
  const T = window.TEACHER || null;

  /* ---------- Toasts ---------- */
  let toastWrap;
  function toast(msg, ms) {
    if (!toastWrap) {
      toastWrap = document.createElement('div');
      toastWrap.className = 'toast-wrap';
      document.body.appendChild(toastWrap);
    }
    const t = document.createElement('div');
    t.className = 'toast';
    t.textContent = msg;
    toastWrap.appendChild(t);
    setTimeout(() => {
      t.classList.add('out');
      setTimeout(() => t.remove(), 450);
    }, ms || 2800);
  }
  window.showToast = toast;

  /* ---------- Scroll reveal ---------- */
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (e.isIntersecting) {
        e.target.classList.add('in');
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.12 });
  document.querySelectorAll('.reveal').forEach((el) => io.observe(el));

  /* ---------- Count-up stats ---------- */
  const cio = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (!e.isIntersecting) return;
      cio.unobserve(e.target);
      const target = parseInt(e.target.dataset.count, 10);
      const start = performance.now();
      const dur = 1200;
      function tick(now) {
        const p = Math.min(1, (now - start) / dur);
        e.target.textContent = Math.round(target * (1 - Math.pow(1 - p, 3)));
        if (p < 1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    });
  }, { threshold: 0.5 });
  document.querySelectorAll('[data-count]').forEach((el) => cio.observe(el));

  /* ---------- Secrets system (teacher pages) ---------- */
  const secretFound = new Set();
  function secretKey() { return 'td-secrets-' + T.id; }
  function loadSecrets() {
    try {
      (JSON.parse(localStorage.getItem(secretKey())) || []).forEach((s) => secretFound.add(s));
    } catch (e) { /* fresh start */ }
  }
  function saveSecrets() {
    try { localStorage.setItem(secretKey(), JSON.stringify([...secretFound])); } catch (e) { /* private mode */ }
  }
  function updateChip(pop) {
    const chip = document.getElementById('secretChip');
    const count = document.getElementById('secretCount');
    if (!chip || !count) return;
    count.textContent = secretFound.size;
    if (pop) {
      chip.classList.remove('pop');
      void chip.offsetWidth;
      chip.classList.add('pop');
    }
  }
  function celebrateAll(quiet) {
    const banner = document.getElementById('goldBanner');
    if (banner) banner.classList.add('show');
    if (!quiet) {
      window.confettiRain(160);
      toast('🏆 ALL 4 SECRETS FOUND! You are officially ' + T.shortName + "'s favourite detective!", 4200);
    }
  }
  function discover(id, label) {
    if (!T) return;
    if (secretFound.has(id)) { toast('😄 You already found that one!'); return; }
    secretFound.add(id);
    saveSecrets();
    updateChip(true);
    toast('🕵️ Secret found (' + secretFound.size + '/4): ' + label, 3200);
    window.confettiBurst(window.innerWidth / 2, window.innerHeight / 3, 60);
    if (secretFound.size >= 4) setTimeout(() => celebrateAll(false), 700);
  }

  if (T) {
    loadSecrets();
    updateChip(false);
    if (secretFound.size >= 4) celebrateAll(true);

    /* Photo taps */
    let taps = 0;
    const frame = document.getElementById('photoFrame');
    if (frame) {
      frame.addEventListener('click', () => {
        taps++;
        frame.classList.remove('wiggle');
        void frame.offsetWidth;
        frame.classList.add('wiggle');
        if (taps === 2) toast('📸 The photo likes the attention…');
        if (taps === 4) toast('👀 One more tap, maybe?');
        if (taps >= 5) {
          document.querySelector('.photo-side').classList.add('stickered');
          frame.classList.add('stickered');
          discover('photo', 'The photo winked back!');
        }
      });
    }

    /* Hidden gift in footer */
    const gift = document.querySelector('.giftbox');
    if (gift) {
      gift.addEventListener('click', (ev) => {
        discover('gift', 'The hidden gift box!');
        const r = gift.getBoundingClientRect();
        window.confettiBurst(r.left + r.width / 2, r.top, 40);
        toast(T.giftJoke, 5000);
      });
    }

    /* Invisible ink (select the invisible text) */
    const ink = document.querySelector('.hidden-ink');
    if (ink) {
      const check = () => {
        const sel = window.getSelection();
        if (sel && sel.toString().trim().length > 4 && ink.contains(sel.anchorNode)) {
          discover('ink', 'The invisible ink!');
        }
      };
      ink.addEventListener('mouseup', check);
      ink.addEventListener('keyup', check);
    }

    /* Open the sealed letter */
    const openBtn = document.getElementById('openLetter');
    const letter = document.getElementById('letter');
    let skipTyping = false;
    if (letter) letter.addEventListener('click', () => { skipTyping = true; });

    function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

    async function typeParagraphs(paras) {
      for (const text of paras) {
        const p = document.createElement('p');
        p.className = 'typing';
        letter.insertBefore(p, letter.querySelector('.ps'));
        for (let i = 0; i <= text.length; i++) {
          if (skipTyping) { p.textContent = text; break; }
          p.textContent = text.slice(0, i);
          if (i % 3 === 0) await sleep(18);
        }
        p.textContent = text;
        p.classList.remove('typing');
        await sleep(250);
      }
      const ps = letter.querySelector('.ps');
      if (ps) ps.classList.add('show');
      toast('💌 Letter fully opened. Every word, only for ' + T.shortName + '.', 3400);
    }

    if (openBtn && letter) {
      openBtn.addEventListener('click', () => {
        openBtn.classList.add('gone');
        letter.classList.add('open');
        window.confettiBurst(window.innerWidth / 2, 220, 40);
        setTimeout(() => {
          letter.scrollIntoView({ behavior: 'smooth', block: 'center' });
          typeParagraphs(T.letter);
        }, 750);
      });
    }

    /* Voice note */
    const voiceBtn = document.getElementById('voiceNote');
    if (voiceBtn && T.audio) {
      const audio = new Audio(T.audio);
      voiceBtn.addEventListener('click', () => {
        if (audio.paused) {
          audio.play().then(() => {
            voiceBtn.textContent = '⏸️ Playing your voice note…';
            toast('🎧 A voice note recorded just for ' + T.shortName + '. Turn the volume up!', 3400);
          }).catch(() => toast('🔇 Hmm, audio needs a moment — try again!'));
        } else {
          audio.pause();
          voiceBtn.textContent = '🎧 Play Your Voice Note';
        }
      });
      audio.addEventListener('ended', () => { voiceBtn.textContent = '🎧 Play Your Voice Note (again!)'; });
    }

    /* ---------- Subject fun buttons ---------- */
    const stage = document.getElementById('funStage');
    let shuffleIdx = -1;

    function render(html) {
      stage.classList.add('show');
      stage.innerHTML = html;
    }

    function nextLine(arr) {
      shuffleIdx = (shuffleIdx + 1) % arr.length;
      return arr[shuffleIdx];
    }

    function playWhistle() {
      try {
        const Ctx = window.AudioContext || window.webkitAudioContext;
        const ctx = new Ctx();
        const t = ctx.currentTime;
        for (let i = 0; i < 2; i++) {
          const o = ctx.createOscillator();
          const g = ctx.createGain();
          const lfo = ctx.createOscillator();
          const lg = ctx.createGain();
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
      } catch (e) { /* no audio, no problem */ }
    }

    const actions = {
      poem() {
        render(T.poem.map((l, i) => '<div class="poem-line" style="animation-delay:' + (i * 0.35) + 's">' + l + '</div>').join(''));
      },
      shuffle() {
        render('<div class="pop-line">' + nextLine(T.shuffleLines) + '</div>');
      },
      equation() {
        render(T.equation.map((l, i) => '<div class="eq-line" style="animation-delay:' + (i * 0.5) + 's">' + l + '</div>').join(''));
      },
      pi() {
        render('<div class="eq-line" style="animation-delay:0s">π = <span id="piDigits"></span></div><div class="reaction-line" style="animation-delay:0s"></div>');
        const digits = '3.14159265358979323846264338327950288419716939937510582';
        const el = document.getElementById('piDigits');
        let i = 0;
        const iv = setInterval(() => {
          el.textContent = digits.slice(0, ++i);
          if (i >= digits.length) {
            clearInterval(iv);
            stage.querySelector('.reaction-line').textContent = T.piNote;
          }
        }, 45);
      },
      element() {
        render('<div class="element-tile"><div class="num">' + T.element.num + '</div><div class="sym">' + T.element.sym + '</div><div class="name">' + T.element.name + '</div><div class="mass">' + T.element.mass + '</div></div><span class="element-note">' + T.element.note + '</span>');
      },
      bubbles() {
        render('<div class="bubble-wrap" id="bubbleWrap"></div><div class="reaction-line"></div>');
        const wrap = document.getElementById('bubbleWrap');
        const bcolors = ['#0f766e', '#ea580c', '#f472b6', '#38bdf8', '#a3e635'];
        let n = 0;
        const iv = setInterval(() => {
          const b = document.createElement('div');
          b.className = 'bubble';
          const s = 12 + Math.random() * 26;
          b.style.width = s + 'px'; b.style.height = s + 'px';
          b.style.left = Math.random() * 90 + '%';
          b.style.background = bcolors[Math.floor(Math.random() * bcolors.length)];
          b.style.animationDuration = 1.4 + Math.random() * 1.4 + 's';
          wrap.appendChild(b);
          setTimeout(() => b.remove(), 3000);
          if (++n > 26) clearInterval(iv);
        }, 90);
        setTimeout(() => {
          stage.querySelector('.reaction-line').textContent = '⚗️ ' + T.reactions[Math.floor(Math.random() * T.reactions.length)];
        }, 900);
      },
      whistle() {
        playWhistle();
        render('<div class="pop-line">📣 PEEP-PEEP! Everyone gather round — it\'s ' + T.shortName + "'s day!</div>");
        window.confettiBurst(window.innerWidth / 2, window.innerHeight / 2, 70);
      },
      pep() {
        render('<div class="pop-line">💪 ' + nextLine(T.pepTalks) + '</div>');
      }
    };

    document.querySelectorAll('[data-fun]').forEach((btn) => {
      btn.addEventListener('click', (ev) => {
        const kind = btn.dataset.fun;
        if (actions[kind]) actions[kind]();
        if (kind !== 'whistle' && kind !== 'bubbles') {
          const r = btn.getBoundingClientRect();
          window.confettiBurst(r.left + r.width / 2, r.top, 18);
        }
      });
    });
  }

  /* ---------- Konami code (all pages) ---------- */
  const seq = ['arrowup', 'arrowup', 'arrowdown', 'arrowdown', 'arrowleft', 'arrowright', 'arrowleft', 'arrowright', 'b', 'a'];
  let ki = 0;
  document.addEventListener('keydown', (e) => {
    const k = (e.key || '').toLowerCase();
    ki = (k === seq[ki]) ? ki + 1 : (k === seq[0] ? 1 : 0);
    if (ki === seq.length) {
      ki = 0;
      document.body.classList.add('party');
      window.confettiRain(140);
      if (T) discover('konami', 'The legendary Konami code!');
      else toast('🌈 PARTY MODE UNLOCKED! (Old-school cheat codes still work here)', 4000);
    }
  });

  /* ---------- Teachers page: secret progress badges ---------- */
  document.querySelectorAll('[data-badge]').forEach((el) => {
    let n = 0;
    try { n = (JSON.parse(localStorage.getItem('td-secrets-' + el.dataset.badge)) || []).length; } catch (e) { /* noop */ }
    el.textContent = '🕵️ Secrets found: ' + Math.min(n, 4) + '/4';
  });

  /* ---------- Wall of gratitude ---------- */
  const wallGrid = document.getElementById('wallGrid');
  if (wallGrid) {
    const preset = window.WALL_NOTES || [];
    let extra = [];
    try { extra = JSON.parse(localStorage.getItem('td-wall')) || []; } catch (e) { /* noop */ }
    const noteColors = ['#fef08a', '#fbcfe8', '#bbf7d0', '#bfdbfe', '#fed7aa', '#e9d5ff'];

    function addNote(note, by, i) {
      const d = document.createElement('div');
      d.className = 'sticky-note reveal in';
      d.style.background = noteColors[i % noteColors.length];
      d.style.setProperty('--rot', ((i % 5) - 2) * 1.4 + 'deg');
      d.textContent = note;
      const s = document.createElement('span');
      s.className = 'by';
      s.textContent = '— ' + by;
      d.appendChild(s);
      wallGrid.appendChild(d);
    }
    preset.forEach((n, i) => addNote(n.note, n.by, i));
    extra.forEach((n, i) => addNote(n.note, n.by, i + preset.length));

    const form = document.getElementById('wallForm');
    if (form) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        const by = (form.querySelector('input').value || 'A secret admirer').trim();
        const note = (form.querySelector('textarea').value || '').trim();
        if (!note) { toast('✍️ Write a little note first!'); return; }
        extra.push({ note, by });
        try { localStorage.setItem('td-wall', JSON.stringify(extra)); } catch (err) { /* noop */ }
        addNote(note, by, preset.length + extra.length - 1);
        form.reset();
        window.confettiBurst(window.innerWidth / 2, window.innerHeight / 2, 40);
        toast('💛 Your note is on the wall! Thank you!');
      });
    }
  }
})();
