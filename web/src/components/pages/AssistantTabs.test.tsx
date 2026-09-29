import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AssistantTabs } from "./AssistantTabs";

describe("AssistantTabs", () => {
  it("renders the three assistant sections", () => {
    render(<AssistantTabs active="chat" onSelect={vi.fn()} />);

    expect(screen.getByRole("tab", { name: "Asistente" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Proyectos" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Sesiones de planificación" })).toBeInTheDocument();
  });

  it("marks the active section as selected", () => {
    render(<AssistantTabs active="projects" onSelect={vi.fn()} />);

    expect(screen.getByRole("tab", { name: "Proyectos" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Asistente" })).toHaveAttribute("aria-selected", "false");
  });

  it("selects the clicked section", async () => {
    const onSelect = vi.fn();
    render(<AssistantTabs active="chat" onSelect={onSelect} />);

    await userEvent.setup().click(screen.getByRole("tab", { name: "Sesiones de planificación" }));

    expect(onSelect).toHaveBeenCalledWith("planning-sessions");
  });
});
