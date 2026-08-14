// Confetti engine for Teacher's Day 🎉 — exposes burst + rain helpers
(function () {
  const colors = ['#7c3aed', '#f43f5e', '#f59e0b', '#10b981', '#3b82f6', '#f472b6', '#fbbf24'];
  const shapes = ['🎉', '💐', '⭐', '📚', '', '✏️', '❤️', '✨'];

  function makePiece(useEmoji, x, y, spread) {
    const el = document.createElement('div');
    el.className = 'confetti-piece';
    const size = 8 + Math.random() * 10;

    if (x !== undefined) {
      // burst mode: start at x,y and drift sideways
      el.style.left = x + 'px';
      el.style.top = y + 'px';
      const dx = (Math.random() - 0.5) * spread * 2;
      const dur = 1.2 + Math.random() * 1.4;
      el.style.animationDuration = dur + 's';
      el.style.setProperty('--dx', dx + 'px');
      el.style.animationName = 'none';
      requestAnimationFrame(() => {
        el.style.transition = `transform ${dur}s ease-out, opacity ${dur}s ease-out`;
        el.style.transform = `translate(${dx}px, ${140 + Math.random() * 220}px) rotate(${360 + Math.random() * 540}deg)`;
        el.style.opacity = '0';
      });
      setTimeout(() => el.remove(), dur * 1000 + 100);
    } else {
      // rain mode
      el.style.left = Math.random() * 100 + 'vw';
      el.style.animationDuration = 4 + Math.random() * 5 + 's';
    }

    if (useEmoji) {
      el.textContent = shapes[Math.floor(Math.random() * shapes.length)];
      el.style.fontSize = size + 8 + 'px';
    } else {
      el.style.width = size + 'px';
      el.style.height = size * 0.6 + 'px';
      el.style.background = colors[Math.floor(Math.random() * colors.length)];
      el.style.borderRadius = '2px';
    }
    document.body.appendChild(el);
    return el;
  }

  // Gentle ambient sprinkle on load
  for (let i = 0; i < 24; i++) {
    setTimeout(() => makePiece(Math.random() > 0.7), i * 90);
  }
  setInterval(() => makePiece(Math.random() > 0.75), 1600);

  // Public API
  window.confettiBurst = function (x, y, count) {
    count = count || 50;
    for (let i = 0; i < count; i++) {
      setTimeout(() => makePiece(Math.random() > 0.5, x, y, 160), i * 12);
    }
  };

  window.confettiRain = function (count) {
    count = count || 80;
    for (let i = 0; i < count; i++) {
      setTimeout(() => makePiece(Math.random() > 0.6), i * 30);
    }
  };
})();
