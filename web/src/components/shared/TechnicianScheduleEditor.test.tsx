import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { getTechnicianSchedule, saveTechnicianSchedule } from "../../api";
import { formatTechnicianSchedule, TechnicianScheduleEditor } from "./TechnicianScheduleEditor";

vi.mock("../../api", () => ({ ApiError: class ApiError extends Error {}, getTechnicianSchedule: vi.fn(), saveTechnicianSchedule: vi.fn() }));
describe("TechnicianScheduleEditor", () => {
  it("summarizes consecutive days that share the same hours", () => {
    expect(formatTechnicianSchedule([
      { weekday: 1, opens_at: "09:00:00", closes_at: "18:00:00" },
      { weekday: 2, opens_at: "09:00:00", closes_at: "18:00:00" },
      { weekday: 3, opens_at: "09:00:00", closes_at: "18:00:00" },
      { weekday: 4, opens_at: "09:00:00", closes_at: "18:00:00" },
      { weekday: 5, opens_at: "09:00:00", closes_at: "18:00:00" },
      { weekday: 6, opens_at: "09:00:00", closes_at: "14:00:00" },
    ])).toBe("Lun–Vie 09:00–18:00 · Sáb 09:00–14:00");
  });

  it("loads seven weekdays, validates intervals, saves and reports the updated summary", async () => {
    vi.mocked(getTechnicianSchedule).mockResolvedValue({ technician_id: 4, schedule: [] });
    vi.mocked(saveTechnicianSchedule).mockResolvedValue({ technician_id: 4, schedule: [] });
    const onSaved = vi.fn();
    render(<TechnicianScheduleEditor technician={{ id: 4, username: "Luis" }} onSaved={onSaved} />);
    const editor = await screen.findByLabelText("Días y horarios de atención");
    for (const day of ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]) expect(within(editor).getByRole("button", { name: day })).toBeInTheDocument();
    const user = userEvent.setup();
    await user.click(within(editor).getByRole("button", { name: "Lun" }));
    fireEvent.change(screen.getByLabelText("Inicio Lun"), { target: { value: "10:00" } });
    fireEvent.change(screen.getByLabelText("Fin Lun"), { target: { value: "09:00" } });
    expect(screen.getByRole("alert")).toHaveTextContent("El horario de fin debe ser posterior al de inicio.");
    expect(screen.getByRole("button", { name: "Guardar horario" })).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Fin Lun"), { target: { value: "11:00" } });
    await user.click(screen.getByRole("button", { name: "Guardar horario" }));
    await waitFor(() => expect(saveTechnicianSchedule).toHaveBeenCalledWith(4, [{ weekday: 1, opens_at: "10:00", closes_at: "11:00" }]));
    expect(onSaved).toHaveBeenCalledWith("Lun 10:00–11:00");
    expect(await screen.findByRole("status")).toHaveTextContent("Horario guardado");
  });
});
