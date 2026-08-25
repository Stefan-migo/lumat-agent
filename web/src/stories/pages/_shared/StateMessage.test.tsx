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

  it("applies the tone accent to the title and the left bar, and the matching tint to the surface", () => {
    const { container } = render(
      <StateMessage tone="danger" role="alert" title="No pudimos cargar el panel" />,
    );
    const region = container.querySelector("section") as HTMLElement;
    expect(region.style.borderLeftColor).toBe("var(--danger)");
    expect(region.style.background).toBe("var(--danger-tint)");
  });

  it("state-matrix pairing: danger→role=alert and loading→role=status, each with a visible Spanish label (CST-PRIM-4/5)", () => {
    const { unmount } = render(
      <StateMessage tone="danger" role="alert" title="Error al conectar el agente" />,
    );
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Error al conectar el agente");
    // alert is semantically color-coded (danger tint/accent) but the label + role carry it.
    const asSection = alert as HTMLElement;
    expect(asSection.style.borderLeftColor).toBe("var(--danger)");
    unmount();

    render(
      <StateMessage tone="info" role="status" title="Cargando indicadores" spinner />,
    );
    const status = screen.getByRole("status");
    expect(status).toHaveTextContent("Cargando indicadores");
    expect(status.querySelector(".spinner__indicator")).not.toBeNull();
  });
});
