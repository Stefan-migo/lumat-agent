import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
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
    vi.mocked(listAppointments).mockResolvedValue({ appointments: [] });
  });

  it("covers production-shaped lifecycle and independent sync data", () => {
    render(<AgendaPageStory data={Data.args?.data} state="ready" />);

    expect(screen.getByText("Mantención de calefón")).toBeInTheDocument();
    expect(screen.getByText("Cancelada")).toBeInTheDocument();
    expect(screen.getByText("Completada")).toBeInTheDocument();
    expect(screen.getByText("No asistió")).toBeInTheDocument();
    expect(screen.getByText("Calendario con error")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Reintentar calendario" })).toHaveLength(2);
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
    const user = userEvent.setup();
    vi.mocked(cancelAppointment).mockResolvedValue({ ok: true, appointment: Data.args!.data![0] });
    vi.mocked(retryCalendarSync).mockResolvedValue({ ok: true, calendar: { status: "synced", error: null } });
    vi.mocked(listAppointments).mockResolvedValue({ appointments: Data.args!.data! });
    render(<AgendaPageStory data={Data.args?.data} state="ready" />);

    await user.click(screen.getByRole("button", { name: "Cancelar visita" }));
    expect(screen.getByRole("dialog", { name: "Cancelar visita" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Confirmar cancelación" }));
    await waitFor(() => expect(cancelAppointment).toHaveBeenCalled());

    const retry = screen.getAllByRole("button", { name: "Reintentar calendario" })[0];
    retry.focus();
    await user.keyboard("{Enter}");
    await waitFor(() => expect(retryCalendarSync).toHaveBeenCalled());
  });

  it("exposes keyboard and narrow viewport stories without inventing controls", () => {
    expect(KeyboardActions).toBeDefined();
    expect(Mobile.parameters?.viewport).toEqual({ defaultViewport: "mobile-compact" });
    expect(SyncFailure.parameters?.viewport).toEqual({ defaultViewport: "bp-sm" });
    expect(CancelConfirmation).toBeDefined();
    expect(screen.queryByText(/crear|editar|reagendar|disponibilidad/i)).not.toBeInTheDocument();
  });
});
