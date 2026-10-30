import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { CollapsibleMessages } from "./CollapsibleMessages";

describe("CollapsibleMessages", () => {
  it("renders its supplied children", () => {
    render(<CollapsibleMessages total={4} expanded={false} onToggle={vi.fn()}><p>Message rows</p></CollapsibleMessages>);

    expect(screen.getByText("Message rows")).toBeInTheDocument();
  });

  it("does not show a control when total is at or below the preview count", () => {
    const { rerender } = render(<CollapsibleMessages total={10} expanded={false} onToggle={vi.fn()}>Rows</CollapsibleMessages>);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();

    rerender(<CollapsibleMessages total={3} previewCount={3} expanded={false} onToggle={vi.fn()}>Rows</CollapsibleMessages>);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("shows how many messages stay hidden, above the rows, and calls onToggle", () => {
    const onToggle = vi.fn();
    render(<CollapsibleMessages total={12} expanded={false} onToggle={onToggle}><p>Rows</p></CollapsibleMessages>);

    const control = screen.getByRole("button", { name: "2 mensajes anteriores · Ver todos" });
    expect(control).toHaveAttribute("aria-expanded", "false");
    expect(control.compareDocumentPosition(screen.getByText("Rows")) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    fireEvent.click(control);
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("shows the collapse label when expanded", () => {
    render(<CollapsibleMessages total={12} expanded onToggle={vi.fn()}>Rows</CollapsibleMessages>);

    expect(screen.getByRole("button", { name: "Ver menos" })).toHaveAttribute("aria-expanded", "true");
  });
});
