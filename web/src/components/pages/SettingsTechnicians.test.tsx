import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getTechnicianSchedule, saveTechnicianSchedule } from "../../api";
import { SettingsTechnicians } from "./SettingsTechnicians";

vi.mock("../../api", () => ({
  ApiError: class ApiError extends Error {},
  getTechnicianSchedule: vi.fn(),
  saveTechnicianSchedule: vi.fn(),
}));

const technicians = [
  { id: 11, username: "jperez" },
  { id: 12, username: "mgonzalez" },
];

beforeEach(() => {
  vi.mocked(getTechnicianSchedule).mockReset().mockResolvedValue({ technician_id: 11, schedule: [] });
  vi.mocked(saveTechnicianSchedule).mockReset().mockResolvedValue({ technician_id: 11, schedule: [] });
});

describe("SettingsTechnicians", () => {
  it("shows one selected technician editor and searches without removing the selection", async () => {
    render(<SettingsTechnicians technicians={technicians} />);
    expect(await screen.findByRole("heading", { name: "jperez" })).toBeVisible();
    expect(screen.getByText("Disponibilidad para visitas.")).toBeVisible();
    expect(screen.getAllByLabelText("Días y horarios de atención")).toHaveLength(1);
    expect(screen.getByRole("button", { name: "jperez" })).toHaveAttribute("aria-pressed", "true");

    await userEvent.setup().type(screen.getByRole("searchbox", { name: "Buscar técnico" }), "sin-coincidencias");
    expect(await screen.findByText("No hay técnicos que coincidan con la búsqueda.")).toBeVisible();
    expect(screen.getByRole("heading", { name: "jperez" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Guardar horario" })).toBeVisible();
  });

  it("retains a technician draft when switching and saves only the selected id and payload", async () => {
    const { container } = render(<SettingsTechnicians technicians={technicians} />);
    const user = userEvent.setup();
    const firstEditor = await screen.findByLabelText("Días y horarios de atención");
    await user.click(within(firstEditor).getByRole("button", { name: "Lun" }));
    fireEvent.change(within(firstEditor).getByLabelText("Inicio Lun"), { target: { value: "10:00" } });

    screen.getByRole("button", { name: "mgonzalez" }).focus();
    await user.keyboard("{Enter}");
    expect(await screen.findByRole("heading", { name: "mgonzalez" })).toBeVisible();
    expect(container.querySelectorAll('[aria-label="Días y horarios de atención"]')).toHaveLength(2);
    const secondEditor = [...container.querySelectorAll<HTMLElement>('[aria-label="Días y horarios de atención"]')].find((element) => !element.closest("[hidden]"))!;
    expect(within(secondEditor).getByRole("button", { name: "Lun" })).toHaveAttribute("aria-pressed", "false");
    await user.click(screen.getByRole("button", { name: "jperez" }));
    expect(await screen.findByRole("heading", { name: "jperez" })).toBeVisible();
    const activePanel = container.querySelector<HTMLElement>('section[aria-label="Horario de jperez"]:not([hidden])')!;
    const restoredEditor = within(activePanel).getByLabelText("Días y horarios de atención");
    expect(within(restoredEditor).getByRole("button", { name: "Lun" })).toHaveAttribute("aria-pressed", "true");
    expect(within(restoredEditor).getByLabelText("Inicio Lun")).toHaveValue("10:00");

    await user.click(await within(activePanel).findByRole("button", { name: "Guardar horario" }));
    await waitFor(() => expect(saveTechnicianSchedule).toHaveBeenCalledWith(11, [
      { weekday: 1, opens_at: "10:00", closes_at: "18:00" },
    ]));
    expect(saveTechnicianSchedule).toHaveBeenCalledTimes(1);
  });

  it("keeps invalid-time rejection in the shared schedule editor", async () => {
    render(<SettingsTechnicians technicians={technicians} />);
    const user = userEvent.setup();
    const editor = await screen.findByLabelText("Días y horarios de atención");
    await user.click(within(editor).getByRole("button", { name: "Lun" }));
    fireEvent.change(within(editor).getByLabelText("Inicio Lun"), { target: { value: "10:00" } });
    fireEvent.change(within(editor).getByLabelText("Fin Lun"), { target: { value: "09:00" } });
    expect(screen.getByRole("alert")).toHaveTextContent("El horario de fin debe ser posterior al de inicio.");
    expect(screen.getByRole("button", { name: "Guardar horario" })).toBeDisabled();
    expect(saveTechnicianSchedule).not.toHaveBeenCalled();
  });
});
