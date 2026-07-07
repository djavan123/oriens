// app/static/sw.js — service worker do Oriens (PWA).
// Estratégia: HTML network-first (evita telas desatualizadas); assets estáticos
// cache-first COM população de cache no primeiro fetch → app funciona offline
// depois da 1ª visita (Tailwind/HTMX/Alpine/Sortable/fonte são auto-hospedados).
const CACHE = "oriens-static-v2";
const STATIC_ASSETS = [
  "/static/icon.svg",
  "/static/manifest.webmanifest",
  "/static/css/theme.css",
  "/static/vendor/tailwind.js",
  "/static/vendor/htmx.min.js",
  "/static/vendor/alpine.min.js",
  "/static/vendor/sortable.min.js",
  "/static/vendor/fonts/inter.css",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(STATIC_ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  // Só intercepta GET. POST/PATCH/DELETE (HTMX, login) passam direto.
  if (req.method !== "GET") return;

  // Assets estáticos: cache-first; ao buscar da rede, guarda no cache (offline).
  if (req.url.includes("/static/")) {
    event.respondWith(
      caches.match(req).then(
        (hit) =>
          hit ||
          fetch(req).then((res) => {
            if (res && res.ok) {
              const copy = res.clone();
              caches.open(CACHE).then((c) => c.put(req, copy));
            }
            return res;
          })
      )
    );
    return;
  }

  // Resto (páginas): rede primeiro; se cair, tenta o que houver em cache.
  event.respondWith(fetch(req).catch(() => caches.match(req)));
});
