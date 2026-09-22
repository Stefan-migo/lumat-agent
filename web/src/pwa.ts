export const SERVICE_WORKER_PATH = "/panel/app/sw.js";

export function shouldRegisterPwa(input: { protocol: string; serviceWorker: boolean }): boolean {
  return input.protocol === "https:" && input.serviceWorker;
}

export async function registerPwa(): Promise<ServiceWorkerRegistration | undefined> {
  if (typeof navigator === "undefined" || typeof location === "undefined") return undefined;
  if (!shouldRegisterPwa({ protocol: location.protocol, serviceWorker: "serviceWorker" in navigator })) return undefined;
  try {
    return await navigator.serviceWorker.register(SERVICE_WORKER_PATH, { scope: "/panel/app/" });
  } catch {
    return undefined;
  }
}
