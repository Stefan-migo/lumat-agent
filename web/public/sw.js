const CACHE_NAME = "lumat-shell-v1";
const SHELL_URL = "/panel/app/";

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.add(SHELL_URL)).then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("push", (event) => {
  const body = event.data ? event.data.text() : "";
  event.waitUntil(self.registration.showNotification("Lumat", { body, data: { url: "/panel/app/" } }));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = event.notification.data?.url ?? "/panel/app/";
  event.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
    const client = clients.find((candidate) => new URL(candidate.url).origin === self.location.origin && candidate.url.startsWith(self.registration.scope));
    return client ? client.focus() : self.clients.openWindow(url);
  }));
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.pathname === "/panel/api" || url.pathname.startsWith("/panel/api/") || url.pathname.endsWith(".html")) return;
  const isAsset = url.pathname.startsWith("/panel/app/assets/");
  const isNetworkFirst = url.pathname === SHELL_URL
    || url.pathname.startsWith("/panel/app/brand/")
    || url.pathname === "/panel/app/manifest.webmanifest";
  if (!isAsset && !isNetworkFirst) return;
  event.respondWith(
    caches.open(CACHE_NAME).then(async (cache) => {
      if (isAsset) {
        const cached = await cache.match(request);
        if (cached) return cached;
        const response = await fetch(request);
        if (response.ok) await cache.put(request, response.clone());
        return response;
      }
      try {
        const response = await fetch(request);
        if (response.ok) await cache.put(request, response.clone());
        return response;
      } catch (error) {
        const cached = await cache.match(request);
        if (cached) return cached;
        throw error;
      }
    }),
  );
});

// ponytail: cached /panel/app/assets/** entries grow by roughly one bundle per deploy; version CACHE_NAME once a build id reaches the panel image (GIT_SHA is wired only into the api build, not the nginx panel image).
