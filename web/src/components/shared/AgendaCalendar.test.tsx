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
  it("renders a month table with aligned weekdays and empty adjacent cells", () => {
    const { container } = render(<AgendaCalendar {...baseProps} view="month" />);

    expect(screen.getByRole("table", { name: "Calendario de septiembre de 2026" })).toBeInTheDocument();
    expect(screen.getAllByRole("columnheader")).toHaveLength(7);
    expect(screen.getAllByRole("cell", { hidden: true })).toHaveLength(35);
    expect(screen.getAllByRole("row")).toHaveLength(6);
    expect(container.querySelectorAll(".agenda-calendar__day")).toHaveLength(30);
    expect(screen.getAllByRole("button", { name: /septiembre/ })).toHaveLength(30);
    expect(screen.getByRole("button", { name: /4 de septiembre.*4 visitas/ })).toBeInTheDocument();
  });

  it("renders exactly seven days in a Monday-first week row", () => {
    render(<AgendaCalendar {...baseProps} view="week" />);

    expect(screen.getAllByRole("cell")).toHaveLength(7);
    expect(screen.getAllByRole("row")).toHaveLength(2);
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

  it("includes each visit count in the day accessible name", () => {
    render(<AgendaCalendar {...baseProps} view="month" />);

    expect(screen.getByRole("button", { name: /4 de septiembre.*4 visitas/ })).toBeInTheDocument();
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
    expect(selected).toHaveAttribute("aria-pressed", "true");
    expect(selected).toHaveAttribute("aria-selected", "true");
    expect(document.querySelector(".agenda-calendar__today")).toHaveTextContent("Hoy");
    expect(document.querySelectorAll(".agenda-calendar__today, .agenda-calendar__selected")).toHaveLength(1);
    fireEvent.click(selected);
    expect(onSelectDay).toHaveBeenCalledWith(null);
  });

  it("uses one status line when today and selection apply to the same day", () => {
    render(<AgendaCalendar {...baseProps} />);
    const day = screen.getByRole("button", { name: /24 de septiembre.*2 visitas/ });
    expect(day.querySelectorAll(".agenda-calendar__today, .agenda-calendar__selected")).toHaveLength(1);
    expect(day).toHaveAttribute("aria-current", "date");
    expect(day).toHaveAttribute("aria-selected", "true");
  });

  it("emits navigation and view changes", () => {
    const onNavigate = vi.fn();
    const onViewChange = vi.fn();
    render(<AgendaCalendar {...baseProps} onNavigate={onNavigate} onViewChange={onViewChange} />);

    fireEvent.click(screen.getByRole("button", { name: "Período anterior" }));
    fireEvent.click(screen.getByRole("button", { name: "Hoy" }));
    fireEvent.click(screen.getByRole("button", { name: "Período siguiente" }));
    fireEvent.click(screen.getByRole("button", { name: "Ver semana" }));
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
