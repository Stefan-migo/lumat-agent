import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Settings } from "../../types";
import { SettingsHoursEditor } from "./SettingsHoursEditor";

type HoursData = Settings["hours"];
const initialHours: HoursData = {
  timezone: "America/Santiago",
  schedule: [
    { days: [1, 2, 3, 4, 5], open: "09:00", close: "18:00" },
    { days: [6], open: "09:00", close: "14:00" },
  ],
};

function renderEditor(hours = initialHours) {
  const onChange = vi.fn();
  render(<SettingsHoursEditor hours={hours} onChange={onChange} />);
  return onChange;
}

describe("SettingsHoursEditor", () => {
  it("renders the compact schedule table and timezone control in the card header", () => {
    renderEditor();
    const card = screen.getByRole("heading", { name: "Horarios de atención" }).closest(".card");
    expect(card).not.toBeNull();
    expect(within(card as HTMLElement).getByText("Define cuándo atiende tu equipo.")).toBeInTheDocument();
    expect(within(card as HTMLElement).getByLabelText("Zona horaria")).toHaveValue("America/Santiago");
    expect(within(card as HTMLElement).getByRole("table", { name: "Horarios de atención" })).toBeInTheDocument();
    expect(within(card as HTMLElement).getByText("Lun, Mar, Mié, Jue, Vie")).toBeInTheDocument();
    expect(within(card as HTMLElement).getByLabelText("Inicio horario 1")).toHaveValue("09:00");
    expect(within(card as HTMLElement).getByLabelText("Fin horario 1")).toHaveValue("18:00");
    expect(within(card as HTMLElement).getByText("Dom")).toBeInTheDocument();
    expect(within(card as HTMLElement).getByText("Sin horario")).toBeInTheDocument();
    expect(within(card as HTMLElement).queryByRole("button", { name: /guardar/i })).not.toBeInTheDocument();
  });

  it("emits the exact controlled payload when a row time or timezone changes", async () => {
    const user = userEvent.setup();
    const onChange = renderEditor();
    fireEvent.change(screen.getByLabelText("Inicio horario 1"), { target: { value: "08:30" } });
    expect(onChange).toHaveBeenLastCalledWith({
      ...initialHours,
      schedule: [{ ...initialHours.schedule[0], open: "08:30" }, initialHours.schedule[1]],
    });
    await user.selectOptions(screen.getByLabelText("Zona horaria"), "Pacific/Easter");
    expect(onChange).toHaveBeenLastCalledWith({ ...initialHours, timezone: "Pacific/Easter" });
  });

  it("deletes only the selected schedule", async () => {
    const user = userEvent.setup();
    const onChange = renderEditor();
    await user.click(screen.getByRole("button", { name: "Eliminar horario 1" }));
    expect(onChange).toHaveBeenCalledWith({ ...initialHours, schedule: [initialHours.schedule[1]] });
  });

  it("opens an add form and cancellation leaves the parent unchanged", async () => {
    const user = userEvent.setup();
    const onChange = renderEditor();
    expect(screen.queryByRole("group", { name: "Días de atención" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Agregar horario" }));
    expect(screen.getByRole("group", { name: "Días de atención" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(onChange).not.toHaveBeenCalled();
    expect(screen.queryByRole("group", { name: "Días de atención" })).not.toBeInTheDocument();
  });

  it("excludes occupied days and adds a valid new schedule without changing existing rows", async () => {
    const user = userEvent.setup();
    const onChange = renderEditor();
    await user.click(screen.getByRole("button", { name: "Agregar horario" }));
    const days = screen.getByRole("group", { name: "Días de atención" });
    for (const day of ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"]) {
      await user.click(within(days).getByRole("button", { name: day }));
      expect(within(days).getByRole("button", { name: day })).toHaveAttribute("aria-pressed", "false");
    }
    await user.click(within(days).getByRole("button", { name: "Dom" }));
    await user.click(screen.getByRole("button", { name: "Agregar horario" }));
    expect(onChange).toHaveBeenCalledWith({
      ...initialHours,
      schedule: [...initialHours.schedule, { days: [7], open: "09:00", close: "18:00" }],
    });
  });

  it("allows editing a row's days but rejects empty, occupied, or invalid intervals without mutation", async () => {
    const user = userEvent.setup();
    const onChange = renderEditor();
    await user.click(screen.getByRole("button", { name: "Editar días horario 2" }));
    const days = screen.getByRole("group", { name: "Días de atención horario 2" });
    await user.click(within(days).getByRole("button", { name: "Lun" }));
    expect(within(days).getByRole("button", { name: "Lun" })).toHaveAttribute("aria-pressed", "false");
    expect(within(days).getByRole("button", { name: "Sáb" })).toHaveAttribute("aria-pressed", "true");
    await user.click(within(days).getByRole("button", { name: "Sáb" }));
    expect(screen.getByRole("button", { name: "Confirmar horario" })).toBeDisabled();
    expect(onChange).not.toHaveBeenCalled();
    await user.click(within(days).getByRole("button", { name: "Dom" }));
    fireEvent.change(screen.getByLabelText("Inicio horario 2"), { target: { value: "15:00" } });
    expect(screen.getByRole("button", { name: "Confirmar horario" })).toBeDisabled();
    expect(onChange).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Fin horario 2"), { target: { value: "17:00" } });
    await user.click(screen.getByRole("button", { name: "Confirmar horario" }));
    expect(onChange).toHaveBeenCalledWith({
      ...initialHours,
      schedule: [initialHours.schedule[0], { days: [7], open: "15:00", close: "17:00" }],
    });
  });
});
