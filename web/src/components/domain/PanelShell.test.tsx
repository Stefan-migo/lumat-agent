import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PanelShell } from "./PanelShell";
import type { User } from "../../types";

const admin: User = { username: "ana", role: "admin" };
const operador: User = { username: "vero", role: "operador" };

function sidebar(container: HTMLElement) {
  return within(container.querySelector(".panel-shell__sidebar") as HTMLElement);
}

describe("PanelShell rail contract (2C-1)", () => {
  it("filters role-authorized navigation in named groups from the sidebar search", async () => {
    const user = userEvent.setup();
    const { container } = render(<PanelShell user={operador}><p>Contenido</p></PanelShell>);
    const rail = sidebar(container);

    expect(rail.getByRole("searchbox", { name: "Buscar en el menú" })).toBeInTheDocument();
    expect(rail.getByRole("group", { name: "General" })).toHaveTextContent("Panel unificado");
    expect(rail.getByRole("group", { name: "Operación" })).toHaveTextContent("Conversaciones");
    expect(rail.queryByRole("group", { name: "Administración" })).not.toBeInTheDocument();

    await user.type(rail.getByRole("searchbox", { name: "Buscar en el menú" }), "cliente");
    expect(rail.getByRole("button", { name: "Clientes" })).toBeInTheDocument();
    expect(rail.queryByRole("button", { name: "Conversaciones" })).not.toBeInTheDocument();
  });

  it("provides desktop back, breadcrumb, notification, and account actions", async () => {
    const user = userEvent.setup();
    const logout = vi.fn();
    const back = vi.spyOn(window.history, "back");
    render(<PanelShell user={admin} currentView="clients" onLogout={logout}><p>Contenido</p></PanelShell>);

    expect(screen.getByRole("navigation", { name: "Ruta de navegación" })).toHaveTextContent("Clientes");
    await user.click(screen.getByRole("button", { name: "Volver" }));
    expect(back).toHaveBeenCalledOnce();
    expect(screen.getByRole("button", { name: "Cargando notificaciones" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /abrir menú de usuario/i }));
    expect(screen.getByRole("menu", { name: "Cuenta de ana" })).toBeInTheDocument();
    await user.click(within(screen.getByRole("menu", { name: "Cuenta de ana" })).getByRole("menuitem", { name: "Cerrar sesión" }));
    expect(logout).toHaveBeenCalledOnce();
    back.mockRestore();
  });

  it("shows chat to an operador while keeping privileged sections hidden", () => {
    const { container } = render(<PanelShell user={operador}><p>Contenido</p></PanelShell>);
    const rail = sidebar(container);
    expect(rail.getByRole("button", { name: "Asistente Lumat" })).toBeInTheDocument();
    for (const label of ["Base de Conocimientos", "Automatizaciones", "Configuración", "Usuarios"]) {
      expect(rail.queryByRole("button", { name: label })).not.toBeInTheDocument();
    }
    const footer = within(container.querySelector(".panel-shell__footer-nav") as HTMLElement);
    expect(footer.getByRole("button", { name: "Agente Lumat" })).toBeInTheDocument();
  });

  it("enters focus mode from the keyboard, traps focus, and restores the trigger on Escape", async () => {
    const user = userEvent.setup();
    render(<PanelShell user={admin}><button type="button">Content action</button></PanelShell>);
    const trigger = screen.getByRole("button", { name: /modo foco/i });
    trigger.focus();

    await user.keyboard("[Enter]");
    expect(screen.getByRole("region", { name: /modo foco/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /salir del modo foco/i })).toHaveFocus();

    await user.keyboard("[Escape]");
    expect(screen.queryByRole("region", { name: /modo foco/i })).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

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
