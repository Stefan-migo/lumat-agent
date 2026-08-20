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

describe("ConversationsList page story (T4.3, R-PRD-PG-6)", () => {  it("renders the page title 'Conversations'", () => {
    render(<ConversationsListView />);
    expect(screen.getByRole("heading", { name: "Conversations" })).toBeInTheDocument();
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

  it("highlights human-state rows with the warning background (S1)", () => {
    render(<ConversationsListView />);
    const table = screen.getByRole("table");
    for (const c of conversations) {
      const row = within(table).getByText(`#${c.id}`).closest("tr")!;
      const humanRow = c.state === "human";
      if (humanRow) {
        expect(row.style.background).toBe("var(--warning-bg)");
      } else {
        expect(row.style.background).not.toBe("var(--warning-bg)");
      }
    }
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
});

describe("ConversationsList Empty story", () => {
  it("renders the empty state with the expected message", () => {
    render(<ConversationsListEmpty />);
    expect(screen.getByText("No conversations found")).toBeInTheDocument();
  });
});
