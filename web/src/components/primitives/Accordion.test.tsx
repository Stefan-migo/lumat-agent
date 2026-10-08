import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { Accordion } from "./Accordion";

describe("Accordion", () => {
  it("shows its count and expands and collapses an associated region", () => {
    render(<Accordion title="Respuestas automáticas" count={3}><p>Contenido del grupo</p></Accordion>);
    const button = screen.getByRole("button", { name: /Respuestas automáticas/ });
    const panel = screen.getByRole("region", { hidden: true });
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(button).toHaveAttribute("aria-controls", panel.id);
    expect(panel).toHaveAttribute("aria-labelledby", button.id);

    fireEvent.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Contenido del grupo")).toBeVisible();
    fireEvent.click(button);
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Contenido del grupo")).not.toBeVisible();
  });
});
