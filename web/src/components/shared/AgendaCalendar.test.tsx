import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AgendaCalendar } from "./AgendaCalendar";

const baseProps = {
  view: "month" as const,
  anchor: "2026-09-24",
  selectedDay: "2026-09-24",
  visitCounts: { "2026-09-04": 4, "2026-09-24": 2 },
  timezone: "America/Santiago",
  today: "2026-09-24",
  onSelectDay: vi.fn(),
  onViewChange: vi.fn(),
  onNavigate: vi.fn(),
};

describe("AgendaCalendar", () => {
  it("renders a month grid with aligned weekdays and empty adjacent cells", () => {
    const { container } = render(<AgendaCalendar {...baseProps} view="month" />);

    expect(screen.getByRole("grid", { name: "Calendario de septiembre de 2026" })).toBeInTheDocument();
    expect(screen.getAllByRole("columnheader")).toHaveLength(7);
    expect(screen.getAllByRole("gridcell", { hidden: true })).toHaveLength(35);
    expect(container.querySelectorAll(".agenda-calendar__day")).toHaveLength(30);
    expect(screen.getAllByRole("button", { name: /septiembre/ })).toHaveLength(30);
    expect(screen.getByRole("button", { name: /4 de septiembre.*4 visitas/ })).toBeInTheDocument();
  });

  it("renders exactly seven days in Monday-first week order", () => {
    render(<AgendaCalendar {...baseProps} view="week" />);

    expect(screen.getAllByRole("gridcell")).toHaveLength(7);
    expect(screen.getAllByRole("columnheader").map((header) => header.textContent)).toEqual([
      "lun",
      "mar",
      "mié",
      "jue",
      "vie",
      "sáb",
      "dom",
    ]);
    expect(screen.getAllByRole("button", { name: /visitas/ })).toHaveLength(7);
  });

  it("keeps empty month cells non-interactive and selectable zero-count days", () => {
    const onSelectDay = vi.fn();
    render(<AgendaCalendar {...baseProps} view="month" selectedDay={null} visitCounts={{}} onSelectDay={onSelectDay} />);

    expect(screen.getAllByRole("button", { name: /0 visitas/ })).toHaveLength(30);
    expect(screen.queryByRole("button", { name: /agosto/ })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /^martes 1 de septiembre,/ }));
    expect(onSelectDay).toHaveBeenCalledWith("2026-09-01");
  });

  it("toggles the selected day and exposes selection and today without colour", () => {
    const onSelectDay = vi.fn();
    render(<AgendaCalendar {...baseProps} view="month" onSelectDay={onSelectDay} />);

    const selected = screen.getByRole("button", { name: /24 de septiembre.*2 visitas/ });
    expect(selected).toHaveAttribute("aria-selected", "true");
    expect(document.querySelector(".agenda-calendar__today")).toHaveTextContent("Hoy");
    fireEvent.click(selected);
    expect(onSelectDay).toHaveBeenCalledWith(null);
  });

  it("emits navigation and view changes", () => {
    const onNavigate = vi.fn();
    const onViewChange = vi.fn();
    render(<AgendaCalendar {...baseProps} onNavigate={onNavigate} onViewChange={onViewChange} />);

    fireEvent.click(screen.getByRole("button", { name: "Período anterior" }));
    fireEvent.click(screen.getByRole("button", { name: "Hoy" }));
    fireEvent.click(screen.getByRole("button", { name: "Período siguiente" }));
    fireEvent.click(screen.getByRole("button", { name: "Semana" }));
    expect(onNavigate.mock.calls).toEqual([[-1], [0], [1]]);
    expect(onViewChange).toHaveBeenCalledWith("week");
  });

  it("supports keyboard day selection", async () => {
    const user = userEvent.setup();
    const onSelectDay = vi.fn();
    render(<AgendaCalendar {...baseProps} view="month" selectedDay={null} onSelectDay={onSelectDay} />);
    const day = screen.getByRole("button", { name: /^viernes 4 de septiembre,/ });

    day.focus();
    await user.keyboard("{Enter}");
    expect(onSelectDay).toHaveBeenCalledWith("2026-09-04");
  });
});
