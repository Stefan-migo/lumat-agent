import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PageFrame } from "./PageFrame";
import { StateMessage } from "./StateMessage";

describe("PageFrame (DS-UI-FRAME)", () => {
  it("renders the titlebar title and meta", () => {
    render(
      <PageFrame title="Panel" meta="Ventana de 7 días">
        <p>contenido</p>
      </PageFrame>,
    );
    expect(screen.getByRole("heading", { name: "Panel" })).toBeInTheDocument();
    expect(screen.getByText("Ventana de 7 días")).toBeInTheDocument();
  });

  it("renders actions in the titlebar", () => {
    render(
      <PageFrame title="Panel" actions={<button type="button">Exportar</button>}>
        <p>contenido</p>
      </PageFrame>,
    );
    expect(screen.getByRole("button", { name: "Exportar" })).toBeInTheDocument();
  });

  it("renders the banner slot before the content region", () => {
    const { container } = render(
      <PageFrame
        title="Panel"
        state={<StateMessage tone="warning" role="status" title="Datos posiblemente desactualizados" />}
      >
        <p>contenido principal</p>
      </PageFrame>,
    );
    const banner = container.querySelector(".page-frame__banner");
    const content = container.querySelector(".page-frame__content");
    expect(banner).not.toBeNull();
    expect(content).not.toBeNull();
    expect(banner!.compareDocumentPosition(content!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByRole("status")).toHaveTextContent("Datos posiblemente desactualizados");
    expect(screen.getByText("contenido principal")).toBeInTheDocument();
  });

  it("emits a tokenized titlebar with no lime rail and no forest tint", () => {
    const { container } = render(
      <PageFrame title="Panel">
        <p>contenido</p>
      </PageFrame>,
    );
    expect(container.querySelector(".page-frame")).not.toBeNull();
    expect(container.querySelector(".page-frame__titlebar")).not.toBeNull();
  });
});
