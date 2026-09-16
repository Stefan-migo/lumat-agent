import { expect, test, type Page } from "@playwright/test";

const user = { id: 1, username: "admin", role: "admin" };
const now = Date.now();
const isoDaysAgo = (days: number) => new Date(now - days * 86400000).toISOString();
const calls: string[] = [];

const message = (id: number, content: string, status: "processed" | "failed") => ({
  id,
  thread_id: 7,
  author: "admin" as const,
  content,
  status,
  assistant_metadata: { run_id: "run-7" },
});

const thread = {
  thread: {
    id: 7,
    user_id: 1,
    status: "active",
    active_run_id: "run-7",
    current_plan: { tool: "send_reply", arguments: { text: "fixture" }, status: "pending", requires_approval: true },
    assistant_state: {
      stage: "approval_pending",
      approval: { token: "approval-token", status: "pending", tool: "send_reply" },
      events: [],
    },
  },
  messages: [message(1, "Persisted context", "processed"), message(2, "Retry me", "failed")],
  attachments: [],
};

const summaries = [
  { id: 7, title: "Conversación de hoy", created_at: isoDaysAgo(0), updated_at: isoDaysAgo(0) },
  { id: 8, title: "Consulta reciente", created_at: isoDaysAgo(3), updated_at: isoDaysAgo(3) },
  { id: 9, title: "Consulta anterior", created_at: isoDaysAgo(10), updated_at: isoDaysAgo(10) },
];

async function stubBackend(page: Page) {
  calls.length = 0;
  await page.route("**/panel/ws", (route) => route.abort());
  await page.route("**/panel/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const method = request.method();
    calls.push(`${method} ${url.pathname}`);

    let body: unknown = {};
    if (url.pathname === "/panel/api/me") body = user;
    else if (url.pathname === "/panel/api/notifications") body = { notifications: [] };
    else if (url.pathname === "/panel/api/assistant/capabilities") body = { tools: [], personas: [], prompts: [], kb_available: true, memory_available: true };
    else if (url.pathname === "/panel/api/chat/threads" && method === "GET") body = { threads: summaries };
    else if (url.pathname === "/panel/api/chat/threads" && method === "POST") body = thread;
    else if (url.pathname === "/panel/api/chat/threads/7" && method === "GET") body = thread;
    else if (url.pathname === "/panel/api/chat/threads/7/messages") body = { message: message(3, "Mensaje enviado", "processed") };
    else if (url.pathname === "/panel/api/chat/threads/7/approval") body = { status: "consumed", message: message(4, "Plan aprobado", "processed") };
    else if (url.pathname === "/panel/api/chat/threads/7/stream") {
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: `data: ${JSON.stringify({ type: "plan", thread_id: 7, run_id: "run-7", sequence: 0, plan: { tool: "send_reply", status: "pending" } })}\n\n`,
      });
      return;
    } else if (url.pathname === "/panel/api/planning/sessions") body = { session: { slug: "tema", topic: "tema", status: "active" } };
    else if (url.pathname.includes("/attachments")) body = { attachment: { id: 10, filename: "fixture.txt" } };
    else if (url.pathname === "/panel/api/chat/threads/8" || url.pathname === "/panel/api/chat/threads/9") body = thread;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });
}

async function openChat(page: Page, width = 1024, withThread = true) {
  await page.setViewportSize({ width, height: 900 });
  await stubBackend(page);
  await page.goto(withThread ? "chat?thread_id=7" : "chat");
  await expect(page.locator(".assistant-chat__conversation")).toBeVisible();
  if (withThread) await expect(page.getByText("Persisted context")).toBeVisible();
}

