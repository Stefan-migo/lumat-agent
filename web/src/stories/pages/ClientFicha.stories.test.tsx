import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { ClientFichaView } from "./ClientFicha.stories";
import { clients } from "./_shared/mockData/clients";
import { customerStateTone } from "./_shared/toneMaps";

/** Uses customer id 1 (Marcela Fuentes — real entry from clients.ts). */
const customer = clients[0];

describe("ClientFicha page story (R-PRD-PG-6)", () => {
  it("renders the ficha header with customer name + phone (PageHeader)", () => {
    render(<ClientFichaView />);
    expect(
      screen.getByRole("heading", { name: `Ficha: ${customer.name}` }),
    ).toBeInTheDocument();
    expect(screen.getByText(customer.phone_e164!)).toBeInTheDocument();
  });

  it("renders the state Badge with the customerStateTone tone", () => {
    render(<ClientFichaView />);
    const badge = screen.getByText(customer.state, {
      selector: "[data-tone]",
    });
    expect(badge.getAttribute("data-tone")).toBe(customerStateTone(customer.state));
  });

  it("renders consent status and muted email/comuna/address/created", () => {
    render(<ClientFichaView />);
    expect(screen.getByText(customer.consent_status ? "Consentimiento: Sí" : "Consentimiento: No")).toBeInTheDocument();
    expect(screen.getByText(customer.email!)).toBeInTheDocument();
    expect(screen.getByText(customer.comuna!)).toBeInTheDocument();
    expect(screen.getByText(customer.address!)).toBeInTheDocument();
    expect(screen.getByText(new RegExp(customer.created_at!.slice(0, 10)))).toBeInTheDocument();
  });

  it("renders the info FlashMessage", () => {
    render(<ClientFichaView />);
    expect(screen.getByText(/Estado actualizado el/)).toBeInTheDocument();
  });

  it("renders the state-form Card: Select with 4 states + Change button", () => {
    render(<ClientFichaView />);
    const combo = screen.getByRole("combobox", { name: /Estado/i });
    const options = within(combo).getAllByRole("option");
    expect(options.map((o) => o.textContent)).toEqual(
      ["nuevo", "activo", "inactivo", "bloqueado"],
    );
    expect(screen.getByRole("button", { name: /Cambiar estado/i })).toBeInTheDocument();
  });

  it("renders the notes Card with author + timestamp + textarea + Add", () => {
    render(<ClientFichaView />);
    expect(screen.getByText(/Marcela Fuentes.*ago/)).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /Nueva nota/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Agregar" })).toBeInTheDocument();
  });

  it("renders the three history DataTables (conversations / cases / messages)", () => {
    render(<ClientFichaView />);
    const tables = screen.getAllByRole("table");
    expect(tables.length).toBeGreaterThanOrEqual(3);
    // header cells of each history table
    for (const header of ["Historial", "Conversaciones", "Casos", "Mensajes"]) {
      expect(screen.getByRole("heading", { name: header })).toBeInTheDocument();
    }
  });
});
