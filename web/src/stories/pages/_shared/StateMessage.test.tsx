import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { StateMessage } from "./StateMessage";

describe("StateMessage (DS-UI-FRAME)", () => {
  it("renders a status region pairing a visible title and role='status'", () => {
    render(<StateMessage tone="info" role="status" title="Cargando indicadores" />);
    // role-pairing: the visible label + semantic role are both present; the
    // accent/background are applied via tokens (semantic color) alongside the
    // label, never color alone.
    expect(screen.getByRole("status")).toHaveTextContent("Cargando indicadores");
  });

  it("renders an alert region pairing a visible title and role='alert'", () => {
    render(<StateMessage tone="danger" role="alert" title="No pudimos cargar el panel" />);
    expect(screen.getByRole("alert")).toHaveTextContent("No pudimos cargar el panel");
  });

  it("renders the detail when provided", () => {
    render(
      <StateMessage
        tone="warning"
        role="status"
        title="Datos posiblemente desactualizados"
        detail="Mostramos la información disponible."
      />,
    );
    expect(screen.getByText("Mostramos la información disponible.")).toBeInTheDocument();
  });

  it("shows the spinner indicator only when requested", () => {
    const { rerender, container } = render(
      <StateMessage tone="info" role="status" title="Cargando" spinner />,
    );
    expect(container.querySelector(".spinner__indicator")).not.toBeNull();
    rerender(<StateMessage tone="info" role="status" title="Cargando" />);
    expect(container.querySelector(".spinner__indicator")).toBeNull();
  });

  it("applies the tone accent to the title and the region rail", () => {
    const { container } = render(
      <StateMessage tone="danger" role="alert" title="No pudimos cargar el panel" />,
    );
    const region = container.querySelector("section") as HTMLElement;
    expect(region.style.borderLeftColor).toBe("var(--danger)");
    expect(region.style.background).toBe("var(--danger-bg)");
  });
});
