import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CaseActions, type CaseActionTarget } from "./CaseActions";

const target: CaseActionTarget = {
  id: 42,
  status: "abierto",
  responsible_id: 7,
  emergency: true,
  ack_by: null,
};

const users = [
  { id: 7, username: "ana" },
  { id: 8, username: "luis" },
];

describe("CaseActions", () => {
  it("renders current status and all status options", () => {
    render(<CaseActions target={target} users={users} />);

    const status = screen.getByRole("combobox", { name: "Estado caso 42" }) as HTMLSelectElement;
    expect(status.value).toBe("abierto");
    expect(Array.from(status.options, (option) => option.value)).toEqual([
      "abierto",
      "en_evaluacion",
      "escalado",
      "cerrado",
    ]);
  });

  it("renders the unassigned option and provided users", () => {
    render(<CaseActions target={target} users={users} />);

    const responsible = screen.getByRole("combobox", { name: "Responsable caso 42" }) as HTMLSelectElement;
    expect(Array.from(responsible.options, (option) => option.textContent)).toEqual([
      "Sin asignar",
      "ana",
      "luis",
    ]);
    expect(responsible.value).toBe("7");
  });

  it("updates the selected status and responsible user", async () => {
    const onUpdate = vi.fn().mockResolvedValue(undefined);
    render(<CaseActions target={target} users={users} onUpdate={onUpdate} />);

    fireEvent.change(screen.getByRole("combobox", { name: "Estado caso 42" }), {
      target: { value: "escalado" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: "Responsable caso 42" }), {
      target: { value: "8" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Actualizar" }));

    await waitFor(() => expect(onUpdate).toHaveBeenCalledWith(42, "escalado", 8));
  });

  it("passes null when removing the responsible user", async () => {
    const onUpdate = vi.fn().mockResolvedValue(undefined);
    render(<CaseActions target={target} users={users} onUpdate={onUpdate} />);

    fireEvent.change(screen.getByRole("combobox", { name: "Responsable caso 42" }), {
      target: { value: "" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Actualizar" }));

    await waitFor(() => expect(onUpdate).toHaveBeenCalledWith(42, "abierto", null));
  });

  it("shows acknowledgement only for an unanswered emergency and acknowledges the target", async () => {
    const onAcknowledge = vi.fn().mockResolvedValue(undefined);
    const { rerender } = render(
      <CaseActions target={target} users={users} onAcknowledge={onAcknowledge} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Reconocer" }));
    await waitFor(() => expect(onAcknowledge).toHaveBeenCalledWith(42));

    rerender(
      <CaseActions target={{ ...target, ack_by: "ana" }} users={users} onAcknowledge={onAcknowledge} />,
    );
    expect(screen.queryByRole("button", { name: "Reconocer" })).not.toBeInTheDocument();

    rerender(
      <CaseActions target={{ ...target, emergency: false }} users={users} onAcknowledge={onAcknowledge} />,
    );
    expect(screen.queryByRole("button", { name: "Reconocer" })).not.toBeInTheDocument();
  });
});
