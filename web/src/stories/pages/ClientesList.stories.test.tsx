import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { clients as customers } from "./_shared/mockData/clients";
import { customerStateTone } from "./_shared/toneMaps";
import { ClientesListView, ClientesListEmpty } from "./ClientesList.stories";

describe("ClientesList page story (R-PRD-PG-6)", () => {
  it("renders the page title", () => {
    render(<ClientesListView />);
    expect(screen.getByRole("heading", { name: "Clientes" })).toBeInTheDocument();
  });

  it("renders the SearchInput-pattern search control", () => {
    render(<ClientesListView />);
    expect(screen.getByRole("searchbox", { name: "Buscar clientes" })).toBeInTheDocument();
  });

  it("renders the Export CSV secondary action", () => {
    render(<ClientesListView />);
    expect(screen.getByRole("link", { name: "Exportar CSV" })).toBeInTheDocument();
  });

  it("renders the customer table with R-PRD-PG-6 fields", () => {
    render(<ClientesListView />);
    const table = screen.getByRole("table");
    const first = customers[0];

    // Name → ficha link (scope the row for unambiguous field lookups)
    const nameLink = within(table).getByRole("link", { name: first.name! });
    expect(nameLink.getAttribute("href")).toContain(String(first.id));
    const firstRow = nameLink.closest("tr")!;
    expect(firstRow).not.toBeNull();

    // Phone, state (tone-wired), consent, created
    expect(within(firstRow).getByText(first.phone_e164!)).toBeInTheDocument();
    const stateBadge = within(firstRow).getByText(first.state);
    expect(stateBadge.getAttribute("data-tone")).toBe(customerStateTone(first.state));

    const consentCell = within(firstRow).getByText(first.consent_status ? "Sí" : "No");
    expect(consentCell).toBeInTheDocument();
    expect(within(firstRow).getByText(new RegExp("^2026"))).toBeInTheDocument();
  });

  it("renders the Consent header", () => {
    render(<ClientesListView />);
    const table = screen.getByRole("table");
    expect(within(table).getByRole("columnheader", { name: "Consentimiento" })).toBeInTheDocument();
  });
});

describe("ClientesList Empty story", () => {
  it("renders the empty state with the expected message", () => {
    render(<ClientesListEmpty />);
    expect(screen.getByText("No customers found")).toBeInTheDocument();
  });
});
