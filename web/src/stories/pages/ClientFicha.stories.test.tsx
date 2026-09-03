import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ClientFicha } from "../../components/pages/ClientFicha";
import { ClientFichaView, NoMemo } from "./ClientFicha.stories";
import { clients } from "./_shared/mockData/clients";
import type { CustomerState } from "../../types";

const customer = clients[0];
const fichaResponse = {
  customer,
  history: {
    conversations: [], cases: [], messages: [], appointments: [], visit_history: [
      { id: 1, appointment_id: 4, action: "booked", status: "booked", to_status: "booked", actor: "oper", created_at: "2026-07-15T12:00:00Z" },
      { id: 2, appointment_id: 4, action: "cancelled", status: "cancelled", to_status: "cancelled", actor: "oper", created_at: "2026-07-15T13:00:00Z" },
    ],
  },
  notes: [],
  memo: "Acta de cierre de Marcela",
  states: ["nuevo", "activo", "inactivo", "bloqueado"] as CustomerState[],
};
const failedCalendarAppointment = {
  id: 4,
  service: "Reparación de calefón",
  customer_id: customer.id,
  case_id: 8,
  technician_id: 3,
  local_start: "2026-07-15T09:00:00",
  timezone: "America/Santiago",
  starts_at: "2026-07-15T12:00:00Z",
  ends_at: "2026-07-15T13:00:00Z",
  duration_minutes: 60,
  status: "booked",
  calendar_status: "error",
  calendar_error: "Calendar provider unavailable.",
};
const memoriesResponse = {
  memories: [{
    id: 11,
    scope: "customer",
    entity_id: String(customer.id),
    tipo: "preference" as const,
    titulo: "Horario",
    contenido: "Prefiere contacto por la tarde.",
    topic_key: "contacto",
    pin: false,
    status: "active" as const,
    created_at: null,
    updated_at: null,
  }],
};

beforeEach(() => vi.restoreAllMocks());

describe("ClientFicha page", () => {
  it("renders the ficha sections and customer memories from the API", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => new Response(
      JSON.stringify(String(input).endsWith("/memories") ? memoriesResponse : fichaResponse),
      { status: 200 },
    ));

    render(<ClientFicha customerId={customer.id} />);
    expect(screen.getByRole("heading", { name: "Cargando ficha" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("heading", { name: `Ficha: ${customer.name}` })).toBeInTheDocument());
    expect(screen.getByRole("heading", { name: "Memo del cliente" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Memorias del cliente" })).toBeInTheDocument();
    expect(screen.getByText("Prefiere contacto por la tarde.")).toBeInTheDocument();
    expect(screen.getByText("Acta de cierre de Marcela")).toBeInTheDocument();
  });

  it("renders the no-memo state without an error surface", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => new Response(
      JSON.stringify(String(input).endsWith("/memories") ? { memories: [] } : { ...fichaResponse, memo: "" }),
      { status: 200 },
    ));

    render(<ClientFicha customerId={customer.id} />);
    await waitFor(() => expect(screen.getByText("Todavía no hay memo para este cliente.")).toBeInTheDocument());
    expect(screen.getByText("Sin memorias todavía")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("preserves story wrappers for populated and no-memo variants", () => {
    render(<><ClientFichaView /><NoMemo /></>);
    expect(screen.getAllByRole("heading", { name: "Ficha: Marcela Fuentes" })).toHaveLength(2);
    expect(screen.getByText("Todavía no hay memo para este cliente.")).toBeInTheDocument();
  });

  it("renders chronological visit lifecycle and actionable integration failures", async () => {
    const user = userEvent.setup();
    const onRetryCalendar = vi.fn();
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200 }));

    render(<ClientFicha data={{
      ...fichaResponse,
      history: { ...fichaResponse.history, appointments: [failedCalendarAppointment] },
    }} memories={[]} onRetryCalendar={onRetryCalendar} />);
    expect(screen.getByRole("heading", { name: "Visitas" })).toBeInTheDocument();
    expect(screen.getAllByText(/Agendada/)).toHaveLength(2);
    expect(screen.getByText(/Cancelada/)).toBeInTheDocument();
    expect(screen.getByText("Historial de visitas ordenado cronológicamente")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toContainElement(screen.getByRole("heading", { name: "No se pudo sincronizar el calendario" }));
    await user.click(screen.getByRole("button", { name: "Reintentar calendario" }));
    await waitFor(() => expect(onRetryCalendar).toHaveBeenCalledWith(4));
    expect(fetchMock).toHaveBeenCalledWith("/panel/api/appointments/4/calendar/sync", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
    });
  });
});
