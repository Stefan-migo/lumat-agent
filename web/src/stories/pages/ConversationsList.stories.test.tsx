import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { conversations } from "./_shared/mockData/conversations";
import { clients } from "./_shared/mockData/clients";
import { users } from "./_shared/mockData/users";
import { statusTone } from "../../components/primitives/StatusBadge";
import { conversationLabel } from "./_shared/toneMaps";
import {
  ConversationsListView,
  ConversationsListEmpty,
  assigneeForConversation,
} from "./ConversationsList.stories";

const customerName = (customer_id: number): string =>
  clients.find((c) => c.id === customer_id)?.name ?? "—";

describe("ConversationsList page story (T4.3, R-PRD-PG-6)", () => {
  it("renders the Spanish page title 'Conversaciones'", () => {
    render(<ConversationsListView />);
    expect(screen.getByRole("heading", { name: "Conversaciones" })).toBeInTheDocument();
  });

  it("renders the conversation table with every conversation row", () => {
    render(<ConversationsListView />);
    const table = screen.getByRole("table");
    const first = conversations[0];

    // # column
    const idCell = within(table).getByText(`#${first.id}`);
    expect(idCell).toBeInTheDocument();
    const row = idCell.closest("tr")!;
    expect(row).not.toBeNull();

    // Customer name + muted phone (design D5)
    const nameLink = within(row).getByRole("link", { name: customerName(first.customer_id) });
    expect(nameLink.getAttribute("href")).toContain(String(first.customer_id));
    expect(within(row).getByText(first.wa_phone!)).toBeInTheDocument();

    // State badge with the design tone (disambiguate from the filter select
    // — match the element that carries data-tone). The badge renders the
    // approved Spanish label (DS-UI-LABELS), never the raw state.
    const stateBadge = within(row)
      .getAllByText(conversationLabel(first.state))
      .find((el) => el.getAttribute("data-tone") === statusTone[first.state as keyof typeof statusTone]);
    expect(stateBadge, "state should render as StatusBadge with the expected tone").toBeDefined();
    expect(within(row).getByText(first.summary!)).toBeInTheDocument();
    expect(within(row).getAllByText(first.last_message_at!.slice(0, 10))?.length).toBeGreaterThan(0);
    expect(within(row).getAllByText(first.created_at!.slice(0, 10))?.length).toBeGreaterThan(0);
  });

  it("renders the column headers (#, Customer, State, Summary, Last message, Created)", () => {
    render(<ConversationsListView />);
    const table = screen.getByRole("table");
    for (const header of ["#", "Cliente", "Estado", "Resumen", "Último mensaje", "Creada"]) {
      expect(within(table).getByRole("columnheader", { name: header })).toBeInTheDocument();
    }
  });

  it("renders every conversation in the mock", () => {
    render(<ConversationsListView />);
    const table = screen.getByRole("table");
    for (const c of conversations) {
      expect(within(table).getByText(`#${c.id}`)).toBeInTheDocument();
    }
  });
});

