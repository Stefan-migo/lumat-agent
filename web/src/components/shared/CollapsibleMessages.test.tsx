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

  it("shows the total and calls onToggle when clicked", () => {
    const onToggle = vi.fn();
    render(<CollapsibleMessages total={12} expanded={false} onToggle={onToggle}>Rows</CollapsibleMessages>);

    fireEvent.click(screen.getByRole("button", { name: "Ver todos (12)" }));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("shows the collapse label when expanded", () => {
    render(<CollapsibleMessages total={12} expanded onToggle={vi.fn()}>Rows</CollapsibleMessages>);

    expect(screen.getByRole("button", { name: "Ver menos" })).toBeInTheDocument();
  });
});
