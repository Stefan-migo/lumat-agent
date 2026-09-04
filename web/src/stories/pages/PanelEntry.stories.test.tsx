import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it, vi } from "vitest";
import { DashboardOverview } from "./Dashboard.stories";
import { PanelShell } from "../../components/domain/PanelShell";

const dashboard = <DashboardOverview />;
const panelShellRaw = readFileSync(
  join(process.cwd(), "src", "components", "domain", "PanelShell.tsx"),
  "utf8",
);

describe("Panel entry layout", () => {
  it("keeps logout visible and accessible in expanded and collapsed account blocks", async () => {
    const onLogout = vi.fn();
    const user = userEvent.setup();
    const { container } = render(
      <PanelShell user={{ username: "ana", role: "admin" }} onLogout={onLogout}>
        {dashboard}
      </PanelShell>,
    );

    const sidebar = container.querySelector(".panel-shell__sidebar") as HTMLElement;
    const logout = sidebar.querySelector<HTMLButtonElement>(".panel-shell__logout")!;
    expect(logout).toHaveAccessibleName("Cerrar sesión");
    expect(logout).toHaveAttribute("title", "Cerrar sesión");
    await user.click(logout);
    expect(onLogout).toHaveBeenCalledOnce();

    const toggle = container.querySelector<HTMLButtonElement>(".panel-shell__collapse-button")!;
    expect(toggle).toHaveAttribute("aria-label", "Colapsar panel lateral");
    expect(toggle).toHaveAttribute("title", "Colapsar panel lateral");
    await user.click(toggle);
    const compactLogout = sidebar.querySelector<HTMLButtonElement>(".panel-shell__logout")!;
    expect(compactLogout).toHaveAccessibleName("Cerrar sesión");
    expect(compactLogout).toHaveAttribute("aria-label", "Cerrar sesión");
  });

  it("renders the confirmed logo assets for expanded, collapsed, and drawer brands", async () => {
    const user = userEvent.setup();
    const { container } = render(<PanelShell user={{ username: "ana", role: "admin" }}>{dashboard}</PanelShell>);
    const sidebar = container.querySelector(".panel-shell__sidebar") as HTMLElement;

    expect(sidebar.querySelector(".panel-shell__brand-image")).toHaveAttribute("src", "/panel/app/brand/lumat-logo.png");
    expect(sidebar.querySelector(".panel-shell__brand-image")).toHaveAttribute("alt", "Lumat");

    await user.click(container.querySelector<HTMLButtonElement>(".panel-shell__collapse-button")!);
    expect(sidebar.querySelector(".panel-shell__brand-mark")).toHaveAttribute("src", "/panel/app/brand/lumat-mark.png");
    expect(sidebar.querySelector(".panel-shell__brand-mark")).toHaveAttribute("alt", "");
    expect(sidebar.querySelector(".panel-shell__brand")).toHaveAttribute("aria-label", "Lumat, panel operativo");

    await user.click(screen.getByRole("button", { name: "Menú" }));
    const drawer = screen.getByRole("dialog", { name: "Navegación" });
    expect(within(drawer).getByAltText("Lumat")).toHaveAttribute("src", "/panel/app/brand/lumat-logo.png");
  });

  it("resets the document margin and gives the shell the full viewport height", () => {
    const tokens = readFileSync(join(process.cwd(), "src", "tokens", "tokens.css"), "utf8");
    const { container } = render(<PanelShell user={{ username: "ana", role: "admin" }}>{dashboard}</PanelShell>);

    expect(tokens).toMatch(/body\s*\{[^}]*margin:\s*0/);
    expect(container.querySelector(".panel-shell")).toBeInTheDocument();
    expect(panelShellRaw).toMatch(/\.panel-shell\s*\{[^}]*min-height:\s*100dvh/);
    expect(panelShellRaw).toMatch(/\.panel-shell__content-area\s*\{[^}]*min-height:\s*100dvh/);
  });

  it("composes the dashboard main landmark with the complete admin information architecture", () => {
    render(
      <PanelShell user={{ username: "ana", role: "admin" }} drawerInitiallyOpen>
        {dashboard}
      </PanelShell>,
    );

    expect(screen.getAllByRole("main")).toHaveLength(1);
    expect(screen.getByRole("link", { name: "Saltar al contenido" })).toHaveAttribute("href", "#panel-main-content");
    const main = screen.getByRole("main");
    expect(within(main).getByRole("heading", { name: "Panel" })).toBeInTheDocument();
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
