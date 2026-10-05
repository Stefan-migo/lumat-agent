import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { cancelAppointment, closeAppointment, createCase, fetchCases, fetchClients, fetchTechnicians, listAppointments, rescheduleAppointment, retryCalendarSync } from "../../api";
import {
  AgendaPageStory,
  CancelConfirmation,
  CloseConfirmation,
  CreateVisit,
  Data,
  Empty,
  Error,
  Forbidden,
  KeyboardActions,
  Loading,
  Mobile,
  SectionEmpty,
  Stale,
  SyncFailure,
} from "./AgendaPage.stories";

vi.mock("../../api", () => ({
  cancelAppointment: vi.fn(),
  closeAppointment: vi.fn(),
  rescheduleAppointment: vi.fn(),
  listAppointments: vi.fn(),
  retryCalendarSync: vi.fn(),
  createCase: vi.fn(),
  fetchCases: vi.fn(),
  fetchClients: vi.fn(),
  fetchTechnicians: vi.fn(),
}));

describe("AgendaPage Storybook state matrix", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date("2026-09-05T12:00:00-04:00"));
    vi.mocked(listAppointments).mockResolvedValue({ appointments: [] });
  });

  afterEach(() => vi.useRealTimers());

  it("covers production-shaped lifecycle and independent sync data across register views", async () => {
    render(<AgendaPageStory data={Data.args?.data} state="ready" />);

    expect(screen.getByText("Mantención de calefón")).toBeInTheDocument();
    await userEvent.setup({ advanceTimers: vi.advanceTimersByTime }).click(screen.getByRole("tab", { name: "No activas" }));
    expect(screen.getByText("Cancelada")).toBeInTheDocument();
    expect(screen.getByText("Completada")).toBeInTheDocument();
    expect(screen.getAllByText("No asistió").length).toBeGreaterThan(0);
    expect(screen.getByText("Visita de diagnóstico")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /Acciones para/ })).toHaveLength(3);
    await userEvent.setup({ advanceTimers: vi.advanceTimersByTime }).click(screen.getByRole("tab", { name: "Activas" }));
    expect(screen.getByText("Calendario con error")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /Acciones para/ })).toHaveLength(1);
  });

  it.each([
    [Loading, "Cargando agenda"],
    [Empty, "No hay visitas"],
    [Error, "No pudimos cargar la agenda"],
    [Forbidden, "No tienes permiso para ver la agenda"],
    [Stale, "Datos posiblemente desactualizados"],
  ])("renders the %s recovery state", (story, label) => {
    render(<AgendaPageStory {...(story.args ?? {})} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("covers the cancel confirmation and sync retry paths", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    vi.mocked(cancelAppointment).mockResolvedValue({ ok: true, appointment: Data.args!.data![0] });
    vi.mocked(retryCalendarSync).mockResolvedValue({ ok: true, calendar: { status: "synced", error: null } });
    vi.mocked(listAppointments).mockResolvedValue({ appointments: Data.args!.data! });
    render(<AgendaPageStory data={Data.args?.data} state="ready" />);

    await user.click(screen.getByRole("button", { name: "Acciones para Mantención de calefón" }));
    await user.click(screen.getByRole("menuitem", { name: "Cancelar visita" }));
    const dialog = screen.getByRole("dialog", { name: "Cancelar visita" });
    expect(dialog.querySelector(".dialog__icon svg")).toBeInTheDocument();
    expect(dialog).toHaveTextContent("Indica el motivo de la cancelación de esta visita.");
    expect(dialog).toHaveTextContent("Camila Soto");
    expect(dialog).toHaveTextContent("Visita seleccionada");
    expect(dialog).toHaveTextContent("Esta acción no se puede revertir desde la agenda.");
    expect(within(dialog).getByLabelText("Motivo de cancelación")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Confirmar cancelación" }));
    await waitFor(() => expect(cancelAppointment).toHaveBeenCalled());

    await user.click(screen.getByRole("tab", { name: "No activas" }));
    await user.click(screen.getByRole("button", { name: "Acciones para Visita de diagnóstico" }));
    await user.click(screen.getByRole("menuitem", { name: "Reintentar calendario" }));
    await waitFor(() => expect(retryCalendarSync).toHaveBeenCalled());

    const { container: confirmationContainer } = render(<AgendaPageStory data={Data.args?.data} state="ready" />);
    await act(async () => {
      await CancelConfirmation.play?.({ canvasElement: confirmationContainer } as Parameters<NonNullable<typeof CancelConfirmation.play>>[0]);
    });
    expect(screen.getAllByRole("dialog", { name: "Cancelar visita" })).toHaveLength(1);
  });

  it("covers the outcome confirmation while preserving the appointment facts", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    vi.mocked(closeAppointment).mockResolvedValue({ ok: true, appointment: Data.args!.data![0] });
    vi.mocked(listAppointments).mockResolvedValue({ appointments: Data.args!.data! });
    render(<AgendaPageStory data={Data.args?.data} state="ready" />);
    expect(screen.getByText("Mantención de calefón")).toBeInTheDocument();
    expect(screen.getByText("Camila Soto")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Acciones para Mantención de calefón" }));
    await user.click(screen.getByRole("menuitem", { name: "Cerrar visita" }));
    const dialog = screen.getByRole("dialog", { name: "Cerrar visita" });
    expect(dialog.querySelector(".dialog__icon svg")).toBeInTheDocument();
    expect(dialog).toHaveTextContent("Camila Soto");
    expect(dialog).toHaveTextContent("Visita seleccionada");
    expect(dialog).toHaveTextContent("Este cierre no se puede revertir desde la agenda.");
    await user.click(screen.getByRole("button", { name: "Confirmar cierre" }));
    await waitFor(() => expect(closeAppointment).toHaveBeenCalledWith(1, "completed"));
    const { container: storyContainer } = render(<AgendaPageStory data={Data.args?.data} state="ready" />);
    await act(async () => {
      await CloseConfirmation.play?.({ canvasElement: storyContainer } as Parameters<NonNullable<typeof CloseConfirmation.play>>[0]);
    });
    expect(within(storyContainer).getByRole("dialog", { name: "Cerrar visita" })).toBeInTheDocument();
  });

  it("covers rescheduling while preserving appointment facts", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    vi.mocked(fetchTechnicians).mockResolvedValue({ technicians: [{ id: 30, username: "Luis" }] });
    vi.mocked(rescheduleAppointment).mockResolvedValue({ ok: true, appointment: {} });
    render(<AgendaPageStory data={Data.args?.data} state="ready" />);
    expect(screen.getByText("Camila Soto")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Acciones para Mantención de calefón" }));
    await user.click(screen.getByRole("menuitem", { name: "Reprogramar" }));
    const dialog = screen.getByRole("dialog", { name: "Reprogramar visita" });
    expect(dialog.querySelector(".dialog__icon svg")).toBeInTheDocument();
    expect(dialog).toHaveTextContent("Actualiza la fecha, el horario y el técnico asignado.");
    expect(within(dialog).getByRole("heading", { name: "Programación actual" })).toBeInTheDocument();
    expect(within(dialog).getByLabelText("Fecha")).toHaveValue("2026-09-05");
    expect(within(dialog).getByRole("button", { name: "Cancelar" })).toBeInTheDocument();
    expect(screen.getByText("Mantención de calefón")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Confirmar reprogramación" }));
    await waitFor(() => expect(rescheduleAppointment).toHaveBeenCalled());
  });

  it("covers the expanded create dialog and inline manual-case affordance", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    vi.mocked(fetchClients).mockResolvedValue({ clients: [{ id: 10, name: "Camila Soto" }] as never });
    vi.mocked(fetchCases).mockResolvedValue({ cases: [], users: [] });
    vi.mocked(fetchTechnicians).mockResolvedValue({ technicians: [{ id: 30, username: "Luis" }] });

    render(<AgendaPageStory {...(CreateVisit.args ?? {})} />);
    await user.click(screen.getByRole("button", { name: "Nueva visita" }));

    const dialog = await screen.findByRole("dialog", { name: "Nueva visita" });
    const form = dialog.querySelector(".agenda-create-form");
    expect(form).toBeInTheDocument();
    expect(form).not.toHaveAttribute("hidden");
    expect(form?.children.length).toBeGreaterThan(1);
    expect(screen.getByRole("combobox", { name: "Caso vinculado" })).toBeInTheDocument();
    await user.type(screen.getByRole("combobox", { name: "Caso vinculado" }), "Walk-in case");
    expect(screen.getByRole("option", { name: "Crear «Walk-in case»" })).toBeInTheDocument();
    expect(screen.getByLabelText("Servicio")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Crear visita" })).toBeInTheDocument();
    expect(createCase).not.toHaveBeenCalled();
  });

  it("does not render an empty Hoy section for an upcoming active visit", () => {
    render(<AgendaPageStory {...(SectionEmpty.args ?? {})} />);
    expect(screen.queryByRole("heading", { name: "Hoy", level: 2 })).not.toBeInTheDocument();
    expect(screen.getByText("Instalación de cocina")).toBeInTheDocument();
  });

  it("exposes keyboard and narrow viewport stories without inventing controls", () => {
    expect(KeyboardActions).toBeDefined();
    expect(Mobile.parameters?.viewport).toEqual({ defaultViewport: "mobile-compact" });
    expect(SyncFailure.parameters?.viewport).toEqual({ defaultViewport: "bp-sm" });
    expect(CancelConfirmation.play).toBeDefined();

    render(<AgendaPageStory data={Data.args?.data} state="ready" />);
    expect(screen.getByText("Mantención de calefón")).toBeInTheDocument();
    // Creation is the only control this page gained (agenda-booking); the guard keeps
    // asserting that edit, reschedule and availability are still not invented.
    expect(screen.getByRole("button", { name: "Nueva visita" })).toBeInTheDocument();
    expect(screen.queryByText(/editar|reagendar/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /editar|reagendar/i })).not.toBeInTheDocument();
  });
});
