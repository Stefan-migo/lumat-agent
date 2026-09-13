import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProjectsPage } from "./ProjectsPage";
import { parsePanelPath, pathForView } from "../domain/panelRoutes";

describe("projects panel", () => {
  it("parses and emits the project route", () => {
    expect(parsePanelPath("/panel/app/projects")).toEqual({ view: "projects" });
    expect(pathForView("projects")).toBe("/panel/app/projects");
  });

  it("renders grouped SDB artifacts without mutation controls", () => {
    render(<ProjectsPage data={{ projects: [{ id: 1, slug: "ops", name: "Operations", purpose: "Run ops", status: "active", created_at: null, updated_at: null }] }} state="ready" />);
    expect(screen.getByText("Operations")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /crear|renombrar|archivar|fusionar/i })).not.toBeInTheDocument();
  });
});
