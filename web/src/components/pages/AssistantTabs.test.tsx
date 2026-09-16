import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { AssistantTabs } from "./AssistantTabs";

describe("AssistantTabs", () => {
  it("renders the three assistant sections", () => {
    render(<AssistantTabs active="chat" onSelect={vi.fn()} />);

    expect(screen.getByRole("tab", { name: "Chat" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Proyectos" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Sesiones de planning" })).toBeInTheDocument();
  });

  it("marks the active section as selected", () => {
    render(<AssistantTabs active="projects" onSelect={vi.fn()} />);

    expect(screen.getByRole("tab", { name: "Proyectos" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Chat" })).toHaveAttribute("aria-selected", "false");
  });

  it("selects the clicked section", () => {
    const onSelect = vi.fn();
    render(<AssistantTabs active="chat" onSelect={onSelect} />);

    fireEvent.click(screen.getByRole("tab", { name: "Sesiones de planning" }));

    expect(onSelect).toHaveBeenCalledWith("planning-sessions");
  });
});
