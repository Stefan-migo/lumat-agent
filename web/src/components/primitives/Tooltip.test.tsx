import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { Tooltip } from "./Tooltip";

describe("Tooltip (CST-PRIM-7)", () => {
  it("connects a native hint to its labelled trigger", () => {
    render(<Tooltip label="Información adicional">Estado</Tooltip>);

    const trigger = screen.getByRole("button", { name: "Estado" });
    const tooltip = screen.getByRole("tooltip", { hidden: true });
    expect(trigger).toHaveAttribute("aria-describedby", tooltip.id);
    expect(tooltip).toHaveAttribute("popover", "hint");
    expect(tooltip).toHaveAttribute("aria-hidden", "true");
    expect(tooltip).toHaveClass("tooltip__content");
  });

  it("shows on keyboard focus and hides on blur", () => {
    render(<Tooltip label="Información adicional">Estado</Tooltip>);
    const trigger = screen.getByRole("button", { name: "Estado" });
    const tooltip = screen.getByRole("tooltip", { hidden: true });

    fireEvent.focus(trigger);
    expect(tooltip).toHaveAttribute("aria-hidden", "false");
    fireEvent.blur(trigger);
    expect(tooltip).toHaveAttribute("aria-hidden", "true");
  });

  it("shows on hover and remains a real interactive 40px control", () => {
    render(<Tooltip label="Información adicional">Estado</Tooltip>);
    const trigger = screen.getByRole("button", { name: "Estado" });
    const tooltip = screen.getByRole("tooltip", { hidden: true });

    fireEvent.mouseEnter(trigger);
    expect(tooltip).toHaveAttribute("aria-hidden", "false");
    fireEvent.mouseLeave(trigger);
    expect(tooltip).toHaveAttribute("aria-hidden", "true");
  });
});
