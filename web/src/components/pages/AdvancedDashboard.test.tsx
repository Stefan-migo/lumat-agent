import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
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
});
