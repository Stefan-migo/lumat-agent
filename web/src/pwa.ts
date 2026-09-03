export const SERVICE_WORKER_PATH = "/panel/sw.js";

export function shouldRegisterPwa(input: { protocol: string; serviceWorker: boolean }): boolean {
  return input.protocol === "https:" && input.serviceWorker;
}

export function isCacheableAsset(url: string, method = "GET"): boolean {
  if (method !== "GET") return false;
  const parsed = new URL(url, "https://panel.test");
  if (parsed.pathname === "/panel/api" || parsed.pathname.startsWith("/panel/api/") || parsed.pathname === "/panel/" || parsed.pathname.endsWith(".html")) return false;
  return parsed.pathname.startsWith("/panel/assets/")
    || parsed.pathname.startsWith("/panel/brand/")
    || parsed.pathname === "/panel/manifest.webmanifest";
}

export function isObsoleteCache(cacheName: string, activeCache: string): boolean {
  return cacheName.startsWith("lumat-shell-") && cacheName !== activeCache;
}

export async function registerPwa(): Promise<ServiceWorkerRegistration | undefined> {
  if (typeof navigator === "undefined" || typeof location === "undefined") return undefined;
  if (!shouldRegisterPwa({ protocol: location.protocol, serviceWorker: "serviceWorker" in navigator })) return undefined;
  try {
    return await navigator.serviceWorker.register(SERVICE_WORKER_PATH, { scope: "/panel/" });
  } catch {
    return undefined;
  }
}
