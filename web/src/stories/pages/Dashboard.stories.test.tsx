import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { activity, kpis } from "./_shared/mockData/dashboard";
import { DashboardOverview } from "./Dashboard.stories";

/** Mirrors the Avatar primitive's initials derivation so the test asserts the
 *  visible initials (what the user sees) without coupling to the Avatar
 *  component's internals. Kept inline because the rule is local to the
 *  Avatar — duplicating it here is cheaper than exporting it (R3-003:
 *  accepted as-is; if Avatar's rule changes, update this helper in lockstep). */
const initials = (name: string) =>
  name
    .split(" ")
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

describe("Dashboard page story (R-PRD-PG-6)", () => {
  it("renders the hero greeting and subtitle, without a CTA", () => {
    render(<DashboardOverview />);
    expect(screen.getByRole("heading", { name: "Buen día, equipo Lumat" })).toBeInTheDocument();
    expect(screen.getByText("Actividad del agente en los últimos 7 días")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Nueva prueba" })).not.toBeInTheDocument();
  });

  it("renders every KPI card with label, value, and delta from the mock data", () => {
    render(<DashboardOverview />);
    for (const kpi of kpis) {
      // Scope each KPI by its label so cross-card assertions cannot collide.
      const card = screen.getByText(kpi.label).closest<HTMLElement>(".kpi")!;
      expect(card).not.toBeNull();
      const card_ = within(card);
      expect(card_.getByText(kpi.value)).toBeInTheDocument();
      expect(card_.getByText(kpi.delta)).toBeInTheDocument();
    }
  });

  it("renders the actividad reciente card with every event row (avatar initials, title, context, time)", () => {
    render(<DashboardOverview />);
    for (const row of activity) {
      // Scope each row by its unique title so cross-row assertions cannot collide.
      const listItem = screen.getByText(row.title).closest("li");
      expect(listItem).not.toBeNull();
      const row_ = within(listItem!);
      expect(row_.getByText(initials(row.name))).toBeInTheDocument();
      expect(row_.getByText(row.context)).toBeInTheDocument();
      expect(row_.getByText(row.time)).toBeInTheDocument();
    }
  });

  it.each([
    ["loading", "Cargando indicadores"],
    ["empty", "Aún no hay actividad en esta ventana"],
    ["stale", "Datos posiblemente desactualizados"],
    ["partial-error", "Una parte del panel no está disponible"],
    ["fatal-error", "No pudimos cargar el panel"],
  ] as const)("renders the %s state via the shared StateMessage", (state, message) => {
    render(<DashboardOverview state={state} />);
    expect(screen.getByText(message)).toBeInTheDocument();
  });
});
