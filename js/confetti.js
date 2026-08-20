/* ==========================================================================
   Confetti engine — OPTIMIZED (canvas-based)
   GPU-friendly: single canvas, requestAnimationFrame batching.
   Exposes `confettiBurst(x, y, count)` and `confettiRain(count)`.
   ========================================================================== */
(function () {
  'use strict';

  var reducedMotion = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var COLORS = ['#d6337c', '#ff5f8d', '#ff8a3d', '#ffc93c', '#7bd44a', '#22c39a', '#17b6c7', '#3ea6f5', '#8a5cf6', '#6b3fd4'];
  var canvas = null;
  var ctx = null;
  var pieces = [];
  var rafId = null;
  var running = false;

  function ensureCanvas() {
    if (canvas) return;
    canvas = document.createElement('canvas');
    canvas.className = 'confetti-canvas';
    ctx = canvas.getContext('2d');
    resize();
    document.body.appendChild(canvas);
    window.addEventListener('resize', resize);
  }

  function resize() {
    if (!canvas) return;
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }

  function spawnBurst(x, y, count) {
    count = count || 50;
    for (var i = 0; i < count; i++) {
      var angle = Math.random() * Math.PI * 2;
      var speed = 4 + Math.random() * 8;
      pieces.push({
        x: x, y: y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed - 4,
        size: 4 + Math.random() * 6,
        color: COLORS[Math.floor(Math.random() * COLORS.length)],
        rotation: Math.random() * 360,
        rotSpeed: (Math.random() - 0.5) * 12,
        life: 1,
        decay: 0.012 + Math.random() * 0.008,
        shape: Math.random() > 0.5 ? 'rect' : 'circle'
      });
    }
  }

  function spawnRain(count) {
    count = count || 60;
    for (var i = 0; i < count; i++) {
      pieces.push({
        x: Math.random() * canvas.width,
        y: -20 - Math.random() * 200,
        vx: (Math.random() - 0.5) * 2,
        vy: 2 + Math.random() * 3,
        size: 4 + Math.random() * 6,
        color: COLORS[Math.floor(Math.random() * COLORS.length)],
        rotation: Math.random() * 360,
        rotSpeed: (Math.random() - 0.5) * 6,
        life: 1,
        decay: 0.004 + Math.random() * 0.003,
        shape: Math.random() > 0.5 ? 'rect' : 'circle'
      });
    }
  }

  function tick() {
    if (!ctx || !canvas) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    for (var i = pieces.length - 1; i >= 0; i--) {
      var p = pieces[i];
      p.x += p.vx;
      p.y += p.vy;
      p.vy += 0.15; // gravity
      p.vx *= 0.99; // friction
      p.rotation += p.rotSpeed;
      p.life -= p.decay;

      if (p.life <= 0 || p.y > canvas.height + 50) {
        pieces.splice(i, 1);
        continue;
      }

      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate(p.rotation * Math.PI / 180);
      ctx.globalAlpha = Math.max(0, p.life);
      ctx.fillStyle = p.color;

      if (p.shape === 'rect') {
        ctx.fillRect(-p.size / 2, -p.size / 4, p.size, p.size / 2);
      } else {
        ctx.beginPath();
        ctx.arc(0, 0, p.size / 2, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();
    }

    if (pieces.length > 0) {
      rafId = requestAnimationFrame(tick);
    } else {
      running = false;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
  }

  function startLoop() {
    if (running) return;
    running = true;
    rafId = requestAnimationFrame(tick);
  }

  window.confettiBurst = function (x, y, count) {
    if (reducedMotion) return;
    ensureCanvas();
    spawnBurst(x, y, count);
    startLoop();
  };

  window.confettiRain = function (count) {
    if (reducedMotion) return;
    ensureCanvas();
    spawnRain(count);
    startLoop();
  };
})();
