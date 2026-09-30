import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { Tabs } from "./Tabs";

const tabs = [
  { id: "datos", label: "Datos" },
  { id: "notas", label: "Notas" },
];

describe("Tabs (CORP-TABS-1)", () => {
  it("renders a tablist with the first tab active and its panel visible", () => {
    render(
      <Tabs tabs={tabs} ariaLabel="Ficha">
        {(activeId) => <p>Panel: {activeId}</p>}
      </Tabs>,
    );

    const tablist = screen.getByRole("tablist");
    expect(tablist).toHaveAttribute("aria-label", "Ficha");

    const tabDatos = screen.getByRole("tab", { name: "Datos" });
    const tabNotas = screen.getByRole("tab", { name: "Notas" });
    expect(tabDatos).toHaveAttribute("aria-selected", "true");
    expect(tabNotas).toHaveAttribute("aria-selected", "false");

    const panel = screen.getByRole("tabpanel");
    expect(tabDatos).toHaveAttribute("aria-controls", panel.id);
    expect(panel).toHaveTextContent("Panel: datos");
  });

  it("moves selection and swaps the panel on click", async () => {
    render(<Tabs tabs={tabs}>{(activeId) => <p>Panel: {activeId}</p>}</Tabs>);

    await userEvent.setup().click(screen.getByRole("tab", { name: "Notas" }));

    expect(screen.getByRole("tab", { name: "Datos" })).toHaveAttribute(
      "aria-selected",
      "false",
    );
    expect(screen.getByRole("tab", { name: "Notas" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Panel: notas");
  });

  it("supports keyboard navigation with ArrowRight, Home, and End", async () => {
    render(<Tabs tabs={tabs}>{(activeId) => <p>Panel: {activeId}</p>}</Tabs>);

    const datos = screen.getByRole("tab", { name: "Datos" });
    const user = userEvent.setup();
    await user.click(datos);
    await user.keyboard("{ArrowRight}");

    const notas = screen.getByRole("tab", { name: "Notas" });
    expect(notas).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Panel: notas");

    await user.keyboard("{Home}");
    expect(datos).toHaveAttribute("aria-selected", "true");

    await user.keyboard("{End}");
    expect(notas).toHaveAttribute("aria-selected", "true");
  });

  it("uses semantic text and a high-contrast active indicator with visible focus", () => {
    const css = readFileSync(join(process.cwd(), "src/components/primitives/primitives.css"), "utf8");
    expect(css).toMatch(/\.tabs__tab\s*\{[^}]*color:\s*var\(--text-muted\)/s);
    expect(css).toMatch(/\.tabs__tab\[aria-selected="true"\]\s*\{[^}]*color:\s*var\(--text\)[^}]*border-bottom-color:\s*var\(--chrome-950\)/s);
    expect(css).toMatch(/\.tabs__tab:focus-visible\s*\{[^}]*outline:\s*var\(--focus-ring-width\) solid var\(--focus-ring\)/s);
  });
});

describe("Tabs controlled (CORP-TABS-2)", () => {
  it("honors activeTab and fires onTabChange", async () => {
    const onTabChange = vi.fn();
    render(
      <Tabs tabs={tabs} activeTab="notas" onTabChange={onTabChange}>
        {(activeId) => <p>Panel: {activeId}</p>}
      </Tabs>,
    );

    expect(screen.getByRole("tab", { name: "Notas" })).toHaveAttribute(
      "aria-selected",
      "true",
    );

    await userEvent.setup().click(screen.getByRole("tab", { name: "Datos" }));
    expect(onTabChange).toHaveBeenCalledWith("datos");
    // Controlled: selection still comes from the prop, not the click.
    expect(screen.getByRole("tab", { name: "Notas" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });
});
