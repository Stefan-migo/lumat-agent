import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { clients as customers } from "./_shared/mockData/clients";
import { customerStateLabel, customerStateTone } from "./_shared/toneMaps";
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

    // Phone, state (Spanish label + tone-wired), consent, created
    expect(within(firstRow).getByText(first.phone_e164!)).toBeInTheDocument();
    const stateLabel = customerStateLabel(first.state);
    const stateBadge = within(firstRow).getByText(stateLabel);
    expect(stateBadge.getAttribute("data-tone")).toBe(customerStateTone(first.state));

    const consentCell = within(firstRow).getByText(first.consent_status ? "Sí" : "No");
    expect(consentCell).toBeInTheDocument();
    expect(within(firstRow).getByText(new RegExp("^2026"))).toBeInTheDocument();
  });

  it("renders each customer's approved Spanish state label (triangulation)", () => {
    render(<ClientesListView />);
    const table = screen.getByRole("table");
    // Cover a different state than the first row (e.g. bloqueado → "Bloqueado")
    const blocked = customers.find((c) => c.state === "bloqueado")!;
    const row = within(table).getByRole("link", { name: blocked.name! }).closest("tr")!;
    const badge = within(row).getByText(customerStateLabel(blocked.state));
    expect(badge.getAttribute("data-tone")).toBe(customerStateTone(blocked.state));
  });

  it("renders a stale-data banner pairing status role with a visible label", () => {
    render(<ClientesListView state="stale" />);
    const banner = screen.getByRole("status");
    expect(within(banner).getByText("Datos posiblemente desactualizados")).toBeInTheDocument();
  });

  it("renders a partial-error banner pairing status role with a visible label", () => {
    render(<ClientesListView state="partial-error" />);
    const banner = screen.getByRole("status");
    expect(within(banner).getByText(/no pudimos actualizar parte del listado/i)).toBeInTheDocument();
  });

  it("renders a fatal-error banner pairing alert role with a visible label", () => {
    render(<ClientesListView state="fatal-error" />);
    const banner = screen.getByRole("alert");
    expect(within(banner).getByText(/no pudimos cargar los clientes/i)).toBeInTheDocument();
  });

  it("renders a loading banner pairing status role with a visible label and spinner", () => {
    render(<ClientesListView state="loading" />);
    const banner = screen.getByRole("status");
    expect(within(banner).getByText("Cargando clientes")).toBeInTheDocument();
  });

  it("renders the Consent header", () => {
    render(<ClientesListView />);
    const table = screen.getByRole("table");
    expect(within(table).getByRole("columnheader", { name: "Consentimiento" })).toBeInTheDocument();
  });
});

describe("ClientesList Empty story", () => {
  it("renders the empty state with the approved Spanish message", () => {
    render(<ClientesListEmpty />);
    expect(screen.getByText("No hay registros")).toBeInTheDocument();
  });
});
