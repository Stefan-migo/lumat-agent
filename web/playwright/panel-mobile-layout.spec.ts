import { expect, test, type Page } from "@playwright/test";

// Mobile layout regression probes for the project-detail tabs.
// - The tab bar must keep its own height on mobile: `.tabs` is a column flexbox
//   and, with `overflow` on the tablist, it used to shrink (20px) under a tall
//   panel and paint content over the labels.
// - A skills row must keep a wide copy column; the chips move to their own line.
const projectDetail = {
  project: {
    id: 1,
    slug: "test",
    name: "Proyecto Test",
    purpose: "Probar la vista móvil del detalle del proyecto.",
    status: "active",
    created_at: null,
    updated_at: null,
    config: {
      instructions: "Trabaja con el contexto del proyecto.",
      tool_policy: { opt_in_enabled: [] },
      skills: [{ name: "resumen-operativo", description: "Resume el estado del proyecto para el equipo.", body: "## Cuerpo" }],
    },
  },
};

async function stubBackend(page: Page) {
  await page.route("**/panel/ws", (route) => route.abort());
  await page.route("**/panel/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let body: unknown = {};
    if (path === "/panel/api/me") body = { id: 1, username: "admin", role: "admin" };
    else if (path === "/panel/api/notifications") body = { notifications: [] };
    else if (path === "/panel/api/projects") body = { projects: [projectDetail.project] };
    else if (path === "/panel/api/assistant/capabilities") body = { tools: [], personas: [], prompts: [], kb_available: true, memory_available: true };
    else if (path === "/panel/api/skills") body = { skills: [{ name: "catalogo-global", description: "Entrada global de prueba", scope: "global", body: "## Cuerpo global" }] };
    else if (path === "/panel/api/projects/test") body = projectDetail;
    else if (path.startsWith("/panel/api/projects/test/files")) body = { files: [] };
    else if (path.startsWith("/panel/api/projects/test/folders")) body = { folders: [] };
    else if (path.startsWith("/panel/api/projects/test/agents")) body = { agents: [], latest_run: null };
    else if (path === "/panel/api/chat/threads") body = { threads: [] };
    else if (path === "/panel/api/chat/active-runs") body = { active_runs: [] };
    else if (path === "/panel/api/clients") body = { clients: [] };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });
}

const MOBILE = { width: 390, height: 844 };

test.describe("Project detail mobile layout", () => {
  test("the embedded Contexto tab bar keeps its height and does not paint over the first card", async ({ page }) => {
    await page.setViewportSize(MOBILE);
    await stubBackend(page);
    await page.goto("chat?context=test");

    const tablist = page.locator('.projects-page--embedded .tabs [role="tablist"]');
    const card = page.locator(".projects-page--embedded .tabs__panel .card").first();
    await expect(tablist).toBeVisible();
    await expect(card).toBeVisible();

    const bar = (await tablist.boundingBox())!;
    const cardBox = (await card.boundingBox())!;
    expect(bar.height).toBeGreaterThanOrEqual(44);
    expect(cardBox.y).toBeGreaterThanOrEqual(bar.y + bar.height - 1);
  });

  test("a skills row keeps a wide copy column and moves the chips to their own line", async ({ page }) => {
    await page.setViewportSize(MOBILE);
    await stubBackend(page);
    await page.goto("chat?context=test");
    await page.getByRole("tab", { name: "Skills" }).click();

    const copy = page.locator(".project-skills__copy").first();
    const meta = page.locator(".project-skills__meta").first();
    await expect(copy).toBeVisible();

    const copyBox = (await copy.boundingBox())!;
    const metaBox = (await meta.boundingBox())!;
    expect(copyBox.width).toBeGreaterThan(150);
    expect(metaBox.y).toBeGreaterThanOrEqual(copyBox.y + copyBox.height - 2);
  });

  test("no tabbed route collapses its tab bar at 390px", async ({ page }) => {
    await page.setViewportSize(MOBILE);
    await stubBackend(page);

    for (const route of ["settings", "clients", "projects/test"]) {
      await page.goto(route);
      await page.waitForTimeout(400);
      const bars = page.locator('[role="tablist"]');
      const count = await bars.count();
      for (let index = 0; index < count; index += 1) {
        const bar = bars.nth(index);
        if (!(await bar.isVisible())) continue;
        const box = (await bar.boundingBox())!;
        expect(box.height, `${route} tablist #${index}`).toBeGreaterThanOrEqual(44);
      }
    }
  });
});
