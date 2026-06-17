// app/static/sw.js — service worker mínimo do Oriens.
// Objetivo: tornar o app "instalável" no celular (PWA). Mantém estratégia
// network-first sem cache agressivo de HTML, evitando telas desatualizadas.
const CACHE = "oriens-static-v1";
const STATIC_ASSETS = ["/static/icon.svg", "/static/manifest.webmanifest"];

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

  // Assets estáticos: cache-first (rápido e offline).
  if (req.url.includes("/static/")) {
    event.respondWith(caches.match(req).then((hit) => hit || fetch(req)));
    return;
  }

  // Resto (páginas): rede primeiro; se cair, tenta o que houver em cache.
  event.respondWith(fetch(req).catch(() => caches.match(req)));
});
