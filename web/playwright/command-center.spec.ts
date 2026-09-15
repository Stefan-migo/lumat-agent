import { expect, test, type Page } from "@playwright/test";

const user = { id: 1, username: "admin", role: "admin" };
const message = (id: number, content: string, status: "processed" | "failed") => ({
  id,
  thread_id: 7,
  author: "admin" as const,
  content,
  status,
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

async function stubBackend(page: Page) {
  await page.route("**/panel/ws", (route) => route.abort());
  await page.route("**/panel/api/**", async (route) => {
    const url = new URL(route.request().url());
    let body: unknown;
    if (url.pathname === "/panel/api/me") body = user;
    else if (url.pathname === "/panel/api/notifications") body = { notifications: [] };
    else if (url.pathname === "/panel/api/assistant/capabilities") body = { tools: [{ name: "read", description: "Read-only fixture", read_only: true, write: false }], personas: ["assistant"], prompts: ["default"], kb_available: true, memory_available: true };
    else if (url.pathname === "/panel/api/chat/threads" && route.request().method() === "GET") body = { threads: [{ id: 7, title_or_preview: "Fixture conversation", updated_at: "2026-09-15T12:00:00Z", status: "active", run_status: "approval_pending", approval_status: "pending" }] };
    else if (url.pathname === "/panel/api/chat/threads" && route.request().method() === "POST") body = thread;
    else if (url.pathname === "/panel/api/chat/threads/7") body = thread;
    else if (url.pathname === "/panel/api/conversations") body = { items: [{ id: 9, customer_id: 1, wa_phone: "+56911111111", state: "bot", responsible_id: null, version: 1, summary: "Emergency fixture", latest_inbound_at: "2026-09-15T12:00:00Z", reply_window_open: true, delivery_summary: { failed: 0, pending: 0, sending: 0, sent: 0, unknown: 0 }, last_message_at: "2026-09-15T12:00:00Z", created_at: "2026-09-15T11:00:00Z", closed_at: null, customer: { id: 1, name: "Fixture customer", phone_e164: "+56911111111" }, case: { id: 44, service: "Emergency", priority: "high", status: "open", emergency: true, summary: "Emergency fixture", acknowledged_at: null }, case_id: 44, emergency: true, acknowledged_at: null, case_status: "open", case_priority: "high", captured_data: null }], total: 1, offset: 0, limit: 20, counts: { all: 1, human: 0, emergency: 1, case: 1, closed: 0 } };
    else body = {};
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });
}

async function openCommandCenter(page: Page, width: number) {
  await page.setViewportSize({ width, height: 900 });
  await stubBackend(page);
  await page.goto("chat");
  await expect(page.locator("#command-center-conversation")).toBeVisible();
  await expect(page.getByText("Persisted context")).toBeVisible();
}

test.describe("Command Center narrow browser contract", () => {
  test("keeps desktop zones ordered and contained", async ({ page }) => {
    await openCommandCenter(page, 1024);
    const zones = page.locator(".command-center > [data-zone]");
    await expect(zones).toHaveCount(3);
    const boxes = await zones.evaluateAll((elements) => elements.map((element) => {
      const box = element.getBoundingClientRect();
      return { left: box.left, right: box.right, visible: getComputedStyle(element).display !== "none" };
    }));
    expect(boxes.every((box) => box.visible)).toBe(true);
    expect(boxes[0].left).toBeLessThan(boxes[1].left);
    expect(boxes[1].left).toBeLessThan(boxes[2].left);
    expect(await page.locator(".command-center").evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
    // The navigator zone must be populated from the bounded list seam at desktop,
    // not merely present: an empty navigator still renders "in order" but is not scannable.
    await expect(page.locator("#command-center-navigator").getByRole("button", { name: /fixture conversation/i })).toBeVisible();
  });

  test("uses one compact zone at 390px and allows keyboard tab switching", async ({ page }) => {
    await openCommandCenter(page, 390);
    await expect(page.locator(".command-center")).toHaveAttribute("data-tier", "compact");
    await expect(page.locator(".command-center [data-zone][data-zone-active='true']")).toHaveCount(1);
    const contextTab = page.getByRole("tab", { name: "Read-only execution context" });
    await contextTab.focus();
    await contextTab.press("Enter");
    await expect(contextTab).toHaveAttribute("aria-selected", "true");
    await expect(page.locator("#command-center-context")).toBeVisible();
    await expect(page.locator("#command-center-conversation")).toBeHidden();
  });

  test("uses the distinct tablet tier at 768px and switches zones with keyboard only", async ({ page }) => {
    await openCommandCenter(page, 768);
    await expect(page.locator(".command-center")).toHaveAttribute("data-tier", "tablet");
    await expect(page.locator(".command-center [data-zone][data-zone-active='true']")).toHaveCount(1);
    const navigatorTab = page.getByRole("tab", { name: "Thread navigator" });
    await navigatorTab.focus();
    await navigatorTab.press("Enter");
    await expect(navigatorTab).toHaveAttribute("aria-selected", "true");
    await expect(page.locator("#command-center-navigator")).toBeVisible();
    await expect(page.locator("#command-center-conversation")).toBeHidden();
  });

  test("enters focus mode by keyboard, exposes Escape, and restores focus", async ({ page }) => {
    await openCommandCenter(page, 1024);
    const trigger = page.getByRole("button", { name: "Entrar en modo foco" });
    await trigger.focus();
    await trigger.press("Enter");
    await expect(page.getByRole("button", { name: "Salir del modo foco" })).toBeVisible();
    await expect(page.locator("#panel-shell-sidebar")).toHaveAttribute("aria-hidden", "true");
    await expect(page.getByRole("button", { name: "Salir del modo foco" })).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("button", { name: "Entrar en modo foco" })).toBeFocused();
    await expect(page.locator("#panel-shell-sidebar")).not.toHaveAttribute("aria-hidden", "true");
  });

  for (const width of [390, 768, 1024]) {
    test(`keeps critical actions reachable at ${width}px`, async ({ page }) => {
      await openCommandCenter(page, width);
      if (width < 1024) {
        await page.getByRole("tab", { name: "Conversation zone" }).focus();
        await page.getByRole("tab", { name: "Conversation zone" }).press("Enter");
      }
      await expect(page.getByRole("button", { name: "Enviar" })).toBeVisible();
      await expect(page.getByRole("button", { name: "Aprobar" })).toBeVisible();
      await expect(page.getByRole("button", { name: "Reintentar" })).toBeVisible();
      const conversations = page.getByRole("button", { name: "Conversaciones" }).first();
      await expect(conversations).toBeVisible();
      await conversations.click();
      await expect(page.getByRole("button", { name: "Reconocer emergencia" })).toBeVisible();
    });
  }
});
