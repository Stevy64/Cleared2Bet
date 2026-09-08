const CACHE = 'paris-v48';
const PRECACHE = [
  '/manifest.webmanifest',
  '/static/css/app.css?v=48',
  '/static/js/app.js?v=48',
  '/static/vendor/alpine.min.js?v=48',
  '/static/img/hero-accueil.jpg',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') self.skipWaiting();
});

function withCacheFlag(response) {
  const headers = new Headers(response.headers);
  headers.set('X-SW-Cache', '1');
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE);
  const cached = await cache.match(request);
  const network = fetch(request).then((res) => {
    if (res && res.ok) cache.put(request, res.clone());
    return res;
  }).catch(() => cached);
  if (cached) {
    network.catch(() => {});
    return cached;
  }
  return network;
}

async function networkFirst(request, { flagCache } = {}) {
  const cache = await caches.open(CACHE);
  try {
    const res = await fetch(request);
    if (res && res.ok) cache.put(request, res.clone());
    return res;
  } catch (err) {
    const cached = await cache.match(request);
    if (cached) return flagCache ? withCacheFlag(cached) : cached;
    throw err;
  }
}

function isAppShell(path) {
  return (
    path === '/'
    || path === '/historique'
    || path === '/verification'
    || path === '/reglages'
    || /^\/matchs\/\d+\/?$/.test(path)
  );
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;

  const path = url.pathname;

  // Toujours le réseau pour le SW lui-même.
  if (path === '/sw.js') return;

  if (path.startsWith('/api/')) {
    event.respondWith(networkFirst(req, { flagCache: true }));
    return;
  }

  // Pages HTML : réseau d’abord (évite de rester coincé sur une vieille UI).
  if (req.mode === 'navigate' || isAppShell(path)) {
    event.respondWith(networkFirst(req, { flagCache: false }));
    return;
  }

  if (path === '/manifest.webmanifest' || path.startsWith('/static/')) {
    event.respondWith(staleWhileRevalidate(req));
  }
});
