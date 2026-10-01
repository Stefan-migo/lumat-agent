import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { DashboardOverview, Desktop, Mobile, Tablet } from "./Dashboard.stories";

describe("Dashboard page story (R-PRD-PG-6)", () => {
  it("renders real KPI cards, motivos, and the window caption", () => {
    render(<DashboardOverview data={{ contacts: 12, motivos: [["consulta", 3]], derived: 2, visit_requests: 1, window_days: 7, window_start: "2026-08-18" }} />);
    expect(screen.getByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByText("Contactos")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("Derivados")).toBeInTheDocument();
    expect(screen.getByText("Solicitudes de visita")).toBeInTheDocument();
    expect(screen.getByText(/consulta/)).toBeInTheDocument();
    expect(screen.getByText("Actividad de los últimos 7 días · Desde 18 ago 2026")).toBeInTheDocument();
  });

  it("does not render fabricated deltas or the old activity feed", () => {
    render(<DashboardOverview data={{ contacts: 12, motivos: [], derived: 2, visit_requests: 1, window_days: 7, window_start: "2026-08-18" }} />);
    expect(screen.queryByText("Resolución autónoma")).not.toBeInTheDocument();
    expect(screen.queryByText("Tiempo de respuesta")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Actividad reciente" })).not.toBeInTheDocument();
  });

  it("keeps the owner override and urgent cases in the responsive dashboard stories", () => {
    render(<DashboardOverview />);
    expect(screen.queryByRole("button", { name: "Abrir Casos" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Rosa" })).toHaveTextContent("Urgente");
    expect(Desktop.parameters?.viewport).toEqual({ width: 1280, height: 900 });
    expect(Tablet.parameters?.viewport).toEqual({ width: 768, height: 1024 });
    expect(Mobile.parameters?.viewport).toEqual({ width: 390, height: 844 });
  });

  it.each([
    ["loading", "Cargando indicadores"],
    ["empty", "Aún no hay actividad en esta ventana"],
    ["stale", "Los datos pueden estar desactualizados"],
    ["partial-error", "No pudimos cargar toda la actividad"],
    ["fatal-error", "No pudimos cargar el panel"],
  ] as const)("renders the %s state via the shared StateMessage", (state, message) => {
    render(<DashboardOverview state={state} />);
    expect(screen.getByText(message)).toBeInTheDocument();
  });
});
