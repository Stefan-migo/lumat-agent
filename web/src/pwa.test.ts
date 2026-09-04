import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { isCacheableAsset, isObsoleteCache, SERVICE_WORKER_PATH, shouldRegisterPwa } from "./pwa";

describe("PWA shell", () => {
  it("ships install metadata and both required icon purposes", () => {
    const manifest = readFileSync("public/manifest.webmanifest", "utf8");
    const metadata = JSON.parse(manifest) as {
      display: string;
      scope: string;
      start_url: string;
      icons: Array<{ purpose?: string; src: string }>;
    };

    expect(metadata.display).toBe("standalone");
    expect(metadata.start_url).toBe("/panel/app/");
    expect(metadata.scope).toBe("/panel/app/");
    expect(metadata.icons).toEqual(expect.arrayContaining([
      expect.objectContaining({ src: "/panel/app/brand/lumat-mark.png" }),
      expect.objectContaining({ purpose: expect.stringContaining("maskable") }),
    ]));
    expect(readFileSync("index.html", "utf8")).toContain('href="/panel/app/manifest.webmanifest"');
    expect(readFileSync("vite.config.ts", "utf8")).toContain("base: '/panel/app/'");
  });

  it("does not register on insecure contexts or unsupported browsers", () => {
    expect(shouldRegisterPwa({ protocol: "http:", serviceWorker: true })).toBe(false);
    expect(shouldRegisterPwa({ protocol: "https:", serviceWorker: false })).toBe(false);
    expect(shouldRegisterPwa({ protocol: "https:", serviceWorker: true })).toBe(true);
  });

  it("allows only public static assets and never API or session HTML", () => {
    expect(isCacheableAsset("https://panel.test/panel/app/assets/index-abc123.js")).toBe(true);
    expect(isCacheableAsset("https://panel.test/panel/app/brand/lumat-mark.png")).toBe(true);
    expect(isCacheableAsset("https://panel.test/panel/app/manifest.webmanifest")).toBe(true);
    expect(isCacheableAsset("https://panel.test/panel/api/notifications")).toBe(false);
    expect(isCacheableAsset("https://panel.test/panel/api")).toBe(false);
    expect(isCacheableAsset("https://panel.test/panel/app/")).toBe(true);
    expect(isCacheableAsset("https://panel.test/panel/app/index.html")).toBe(false);
    expect(isCacheableAsset("https://panel.test/panel/app/assets/app.js", "POST")).toBe(false);
  });

  it("replaces older shell versions without deleting the active cache", () => {
    expect(isObsoleteCache("lumat-shell-v0", "lumat-shell-v1")).toBe(true);
    expect(isObsoleteCache("lumat-shell-v1", "lumat-shell-v1")).toBe(false);
    expect(isObsoleteCache("other-cache", "lumat-shell-v1")).toBe(false);
  });

  it("registers the worker with the production subtree and scopes its cache", () => {
    expect(SERVICE_WORKER_PATH).toBe("/panel/app/sw.js");
    const worker = readFileSync("public/sw.js", "utf8");
    const registration = readFileSync("src/pwa.ts", "utf8");
    expect(worker).toContain('const SHELL_URL = "/panel/app/"');
    expect(registration).toContain('scope: "/panel/app/"');
    expect(worker).toContain('url.pathname.startsWith("/panel/app/assets/")');
    expect(worker).toContain('url.pathname.startsWith("/panel/api/")');
  });
});
