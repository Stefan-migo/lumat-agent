import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ClientFicha } from "../../components/pages/ClientFicha";
import { ClientFichaView, NoMemo, ClientFichaCalendarFailure, ClientFichaLoading, ClientFichaError, ClientFichaDenied, UnansweredEmergency, ArchivedClientFicha } from "./ClientFicha.stories";
import { clients } from "./_shared/mockData/clients";
import type { ClientFichaResponse } from "../../types";

const customer = clients[0];
const fichaResponse: ClientFichaResponse = {
  customer,
  history: {
    conversations: [], cases: [], messages: [], messages_total: 0, appointments: [],
  },
    notes: [],
  users: [],
  memo: "Acta de cierre de Marcela",
  states: ["nuevo", "contactado", "pendiente", "agendado", "en_evaluacion", "finalizado", "cancelado", "postventa"],
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

  it("renders appointments and actionable integration failures", async () => {
    const user = userEvent.setup();
    const onRetryCalendar = vi.fn();
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200 }));

    render(<ClientFicha data={{
      ...fichaResponse,
      history: { ...fichaResponse.history, appointments: [failedCalendarAppointment] },
    }} memories={[]} onRetryCalendar={onRetryCalendar} />);
    expect(screen.getByRole("heading", { name: "Visitas" })).toBeInTheDocument();
    // The approved appointment label is "Reservada" (DS StatusBadge table).
    expect(screen.getByText("Reservada")).toBeInTheDocument();
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

describe("ClientFicha state matrix stories", () => {
  it("renders archived customers with an available restore action", async () => {
    const user = userEvent.setup();
    render(<ArchivedClientFicha />);
    expect(screen.getByText("Cliente archivado")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: `Acciones para ${customer.name}` }));
    expect(await screen.findByRole("menuitem", { name: "Restaurar" })).toBeInTheDocument();
  });

  it("renders the calendar-sync failure with its retry control", () => {
    render(<ClientFichaCalendarFailure />);

    expect(screen.getByRole("alert")).toHaveTextContent("No se pudo sincronizar el calendario");
    expect(screen.getByRole("button", { name: "Reintentar calendario" })).toBeInTheDocument();
  });

  it("shows acknowledge control for an unanswered emergency story", () => {
    render(<UnansweredEmergency />);
    expect(screen.getByText("Emergencia sin reconocer")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reconocer" })).toBeInTheDocument();
  });

  it("renders the loading state without a payload and without a request", () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    render(<ClientFichaLoading />);

    expect(screen.getByRole("heading", { name: "Cargando ficha" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /^Ficha:/ })).not.toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("keeps the last payload readable under a failed read", () => {
    render(<ClientFichaError />);

    expect(screen.getByRole("alert")).toHaveTextContent("No pudimos cargar la ficha");
    expect(screen.getByRole("heading", { name: `Ficha: ${customer.name}` })).toBeInTheDocument();
  });

  it("renders the denied state", () => {
    render(<ClientFichaDenied />);

    expect(screen.getByRole("alert")).toHaveTextContent("No tienes permiso para ver este panel");
  });

  it("composes the two regions and the shared data surfaces", () => {
    const { container } = render(<ClientFichaView />);

    expect(container.querySelector(".detail-region__rail")).not.toBeNull();
    expect(container.querySelector(".detail-region__main")).not.toBeNull();
    expect(container.querySelectorAll(".data-region").length).toBeGreaterThan(0);
  });
});
