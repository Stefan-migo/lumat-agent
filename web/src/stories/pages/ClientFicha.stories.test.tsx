import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { ClientFichaView } from "./ClientFicha.stories";
import { clients } from "./_shared/mockData/clients";
import {
  caseStatusLabel,
  caseStatusTone,
  conversationLabel,
  customerStateLabel,
  customerStateTone,
  directionLabel,
} from "./_shared/toneMaps";

/** Uses customer id 1 (Marcela Fuentes — real entry from clients.ts). */
const customer = clients[0];

// The ficha history cases (mirrors ClientFicha.stories.tsx historyCases).
const historyCasesStatuses = ["escalado", "cerrado"];

describe("ClientFicha page story (R-PRD-PG-6)", () => {
  it("renders the ficha header with customer name + phone (PageHeader)", () => {
    render(<ClientFichaView />);
    expect(
      screen.getByRole("heading", { name: `Ficha: ${customer.name}` }),
    ).toBeInTheDocument();
    expect(screen.getByText(customer.phone_e164!)).toBeInTheDocument();
  });

  it("renders the state Badge with the customerStateTone tone and customerStateLabel", () => {
    render(<ClientFichaView />);
    const badge = screen.getByText(customerStateLabel(customer.state), {
      selector: "[data-tone]",
    });
    expect(badge.getAttribute("data-tone")).toBe(customerStateTone(customer.state));
  });

  it("renders consent status and muted email/comuna/address/created", () => {
    render(<ClientFichaView />);
    expect(
      screen.getByText(customer.consent_status ? "Consentimiento: Sí" : "Consentimiento: No"),
    ).toBeInTheDocument();
    expect(screen.getByText(customer.email!)).toBeInTheDocument();
    expect(screen.getByText(customer.comuna!)).toBeInTheDocument();
    expect(screen.getByText(customer.address!)).toBeInTheDocument();
    expect(screen.getByText(new RegExp(customer.created_at!.slice(0, 10)))).toBeInTheDocument();
  });

  it("renders the info FlashMessage", () => {
    render(<ClientFichaView />);
    expect(screen.getByText(/Estado actualizado el/)).toBeInTheDocument();
  });

  it("renders the state-form Card: Select with 4 approved Spanish states + save button", () => {
    render(<ClientFichaView />);
    const combo = screen.getByRole("combobox", { name: /estado/i });
    const options = within(combo).getAllByRole("option");
    // Approved Spanish labels, never raw keys (DS-UI-LABELS / DESIGN_SYSTEM §Clientes).
    expect(options.map((o) => o.textContent)).toEqual(
      ["nuevo", "activo", "inactivo", "bloqueado"].map((s) => customerStateLabel(s)),
    );
    expect(screen.getByRole("button", { name: /guardar estado/i })).toBeInTheDocument();
  });

  it("renders the notes Card with author + timestamp + textarea + Add", () => {
    render(<ClientFichaView />);
    expect(screen.getByText(/Marcela Fuentes.*ago/)).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /nueva nota/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Agregar" })).toBeInTheDocument();
  });

  it("renders the customer_memo distinctly from staff notes (CR-7)", () => {
    render(<ClientFichaView />);
    expect(screen.getByRole("heading", { name: "Memo del cliente" })).toBeInTheDocument();
    expect(
      screen.getByText(/acta del cierre: cliente pidio recalcular el presupuesto/),
    ).toBeInTheDocument();
    // The memo card is separate from the notes card heading
    expect(screen.getByRole("heading", { name: "Notas" })).toBeInTheDocument();
  });

  it("shows an empty memo surface without error when there is no memo yet (CR-7)", () => {
    render(<ClientFichaView memo="" />);
    expect(screen.getByRole("heading", { name: "Memo del cliente" })).toBeInTheDocument();
    expect(screen.getByText("Todavía no hay memo para este cliente.")).toBeInTheDocument();
  });

  it("renders the three history DataTables (conversations / cases / messages)", () => {
    render(<ClientFichaView />);
    const tables = screen.getAllByRole("table");
    expect(tables.length).toBeGreaterThanOrEqual(3);
    for (const header of ["Historial", "Conversaciones", "Casos", "Mensajes"]) {
      expect(screen.getByRole("heading", { name: header })).toBeInTheDocument();
    }
  });
});

describe("ClientFicha case rows (DS-UI-TONEFIX)", () => {
  it("renders every case status with caseStatusTone, never customerStateTone", () => {
    render(<ClientFichaView />);
    // Find all case-status badges by their approved Spanish label.
    for (const status of historyCasesStatuses) {
      const labels = caseStatusLabel(status);
      const badge = screen.getAllByText(labels);
      // At least one case-row badge renders for each status with the case tone.
      expect(badge.length).toBeGreaterThan(0);
      for (const el of badge) {
        expect(el.getAttribute("data-tone")).toBe(caseStatusTone(status));
        // The tone must come from the case map, not the customer map (DS-UI-TONEFIX).
        expect(el.getAttribute("data-tone")).not.toBe(customerStateTone(status));
      }
    }
  });

  it("does not leak the raw case status key on any non-technical surface", () => {
    render(<ClientFichaView />);
    // Raw keys would surface under the Estado header of the cases table.
    for (const status of historyCasesStatuses) {
      expect(screen.queryByText(status as string)).not.toBeInTheDocument();
      expect(screen.queryByText(caseStatusLabel(status))).not.toBeNull();
    }
  });
});

describe("ClientFicha history label maps (DS-UI-LABELS)", () => {
  it("renders conversation states via conversationLabel", () => {
    render(<ClientFichaView />);
    // Every history-conversation state must surface as its approved Spanish label.
    for (const conv of [
      { state: "bot" },
      { state: "human" },
      { state: "closed" },
    ]) {
      expect(getWithinAnyCell(conversationLabel(conv.state))).toBeTruthy();
    }
  });

  it("renders message directions via directionLabel", () => {
    render(<ClientFichaView />);
    expect(getWithinAnyCell(directionLabel("inbound"))).toBeTruthy();
    expect(getWithinAnyCell(directionLabel("outbound"))).toBeTruthy();
  });
});

describe("ClientFicha state form states (DS-UI-STATES)", () => {
  it("shows a saving state that disables the customer-state save button", () => {
    render(<ClientFichaView isSaving />);
    // Saving announces the async operation (role=status) and blocks duplicate
    // submission (button disabled) — DESIGN_SYSTEM §Button loading contract.
    expect(screen.getByText(/guardando/i)).toBeInTheDocument();
    const saveButton = screen.getByRole("button", { name: /guardar estado/i });
    expect(saveButton).toBeDisabled();
    // The state Select stays controllable while saving (input is preserved).
    expect(screen.getByRole("combobox", { name: /estado/i })).toBeEnabled();
  });
});

/** Returns true when `text` appears inside any table cell (history tables). */
function getWithinAnyCell(text: string) {
  let found = false;
  const tables = document.querySelectorAll("table");
  tables.forEach((t) => {
    const cellTexts = Array.from(t.querySelectorAll("td")).map((td) => td.textContent ?? "");
    if (cellTexts.some((c) => c.includes(text))) found = true;
  });
  return found;
}
