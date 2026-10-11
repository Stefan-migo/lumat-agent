import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Popover } from "./Popover";

describe("Popover (CST-PRIM-7)", () => {
  it("uses native popover semantics and an accessible trigger", () => {
    render(
      <Popover title="Acciones" triggerLabel="Abrir acciones">
        <button type="button">Editar</button>
      </Popover>,
    );

    const trigger = screen.getByRole("button", { name: "Abrir acciones" });
    const panel = screen.getByRole("dialog", { name: "Acciones" });

    expect(trigger).toHaveAttribute("popovertarget", panel.id);
    expect(panel).toHaveAttribute("popover", "auto");
  });

  it("gives each instance a unique anchor shared by its trigger and panel", () => {
    render(<><Popover title="First" triggerLabel="First"><span>One</span></Popover><Popover title="Second" triggerLabel="Second"><span>Two</span></Popover></>);

    const roots = Array.from(document.querySelectorAll<HTMLElement>(".popover"));
    const anchors = roots.map((root) => root.style.getPropertyValue("--pop-anchor"));
    expect(anchors[0]).toMatch(/^--pop-anchor-/);
    expect(anchors[1]).toMatch(/^--pop-anchor-/);
    expect(anchors[0]).not.toBe(anchors[1]);
    for (const [index, root] of roots.entries()) {
      const trigger = root.querySelector<HTMLButtonElement>(".popover__trigger");
      const panel = root.querySelector<HTMLElement>(".popover__panel");
      expect(trigger).toBeInTheDocument();
      expect(panel).toBeInTheDocument();
      expect(trigger?.getAttribute("popovertarget")).toBe(panel?.id);
      expect(anchors[index]).toBeTruthy();
    }
  });

  it("renders a custom trigger node without changing its accessible name", () => {
    render(
      <Popover title="Archivos" triggerLabel="Archivos 2" trigger={<><span aria-hidden="true">Icon</span>Archivos 2</>}>
        <span>Contenido</span>
      </Popover>,
    );

    expect(screen.getByRole("button", { name: "Archivos 2" })).toHaveTextContent("IconArchivos 2");
  });

  it("keeps a visually hidden title as the dialog accessible name", () => {
    render(
      <Popover title="Agregar al hilo" triggerLabel="+" hideTitle>
        <span>Contenido</span>
      </Popover>,
    );

    const panel = screen.getByRole("dialog", { name: "Agregar al hilo" });
    expect(panel.querySelector("h2")).toHaveClass("visually-hidden");
    expect(panel).toHaveAttribute("aria-labelledby", panel.querySelector("h2")?.id);
  });

  it("keeps native controls for disabled and complete states", () => {
    const { rerender } = render(
      <Popover title="Acciones" triggerLabel="Abrir acciones" state="loading">
        <span>Contenido</span>
      </Popover>,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Cargando");

    rerender(
      <Popover title="Acciones" triggerLabel="Abrir acciones" state="empty">
        <span>Contenido</span>
      </Popover>,
    );
    expect(screen.getByRole("status")).toHaveTextContent("No hay opciones disponibles");

    rerender(
      <Popover title="Acciones" triggerLabel="Abrir acciones" state="error">
        <span>Contenido</span>
      </Popover>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("No fue posible cargar las opciones");

    rerender(
      <Popover title="Acciones" triggerLabel="Abrir acciones" state="disabled">
        <span>Contenido</span>
      </Popover>,
    );
    expect(screen.getByRole("button", { name: "Abrir acciones" })).toBeDisabled();
  });
});
