import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it, vi } from "vitest";
import { apiFetch, getDashboardToday, getDashboardTrend } from "../../api";
import { Dashboard } from "./Dashboard";

vi.mock("../../api", async () => {
  const actual = await vi.importActual<typeof import("../../api")>("../../api");
  const mockedApiFetch = vi.fn();
  return {
    ...actual,
    apiFetch: mockedApiFetch,
    getDashboardKpis: vi.fn((windowDays: number) => mockedApiFetch(`/panel/api/kpis?window_days=${windowDays}`)),
    getDashboardToday: vi.fn(),
    getDashboardTrend: vi.fn(),
  };
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
    appointments_today: [{ id: 4, service: "visita", customer_name: "Ana", local_start: "2026-09-09T10:00:00.000000", starts_at: "2026-09-09T13:00:00Z", ends_at: "2026-09-09T14:00:00Z" }],
    unanswered_conversations: [{ id: 5, customer_name: "Pedro", last_message_at: "2026-09-09T12:00:00Z", state: "BOT" }],
    urgent_cases: [{ id: 6, customer_id: 9, conversation_id: 77, customer_name: "Lucía", service: "calefont", summary: "No enciende", emergency: true, escalated_at: "2026-09-09T11:00:00Z" }],
  },
};

describe("Dashboard operational surface", () => {
  it("uses Dashboard as the page title", () => {
    render(<Dashboard data={data} state="ready" />);
    expect(screen.getByRole("heading", { level: 1, name: "Dashboard" })).toBeInTheDocument();
  });

  it("capitalises the weekday in the Hoy date chip", () => {
    render(<Dashboard data={data} state="ready" />);
    expect(screen.getByText("Miércoles, 9 de septiembre")).toBeInTheDocument();
  });

  it("labels the agenda operations card as Agenda de hoy", () => {
    render(<Dashboard data={data} state="ready" />);
    expect(screen.getByRole("heading", { level: 3, name: "Agenda de hoy" })).toBeInTheDocument();
  });

  it("formats today's appointment time in the payload timezone", () => {
    render(<Dashboard data={data} state="ready" />);
    expect(screen.getByText("10:00")).toBeInTheDocument();
    expect(screen.queryByText(data.today.appointments_today[0].local_start)).not.toBeInTheDocument();
  });

  it("orders the agenda row: customer name and time on the title line, service below", () => {
    render(<Dashboard data={data} state="ready" />);
    const agenda = screen.getByRole("heading", { level: 3, name: "Agenda de hoy" }).closest(".dashboard__card-ops") as HTMLElement;
    const row = agenda.querySelector(".dashboard__row") as HTMLElement;
    expect(row.querySelector(".dashboard__row__head > strong")).toHaveTextContent("Ana");
    expect(row.querySelector(".dashboard__row__head .dashboard__row__time")).toHaveTextContent("10:00");
    expect(row.querySelector("small")).toHaveTextContent("visita");
  });

  it("labels the activity section as Actividad del período", () => {
    render(<Dashboard data={data} state="ready" />);
    expect(screen.getByRole("heading", { level: 2, name: "Actividad del período" })).toBeInTheDocument();
  });

  it("formats the page subtitle date like the period caption", () => {
    render(<Dashboard data={data} state="ready" />);
    expect(screen.getByText("Actividad de los últimos 7 días · Desde 3 sept 2026")).toBeInTheDocument();
  });

  it("renders both reference empty-state messages when the chart has no data", () => {
    render(<Dashboard data={{ ...data, trend: [] }} state="ready" />);
    expect(screen.getByText("Sin contactos en este período")).toBeInTheDocument();
    expect(screen.getByText("La actividad aparecerá aquí cuando se registren contactos.")).toBeInTheDocument();
  });

  it("renders the chart empty state for zero-count buckets and keeps the total line", () => {
    const trend = Array.from({ length: 7 }, (_, index) => ({ start: `2026-09-${String(index + 3).padStart(2, "0")}`, count: 0 }));
    render(<Dashboard data={{ ...data, trend }} state="ready" />);
    expect(screen.getByText("0 contactos · 7 días")).toBeInTheDocument();
    expect(screen.getByText("Sin contactos en este período")).toBeInTheDocument();
    expect(screen.queryByText("lun")).not.toBeInTheDocument();
  });

  it("thins day labels for a 30-day trend while rendering every bar", () => {
    const trend = Array.from({ length: 30 }, (_, index) => ({ start: `2026-09-${String(index + 1).padStart(2, "0")}`, count: index + 1 }));
    const { container } = render(<Dashboard data={{ ...data, trend }} state="ready" />);

    expect(container.querySelectorAll(".dashboard__bar-col__day")).toHaveLength(6);
    expect(container.querySelectorAll(".dashboard__bar")).toHaveLength(30);
  });

  it("renders the period chart axis and footer alongside the motivos summary", () => {
    const { container } = render(<Dashboard data={data} state="ready" />);
    const chart = screen.getByLabelText("Tendencia de contactos de 7 días");

    expect(chart.querySelectorAll(".dashboard__plot__axis > span")).toHaveLength(5);
    expect(screen.getByText("Cada barra representa un día.")).toBeInTheDocument();
    expect(screen.getByText("3 sept – 4 sept 2026")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "Motivos de contacto" })).toBeInTheDocument();
    expect(screen.getByText("Ordenados por frecuencia")).toBeInTheDocument();
    expect(screen.getByText("2 contactos en el período")).toBeInTheDocument();
    expect(screen.getByText("calefont").closest(".dashboard__motivo")?.querySelector(".dashboard__motivo-count")).toHaveTextContent("3");
    expect(container.querySelectorAll(".dashboard__bar-col__value")).toHaveLength(0);
  });

  it("shows empty HOY metric counts in the card body without count chips", () => {
    const today = { ...data.today, unanswered_conversations: [], urgent_cases: [] };
    render(<Dashboard data={{ ...data, today }} state="ready" />);
    for (const [title, message] of [["Sin respuesta", "No hay conversaciones pendientes"], ["Urgentes", "No hay casos urgentes"]]) {
      const card = screen.getByRole("heading", { level: 3, name: title }).closest(".dashboard__card-ops");
      expect(card?.querySelector(".dashboard__card-ops__count")).not.toBeInTheDocument();
      expect(card?.querySelector(".dashboard__metric-value")).toHaveTextContent("0");
      expect(card).toHaveTextContent(message);
    }
    const agenda = screen.getByRole("heading", { level: 3, name: "Agenda de hoy" }).closest(".dashboard__card-ops");
    expect(agenda?.querySelector(".dashboard__card-ops__count")).toHaveTextContent("1");
  });

  it("shows non-empty HOY metric counts above their rows without count chips", () => {
    render(<Dashboard data={data} state="ready" />);
    for (const [title, count] of [["Sin respuesta", "1"], ["Urgentes", "1"]]) {
      const card = screen.getByRole("heading", { level: 3, name: title }).closest(".dashboard__card-ops");
      const metricContent = card?.querySelector(".dashboard__metric-content");
      expect(card?.querySelector(".dashboard__card-ops__count")).not.toBeInTheDocument();
      expect(metricContent?.firstElementChild).toHaveClass("dashboard__metric-value");
      expect(metricContent?.firstElementChild).toHaveTextContent(count);
      expect(metricContent?.lastElementChild).toHaveClass("dashboard__list");
      expect(metricContent?.querySelectorAll(".dashboard__list > li")).toHaveLength(1);
    }
  });

  it("caps unanswered and urgent HOY rows at three while keeping the true totals", () => {
    const today = {
      ...data.today,
      unanswered_conversations: Array.from({ length: 5 }, (_, index) => ({ id: index, customer_name: `Customer ${index}`, last_message_at: "2026-09-09T12:00:00Z", state: "BOT" })),
      urgent_cases: Array.from({ length: 4 }, (_, index) => ({ id: index, customer_id: index, conversation_id: null, customer_name: `Case ${index}`, service: "calefont", summary: "Urgent", emergency: true, escalated_at: "2026-09-09T11:00:00Z" })),
    };
    const { container } = render(<Dashboard data={{ ...data, today }} state="ready" />);

    for (const [title, total] of [["Sin respuesta", "5"], ["Urgentes", "4"]]) {
      const card = screen.getByRole("heading", { level: 3, name: title }).closest(".dashboard__card-ops");
      expect(card?.querySelector(".dashboard__metric-value")).toHaveTextContent(total);
      expect(card?.querySelectorAll(".dashboard__list > li")).toHaveLength(3);
    }
    expect(container.querySelectorAll(".dashboard__card-ops--danger .dashboard__row--urgent")).toHaveLength(3);
  });

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

  it("opens the real target for each urgent case row", () => {
    const onOpenRoute = vi.fn();
    const today = {
      ...data.today,
      urgent_cases: [
        { id: 6, customer_id: 9, conversation_id: 77, customer_name: "Lucía", service: "calefont", summary: "No enciende", emergency: true, escalated_at: "2026-09-09T11:00:00Z" },
        { id: 7, customer_id: 12, conversation_id: null, customer_name: "Mario", service: "caldera", summary: "Sin agua caliente", emergency: true, escalated_at: "2026-09-09T12:00:00Z" },
      ],
    };
    render(<Dashboard data={{ ...data, today }} state="ready" onOpenRoute={onOpenRoute} />);

    fireEvent.click(screen.getByRole("button", { name: /Lucía/ }));
    fireEvent.click(screen.getByRole("button", { name: /Mario/ }));

    expect(onOpenRoute).toHaveBeenNthCalledWith(1, { view: "conversations", conversationId: 77 });
    expect(onOpenRoute).toHaveBeenNthCalledWith(2, { view: "clients", clientId: 12, clientTab: "cases" });
  });

  it("renders urgent name and tag in the head with summary in its own line", () => {
    const { container } = render(<Dashboard data={data} state="ready" />);
    const urgentRow = container.querySelector(".dashboard__row--urgent");

    expect(urgentRow?.querySelector(".dashboard__row__head > strong")).toHaveTextContent("Lucía");
    expect(urgentRow?.querySelector(".dashboard__row__head .dashboard__tag")).toHaveTextContent("Urgente");
    expect(urgentRow?.querySelector("small.dashboard__row__summary")).toHaveTextContent("No enciende");
  });

  it("renders the responsive navigation shortcuts and assistant", () => {
    const onNavigate = vi.fn();
    render(<Dashboard data={data} state="ready" role="admin" onNavigate={onNavigate} />);
    expect(screen.getByText("Asistente Lumat")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Abrir asistente" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Accesos rápidos" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Abrir Configuración" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Abrir Automatizaciones" })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /^Abrir (Conversaciones|Clientes|Agenda|Configuración|Automatizaciones)$/ })).toHaveLength(5);
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
    expect(screen.getByText("calefont").closest(".dashboard__motivo")?.querySelector(".dashboard__motivo-count")).toHaveTextContent("3");
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

  it("refetches KPI and trend data when the activity period changes", async () => {
    vi.mocked(apiFetch).mockResolvedValue(data);
    vi.mocked(getDashboardToday).mockResolvedValue(data.today);
    vi.mocked(getDashboardTrend).mockResolvedValue({ buckets: data.trend });

    render(<Dashboard />);

    const selector = await screen.findByLabelText("Período de actividad");
    fireEvent.change(selector, { target: { value: "14" } });

    await waitFor(() => {
      expect(vi.mocked(apiFetch)).toHaveBeenLastCalledWith("/panel/api/kpis?window_days=14");
      expect(vi.mocked(getDashboardTrend)).toHaveBeenLastCalledWith(Intl.DateTimeFormat().resolvedOptions().timeZone, 14);
    });
    expect(screen.getByText("Desde el 3 sept 2026")).toBeInTheDocument();
    const period = screen.getByRole("combobox", { name: "Período de actividad" });
    expect(period).toHaveValue("14");
    expect(Array.from((period as HTMLSelectElement).options, (option) => option.textContent)).toEqual([
      "Últimos 7 días",
      "Últimos 14 días",
      "Últimos 30 días",
    ]);
    expect(screen.getByText("Desde el 3 sept 2026")).toBeInTheDocument();
  });

  it("keeps the dashboard CSS contract aligned with the design system", () => {
    const css = readFileSync(join(process.cwd(), "src/components/primitives/primitives.css"), "utf8");
    expect(css).toMatch(/\.dashboard__card-ops\s*\{[^}]*border-radius:\s*var\(--radius-lg\)/s);
    expect(css).toMatch(/\.dashboard__card\s*\{[^}]*border-radius:\s*var\(--radius-lg\)/s);
    expect(css).toMatch(/\.dashboard__card--agent\s*\{[^}]*grid-column:\s*1\s*\/\s*-1/s);
    expect(css).toMatch(/\.dashboard__motivo\s*\{[^}]*background:\s*var\(--brand-bg-elevated\)/s);
    expect(css).not.toMatch(/\.dashboard__section-head h2\s*\{[^}]*text-transform:\s*uppercase/s);
    expect(css).toMatch(/@media \(max-width:\s*63\.99rem\)[\s\S]*?\.dashboard__hoy\s*\{[^}]*grid-template-columns:\s*repeat\(2,/s);
    expect(css).toMatch(/@media \(max-width:\s*63\.99rem\)[\s\S]*?\.dashboard__grid\s*\{[^}]*grid-template-columns:\s*repeat\(2,/s);
  });
});
