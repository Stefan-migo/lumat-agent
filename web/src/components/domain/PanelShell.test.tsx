import { describe, expect, it } from "vitest";
import { render, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PanelShell } from "./PanelShell";
import type { User } from "../../types";

const admin: User = { username: "ana", role: "admin" };

function sidebar(container: HTMLElement) {
  return within(container.querySelector(".panel-shell__sidebar") as HTMLElement);
}

describe("PanelShell rail contract (2C-1)", () => {
  it("renders the navigation landmark with named items and marks the active item", () => {
    const { container } = render(
      <PanelShell user={admin} currentView="clients">
        <p>Contenido</p>
      </PanelShell>,
    );
    const rail = sidebar(container);
    const navigation = rail.getByRole("navigation", { name: "Navegación principal" });

    expect(within(navigation).getByRole("button", { name: "Clientes" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(within(navigation).getByRole("button", { name: "Panel unificado" })).toBeInTheDocument();
    expect(within(navigation).getByRole("button", { name: "Configuración" })).toBeInTheDocument();
  });

  it("keeps every rail control named and exposes collapsed state", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <PanelShell user={admin}>
        <p>Contenido</p>
      </PanelShell>,
    );
    const root = container.querySelector(".panel-shell") as HTMLElement;
    const toggle = container.querySelector(".panel-shell__collapse-button") as HTMLButtonElement;

    await user.click(toggle);
    expect(root).toHaveClass("panel-shell--collapsed");
    expect(toggle).toHaveAttribute("aria-expanded", "false");

    const controls = sidebar(container).getByRole("navigation").querySelectorAll("button");
    expect(controls.length).toBeGreaterThan(0);
    for (const control of controls) {
      expect(control).toHaveAccessibleName();
      expect(control).not.toHaveAttribute("disabled");
    }
  });

  it("keeps rail navigation buttons keyboard reachable", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <PanelShell user={admin}>
        <p>Contenido</p>
      </PanelShell>,
    );
    const navigation = sidebar(container).getByRole("navigation");
    const target = within(navigation).getByRole("button", { name: "Clientes" });

    for (let index = 0; index < 12 && document.activeElement !== target; index += 1) {
      await user.tab();
    }
    expect(target).toHaveFocus();
  });
});
