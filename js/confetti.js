/* ==========================================================================
   Confetti engine — Teacher's Day
   Exposes `confettiBurst(x, y, count)` and `confettiRain(count)`.

   Confetti is ONLY triggered by explicit calls (buttons / celebrations) —
   nothing auto-sprays on page load. Respects prefers-reduced-motion.
   ========================================================================== */
(function () {
  'use strict';

  var reducedMotion = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var COLORS = ['#6d28d9', '#8b5cf6', '#d6356f', '#d99a06', '#f0b429', '#0ea5e9', '#10b981'];
  var SHAPES = ['🎉', '💐', '⭐', '📚', '✏️', '❤️', '✨', '🎓'];

  function pick(arr) { return arr[Math.floor(Math.random() * arr.length)]; }

  /**
   * Create one piece of confetti.
   * @param {Object} opts
   * @param {boolean} opts.burst - true = explode from a point; false = rain from the top
   * @param {number}  [opts.x]   - burst origin (px)
   * @param {number}  [opts.y]   - burst origin (px)
   */
  function spawn(opts) {
    if (reducedMotion) return;

    var el = document.createElement('div');
    el.className = 'confetti-piece';

    var size = 8 + Math.random() * 10;
    var useEmoji = Math.random() > 0.55;

    if (useEmoji) {
      el.textContent = pick(SHAPES);
      el.style.fontSize = (size + 8) + 'px';
    } else {
      el.style.width = size + 'px';
      el.style.height = (size * 0.6) + 'px';
      el.style.background = pick(COLORS);
      el.style.borderRadius = '2px';
    }

    if (opts.burst) {
      el.style.left = opts.x + 'px';
      el.style.top = opts.y + 'px';
      document.body.appendChild(el);

      var dx = (Math.random() - 0.5) * 2 * 170;      // sideways drift
      var dy = 150 + Math.random() * 240;            // downward fall
      var rot = 360 + Math.random() * 540;           // full spins
      var dur = 1100 + Math.random() * 1300;         // ms

      el.animate([
        { transform: 'translate(0, 0) rotate(0deg)', opacity: 1 },
        { transform: 'translate(' + dx + 'px, ' + dy + 'px) rotate(' + rot + 'deg)', opacity: 0 }
      ], { duration: dur, easing: 'cubic-bezier(0.2, 0.7, 0.3, 1)', fill: 'forwards' });

      setTimeout(function () { el.remove(); }, dur + 60);
    } else {
      el.style.left = Math.random() * 100 + 'vw';
      el.style.animationDuration = (4 + Math.random() * 5) + 's';
      // Negative delay starts pieces partway down their fall (no pile-up at top).
      el.style.animationDelay = '-' + (Math.random() * 5).toFixed(2) + 's';
      document.body.appendChild(el);
      setTimeout(function () { el.remove(); }, 10500);
    }
  }

  /** Explode a burst of confetti from a point. */
  window.confettiBurst = function (x, y, count) {
    if (reducedMotion) return;
    count = count || 60;
    for (var i = 0; i < count; i++) {
      setTimeout(function () { spawn({ burst: true, x: x, y: y }); }, i * 12);
    }
  };

  /** Rain confetti across the whole screen. */
  window.confettiRain = function (count) {
    if (reducedMotion) return;
    count = count || 90;
    for (var i = 0; i < count; i++) {
      setTimeout(function () { spawn({ burst: false }); }, i * 28);
    }
  };
})();
