// ¿A cuánto queda? — Service Worker
// Incrementar CACHE en cada versión (acq-vN)
const CACHE = 'acq-v5';
const ARCHIVOS = [
  './',
  './index.html',
  './ciudades.js',
  './data.bin',
  './manifest.json',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/icon-maskable-512.png'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(cache =>
      Promise.all(ARCHIVOS.map(url =>
        fetch(url, { cache: 'reload' }).then(resp => cache.put(url, resp)).catch(() => {})
      ))
    ).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(resp => {
        if (resp.ok && resp.type === 'basic') {
          const copia = resp.clone();
          caches.open(CACHE).then(cache => cache.put(e.request, copia));
        }
        return resp;
      }).catch(() => cached);
    })
  );
});
