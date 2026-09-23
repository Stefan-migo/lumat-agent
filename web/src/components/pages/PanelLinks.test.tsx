import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ClientesList } from "./ClientesList";
import { ConversationsList } from "./ConversationsList";
import { CasesList } from "./CasesList";
import { AppShell } from "../domain/AppShell";
import type { User } from "../../types";

const productionSource = (directory: string): string[] => readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
  const path = join(directory, entry.name);
  if (entry.isDirectory()) return productionSource(path);
  return /\.(ts|tsx)$/.test(entry.name) && !entry.name.includes(".test.") ? [readFileSync(path, "utf8")] : [];
});

describe("panel production links", () => {
  it("contains no story helper imports or hash-based page links", () => {
    const source = productionSource(join(process.cwd(), "src/components/pages"));
    expect(source.some((file) => file.includes(["stories", "pages", "_shared"].join("/")))).toBe(false);
    expect(source.some((file) => /href=\{?`#\//.test(file))).toBe(false);
  });

  it("uses clean route paths for customer drill-down links", () => {
    render(<ClientesList data={[{ id: 7, name: "Cliente vivo", phone_e164: "+56911111111", email: null, comuna: null, address: null, state: "contactado", consent_status: true, consent_at: null, created_at: "2026-08-25" }]} state="ready" />);
    expect(screen.getByRole("link", { name: "Cliente vivo" })).toHaveAttribute("href", "/panel/app/clients/7");
  });

  it("hands conversation drill-downs to the route seam", async () => {
    const onOpenThread = vi.fn();
    render(<ConversationsList data={{ conversations: [{ id: 9, customer_id: 7, wa_phone: "+5697", state: "human", responsible_id: null, version: 1, summary: "Needs visit", latest_inbound_at: "2026-08-25", reply_window_open: false, delivery_summary: { pending: 0, sending: 0, sent: 0, failed: 0, unknown: 0 }, last_message_at: "2026-08-25", created_at: "2026-08-25", closed_at: null }] }} state="ready" onOpenThread={onOpenThread} />);
    screen.getByRole("button", { name: "Abrir conversación #9" }).click();
    expect(onOpenThread).toHaveBeenCalledWith(9);
  });

  it("keeps case customer links on the same route seam", () => {
    const onOpenClient = vi.fn();
    render(<CasesList data={{ cases: [{ id: 3, conversation_id: 9, customer_id: 7, created_at: "2026-08-25", service: "Gas", priority: "alta", status: "abierto", emergency: false, responsible_id: null, summary: "Needs visit", escalated_at: null, closed_at: null, acknowledged_at: null, ack_by: null, customer: { id: 7, name: "Cliente vivo", phone_e164: "+56911111111", email: null, comuna: null, address: null, state: "contactado", consent_status: true, consent_at: null, created_at: "2026-08-25" } }], users: [] }} state="ready" onOpenClient={onOpenClient} />);
    const link = screen.getByRole("link", { name: "Cliente vivo" });
    expect(link).toHaveAttribute("href", "/panel/app/clients/7");
    link.click();
    expect(onOpenClient).toHaveBeenCalledWith(7);
  });

  it.each(["/panel/app/kb", "/panel/app/settings"])("renders permission denial for an operador deep link at %s", async (path) => {
    window.history.replaceState({}, "", path);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ detail: "forbidden" }), { status: 403 }));
    const operador: User = { username: "vero", role: "operador" };
    render(<AppShell user={operador} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("No tienes permiso para ver este panel");
    vi.restoreAllMocks();
    window.history.replaceState({}, "", "/panel/app/");
  });

  it("renders permission denial for an operador deep link to users", async () => {
    window.history.replaceState({}, "", "/panel/app/users");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ detail: "forbidden" }), { status: 403 }));
    render(<AppShell user={{ username: "vero", role: "operador" }} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("No tienes permiso para ver este panel");
    expect(screen.queryByRole("button", { name: "Usuarios" })).not.toBeInTheDocument();
    vi.restoreAllMocks();
    window.history.replaceState({}, "", "/panel/app/");
  });
});
