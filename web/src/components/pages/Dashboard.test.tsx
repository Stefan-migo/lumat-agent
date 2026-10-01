import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it, vi } from "vitest";
import { apiFetch, getDashboardToday, getDashboardTrend } from "../../api";
import { Dashboard } from "./Dashboard";

vi.mock("../../api", async () => {
  const actual = await vi.importActual<typeof import("../../api")>("../../api");
  return { ...actual, apiFetch: vi.fn(), getDashboardToday: vi.fn(), getDashboardTrend: vi.fn() };
});

const data = {
  contacts: 12,
  motivos: [["calefont", 3], ["visita", 1]] as [string, number][],
  derived: 2,
  visit_requests: 1,
  new_customers: 4,
  window_days: 7,
  window_start: "2026-09-03",
  trend: [{ start: "2026-09-03", count: 2 }, { start: "2026-09-04", count: 0 }],
  today: {
    tz: "America/Santiago",
    local_date: "2026-09-09",
    appointments_today: [{ id: 4, service: "visita", customer_name: "Ana", local_start: "10:00", starts_at: "2026-09-09T13:00:00Z", ends_at: "2026-09-09T14:00:00Z" }],
    unanswered_conversations: [{ id: 5, customer_name: "Pedro", last_message_at: "2026-09-09T12:00:00Z", state: "BOT" }],
    urgent_cases: [{ id: 6, customer_name: "Lucía", service: "calefont", summary: "No enciende", emergency: true, escalated_at: "2026-09-09T11:00:00Z" }],
  },
};

