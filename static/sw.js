const CACHE = 'paris-v46';
const PRECACHE = [
  '/',
  '/manifest.webmanifest',
  '/static/css/app.css?v=46',
  '/static/js/app.js?v=46',
  '/static/vendor/alpine.min.js?v=46',
  '/static/img/hero-accueil.jpg',
  '/historique',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(PRECACHE))
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
    return withCacheFlag(cached);
  }
  return network;
}

async function networkFirst(request) {
  const cache = await caches.open(CACHE);
  try {
    const res = await fetch(request);
    if (res && res.ok) cache.put(request, res.clone());
    return res;
  } catch (err) {
    const cached = await cache.match(request);
    if (cached) return withCacheFlag(cached);
    throw err;
  }
}

async function cacheFirst(request) {
  const cache = await caches.open(CACHE);
  const cached = await cache.match(request);
  if (cached) return cached;
  const res = await fetch(request);
  if (res && res.ok) cache.put(request, res.clone());
  return res;
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;

  const path = url.pathname;
  if (path.startsWith('/api/v1/historique') || path.startsWith('/api/v1/verification')) {
    event.respondWith(networkFirst(req));
    return;
  }
  if (path.startsWith('/api/v1/matchs')) {
    event.respondWith(networkFirst(req));
    return;
  }
  if (
    path === '/' ||
    path === '/sw.js' ||
    path === '/manifest.webmanifest' ||
    path.startsWith('/static/') ||
    path === '/historique' ||
    path === '/verification' ||
    path === '/reglages' ||
    /^\/matchs\/\d+\/?$/.test(path)
  ) {
    event.respondWith(cacheFirst(req));
    return;
  }
});
