import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { cancelAppointment, listAppointments, retryCalendarSync } from "../../api";
import {
  AgendaPageStory,
  CancelConfirmation,
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
  listAppointments: vi.fn(),
  retryCalendarSync: vi.fn(),
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
    expect(screen.getByText("No asistió")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Reintentar calendario" })).toHaveLength(1);
    await userEvent.setup({ advanceTimers: vi.advanceTimersByTime }).click(screen.getByRole("tab", { name: "Activas" }));
    expect(screen.getByText("Calendario con error")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Reintentar calendario" })).toHaveLength(1);
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

    await user.click(screen.getByRole("button", { name: "Cancelar visita" }));
    expect(screen.getByRole("dialog", { name: "Cancelar visita de Camila Soto — Mantención de calefón" })).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toHaveTextContent("La visita se marcará como cancelada y esta agenda no ofrece volver a reservarla.");
    await user.click(screen.getByRole("button", { name: "Confirmar cancelación" }));
    await waitFor(() => expect(cancelAppointment).toHaveBeenCalled());

    const retry = screen.getAllByRole("button", { name: "Reintentar calendario" })[0];
    retry.focus();
    await user.keyboard("{Enter}");
    await waitFor(() => expect(retryCalendarSync).toHaveBeenCalled());

    const { container: confirmationContainer } = render(<AgendaPageStory data={Data.args?.data} state="ready" />);
    await act(async () => {
      await CancelConfirmation.play?.({ canvasElement: confirmationContainer } as Parameters<NonNullable<typeof CancelConfirmation.play>>[0]);
    });
    expect(screen.getAllByRole("dialog", { name: "Cancelar visita de Camila Soto — Mantención de calefón" })).toHaveLength(1);
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
    expect(screen.queryByText(/editar|reagendar|disponibilidad/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /editar|reagendar/i })).not.toBeInTheDocument();
  });
});
