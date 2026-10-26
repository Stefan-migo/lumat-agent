import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DayToggle } from "./DayToggle";
import { WEEKDAY_NAMES } from "../shared/agendaTime";

describe("DayToggle", () => {
  it("uses the shared weekday labels", () => {
    const previous = WEEKDAY_NAMES[0];
    WEEKDAY_NAMES[0] = "Lunes compartido";
    try {
      render(<DayToggle value={[]} onChange={() => {}} />);
      expect(screen.getByRole("button", { name: "Lunes compartido" })).toBeInTheDocument();
    } finally {
      WEEKDAY_NAMES[0] = previous;
    }
  });
  it("renders seven pressed-state buttons and reports controlled changes", () => {
    const onChange = vi.fn();
    render(<DayToggle value={["Lun"]} onChange={onChange} />);
    expect(screen.getByRole("group", { name: "Días de la semana" })).toBeInTheDocument();
    expect(screen.getAllByRole("button")).toHaveLength(7);
    expect(screen.getByRole("button", { name: "Lun" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: "Mar" }));
    expect(onChange).toHaveBeenCalledWith(["Lun", "Mar"]);
  });

  it("disables every day button when disabled", () => {
    render(<DayToggle value={[]} onChange={() => {}} disabled />);
    expect(screen.getAllByRole("button").every((button) => (button as HTMLButtonElement).disabled)).toBe(true);
  });
});
