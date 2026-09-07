import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AdvancedDashboard } from "./AdvancedDashboard";

describe("AdvancedDashboard", () => {
  it("renders operational metrics and zero-filled trend buckets", () => {
    render(<AdvancedDashboard data={{
      period: { start: "2026-08-01", end: "2026-08-04", timezone: "America/Santiago" },
      metrics: { contacts: 1, cases: 2, appointments: 0, notification_health: { delivered: 0, failed: 0 }, automation_outcomes: { matched: 0, skipped: 0 } },
      trend: [{ start: "2026-08-01", count: 0 }, { start: "2026-08-02", count: 2 }],
    }} />);
    expect(screen.getByRole("heading", { name: "Indicadores operacionales" })).toBeInTheDocument();
    expect(screen.getByText("Contactos")).toBeInTheDocument();
    expect(screen.getByText("Casos")).toBeInTheDocument();
    expect(screen.getByText("2026-08-02")).toBeInTheDocument();
  });

  it("renders an explicit empty state when every bucket is zero", () => {
    render(<AdvancedDashboard data={{ period: { start: "2026-08-01", end: "2026-08-04", timezone: "UTC" }, metrics: { contacts: 0, cases: 0, appointments: 0, notification_health: {}, automation_outcomes: {} }, trend: [{ start: "2026-08-01", count: 0 }] }} />);
    expect(screen.getByText("Sin actividad en este período")).toBeInTheDocument();
  });

  it("loads summary, trend, and drilldown resources for the live page", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const path = new URL(String(input), "http://localhost").pathname;
      const body = path.endsWith("/summary")
        ? { period: { start: "2026-08-01", end: "2026-08-04", timezone: "UTC" }, metrics: { contacts: 2, cases: 1, appointments: 0, notification_health: {}, automation_outcomes: {} } }
        : path.endsWith("/trend") ? { buckets: [{ start: "2026-08-01", count: 1 }] } : { rows: [] };
      return new Response(JSON.stringify(body), { status: 200 });
    });
    render(<AdvancedDashboard />);
    expect(await screen.findByText("Contactos")).toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([input]) => String(input)).filter((path) => path.includes("/panel/api/dashboard/")).map((path) => new URL(path, "http://localhost").pathname)).toEqual(expect.arrayContaining([
      "/panel/api/dashboard/summary", "/panel/api/dashboard/trend", "/panel/api/dashboard/drilldown",
    ]));
    fetchMock.mockRestore();
  });

  it("renders loading, denied, and generic error states without page data", () => {
    const { rerender } = render(<AdvancedDashboard state="loading" data={null} />);
    expect(screen.getByRole("status")).toHaveTextContent("Cargando indicadores operacionales");
    rerender(<AdvancedDashboard state="denied" data={null} />);
    expect(screen.getByRole("alert")).toHaveTextContent("No tienes permiso para ver este panel");
    rerender(<AdvancedDashboard state="error" data={null} />);
    expect(screen.getByRole("alert")).toHaveTextContent("No pudimos cargar los indicadores operacionales");
  });
});
