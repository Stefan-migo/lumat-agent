import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { conversations, messages } from "./_shared/mockData/conversations";
import { clients } from "./_shared/mockData/clients";
import {
  InboxThreadView,
  isWithinReplyWindow,
} from "./InboxThread.stories";

const nowMs = Date.parse("2026-08-20T12:00:00-04:00");

const findByConvId = (id: number) => conversations.find((c) => c.id === id)!;

describe("isWithinReplyWindow pure helper (R-PRD-PG-10, T1.7)", () => {
  it("is true for a last_message_at within 24h of now", () => {
    const open = findByConvId(103); // last_message_at 2026-08-20T08:15
    expect(isWithinReplyWindow(open.last_message_at, nowMs)).toBe(true);
  });

  it("is false for a last_message_at older than 24h and for null", () => {
    const stale = findByConvId(105); // last_message_at 2026-08-10T14:30
    expect(isWithinReplyWindow(stale.last_message_at, nowMs)).toBe(false);
    expect(isWithinReplyWindow(null, nowMs)).toBe(false);
  });
});

describe("InboxThread composer + window (R-PRD-PG-9 / R-PRD-PG-10)", () => {
  it("render the message bubbles for the conversation (ConversationThreadBubbles pattern)", () => {
    const conv = findByConvId(101);
    render(<InboxThreadView conversation={conv} nowMs={nowMs} />);
    const convMsgs = messages.filter((m) => m.conversation_id === conv.id);
    const bubbles = document.querySelectorAll("[data-bubble]");
    expect(bubbles.length).toBeGreaterThanOrEqual(convMsgs.length);
    const firstIn = convMsgs.find((m) => m.direction === "inbound");
    const inBubble = Array.from(bubbles).find(
      (b) => b.getAttribute("aria-label") === "inbound",
    );
    expect(inBubble).toBeDefined();
    expect(within(screen.getByRole("heading", { name: `# ${conv.id}` }))).toBeTruthy();
  });

  it("ComposerEnabled: open-window notice + enabled Textarea and send Button", () => {
    const conv = findByConvId(103); // human, in-window
    render(<InboxThreadView conversation={conv} nowMs={nowMs} />);
    expect(screen.getByText(/ventana de respuesta abierta/i)).toBeInTheDocument();
    const textarea = screen.getByRole("textbox", { name: /escribe tu respuesta/i });
    expect(textarea).toBeEnabled();
    expect(screen.getByRole("button", { name: "Enviar" })).toBeEnabled();
  });

  it("ComposerDisabled(closed): closed-window notice + disabled composer (R-PRD-PG-10)", () => {
    const conv = findByConvId(102); // closed
    render(<InboxThreadView conversation={conv} nowMs={nowMs} />);
    // FlashMessage carries the long closed-window copy; the composer reason and
    // the flash may share the short phrase, so assert both present distinctly.
    expect(screen.getByText(/ya no se pueden enviar respuestas/i)).toBeInTheDocument();
    expect(screen.getAllByText(/fuera de la ventana de 24 horas/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("textbox", { name: /escribe tu respuesta/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Enviar" })).toBeDisabled();
  });

  it("ComposerDisabled(bot): bot-paused label + disabled composer (R-PRD-PG-9 S2)", () => {
    const conv = findByConvId(101); // bot, in-window
    render(<InboxThreadView conversation={conv} nowMs={nowMs} />);
    expect(screen.getByText(/bot pausado/i)).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /escribe tu respuesta/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Enviar" })).toBeDisabled();
  });
});

describe("InboxThread state controls (R-PRD-PG-9, T1.7)", () => {
  it("Tomar (take, bot->human) reveals Volver a bot and Cerrar", async () => {
    const user = userEvent.setup();
    const conv = findByConvId(101); // starts bot
    render(<InboxThreadView conversation={conv} nowMs={nowMs} />);
    expect(screen.getByRole("button", { name: "Tomar" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cerrar" })).toBeNull();

    await user.click(screen.getByRole("button", { name: "Tomar" }));

    expect(screen.getByRole("button", { name: "Cerrar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Volver a bot" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tomar" })).toBeNull();
  });

  it("Cerrar (human->closed) disables the composer; Volver a bot re-enables bot state", async () => {
    const user = userEvent.setup();
    const conv = findByConvId(103); // human
    render(<InboxThreadView conversation={conv} nowMs={nowMs} />);
    // Starts human + in-window -> enabled
    expect(screen.getByRole("button", { name: "Enviar" })).toBeEnabled();

    await user.click(screen.getByRole("button", { name: "Cerrar" }));
    expect(screen.getByRole("button", { name: "Enviar" })).toBeDisabled();
    expect(screen.getByText(/fuera de la ventana de 24 horas/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Volver a bot" }));
    expect(screen.getByRole("button", { name: "Enviar" })).toBeDisabled();
    expect(screen.getByText(/bot pausado/i)).toBeInTheDocument();
  });
});
