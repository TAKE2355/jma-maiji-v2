const CACHE = 'nimbus-offline-v1';
const SHELL = ['offline.html', 'sw-offline.js'];

self.addEventListener('install', e => { self.skipWaiting(); });

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks =>
    Promise.all(ks.map(k => k !== CACHE ? caches.delete(k) : null))
  ).then(() => self.clients.claim()));
});

// キャッシュ優先。無ければネットワーク、取れたら保存。
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  const isAsset = url.hostname === 'raw.githubusercontent.com'
               || url.hostname === 'fonts.googleapis.com'
               || url.hostname === 'fonts.gstatic.com'
               || (url.origin === self.location.origin &&
                   (url.pathname.includes('/assets/') ||
                    url.pathname.endsWith('offline.html') ||
                    url.pathname.endsWith('sw-offline.js')));
  if (!isAsset) return;

  const isShell = url.origin === self.location.origin &&
                  (url.pathname.endsWith('offline.html') || url.pathname.endsWith('sw-offline.js'));

  e.respondWith((async () => {
    const cache = await caches.open(CACHE);
    // アプリ本体は常に最新を取りに行き、オフライン時だけキャッシュを使う
    if (isShell) {
      try {
        const fresh = await fetch(req, { cache: 'no-store' });
        if (fresh && fresh.status === 200) { cache.put(req, fresh.clone()); return fresh; }
      } catch (err) {}
      const c0 = await cache.match(req, { ignoreSearch: true });
      if (c0) return c0;
      return fetch(req);
    }
    const hit = await cache.match(req, { ignoreSearch: true });
    if (hit) return hit;
    try {
      const res = await fetch(req);
      if (res && res.status === 200) cache.put(req, res.clone());
      return res;
    } catch (err) {
      const any = await cache.match(req, { ignoreSearch: true });
      if (any) return any;
      throw err;
    }
  })());
});
