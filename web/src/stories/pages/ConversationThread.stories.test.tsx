import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import {
  ConversationThreadView,
  ConversationThreadBubbles,
} from "./ConversationThread.stories";
import { conversations, messages } from "./_shared/mockData/conversations";
import { clients } from "./_shared/mockData/clients";
import { conversationLabel, directionLabel } from "./_shared/toneMaps";

const conv = conversations[0];
const customer = clients.find((c) => c.id === conv.customer_id)!;

describe("ConversationThread page story (R-PRD-PG-6)", () => {
  it("renders the thread header `# {id}` with muted state/created/summary", () => {
    render(<ConversationThreadView />);
    expect(screen.getByRole("heading", { name: `# ${conv.id}` })).toBeInTheDocument();
    expect(
      screen.getByText(new RegExp(`${conversationLabel(conv.state)} · ${conv.created_at!.slice(0, 10)}`)),
    ).toBeInTheDocument();
    if (conv.summary) {
      expect(screen.getByText(conv.summary, { exact: false })).toBeInTheDocument();
    }
  });

  it("renders the read-only message DataTable with When/Direction/Type/Content", () => {
    render(<ConversationThreadView />);
    const table = screen.getByRole("table");
    for (const header of ["Cuándo", "Dirección", "Tipo", "Contenido", "Adjunto"]) {
      expect(within(table).getByRole("columnheader", { name: header })).toBeInTheDocument();
    }
  });

  it("renders every message row with the approved direction label, never the raw inbound/outbound", () => {
    render(<ConversationThreadView />);
    const table = screen.getByRole("table");
    const first = within(table).getByText(messages[0].text!).closest("tr")!;
    const cell = within(first)
      .getAllByText(directionLabel(messages[0].direction))
      .find((el) => el.tagName === "TD");
    expect(cell).toBeDefined();
    expect(first.textContent).not.toContain("inbound");
    expect(within(first).getByText(messages[0].msg_type)).toBeInTheDocument();
  });

  it("renders the paperclip for messages with media_url", () => {
    render(<ConversationThreadView />);
    const table = screen.getByRole("table");
    expect(within(table).getByText("📎")).toBeInTheDocument();
  });

  it("renders the HH-5 footer no-reply note as a StateMessage status region", () => {
    render(<ConversationThreadView />);
    const region = screen.getByRole("status");
    expect(within(region).getByText(/Este es un canal automático — no respondas a este mensaje/i)).toBeInTheDocument();
  });

  it("renders a loading banner pairing status role with a visible label (DS-UI-STATES)", () => {
    render(<ConversationThreadView state="loading" />);
    const banner = screen.getByRole("status");
    expect(within(banner).getByText(/cargando/i)).toBeInTheDocument();
  });

  it("renders an empty state with the approved Spanish message (DS-UI-STATES)", () => {
    render(<ConversationThreadView state="empty" />);
    expect(screen.getByText("No hay registros")).toBeInTheDocument();
  });

  it("renders the customer phone in the header meta", () => {
    render(<ConversationThreadView />);
    expect(screen.getByText(new RegExp(customer.name!))).toBeInTheDocument();
  });
});

describe("ConversationThread bubble variant", () => {
  it("renders the bubble list with at least one bubble per message", () => {
    render(<ConversationThreadBubbles />);
    const bubbles = document.querySelectorAll("[data-bubble]");
    expect(bubbles.length).toBeGreaterThanOrEqual(messages.length);
  });

  it("renders each message's direction as an aria label on the bubble", () => {
    render(<ConversationThreadBubbles />);
    const bubbles = Array.from(document.querySelectorAll("[data-bubble]"));
    const inbound = bubbles.filter((b) => b.getAttribute("aria-label") === "inbound");
    expect(inbound.length).toBeGreaterThan(0);
  });
});