describe("Dashboard operational surface", () => {
  it("renders Hoy rows and navigates each row to its operational view", () => {
    const onNavigate = vi.fn();
    render(<Dashboard data={data} state="ready" role="admin" onNavigate={onNavigate} />);

    expect(screen.getByRole("heading", { name: "Hoy" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Ana/ }));
    fireEvent.click(screen.getByRole("button", { name: /Pedro/ }));
    fireEvent.click(screen.getByRole("button", { name: /Lucía/ }));
    expect(onNavigate).toHaveBeenNthCalledWith(1, "agenda");
    expect(onNavigate).toHaveBeenNthCalledWith(2, "conversations");
    expect(onNavigate).toHaveBeenNthCalledWith(3, "cases");
  });

  it("renders the responsive navigation shortcuts and assistant", () => {
    const onNavigate = vi.fn();
    render(<Dashboard data={data} state="ready" role="admin" onNavigate={onNavigate} />);
    expect(screen.getByText("Asistente Lumat")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Abrir asistente" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Accesos rápidos" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Abrir Configuración" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Abrir Casos" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Abrir Configuración" }));
    expect(onNavigate).toHaveBeenCalledWith("settings");
  });

  it("keeps role-specific shortcuts and renders the complete period block", () => {
    const { rerender } = render(<Dashboard data={data} state="ready" role="admin" />);
    expect(screen.queryByRole("button", { name: "Abrir Casos" })).not.toBeInTheDocument();
    expect(screen.getByText("Automatizaciones")).toBeInTheDocument();
    expect(screen.getByText("Contactos")).toBeInTheDocument();
    expect(screen.getByText("Nuevos clientes")).toBeInTheDocument();
    expect(screen.getByText("calefont")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByLabelText("Tendencia de contactos de 7 días")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Lucía" })).toHaveTextContent("Urgente");

    rerender(<Dashboard data={data} state="ready" role="operador" />);
    expect(screen.getByText("Asistente Lumat")).toBeInTheDocument();
    expect(screen.queryByText("Automatizaciones")).not.toBeInTheDocument();

    rerender(<Dashboard data={data} state="ready" role="tecnico" />);
    expect(screen.getByText("Asistente Lumat")).toBeInTheDocument();
    expect(screen.queryByText("Automatizaciones")).not.toBeInTheDocument();
  });

  it("renders a readable fallback when the API sends a null motivo", () => {
    // The API shipped this shape in production despite the published string type.
    const motivos = [["calefont", 3], [null, 1]] as unknown as [string, number][];
    render(<Dashboard data={{ ...data, motivos }} state="ready" role="admin" />);

    expect(screen.getByText("sin clasificar")).toBeInTheDocument();
    expect(screen.getByText("sin clasificar").closest(".dashboard__motivo")?.textContent).toBe("sin clasificar1");
  });

  it("adds footer links to the Hoy operations cards", () => {
    const onNavigate = vi.fn();
    render(<Dashboard data={data} state="ready" onNavigate={onNavigate} />);
    fireEvent.click(screen.getByRole("button", { name: "Ver agenda" }));
    fireEvent.click(screen.getByRole("button", { name: "Ver conversaciones" }));
    fireEvent.click(screen.getByRole("button", { name: "Ver casos" }));
    expect(onNavigate).toHaveBeenNthCalledWith(1, "agenda");
    expect(onNavigate).toHaveBeenNthCalledWith(2, "conversations");
    expect(onNavigate).toHaveBeenNthCalledWith(3, "cases");
    expect(screen.getByRole("button", { name: "Lucía" })).toHaveTextContent("Urgente");
  });

  it.each([
    ["loading", "Cargando indicadores"],
    ["empty", "Aún no hay actividad en esta ventana"],
    ["error", "No pudimos cargar el panel"],
    ["denied", "No tienes permiso para ver este panel"],
  ] as const)("renders the %s state", (state, message) => {
    render(<Dashboard state={state} />);
    expect(screen.getByText(message)).toBeInTheDocument();
  });

  it("keeps the fallback subtitle visible while loading", () => {
    render(<Dashboard state="loading" />);
    expect(screen.getByText("Actividad reciente del negocio")).toBeInTheDocument();
  });

  it.each([
    ["stale", "Los datos pueden estar desactualizados"],
    ["partial-error", "No pudimos cargar toda la actividad"],
    ["fatal-error", "No pudimos cargar el panel"],
  ] as const)("renders a distinct %s state", (state, message) => {
    render(<Dashboard state={state} />);
    expect(screen.getByText(message)).toBeInTheDocument();
  });

  it("keeps KPI data visible and does not render a failed today request as empty", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ ...data, today: undefined });
    vi.mocked(getDashboardToday).mockRejectedValue(new Error("today unavailable"));
    vi.mocked(getDashboardTrend).mockResolvedValue({ buckets: data.trend });

    render(<Dashboard />);

    await waitFor(() => expect(screen.getByText("No pudimos cargar toda la actividad")).toBeInTheDocument());
    expect(screen.getByText("Contactos")).toBeInTheDocument();
    expect(screen.queryByText("Aún no hay actividad en esta ventana")).not.toBeInTheDocument();
  });

  it("keeps the dashboard CSS contract aligned with the design system", () => {
    const css = readFileSync(join(process.cwd(), "src/components/primitives/primitives.css"), "utf8");
    expect(css).toMatch(/\.dashboard__card-ops\s*\{[^}]*border-radius:\s*var\(--radius-lg\)/s);
    expect(css).toMatch(/\.dashboard__card\s*\{[^}]*border-radius:\s*var\(--radius-lg\)/s);
    expect(css).toMatch(/\.dashboard__card--agent\s*\{[^}]*grid-column:\s*1\s*\/\s*-1/s);
    expect(css).toMatch(/\.dashboard__motivo\s*\{[^}]*background:\s*var\(--surface\)/s);
    expect(css).not.toMatch(/\.dashboard__section-head h2\s*\{[^}]*text-transform:\s*uppercase/s);
    expect(css).toMatch(/@media \(max-width:\s*63\.99rem\)[\s\S]*?\.dashboard__hoy\s*\{[^}]*grid-template-columns:\s*repeat\(2,/s);
    expect(css).toMatch(/@media \(max-width:\s*63\.99rem\)[\s\S]*?\.dashboard__grid\s*\{[^}]*grid-template-columns:\s*repeat\(2,/s);
  });
});
