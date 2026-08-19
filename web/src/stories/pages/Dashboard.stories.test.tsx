import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { kpis } from "./_shared/mockData/dashboard";
import { DashboardOverview } from "./Dashboard.stories";

describe("Dashboard page story (R-PRD-PG-6)", () => {
  it("renders the page title", () => {
    render(<DashboardOverview />);
    expect(screen.getByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
  });

  it("renders the muted KPI window caption", () => {
    render(<DashboardOverview />);
    expect(
      screen.getByText(`KPI window: last ${kpis.window_days} days (${kpis.window_start})`),
    ).toBeInTheDocument();
  });

  it("renders the 3 KPI StatCards", () => {
    render(<DashboardOverview />);
    expect(screen.getByText("Contactos")).toBeInTheDocument();
    expect(screen.getByText("Derivados")).toBeInTheDocument();
    expect(screen.getByText("Solicitudes de visita")).toBeInTheDocument();
    expect(screen.getByText(String(kpis.contacts))).toBeInTheDocument();
    expect(screen.getByText(String(kpis.derived))).toBeInTheDocument();
    expect(screen.getByText(String(kpis.visit_requests))).toBeInTheDocument();
  });

  it("renders the Motivos table with every motivo row", () => {
    render(<DashboardOverview />);
    const table = screen.getByRole("table");
    for (const [service, count] of kpis.motivos) {
      // Scope each service to its own row (exact cell match) so the count
      // assertion cannot match a different cell (R3-001).
      const row = within(table).getByText(service, { exact: true }).closest("tr")!;
      expect(row).not.toBeNull();
      expect(within(row).getByText(String(count), { exact: true })).toBeInTheDocument();
    }
  });
});
