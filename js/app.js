/* ==========================================================================
   Teachers' Day — application engine
   --------------------------------------------------------------------------
   Modules (each guarded so missing DOM is harmless):
     1. helpers          — toast + reduced-motion detection
     2. mobileNav        — hamburger menu
     3. revealOnScroll   — fade-in sections
     4. countUp          — animated stats
     5. lightbox         — gallery preview (native <dialog>)
     6. noteShuffle      — random thank-you note generator
     7. celebrate        — "Celebrate" button → confetti
     8. teacherPage      — sealed letter, voice note, subject minigames, secrets
     9. konami           — hidden party-mode easter egg
    10. secretBadges     — progress on the teachers index
    11. gratitudeWall    — sticky-note wall (localStorage) with delete
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

  /* ------------------------------------------------------------------ 2. mobile nav */
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
    // Close after choosing a destination, and on Escape.
    navList.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () { setNav(false); });
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') setNav(false);
    });
    // Close if the user clicks outside the menu.
    document.addEventListener('click', function (e) {
      if (navList.classList.contains('open') &&
          !navList.contains(e.target) && !toggle.contains(e.target)) {
        setNav(false);
      }
    });
  }

  /* ------------------------------------------------------------------ 3. reveal on scroll */
  var revealItems = document.querySelectorAll('.reveal');
  if (reducedMotion) {
    revealItems.forEach(function (el) { el.classList.add('in'); });
  } else if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.classList.add('in');
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.12 });
    revealItems.forEach(function (el) { io.observe(el); });
  } else {
    revealItems.forEach(function (el) { el.classList.add('in'); });
  }

  /* ------------------------------------------------------------------ 4. count-up stats */
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

  /* ------------------------------------------------------------------ 5. lightbox */
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
    // Close when clicking the dimmed backdrop (but not the image itself).
    dialog.addEventListener('click', function (e) {
      if (e.target === dialog) closeLightbox();
    });
  }

  /* ------------------------------------------------------------------ 6. random thank-you note */
  var shuffleBtn = document.querySelector('[data-note-shuffle]');
  var noteOutput = document.querySelector('[data-note-output]');
  if (shuffleBtn && noteOutput) {
    var notes = (window.WISH_NOTES || []).slice();
    var lastIndex = -1;
    function showNote() {
      if (!notes.length) { noteOutput.textContent = 'No notes yet — be the first to write one!'; return; }
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
      who.textContent = '— ' + n.by;
      noteOutput.appendChild(who);
    }
    shuffleBtn.addEventListener('click', function () {
      showNote();
      var r = shuffleBtn.getBoundingClientRect();
      window.confettiBurst(r.left + r.width / 2, r.top, 24);
    });
    showNote(); // show a first note immediately
  }

  /* ------------------------------------------------------------------ 7. celebrate button */
  document.querySelectorAll('[data-celebrate]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      window.confettiRain(160);
      var msg = btn.dataset.celebrate || '🎉 Happy Teachers\u2019 Day!';
      toast(msg, 3600);
    });
  });

  /* ------------------------------------------------------------------ 8. teacher page */
  var T = window.TEACHER || null;
  if (T) initTeacherPage(T);

  function initTeacherPage(T) {
    /* ---- Secrets progress (persisted per teacher) ---- */
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
        void chip.offsetWidth; // restart animation
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

    updateChip(false);
    if (secretFound.length >= 4) celebrateAll(true);

    /* ---- Secret 1: tap the photo five times (keyboard too) ---- */
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

    /* ---- Secret 2: hidden gift box in the footer ---- */
    var gift = document.querySelector('.giftbox');
    if (gift) {
      gift.addEventListener('click', function () {
        discover('gift', 'The hidden gift box!');
        var r = gift.getBoundingClientRect();
        window.confettiBurst(r.left + r.width / 2, r.top, 40);
        toast(T.giftJoke, 5000);
      });
    }

    /* ---- Secret 3: invisible ink (select the hidden text) ---- */
    var ink = document.querySelector('.hidden-ink');
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

    /* ---- Sealed letter: types itself out ---- */
    var openBtn = document.getElementById('openLetter');
    var letter = document.getElementById('letter');
    // Skip the word-by-word typing when the user prefers reduced motion.
    var skipTyping = reducedMotion;
    if (letter) letter.addEventListener('click', function () { skipTyping = true; });

    function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

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
      openBtn.addEventListener('click', function () {
        openBtn.classList.add('gone');
        letter.classList.add('open');
        window.confettiBurst(window.innerWidth / 2, 220, 40);
        setTimeout(function () {
          letter.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'center' });
          typeParagraphs(T.letter);
        }, 750);
      });
    }

    /* ---- Voice note ---- */
    var voiceBtn = document.getElementById('voiceNote');
    if (voiceBtn && T.audio) {
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
      } catch (e) { /* audio unavailable — the message still shows */ }
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
      equation: function () {
        render(T.equation.map(function (l, i) {
          return '<div class="eq-line" style="animation-delay:' + (i * 0.5) + 's">' + l + '</div>';
        }).join(''));
      },
      pi: function () {
        render('<div class="eq-line">\u03C0 = <span id="piDigits"></span></div><div class="reaction-line"></div>');
        var digits = '3.14159265358979323846264338327950288419716939937510582';
        var el = document.getElementById('piDigits');
        var i = 0;
        var iv = setInterval(function () {
          el.textContent = digits.slice(0, ++i);
          if (i >= digits.length) {
            clearInterval(iv);
            stage.querySelector('.reaction-line').textContent = T.piNote;
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
          wrap.appendChild(b);
          setTimeout(function () { b.remove(); }, 3000);
          if (++n > 26) clearInterval(iv);
        }, 90);
        setTimeout(function () {
          stage.querySelector('.reaction-line').textContent =
            '\u2697\uFE0F ' + T.reactions[Math.floor(Math.random() * T.reactions.length)];
        }, 900);
      },
      whistle: function () {
        playWhistle();
        render('<div class="pop-line">\uD83D\uDCE3 PEEP-PEEP! Everyone gather round \u2014 it\u2019s ' + T.shortName + '\u2019s day!</div>');
        window.confettiBurst(window.innerWidth / 2, window.innerHeight / 2, 70);
      },
      pep: function () {
        render('<div class="pop-line">\uD83D\uDCAA ' + nextLine(T.pepTalks) + '</div>');
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

  /* ------------------------------------------------------------------ 9. konami code */
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
    }
  });

  /* ------------------------------------------------------------------ 10. secret badges (teachers index) */
  document.querySelectorAll('[data-badge]').forEach(function (el) {
    var n = 0;
    try { n = (JSON.parse(localStorage.getItem('td-secrets-' + el.dataset.badge)) || []).length; } catch (e) { /* noop */ }
    el.textContent = '\uD83D\uDD75\uFE0F Secrets found: ' + Math.min(n, 4) + '/4';
  });

  /* ------------------------------------------------------------------ 11. gratitude wall */
  var wallGrid = document.getElementById('wallGrid');
  if (wallGrid) {
    var preset = window.WALL_NOTES || [];
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
