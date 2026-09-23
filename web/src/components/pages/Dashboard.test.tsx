import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Dashboard } from "./Dashboard";

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
  it("renders HOY rows and navigates each row to its operational view", () => {
    const onNavigate = vi.fn();
    render(<Dashboard data={data} state="ready" role="admin" onNavigate={onNavigate} />);

    expect(screen.getByRole("heading", { name: "HOY" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Ana/ }));
    fireEvent.click(screen.getByRole("button", { name: /Pedro/ }));
    fireEvent.click(screen.getByRole("button", { name: /Lucía/ }));
    expect(onNavigate).toHaveBeenNthCalledWith(1, "agenda");
    expect(onNavigate).toHaveBeenNthCalledWith(2, "conversations");
    expect(onNavigate).toHaveBeenNthCalledWith(3, "cases");
  });

  it("splits bento navigation by role and renders the complete period block", () => {
    const { rerender } = render(<Dashboard data={data} state="ready" role="admin" />);
    expect(screen.getByText("Agente Lumat")).toBeInTheDocument();
    expect(screen.getByText("Automatizaciones")).toBeInTheDocument();
    expect(screen.getByText("Contactos")).toBeInTheDocument();
    expect(screen.getByText("Nuevos clientes")).toBeInTheDocument();
    expect(screen.getByText("calefont · 3")).toBeInTheDocument();
    expect(screen.getByLabelText("Tendencia de contactos de 7 días")).toBeInTheDocument();

    rerender(<Dashboard data={data} state="ready" role="operador" />);
    expect(screen.queryByText("Agente Lumat")).not.toBeInTheDocument();
    expect(screen.queryByText("Automatizaciones")).not.toBeInTheDocument();
  });

  it("renders a readable fallback when the API sends a null motivo", () => {
    // The API shipped this shape in production despite the published string type.
    const motivos = [["calefont", 3], [null, 1]] as unknown as [string, number][];
    render(<Dashboard data={{ ...data, motivos }} state="ready" role="admin" />);

    expect(screen.getByText("sin clasificar · 1")).toBeInTheDocument();
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
});
