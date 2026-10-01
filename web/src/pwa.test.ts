import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import vm from "node:vm";
import { SERVICE_WORKER_PATH, shouldRegisterPwa } from "./pwa";
import { parsePanelPath, pathForView } from "./components/domain/panelRoutes";

describe("PWA shell", () => {
  it("ships install metadata and both required icon purposes", () => {
    const manifest = readFileSync("public/manifest.webmanifest", "utf8");
    const metadata = JSON.parse(manifest) as {
      display: string;
      scope: string;
      start_url: string;
      theme_color: string;
      background_color: string;
      icons: Array<{ purpose?: string; sizes: string; src: string }>;
    };

    expect(metadata.display).toBe("standalone");
    expect(metadata.start_url).toBe("/panel/app/");
    expect(metadata.scope).toBe("/panel/app/");
    expect(metadata.icons).toEqual(expect.arrayContaining([
      expect.objectContaining({ src: "/panel/app/brand/icon-192.png", sizes: "192x192", purpose: "any" }),
      expect.objectContaining({ src: "/panel/app/brand/icon-512.png", sizes: "512x512" }),
      expect.objectContaining({ src: "/panel/app/brand/icon-maskable-512.png", sizes: "512x512", purpose: expect.stringContaining("maskable") }),
    ]));
    expect(metadata.theme_color).toBe("#143c2c");
    expect(metadata.background_color).toBe("#dbe1d6");
    const index = readFileSync("index.html", "utf8");
    expect(index).toContain('href="/panel/app/manifest.webmanifest"');
    expect(index).toContain('href="/panel/app/brand/favicon.ico"');
    expect(index).toContain('href="/panel/app/brand/apple-touch-icon.png"');
    expect(index).toContain('content="#143c2c"');
    expect(readFileSync("vite.config.ts", "utf8")).toContain("base: '/panel/app/'");
  });

  it("does not register on insecure contexts or unsupported browsers", () => {
    expect(shouldRegisterPwa({ protocol: "http:", serviceWorker: true })).toBe(false);
    expect(shouldRegisterPwa({ protocol: "https:", serviceWorker: false })).toBe(false);
    expect(shouldRegisterPwa({ protocol: "https:", serviceWorker: true })).toBe(true);
  });

  it("exercises the worker cache policy", async () => {
    expect(SERVICE_WORKER_PATH).toBe("/panel/app/sw.js");
    const listeners = new Map<string, (event: any) => void>();
    const entries = new Map<string, Response>();
    let fetchCalls = 0;
    let fetchImpl: (request: Request) => Promise<Response> = async () => new Response("network");
    const keyFor = (request: Request | string) => new URL(typeof request === "string" ? request : request.url, "https://panel.test").href;
    const fetch = (request: Request | string) => {
      fetchCalls += 1;
      return fetchImpl(typeof request === "string" ? new Request(`https://panel.test${request}`) : request);
    };
    const cache = {
      match: async (request: Request | string) => entries.get(keyFor(request))?.clone(),
      put: async (request: Request | string, response: Response) => {
        entries.set(keyFor(request), response.clone());
      },
      add: async (url: string) => {
        const response = await fetch(url);
        if (response.ok) await cache.put(url, response);
      },
    };
    const caches = {
      open: async () => cache,
      keys: async () => ["lumat-shell-v1"],
      delete: async () => true,
    };
    const self = {
      addEventListener: (type: string, handler: (event: any) => void) => listeners.set(type, handler),
      skipWaiting: async () => {},
      clients: { claim: async () => {} },
    };
    vm.runInNewContext(readFileSync("public/sw.js", "utf8"), {
      self,
      caches,
      fetch,
      URL,
      Request,
      Response,
      console,
    });

    const installPromises: Promise<unknown>[] = [];
    listeners.get("install")?.({ waitUntil: (promise: Promise<unknown>) => installPromises.push(promise) });
    await Promise.all(installPromises);

    const dispatch = async (url: string, method = "GET") => {
      let responsePromise: Promise<Response> | undefined;
      listeners.get("fetch")?.({
        request: new Request(`https://panel.test${url}`, { method }),
        respondWith: (promise: Promise<Response>) => { responsePromise = promise; },
      });
      return responsePromise ? responsePromise.then((response) => response.text()) : undefined;
    };
    const setNetworkBody = (body: string) => {
      fetchImpl = async () => new Response(body);
    };

    await cache.put("https://panel.test/panel/app/", new Response("stale shell"));
    setNetworkBody("new shell");
    expect(await dispatch("/panel/app/")).toBe("new shell");

    setNetworkBody("newer shell");
    await dispatch("/panel/app/");
    fetchImpl = async () => { throw new Error("offline"); };
    expect(await dispatch("/panel/app/")).toBe("newer shell");

    await cache.put("https://panel.test/panel/app/assets/index-abc123.js", new Response("cached asset"));
    const callsBeforeAsset = fetchCalls;
    expect(await dispatch("/panel/app/assets/index-abc123.js")).toBe("cached asset");
    expect(fetchCalls).toBe(callsBeforeAsset);

    for (const url of ["/panel/app/brand/icon-192.png", "/panel/app/manifest.webmanifest"]) {
      await cache.put(`https://panel.test${url}`, new Response("stale resource"));
      setNetworkBody("live resource");
      expect(await dispatch(url)).toBe("live resource");
    }

    for (const url of ["/panel/api/notifications", "/panel/api"]) {
      expect(await dispatch(url)).toBeUndefined();
    }
    expect(await dispatch("/panel/app/index.html")).toBeUndefined();
    expect(await dispatch("/panel/app/", "POST")).toBeUndefined();
  });

  it("preserves the nine page destinations and compatibility page contracts", () => {
    const destinations = [
      ["/panel/app/", "dashboard"],
      ["/panel/app/chat", "chat"],
      ["/panel/app/conversations", "conversations"],
      ["/panel/app/clients", "clients"],
      ["/panel/app/agenda", "agenda"],
      ["/panel/app/kb", "kb"],
      ["/panel/app/automation-rules", "automation-rules"],
      ["/panel/app/settings", "settings"],
      ["/panel/app/projects", "projects"],
    ] as const;

    for (const [pathname, view] of destinations) {
      expect(parsePanelPath(pathname).view).toBe(view);
      expect(pathForView(view)).toBe(pathname);
    }
    expect(parsePanelPath("/panel/app/cases")).toEqual({ view: "conversations", conversationTab: "case" });
    expect(parsePanelPath("/panel/app/advanced-dashboard").view).toBe("advanced-dashboard");
  });
});
