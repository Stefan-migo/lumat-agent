import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { casesData } from "./_shared/mockData/cases";
import { caseStatusLabel, caseStatusTone } from "./_shared/toneMaps";
import { CasesListView, CasesListEmpty } from "./CasesList.stories";
import { CasesList } from "../../components/pages/CasesList";

describe("CasesList page story (T4.2, R-PRD-PG-6)", () => {
  it("renders the Spanish page title 'Casos'", () => {
    render(<CasesListView />);
    expect(screen.getByRole("heading", { name: "Casos" })).toBeInTheDocument();
  });

  it("renders an emergency banner via StateMessage pairing alert role with a visible label", () => {
    render(<CasesListView />);
    const alert = screen.getByRole("alert");
    expect(within(alert).getByText("Emergencias sin reconocer")).toBeInTheDocument();
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

    // Status badge: approved Spanish label wired per caseStatusTone
    // (disambiguate from the status select option in the Actions cell — the
    // badge carries data-tone)
    const statusLabel = caseStatusLabel(first.status);
    const statusBadge = within(row)
      .getAllByText(statusLabel)
      .find((el) => el.getAttribute("data-tone") === caseStatusTone(first.status));
    expect(statusBadge, "a status badge with the expected tone should render").toBeDefined();
  });

  it("renders each case's approved Spanish status label (triangulation)", () => {
    render(<CasesListView />);
    const table = screen.getByRole("table");
    // Cover a different status than the first row (e.g. abierto → "Abierto")
    const open = casesData.cases.find((c) => c.status === "abierto")!;
    const row = within(table).getByText(`#${open.id}`).closest("tr")!;
    const label = caseStatusLabel(open.status);
    const badge = within(row)
      .getAllByText(label)
      .find((el) => el.getAttribute("data-tone") === caseStatusTone(open.status));
    expect(badge, "the abierto badge should render the approved label").toBeDefined();
  });

  it("renders the Emergency status region for every case, never a raw ⚠ glyph alone", () => {
    render(<CasesListView />);
    const table = screen.getByRole("table");
    for (const c of casesData.cases) {
      const row = within(table).getByText(`#${c.id}`).closest("tr")!;
      if (c.emergency) {
        // The emergency cell announces via role=status + a visible label; the
        // raw "⚠ Reconocido por" text is replaced by the shared StateMessage.
        const regions = within(row).queryAllByRole("status");
        const emergencyRegion = regions.find((r) => /emergencia/i.test(r.textContent ?? ""));
        expect(emergencyRegion, "an emergency status region should render").toBeDefined();
        expect(within(emergencyRegion!).getByText("Emergencia")).toBeInTheDocument();
        if (c.ack_by) {
          expect(within(emergencyRegion!).getByText(new RegExp(`Reconocida por ${c.ack_by}`))).toBeInTheDocument();
        } else {
          expect(within(emergencyRegion!).getByText(/Sin reconocer/i)).toBeInTheDocument();
        }
      } else {
        const regions = within(row).queryAllByRole("status");
        expect(regions.some((r) => /emergencia/i.test(r.textContent ?? ""))).toBe(false);
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
    expect(within(statusSelect).getByRole("option", { name: "Abierto" })).toBeInTheDocument();

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

  it("renders a loading banner pairing status role with a visible label and spinner", () => {
    render(<CasesListView state="loading" />);
    const banner = screen.getByRole("status");
    expect(within(banner).getByText("Cargando casos")).toBeInTheDocument();
  });
});

describe("CasesList Empty story", () => {
  it("renders the empty state with the approved Spanish message", () => {
    render(<CasesListEmpty />);
    expect(screen.getByText("No hay registros")).toBeInTheDocument();
  });
});

describe("CasesList API behavior", () => {
  it("renders rows from the cases API response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(casesData), { status: 200 }),
    );

    render(<CasesList />);

    await waitFor(() => expect(screen.getByRole("table")).toBeInTheDocument());
    expect(screen.getByText(`#${casesData.cases[0].id}`)).toBeInTheDocument();
    expect(screen.getByText(casesData.cases[0].service)).toBeInTheDocument();
  });

  it("POSTs an update and refetches the cases list", async () => {
    const updated = { ...casesData.cases[0], status: "abierto" };
    const fetchMock = vi.spyOn(globalThis, "fetch");
    fetchMock
      .mockResolvedValueOnce(new Response(JSON.stringify(casesData), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true, case: updated }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ...casesData, cases: [updated, ...casesData.cases.slice(1)] }), { status: 200 }));

    render(<CasesList />);
    await waitFor(() => expect(screen.getByRole("table")).toBeInTheDocument());
    const row = screen.getByText(`#${updated.id}`).closest("tr")!;
    fireEvent.change(within(row).getByLabelText(/estado/i), { target: { value: "abierto" } });
    fireEvent.click(within(row).getByRole("button", { name: "Actualizar" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    expect(fetchMock.mock.calls[1][0]).toBe(`/panel/api/cases/${updated.id}/update`);
    expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body))).toEqual({
      status: "abierto",
      responsible_id: updated.responsible_id,
    });
    expect(fetchMock.mock.calls[2][0]).toBe("/panel/api/cases");
  });

  it("POSTs an acknowledgement and refetches the cases list", async () => {
    const acknowledged = { ...casesData.cases[0], ack_by: "operador" };
    const fetchMock = vi.spyOn(globalThis, "fetch");
    fetchMock
      .mockResolvedValueOnce(new Response(JSON.stringify(casesData), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true, case: acknowledged }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ...casesData, cases: [acknowledged, ...casesData.cases.slice(1)] }), { status: 200 }));

    render(<CasesList />);
    await waitFor(() => expect(screen.getByRole("table")).toBeInTheDocument());
    const row = screen.getByText(`#${acknowledged.id}`).closest("tr")!;
    fireEvent.click(within(row).getByRole("button", { name: "Reconocer" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    expect(fetchMock.mock.calls[1][0]).toBe(`/panel/api/cases/${acknowledged.id}/ack`);
    expect(fetchMock.mock.calls[1][1]?.method).toBe("POST");
    expect(fetchMock.mock.calls[2][0]).toBe("/panel/api/cases");
  });
});
