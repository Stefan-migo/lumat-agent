import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
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
    expect(tabDatos).toHaveAttribute("aria-controls", "tabs-datos-panel");
    expect(tabNotas).toHaveAttribute("aria-selected", "false");

    const panel = screen.getByRole("tabpanel");
    expect(panel).toHaveAttribute("id", "tabs-datos-panel");
    expect(panel).toHaveTextContent("Panel: datos");
  });

  it("moves selection and swaps the panel on click", () => {
    render(<Tabs tabs={tabs}>{(activeId) => <p>Panel: {activeId}</p>}</Tabs>);

    fireEvent.click(screen.getByRole("tab", { name: "Notas" }));

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
});

describe("Tabs controlled (CORP-TABS-2)", () => {
  it("honors activeTab and fires onTabChange", () => {
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

    fireEvent.click(screen.getByRole("tab", { name: "Datos" }));
    expect(onTabChange).toHaveBeenCalledWith("datos");
    // Controlled: selection still comes from the prop, not the click.
    expect(screen.getByRole("tab", { name: "Notas" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });
});