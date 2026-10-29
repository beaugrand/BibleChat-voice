// BibleChat web: keeps the app and every Bible you opened on this phone, so it also works offline.
// index.html (offline()) also fetches the KJV, the Ethiopian Canon and the study data in the background; they are kept here.
const SHELL = "bc-shell-v14", DATA = "bc-data-v1", MEANING = "bc-meaning-v1", STUDY = "bc-study-v1";   // a new model: change MEANING
const FILES = ["./", "index.html", "manifest.webmanifest", "icon.svg", "icon-192.png", "icon-512.png", "cashapp-qr.jpg", "i18n.js", "smart.js", "paths.js", "quoted.json", "paths/index.json", "prayers.js", "prayers.json", "data/catalog.json"];
// the study paths and their pictures are kept too, so a path works offline after the first visit;
// one file at a time, so one failed download can't stop the others (index.html fetches any missing one again later)
self.addEventListener("install", e => { e.waitUntil(caches.open(SHELL).then(c => c.addAll(FILES).then(() =>
  fetch("paths/index.json").then(r => r.json()).then(list => Promise.allSettled(list.map(p => "paths/" + p.id + ".json")
    .concat(list.filter(p => p.image).map(p => "paths/" + p.image)).map(u => c.add(u)))).catch(() => {})))
  .then(() => self.skipWaiting())); });
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => ![SHELL, DATA, MEANING, STUDY].includes(k)).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  const meaning = /\/data\/meaning\//.test(url.pathname);   // the meaning model and verse fingerprints: also never change
  if (meaning || (/\/data\/[^/]+\.json$/.test(url.pathname) && !url.pathname.endsWith("catalog.json"))) {
    // a Bible: the text never changes, so keep the first copy and use it from then on
    // if the phone's storage is full or blocked, still load the Bible straight from the internet
    e.respondWith((async () => {
      let c = null;
      try { c = await caches.open(meaning ? MEANING : DATA); const hit = await c.match(e.request); if (hit) return hit; } catch (err) { c = null; }
      const r = await fetch(e.request);
      if (r.ok && c) c.put(e.request, r.clone()).catch(() => {});
      return r;
    })());
    return;
  }
  // the app itself, the list of Bibles and the study data: fresh when online, saved copy when offline
  // (the study data has its own box, so an app update doesn't throw away the 40 MB kept for offline use)
  const box = /\/data\/study\//.test(url.pathname) ? STUDY : SHELL;
  // the copy is made at once: made later, the page may already have read the answer and the copy would fail
  e.respondWith(fetch(e.request).then(r => { if (r.ok) { const copy = r.clone(); e.waitUntil(caches.open(box).then(c => c.put(e.request, copy)).catch(() => {})); } return r; })
    .catch(() => caches.match(e.request).then(m => m || caches.match("index.html"))));
});
