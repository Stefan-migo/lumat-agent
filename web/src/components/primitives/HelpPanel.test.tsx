import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BookOpen } from "lucide-react";
import { HelpPanel } from "./HelpPanel";

describe("HelpPanel", () => {
  it("renders the supplied icon, title, body, and tone", () => {
    render(<HelpPanel icon={BookOpen} title="Cómo funciona" tone="info">Contenido de ayuda.</HelpPanel>);
    expect(screen.getByRole("heading", { name: "Cómo funciona" })).toBeInTheDocument();
    expect(screen.getByText("Contenido de ayuda.")).toBeInTheDocument();
    expect(document.querySelector(".help-panel")).toHaveAttribute("class", "help-panel help-panel--info");
  });
});
