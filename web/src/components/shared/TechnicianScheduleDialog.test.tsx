import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApiError, getTechnicianSchedule, saveTechnicianSchedule } from "../../api";
import { TechnicianScheduleDialog } from "./TechnicianScheduleDialog";

vi.mock("../../api", () => ({
  ApiError: class ApiError extends Error { structuredDetail?: { code?: string }; constructor(_status: number, detail: string, structuredDetail?: { code?: string }) { super(detail); this.structuredDetail = structuredDetail; } },
  getTechnicianSchedule: vi.fn(),
  saveTechnicianSchedule: vi.fn(),
}));

afterEach(() => vi.clearAllMocks());

describe("TechnicianScheduleDialog", () => {
  it("loads seven weekdays and leaves off-day times disabled", async () => {
    vi.mocked(getTechnicianSchedule).mockResolvedValue({ technician_id: 4, schedule: [{ weekday: 1, opens_at: "09:00:00", closes_at: "18:00:00" }] });
    render(<TechnicianScheduleDialog open technician={{ id: 4, username: "Luis" }} onClose={vi.fn()} />);

    expect(screen.getByRole("status")).toHaveTextContent("Cargando horario");
    const dialog = await screen.findByRole("dialog", { name: "Horario semanal" });
    expect(dialog).toHaveTextContent("Define los días y horarios de atención de Luis.");
    for (const day of ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]) expect(within(dialog).getByRole("button", { name: day })).toBeInTheDocument();
    expect(within(dialog).getByLabelText("Inicio Lun")).toHaveValue("09:00");
    expect(within(dialog).getByLabelText("Fin Lun")).toHaveValue("18:00");
    expect(within(dialog).getByLabelText("Inicio Mar")).toBeDisabled();
  });

  it("blocks invalid enabled intervals and saves only enabled days", async () => {
    const user = userEvent.setup();
    vi.mocked(getTechnicianSchedule).mockResolvedValue({ technician_id: 4, schedule: [] });
    vi.mocked(saveTechnicianSchedule).mockResolvedValue({ technician_id: 4, schedule: [] });
    const onSaved = vi.fn();
    render(<TechnicianScheduleDialog open technician={{ id: 4, username: "Luis" }} onClose={vi.fn()} onSaved={onSaved} />);
    const dialog = await screen.findByRole("dialog", { name: "Horario semanal" });
    await user.click(within(dialog).getByRole("button", { name: "Lun" }));
    const start = within(dialog).getByLabelText("Inicio Lun");
    const end = within(dialog).getByLabelText("Fin Lun");
    fireEvent.change(start, { target: { value: "10:00" } });
    fireEvent.change(end, { target: { value: "09:00" } });
    expect(screen.getByText("El horario de fin debe ser posterior al de inicio.")).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Guardar horario" })).toBeDisabled();

    fireEvent.change(end, { target: { value: "11:00" } });
    await user.click(within(dialog).getByRole("button", { name: "Guardar horario" }));
    await waitFor(() => expect(saveTechnicianSchedule).toHaveBeenCalledWith(4, [{ weekday: 1, opens_at: "10:00", closes_at: "11:00" }]));
    expect(onSaved).toHaveBeenCalledOnce();
    expect(await screen.findByRole("status")).toHaveTextContent("Horario guardado");
  });

  it("shows a recoverable server error without clearing the schedule draft", async () => {
    const user = userEvent.setup();
    vi.mocked(getTechnicianSchedule).mockResolvedValue({ technician_id: 4, schedule: [] });
    vi.mocked(saveTechnicianSchedule).mockRejectedValue(new ApiError(400, "Invalid schedule", { code: "invalid_schedule" }));
    render(<TechnicianScheduleDialog open technician={{ id: 4, username: "Luis" }} onClose={vi.fn()} />);
    const dialog = await screen.findByRole("dialog", { name: "Horario semanal" });
    await user.click(within(dialog).getByRole("button", { name: "Lun" }));
    fireEvent.change(within(dialog).getByLabelText("Inicio Lun"), { target: { value: "09:00" } });
    fireEvent.change(within(dialog).getByLabelText("Fin Lun"), { target: { value: "10:00" } });
    await user.click(within(dialog).getByRole("button", { name: "Guardar horario" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("Revisa los horarios ingresados");
    expect(within(dialog).getByLabelText("Inicio Lun")).toHaveValue("09:00");
  });
});
