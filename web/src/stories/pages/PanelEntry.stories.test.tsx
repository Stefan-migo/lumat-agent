import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DashboardOverview } from "./Dashboard.stories";
import { PanelShell } from "../../components/domain/PanelShell";

const dashboard = <DashboardOverview />;

describe("Panel entry layout", () => {
  it("composes the dashboard main landmark with the complete admin information architecture", () => {
    render(
      <PanelShell user={{ username: "ana", role: "admin" }} drawerInitiallyOpen>
        {dashboard}
      </PanelShell>,
    );

    expect(screen.getAllByRole("main")).toHaveLength(1);
    expect(screen.getByRole("link", { name: "Saltar al contenido" })).toHaveAttribute("href", "#panel-main-content");
    expect(screen.getByRole("heading", { name: "Panel" })).toBeInTheDocument();
    const drawer = screen.getByRole("dialog", { name: "Navegación" });
    expect(within(drawer).getByRole("navigation", { name: "Navegación principal" })).toBeInTheDocument();
    for (const label of ["Panel", "Clientes", "Conversaciones", "Casos", "Base de conocimientos", "Configuración"]) {
      expect(within(drawer).getByRole("button", { name: label })).toBeInTheDocument();
    }
  });

  it("hides admin-only destinations from operators and marks the current item", () => {
    render(
      <PanelShell user={{ username: "veronica", role: "operador" }} currentView="conversations" drawerInitiallyOpen>
        {dashboard}
      </PanelShell>,
    );

    const drawer = screen.getByRole("dialog", { name: "Navegación" });
    expect(within(drawer).queryByRole("button", { name: "Base de conocimientos" })).not.toBeInTheDocument();
    expect(within(drawer).queryByRole("button", { name: "Configuración" })).not.toBeInTheDocument();
    expect(within(drawer).getByRole("button", { name: "Conversaciones" })).toHaveAttribute("aria-current", "page");
  });

  it("exposes the drawer state and restores focus after Escape", async () => {
    const user = userEvent.setup();
    render(
      <PanelShell user={{ username: "ana", role: "admin" }}>
        {dashboard}
      </PanelShell>,
    );

    const menu = screen.getByRole("button", { name: "Menú" });
    expect(menu).toHaveAttribute("aria-expanded", "false");
    expect(menu).toHaveAttribute("aria-controls", "panel-navigation-drawer");

    await user.click(menu);
    expect(menu).toHaveAttribute("aria-expanded", "true");
    await waitFor(() => expect(screen.getByRole("button", { name: "Cerrar" })).toHaveFocus());

    await user.keyboard("{Escape}");
    expect(menu).toHaveAttribute("aria-expanded", "false");
    await waitFor(() => expect(menu).toHaveFocus());
  });

  it("closes on backdrop activation and forwards navigation intent", async () => {
    const onNavigate = vi.fn();
    render(
      <PanelShell user={{ username: "ana", role: "admin" }} drawerInitiallyOpen onNavigate={onNavigate}>
        {dashboard}
      </PanelShell>,
    );

    const drawer = screen.getByRole("dialog", { name: "Navegación" });
    fireEvent.click(within(drawer).getByRole("button", { name: "Clientes" }));
    expect(onNavigate).toHaveBeenCalledWith("clients");

    const menu = screen.getByRole("button", { name: "Menú" });
    fireEvent.click(menu);
    fireEvent.mouseDown(screen.getByTestId("panel-drawer-backdrop"));
    expect(menu).toHaveAttribute("aria-expanded", "false");
  });
});
