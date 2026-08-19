import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { casesData } from "./_shared/mockData/cases";
import { caseStatusTone } from "./_shared/toneMaps";
import { CasesListView, CasesListEmpty } from "./CasesList.stories";

describe("CasesList page story (T4.2, R-PRD-PG-6)", () => {
  it("renders the page title 'Cases (pending / escalated)'", () => {
    render(<CasesListView />);
    expect(screen.getByRole("heading", { name: "Cases (pending / escalated)" })).toBeInTheDocument();
  });

  it("renders a FlashMessage", () => {
    render(<CasesListView />);
    expect(document.querySelector(".flash-message")).toBeInTheDocument();
  });

  it("renders the case table with R-PRD-PG-6 fields (#, Customer, Service, Status, Summary, Emergency)", () => {
    render(<CasesListView />);
    const table = screen.getByRole("table");
    const first = casesData.cases[0];

    // # column
    const idCell = within(table).getByText(`#${first.id}`);
    expect(idCell).toBeInTheDocument();
    const row = idCell.closest("tr")!;
    expect(row).not.toBeNull();

    // Customer (name, linked)
    const customerLink = within(row).getByRole("link", { name: first.customer.name! });
    expect(customerLink.getAttribute("href")).toContain(String(first.customer.id));

    // Service + Summary
    expect(within(row).getByText(first.service)).toBeInTheDocument();
    expect(within(row).getByText(first.summary!)).toBeInTheDocument();

    // Status badge tone wired per caseStatusTone (disambiguate from the
    // status select option in the Actions cell — the badge carries data-tone)
    const statusBadge = within(row)
      .getAllByText(first.status)
      .find((el) => el.getAttribute("data-tone") === caseStatusTone(first.status));
    expect(statusBadge, "a status badge with the expected tone should render").toBeDefined();
  });

  it("renders the Emergency ⚠ indicator / acknowledged-by for every case", () => {
    render(<CasesListView />);
    const table = screen.getByRole("table");
    for (const c of casesData.cases) {
      const row = within(table).getByText(`#${c.id}`).closest("tr")!;
      if (c.emergency) {
        const cell = within(row).getByText(/⚠/);
        expect(cell).toBeInTheDocument();
        if (c.ack_by) {
          expect(within(row).getByText(new RegExp(`Reconocido por ${c.ack_by}`))).toBeInTheDocument();
        }
      } else {
        expect(within(row).queryByText(/⚠/)).not.toBeInTheDocument();
      }
    }
  });

  it("renders the Responsible column from users list", () => {
    render(<CasesListView />);
    const table = screen.getByRole("table");
    const first = casesData.cases[0];
    const row = within(table).getByText(`#${first.id}`).closest("tr")!;
    const responsible = casesData.users.find((u) => u.id === first.responsible_id);
    // Disambiguate the responsible cell (td) from the responsible option inside
    // the Actions select — match the element whose tag is the table cell.
    const cell = within(row)
      .getAllByText(responsible!.username)
      .find((el) => el.tagName === "TD");
    expect(cell).toBeDefined();
    expect(cell).toHaveTextContent(responsible!.username);
  });

  it("renders the Actions row with inline status + responsible Select and Update button", () => {
    render(<CasesListView />);
    const table = screen.getByRole("table");
    const row = within(table).getByText(`#${casesData.cases[0].id}`).closest("tr")!;

    const statusSelect = within(row).getByLabelText(/estado/i);
    expect(statusSelect.tagName).toBe("SELECT");
    expect(within(statusSelect).getByRole("option", { name: "abierto" })).toBeInTheDocument();

    const responsibleSelect = within(row).getByLabelText(/responsable/i);
    expect(responsibleSelect.tagName).toBe("SELECT");

    expect(within(row).getByRole("button", { name: "Actualizar" })).toBeInTheDocument();
  });

  it("shows an Acknowledge button for unanswered emergency cases only", () => {
    render(<CasesListView />);
    const table = screen.getByRole("table");
    for (const c of casesData.cases) {
      const row = within(table).getByText(`#${c.id}`).closest("tr")!;
      const ackButton = within(row).queryByRole("button", { name: "Reconocer" });
      const emergencyUnanswered = c.emergency && c.ack_by === null;
      if (emergencyUnanswered) {
        expect(ackButton).not.toBeNull();
      } else {
        expect(ackButton).toBeNull();
      }
    }
  });
});

describe("CasesList Empty story", () => {
  it("renders the empty state with the expected message", () => {
    render(<CasesListEmpty />);
    expect(screen.getByText("No cases found")).toBeInTheDocument();
  });
});
