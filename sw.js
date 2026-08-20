const CACHE = 'teachers-day-v2';
const APP_SHELL = [
  './', 'index.html', 'teachers.html', 'teacher.html', 'memories.html', 'message.html', 'wall.html',
  'css/style.css', 'js/data.js', 'js/app.js', 'js/confetti.js', 'manifest.webmanifest',
  'assets/logo-crest.png', 'assets/logo.png', 'assets/favicon-192.png'
];
self.addEventListener('install', event => event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(APP_SHELL)).then(() => self.skipWaiting())));
self.addEventListener('activate', event => event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim())));
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request).then(response => {
    if (response.ok && new URL(event.request.url).origin === location.origin) caches.open(CACHE).then(cache => cache.put(event.request, response.clone()));
    return response;
  }).catch(() => caches.match('index.html'))));
});