test.describe("Assistant browser contract", () => {
  test("desktop centers one conversation and replaces the old zone tablist", async ({ page }) => {
    await openChat(page);
    const column = page.locator(".assistant-chat__conversation");
    const box = await column.boundingBox();
    const sidebar = await page.locator("#panel-shell-sidebar").boundingBox();
    expect(box).not.toBeNull();
    expect(sidebar).not.toBeNull();
    expect(box!.width).toBeLessThanOrEqual(768);
    const contentCenter = (sidebar!.x + sidebar!.width + 1024) / 2;
    expect(Math.abs(box!.x + box!.width / 2 - contentCenter)).toBeLessThan(20);
    await expect(page.getByRole("tablist")).toHaveCount(0);
    await expect(page.locator(".command-center [data-zone]")).toHaveCount(0);
  });

  test("history groups threads and context is closed until disclosed", async ({ page }) => {
    await openChat(page, 1200, false);
    await expect(page.getByRole("button", { name: "Historial" })).toBeVisible();
    await expect(page.getByRole("complementary", { name: "Contexto" })).toHaveCount(0);
    await page.getByRole("button", { name: "Historial" }).click();
    const popover = page.getByRole("dialog", { name: "Historial" });
    await expect(popover).toBeVisible();
    for (const label of ["Hoy", "Últimos 7 días", "Anteriores"]) await expect(popover.getByRole("heading", { name: label })).toBeVisible();
    await expect(popover.getByText("Consulta reciente")).toBeVisible();
    await expect(popover.getByText(/Hace|Hoy|\d/).first()).toBeVisible();
    await page.getByRole("button", { name: "Contexto" }).click();
    await expect(page.getByRole("complementary", { name: "Contexto" })).toBeVisible();
    await expect(page.getByText("Solo lectura")).toBeVisible();
  });

  test("navigator rename and delete dialogs cancel without requests", async ({ page }) => {
    await openChat(page, 1200, false);
    await page.getByRole("button", { name: "Historial" }).click();
    const rename = page.getByRole("button", { name: /Renombrar Conversación de hoy/ });
    await rename.click();
    await expect(page.getByRole("dialog", { name: "Renombrar conversación" })).toBeVisible();
    const beforeRename = calls.filter((call) => call.startsWith("PATCH")).length;
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog", { name: "Renombrar conversación" })).toHaveCount(0);
    expect(calls.filter((call) => call.startsWith("PATCH")).length).toBe(beforeRename);

    await page.getByRole("button", { name: "Historial" }).click();
    await page.getByRole("button", { name: /Eliminar Conversación de hoy/ }).click();
    await expect(page.getByRole("dialog", { name: "Eliminar conversación" })).toBeVisible();
    const beforeDelete = calls.filter((call) => call.startsWith("DELETE")).length;
    await page.getByRole("button", { name: "Cancelar" }).click();
    await expect(page.getByRole("dialog", { name: "Eliminar conversación" })).toHaveCount(0);
    expect(calls.filter((call) => call.startsWith("DELETE")).length).toBe(beforeDelete);
  });

  for (const width of [390, 768]) {
    test(`reflows at ${width}px without overflow while preserving actions`, async ({ page }) => {
      await openChat(page, width);
      await expect(page.locator("body")).toHaveJSProperty("scrollWidth", width);
      for (const control of [
        page.getByRole("button", { name: "Enviar" }),
        page.getByLabel("Adjuntar archivo"),
        page.getByRole("button", { name: "Planificar" }),
        page.getByRole("button", { name: "Aprobar" }).last(),
        page.getByRole("button", { name: "Reintentar mensaje" }),
      ]) {
        await control.scrollIntoViewIfNeeded();
        await expect(control).toBeVisible();
      }
    });
  }

  test("preserves send, approval, retry, attachment, and planning paths", async ({ page }) => {
    await openChat(page);
    const composer = page.getByRole("textbox", { name: "Mensaje" });
    await composer.fill("Consulta de prueba");
    await page.getByRole("button", { name: "Enviar" }).click();
    await expect.poll(() => calls.filter((call) => call === "POST /panel/api/chat/threads/7/messages").length).toBe(1);

    await page.getByRole("button", { name: "Aprobar" }).last().click();
    await expect.poll(() => calls.filter((call) => call === "POST /panel/api/chat/threads/7/approval").length).toBe(1);
    await page.getByRole("button", { name: "Reintentar mensaje" }).click();
    await expect.poll(() => calls.filter((call) => call === "POST /panel/api/chat/threads/7/messages").length).toBe(2);
    await expect(composer).toHaveValue("");
    await page.getByLabel("Adjuntar archivo").setInputFiles({ name: "fixture.txt", mimeType: "text/plain", buffer: Buffer.from("fixture") });
    await expect.poll(() => calls.filter((call) => call === "POST /panel/api/chat/threads/7/attachments").length).toBe(1);

    await page.getByRole("button", { name: "Planificar" }).click();
    const dialog = page.getByRole("dialog", { name: "Tema de planificación" });
    await expect(dialog).toBeVisible();
    await dialog.getByRole("button", { name: "Iniciar planificación" }).click();
    await expect(dialog.getByRole("alert")).toHaveText("Ingresa un tema para continuar.");
    expect(calls.filter((call) => call === "POST /panel/api/planning/sessions")).toHaveLength(0);
    await dialog.locator("#planning-topic").fill("  tema  ");
    await dialog.getByRole("button", { name: "Iniciar planificación" }).click();
    await expect.poll(() => calls.filter((call) => call === "POST /panel/api/planning/sessions").length).toBe(1);
  });

  test("keeps visible focus, 200% actions, and reduced motion semantics", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await openChat(page, 1024);
    for (const control of [page.getByRole("textbox", { name: "Mensaje" }), page.getByRole("button", { name: "Historial" }), page.getByRole("button", { name: "Contexto" })]) {
      await control.focus();
      await expect(control).toBeFocused();
    }
    await page.evaluate(() => { document.documentElement.style.zoom = "2"; });
    await page.getByRole("button", { name: "Contexto" }).scrollIntoViewIfNeeded();
    await expect(page.getByRole("button", { name: "Contexto" })).toBeVisible();
    const reducedMotionAnimation = await page.evaluate(() => {
      const stream = document.createElement("p");
      stream.className = "assistant-chat__stream";
      const cursor = document.createElement("span");
      stream.append(cursor);
      document.body.append(stream);
      const animation = getComputedStyle(cursor).animationName;
      stream.remove();
      return animation;
    });
    expect(reducedMotionAnimation).toBe("none");
  });

  test("renders only localized states and generated conversation titles", async ({ page }) => {
    await openChat(page);
    const surface = await page.locator("body").innerText();
    for (const raw of ["open", "processing", "bot", "human"]) expect(surface).not.toMatch(new RegExp(`\\b${raw}\\b`, "i"));
    expect(surface).not.toMatch(/Thread #\d+/i);
  });
});
