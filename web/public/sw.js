const CACHE_NAME = "lumat-shell-v1";
const SHELL_URL = "/panel/app/";

function isCacheableAsset(url, method = "GET") {
  if (method !== "GET" || url.pathname === "/panel/api" || url.pathname.startsWith("/panel/api/") || url.pathname.endsWith(".html")) return false;
  return url.pathname === SHELL_URL
    || url.pathname.startsWith("/panel/app/assets/")
    || url.pathname.startsWith("/panel/app/brand/")
    || url.pathname === "/panel/app/manifest.webmanifest";
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.add(SHELL_URL)).then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter((key) => key.startsWith("lumat-shell-") && key !== CACHE_NAME)
        .map((key) => caches.delete(key)),
    )).then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (!isCacheableAsset(url, request.method)) return;
  event.respondWith(
    caches.open(CACHE_NAME).then(async (cache) => {
      const cached = await cache.match(request);
      if (cached) return cached;
      const response = await fetch(request);
      if (response.ok) await cache.put(request, response.clone());
      return response;
    }),
  );
});
