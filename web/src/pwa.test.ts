import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { isCacheableAsset, isObsoleteCache, shouldRegisterPwa } from "./pwa";

describe("PWA shell", () => {
  it("ships install metadata and both required icon purposes", () => {
    const manifest = readFileSync("public/manifest.webmanifest", "utf8");
    const metadata = JSON.parse(manifest) as { display: string; icons: Array<{ purpose?: string; src: string }> };

    expect(metadata.display).toBe("standalone");
    expect(metadata.icons).toEqual(expect.arrayContaining([
      expect.objectContaining({ src: "/panel/brand/lumat-mark.png" }),
      expect.objectContaining({ purpose: expect.stringContaining("maskable") }),
    ]));
  });

  it("does not register on insecure contexts or unsupported browsers", () => {
    expect(shouldRegisterPwa({ protocol: "http:", serviceWorker: true })).toBe(false);
    expect(shouldRegisterPwa({ protocol: "https:", serviceWorker: false })).toBe(false);
    expect(shouldRegisterPwa({ protocol: "https:", serviceWorker: true })).toBe(true);
  });

  it("allows only public static assets and never API or session HTML", () => {
    expect(isCacheableAsset("https://panel.test/panel/assets/index-abc123.js")).toBe(true);
    expect(isCacheableAsset("https://panel.test/panel/brand/lumat-mark.png")).toBe(true);
    expect(isCacheableAsset("https://panel.test/panel/api/notifications")).toBe(false);
    expect(isCacheableAsset("https://panel.test/panel/api")).toBe(false);
    expect(isCacheableAsset("https://panel.test/panel/")).toBe(false);
    expect(isCacheableAsset("https://panel.test/panel/assets/app.js", "POST")).toBe(false);
  });

  it("replaces older shell versions without deleting the active cache", () => {
    expect(isObsoleteCache("lumat-shell-v0", "lumat-shell-v1")).toBe(true);
    expect(isObsoleteCache("lumat-shell-v1", "lumat-shell-v1")).toBe(false);
    expect(isObsoleteCache("other-cache", "lumat-shell-v1")).toBe(false);
  });
});
