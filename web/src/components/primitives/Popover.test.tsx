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

  it("renders a custom trigger node without changing its accessible name", () => {
    render(
      <Popover title="Archivos" triggerLabel="Archivos 2" trigger={<><span aria-hidden="true">Icon</span>Archivos 2</>}>
        <span>Contenido</span>
      </Popover>,
    );

    expect(screen.getByRole("button", { name: "Archivos 2" })).toHaveTextContent("IconArchivos 2");
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
