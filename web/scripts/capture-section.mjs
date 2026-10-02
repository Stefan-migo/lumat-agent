import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

const routes = {
  dashboard: "/panel/app/",
  clientes: "/panel/app/clients",
  conversaciones: "/panel/app/conversations",
  agenda: "/panel/app/agenda",
  usuarios: "/panel/app/users",
  conocimiento: "/panel/app/kb",
  configuracion: "/panel/app/settings",
};
const viewports = {
  desktop: { width: 1280, height: 900 },
  tablet: { width: 768, height: 1024 },
  mobile: { width: 390, height: 844 },
};
const hiddenChrome = [
  "#panel-shell-sidebar",
  ".panel-shell__footer-nav",
  ".panel-shell__header-row",
];

const section = process.argv[2];
if (!Object.hasOwn(routes, section)) {
  console.error(`Unknown section slug${section ? `: ${section}` : ""}. Valid slugs: ${Object.keys(routes).join(", ")}`);
  process.exit(1);
}

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, "../..");
const git = (...args) => execFileSync("git", args, { cwd: repoRoot, encoding: "utf8" }).trim();
const commonDir = path.resolve(repoRoot, git("rev-parse", "--path-format=absolute", "--git-common-dir"));
const primaryRoot = path.dirname(commonDir);

// Render readiness: wait for fonts and for a layout that is stable across two animation frames,
// instead of a fixed delay that can capture a half-updated layout (review R3-001).
async function waitForStableLayout(page) {
  await page.evaluate(async () => {
    await document.fonts.ready;
    const nextFrame = () => new Promise((resolve) => requestAnimationFrame(() => resolve()));
    let previous = -1;
    for (let attempt = 0; attempt < 30; attempt += 1) {
      await nextFrame();
      await nextFrame();
      const current = document.body.scrollHeight;
      if (current === previous) return;
      previous = current;
    }
  });
}

async function credentials() {
  let username = process.env.PANEL_ADMIN_USERNAME;
  let password = process.env.PANEL_ADMIN_PASSWORD;
  if (!username || !password) {
    const envPath = path.join(primaryRoot, "infra/.env");
    let contents;
    try {
      contents = await readFile(envPath, "utf8");
    } catch {
      throw new Error("Missing PANEL_ADMIN_USERNAME/PANEL_ADMIN_PASSWORD and unable to read primary worktree infra/.env");
    }
    const values = Object.fromEntries(contents.split(/\r?\n/).flatMap((line) => {
      const match = line.match(/^\s*(?:export\s+)?(PANEL_ADMIN_USERNAME|PANEL_ADMIN_PASSWORD)\s*=\s*(.*?)\s*$/);
      if (!match) return [];
      let value = match[2];
      if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
        value = value.slice(1, -1);
      } else {
        value = value.replace(/\s+#.*$/, "");
      }
      return [[match[1], value]];
    }));
    username ||= values.PANEL_ADMIN_USERNAME;
    password ||= values.PANEL_ADMIN_PASSWORD;
  }
  if (!username || !password) throw new Error("Missing PANEL_ADMIN_USERNAME or PANEL_ADMIN_PASSWORD");
  return { username, password };
}

const baseUrl = process.env.CAPTURE_URL || "http://127.0.0.1:5173/panel/app/";
const outputDir = path.join(primaryRoot, "refs/current", section);
let browser;
try {
  const { username, password } = await credentials();
  await mkdir(outputDir, { recursive: true });
  browser = await chromium.launch({ channel: "chrome" });
  const page = await browser.newPage();
  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  const userField = page.getByLabel("Usuario");
  if (await userField.count()) {
    await userField.fill(username);
    await page.getByLabel("Contraseña").fill(password);
    await page.getByRole("button", { name: "Iniciar sesión" }).click();
  }
  try {
    await page.locator("#panel-shell-sidebar").waitFor({ state: "visible", timeout: 15000 });
  } catch {
    throw new Error("Login failed or panel shell did not load (expected #panel-shell-sidebar)");
  }
  const route = routes[section];
  const targetUrl = new URL(route, new URL(baseUrl).origin).href;
  try {
    await page.goto(targetUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#panel-shell-sidebar").waitFor({ state: "visible", timeout: 15000 });
    await page.waitForLoadState("networkidle", { timeout: 30000 });
    await waitForStableLayout(page);
  } catch (error) {
    throw new Error(`Navigation to ${route} failed: ${error.message}`);
  }
  await page.addStyleTag({ content: `${hiddenChrome.join(", ")} { display: none !important; }` });
  const files = {};
  for (const [name, viewport] of Object.entries(viewports)) {
    await page.setViewportSize(viewport);
    await page.waitForLoadState("networkidle", { timeout: 30000 });
    await waitForStableLayout(page);
    const filePath = path.join(outputDir, `${name}.png`);
    await page.screenshot({ path: filePath, fullPage: true });
    files[name] = { sha256: createHash("sha256").update(await readFile(filePath)).digest("hex") };
  }
  const manifest = {
    section,
    route,
    captured_at: new Date().toISOString(),
    app_commit: process.env.CAPTURE_APP_COMMIT || execFileSync("git", ["rev-parse", "HEAD"], { cwd: primaryRoot, encoding: "utf8" }).trim(),
    origin: new URL(baseUrl).origin,
    viewport: viewports,
    files,
    hidden_chrome: hiddenChrome,
  };
  await writeFile(path.join(outputDir, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
  console.log(outputDir);
} catch (error) {
  console.error(`Section capture failed: ${error.message}`);
  process.exitCode = 1;
} finally {
  await browser?.close();
}
