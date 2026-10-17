// BibleChat web: keeps the app and every Bible you opened on this phone, so it also works offline.
const SHELL = "bc-shell-v2", DATA = "bc-data-v1";
const FILES = ["./", "index.html", "manifest.webmanifest", "icon.svg", "icon-192.png", "icon-512.png", "cashapp-qr.jpg"];
self.addEventListener("install", e => { e.waitUntil(caches.open(SHELL).then(c => c.addAll(FILES)).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => ![SHELL, DATA].includes(k)).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  if (/\/data\/[^/]+\.json$/.test(url.pathname) && !url.pathname.endsWith("catalog.json")) {
    // a Bible: the text never changes, so keep the first copy and use it from then on
    e.respondWith(caches.open(DATA).then(async c => (await c.match(e.request)) || fetch(e.request).then(r => { if (r.ok) c.put(e.request, r.clone()); return r; })));
    return;
  }
  // the app itself and the list of Bibles: fresh when online, saved copy when offline
  e.respondWith(fetch(e.request).then(r => { if (r.ok) caches.open(SHELL).then(c => c.put(e.request, r.clone())); return r; })
    .catch(() => caches.match(e.request).then(m => m || caches.match("index.html"))));
});
