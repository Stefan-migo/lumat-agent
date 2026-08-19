import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { conversations } from "./_shared/mockData/conversations";
import { clients } from "./_shared/mockData/clients";
import { ConversationsListView, ConversationsListEmpty } from "./ConversationsList.stories";

const customerName = (customer_id: number): string =>
  clients.find((c) => c.id === customer_id)?.name ?? "—";

describe("ConversationsList page story (T4.3, R-PRD-PG-6)", () => {
  it("renders the page title 'Conversations'", () => {
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

    // State + Summary + Last message + Created (some conversations share the
    // same created/last_message date, so assert presence via getAllByText)
    expect(within(row).getByText(first.state)).toBeInTheDocument();
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

describe("ConversationsList Empty story", () => {
  it("renders the empty state with the expected message", () => {
    render(<ConversationsListEmpty />);
    expect(screen.getByText("No conversations found")).toBeInTheDocument();
  });
});