describe("ConversationsList state/assignee/filter (R-PRD-PG-8, T1.5)", () => {
  it("renders every conversation state as a StatusBadge with its approved label and tone", () => {
    render(<ConversationsListView />);
    const table = screen.getByRole("table");
    for (const c of conversations) {
      const row = within(table).getByText(`#${c.id}`).closest("tr")!;
      const badge = within(row)
        .getAllByText(conversationLabel(c.state))
        .find((el) => el.getAttribute("data-tone") === statusTone[c.state as keyof typeof statusTone]);
      expect(badge, `conversation ${c.id} state badge should render with data-tone`).toBeDefined();
    }
  });

  it("renders the assignee column from the users mock (design-only, R2/D3)", () => {
    render(<ConversationsListView />);
    const table = screen.getByRole("table");
    expect(within(table).getByRole("columnheader", { name: "Asignado" })).toBeInTheDocument();
    const usernames = new Set(users.map((u) => u.username));
    for (const c of conversations) {
      const row = within(table).getByText(`#${c.id}`).closest("tr")!;
      const label = assigneeForConversation(c);
      expect(within(row).getByText(label)).toBeInTheDocument();
      // A resolved assignee is always a real user from users.ts; unassigned shows "—".
      expect(label === "—" || usernames.has(label), `conversation ${c.id} assignee ${label}`).toBe(true);
    }
  });

  it("applies a warning leading treatment to human rows paired with the approved label, never color-only", () => {
    render(<ConversationsListView />);
    const table = screen.getByRole("table");
    for (const c of conversations) {
      const row = within(table).getByText(`#${c.id}`).closest("tr")!;
      const badge = within(row)
        .getAllByText(conversationLabel(c.state))
        .find((el) => el.getAttribute("data-tone") === statusTone[c.state as keyof typeof statusTone]);
      expect(badge, `conversation ${c.id} should render its approved state badge`).toBeDefined();
      if (c.state === "human") {
        // Meaning is never conveyed by color alone: the warning treatment pairs
        // with the approved "Atención humana" badge (data-tone warning).
        expect(badge!.getAttribute("data-tone")).toBe("warning");
      } else if (c.state in statusTone) {
        expect(badge!.getAttribute("data-tone")).not.toBe("warning");
      }
    }
  });

  it("renders a loading banner pairing status role with a visible label (DS-UI-STATES)", () => {
    render(<ConversationsListView state="loading" />);
    const banner = screen.getByRole("status");
    expect(within(banner).getByText(/cargando conversaciones/i)).toBeInTheDocument();
  });

  it("renders a stale banner pairing status role with a visible label (DS-UI-STATES)", () => {
    render(<ConversationsListView state="stale" />);
    const banner = screen.getByRole("status");
    expect(within(banner).getByText(/posiblemente desactualizados/i)).toBeInTheDocument();
  });

  it("renders an error banner pairing alert role with a visible label (DS-UI-STATES)", () => {
    render(<ConversationsListView state="fatal-error" />);
    const alert = screen.getByRole("alert");
    expect(within(alert).getByText(/no pudimos cargar/i)).toBeInTheDocument();
  });

  it("FilterByState=human narrows the table to human-state conversations only", () => {
    render(<ConversationsListView initialFilter="human" />);
    const table = screen.getByRole("table");
    const humanIds = new Set(conversations.filter((c) => c.state === "human").map((c) => c.id));
    const humanRows = Array.from(table.querySelectorAll("tbody tr"));
    expect(humanRows.length, "filtered table should not be empty").toBeGreaterThan(0);

    for (const c of conversations) {
      const row = within(table).queryByText(`#${c.id}`)?.closest("tr") ?? null;
      const isHuman = humanIds.has(c.id);
      if (isHuman) {
        expect(row, `human conversation ${c.id} should be present`).not.toBeNull();
      } else {
        expect(row, `non-human conversation ${c.id} must be filtered out`).toBeNull();
      }
    }
  });

  it("renders the filter-by-state select with approved Spanish labels, never raw keys (DS-UI-LABELS)", () => {
    render(<ConversationsListView />);
    const select = screen.getByLabelText("Filtrar por estado");
    expect(select.tagName).toBe("SELECT");
    const optionLabels = Array.from(select.querySelectorAll("option")).map((o) => o.textContent);
    for (const s of Object.keys(statusTone)) {
      expect(optionLabels).toContain(conversationLabel(s));
      expect(optionLabels).not.toContain(s); // raw bot/human/closed must NOT appear
    }
    expect(optionLabels).toContain("Todos");
  });
});

describe("ConversationsList Empty story", () => {
  it("renders the empty state with the approved Spanish message", () => {
    render(<ConversationsListEmpty />);
    expect(screen.getByText("No hay registros")).toBeInTheDocument();
    expect(screen.getByText(/No existen conversaciones para mostrar/i)).toBeInTheDocument();
  });
});
