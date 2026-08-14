// Lightweight confetti sprinkle for Teacher's Day 🎉
(function () {
  const colors = ['#7c3aed', '#f43f5e', '#f59e0b', '#10b981', '#3b82f6', '#f472b6'];
  const shapes = ['🎉', '💐', '⭐', '📚', '🍎', '✏️', '❤️'];

  function spawnPiece(useEmoji) {
    const el = document.createElement('div');
    el.className = 'confetti-piece';
    const left = Math.random() * 100;
    const duration = 4 + Math.random() * 5;
    const size = 8 + Math.random() * 10;

    el.style.left = left + 'vw';
    el.style.animationDuration = duration + 's';

    if (useEmoji) {
      el.textContent = shapes[Math.floor(Math.random() * shapes.length)];
      el.style.fontSize = size + 6 + 'px';
    } else {
      el.style.width = size + 'px';
      el.style.height = size * 0.6 + 'px';
      el.style.background = colors[Math.floor(Math.random() * colors.length)];
      el.style.borderRadius = '2px';
    }

    document.body.appendChild(el);
    setTimeout(() => el.remove(), duration * 1000);
  }

  // Initial burst
  for (let i = 0; i < 40; i++) {
    setTimeout(() => spawnPiece(Math.random() > 0.7), i * 90);
  }

  // Gentle ongoing sprinkle
  setInterval(() => spawnPiece(Math.random() > 0.7), 900);
})();
