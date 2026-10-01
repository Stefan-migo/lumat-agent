import { afterEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { formatNotificationTime, PanelShell } from "./PanelShell";
import { parsePanelPath } from "./panelRoutes";
import type { User } from "../../types";

const admin: User = { username: "ana", role: "admin" };
const operador: User = { username: "vero", role: "operador" };
const notifications = [
  { id: 1, user_id: 1, operation_id: 1, title: "Atención humana requerida", content: "Carla necesita hablar con una persona.", source: "case", channel: "whatsapp", status: "sent", read_at: null, created_at: "2026-10-01T12:55:00Z" },
  { id: 2, user_id: 1, operation_id: 2, title: "Nueva visita agendada", content: "Pedro Soto · Visita de diagnóstico", source: "appointment", channel: "whatsapp", status: "sent", read_at: null, created_at: "2026-10-01T12:40:00Z" },
  { id: 3, user_id: 1, operation_id: 3, title: "Documento procesado", content: "El manual ya está disponible.", source: "document", channel: "email", status: "sent", read_at: "2026-10-01T11:00:00Z", created_at: "2026-10-01T11:00:00Z" },
];

function mockDialogMethods() {
  const showModal = vi.fn(function (this: HTMLDialogElement) { this.setAttribute("open", ""); });
  const close = vi.fn(function (this: HTMLDialogElement) { this.removeAttribute("open"); });
  Object.defineProperties(HTMLDialogElement.prototype, {
    showModal: { configurable: true, value: showModal },
    close: { configurable: true, value: close },
  });
  return { showModal, close, restore: () => {
    delete (HTMLDialogElement.prototype as Partial<HTMLDialogElement>).showModal;
    delete (HTMLDialogElement.prototype as Partial<HTMLDialogElement>).close;
  } };
}

function sidebar(container: HTMLElement) {
  return within(container.querySelector(".panel-shell__sidebar") as HTMLElement);
}

afterEach(() => {
  delete (HTMLDialogElement.prototype as Partial<HTMLDialogElement>).showModal;
  delete (HTMLDialogElement.prototype as Partial<HTMLDialogElement>).close;
});

describe("PanelShell rail contract (2C-1)", () => {
  it("filters notification rows by tab and shows unread counts and bulk action", async () => {
    const user = userEvent.setup();
    const onMarkAllNotificationsRead = vi.fn();
    render(<PanelShell user={admin} notifications={notifications} notificationState={{ status: "ready", unread: 2 }} onMarkAllNotificationsRead={onMarkAllNotificationsRead}><p>Contenido</p></PanelShell>);
    await user.click(within(document.querySelector(".panel-shell__header-actions") as HTMLElement).getByRole("button", { name: "Notificaciones (2 sin leer)" }));
    const dialog = screen.getByRole("dialog", { name: "Notificaciones" });
    expect(within(dialog).getByText("2 nuevas")).toBeInTheDocument();
    expect(within(dialog).getByRole("tab", { name: "No leídas 2" })).toBeInTheDocument();
    expect(within(dialog).getAllByRole("listitem")).toHaveLength(3);
    await user.click(within(dialog).getByRole("tab", { name: "No leídas 2" }));
    expect(within(dialog).getAllByRole("listitem")).toHaveLength(2);
    expect(within(dialog).queryByText("Documento procesado")).not.toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Marcar todas como leídas" }));
    expect(onMarkAllNotificationsRead).toHaveBeenCalledOnce();
  });

  it("renders the designed empty state", async () => {
    const user = userEvent.setup();
    render(<PanelShell user={admin} notifications={[]} notificationState={{ status: "ready", unread: 0 }}><p>Contenido</p></PanelShell>);
    await user.click(within(document.querySelector(".panel-shell__header-actions") as HTMLElement).getByRole("button", { name: "Notificaciones" }));
    const dialog = screen.getByRole("dialog", { name: "Notificaciones" });
    expect(within(dialog).getByText("No tienes notificaciones")).toBeInTheDocument();
    expect(within(dialog).getByText("Aquí verás las novedades de tus conversaciones, visitas y documentos.")).toBeInTheDocument();
    expect(within(dialog).queryByRole("button", { name: "Marcar todas como leídas" })).not.toBeInTheDocument();
  });

  it("formats notification timestamps as Chilean relative time", () => {
    const now = new Date("2026-10-01T13:00:00Z");
    expect(formatNotificationTime("2026-10-01T12:55:00Z", now)).toBe("Hace 5 min");
    expect(formatNotificationTime("2026-10-01T12:00:00Z", now)).toBe("Hace 1 h");
    expect(formatNotificationTime(null, now)).toBe("");
  });

  it("falls back malformed routes and limits mobile tabs to existing destinations", () => {
    expect(parsePanelPath("/panel/app/%E0%A4%A")).toEqual({ view: "dashboard" });
    expect(parsePanelPath("/panel/app/unknown")).toEqual({ view: "dashboard" });
    const { container } = render(<PanelShell user={admin}><p>Contenido</p></PanelShell>);
    const tabs = within(container.querySelector(".panel-shell__footer-nav") as HTMLElement);
    expect(tabs.getAllByRole("button").map((button) => button.getAttribute("aria-label"))).toEqual([
      // The mobile tab uses the short display label from the reference; the destination keeps its canonical
      // name in NAVIGATION, which is what the sidebar, the drawer and the breadcrumb render.
      "Panel", "Chats", "Asistente", "Agenda", "Clientes",
    ]);
  });

  it("keeps the collapse toggle anchored inside the sidebar (DS-SHELL-1)", () => {
    // DS-SHELL-1: the toggle must stay anchored within the sidebar. It used to render in the content
    // header, which the canonical requirement forbids; this asserts the placement at the DOM level
    // instead of pinning CSS text.
    const { container } = render(<PanelShell user={admin}><p>Contenido</p></PanelShell>);
    const sidebarEl = container.querySelector(".panel-shell__sidebar");
    expect(sidebarEl?.querySelector(".panel-shell__collapse-button")).not.toBeNull();
    expect(container.querySelector(".panel-shell__header .panel-shell__collapse-button")).toBeNull();
  });

  it("keeps every rail control named when the compact tier visually hides its label", () => {
    // The tablet rail hides the label text visually instead of removing it, because the text is what
    // supplies each control's accessible name (canonical: compact sidebar navigation with accessible
    // names). This guards the tempting shortcut of deleting the label to stop it wrapping.
    const { container } = render(<PanelShell user={admin}><p>Contenido</p></PanelShell>);
    const rail = container.querySelectorAll(".panel-shell__sidebar .panel-shell__navigation-button");
    expect(rail).toHaveLength(9);
    for (const button of rail) {
      expect((button.getAttribute("aria-label") ?? button.textContent ?? "").trim()).not.toBe("");
    }
  });

  it("keeps administrator destinations out of every operator navigation surface", async () => {
    const user = userEvent.setup();
    const { restore } = mockDialogMethods();
    const { container } = render(<PanelShell user={operador}><p>Contenido</p></PanelShell>);
    const restricted = ["Base de Conocimientos", "Automatizaciones", "Configuración", "Usuarios"];
    const tabs = within(container.querySelector(".panel-shell__footer-nav") as HTMLElement);
    for (const label of restricted) expect(tabs.queryByRole("button", { name: label })).not.toBeInTheDocument();
    const menu = container.querySelector(".panel-shell__menu-button") as HTMLButtonElement;
    await user.click(menu);
    const drawer = screen.getByRole("dialog", { name: "Navegación" });
    for (const label of restricted) expect(within(drawer).queryByRole("button", { name: label })).not.toBeInTheDocument();
    await user.click(within(drawer).getByRole("button", { name: "Cerrar menú de navegación" }));
    const rail = sidebar(container);
    await user.type(rail.getByRole("searchbox", { name: "Buscar en el menú" }), "usuarios");
    expect(rail.queryByRole("button", { name: "Usuarios" })).not.toBeInTheDocument();
    restore();
  });

  it("opens a native modal dialog, contains keyboard traversal, and restores trigger focus on Escape", async () => {
    const user = userEvent.setup();
    const { showModal, close, restore } = mockDialogMethods();
    render(<PanelShell user={admin}><p>Contenido</p></PanelShell>);
    const trigger = document.querySelector(".panel-shell__menu-button") as HTMLButtonElement;
    await user.click(trigger);
    const dialog = screen.getByRole("dialog", { name: "Navegación" }) as HTMLDialogElement;
    expect(showModal).toHaveBeenCalledOnce();
    expect(dialog).toHaveAttribute("open");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    const closeButton = within(dialog).getByRole("button", { name: "Cerrar menú de navegación" });
    expect(closeButton).toHaveFocus();
    await user.tab();
    expect(within(dialog).getByRole("searchbox", { name: "Buscar en el menú" })).toHaveFocus();
    await user.tab();
    expect(within(dialog).getByRole("button", { name: "Panel unificado" })).toHaveFocus();
    expect(dialog.contains(document.activeElement)).toBe(true);
    fireEvent(dialog, new Event("cancel", { cancelable: true }));
    expect(close).toHaveBeenCalledOnce();
    await waitFor(() => expect(trigger).toHaveFocus());
    restore();
  });

  it("preserves body overflow and closes/unlocks/restores focus when resized to desktop", async () => {
    const user = userEvent.setup();
    const { restore } = mockDialogMethods();
    const originalWidth = window.innerWidth;
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 768 });
    document.body.style.overflow = "clip";
    const { unmount } = render(<PanelShell user={admin}><p>Contenido</p></PanelShell>);
    const trigger = document.querySelector(".panel-shell__menu-button") as HTMLButtonElement;
    await user.click(trigger);
    expect(document.body.style.overflow).toBe("hidden");
    expect(document.querySelector(".panel-shell__content-area")).toHaveAttribute("inert");
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 640 });
    act(() => window.dispatchEvent(new Event("resize")));
    expect(screen.getByRole("dialog", { name: "Navegación" })).toHaveAttribute("open");
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1024 });
    act(() => window.dispatchEvent(new Event("resize")));
    expect(screen.queryByRole("dialog", { name: "Navegación" })).not.toBeInTheDocument();
    expect(document.body.style.overflow).toBe("clip");
    expect(document.querySelector(".panel-shell__content-area")).not.toHaveAttribute("inert");
    await waitFor(() => expect(screen.getByRole("button", { name: "Colapsar panel lateral" })).toHaveFocus());
    await user.click(trigger);
    unmount();
    expect(document.body.style.overflow).toBe("clip");
    document.body.style.overflow = "";
    Object.defineProperty(window, "innerWidth", { configurable: true, value: originalWidth });
    restore();
  });

  it("restores body overflow and clears inert when unmounted while the drawer is open", async () => {
    const user = userEvent.setup();
    const { restore } = mockDialogMethods();
    const originalWidth = window.innerWidth;
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 768 });
    document.body.style.overflow = "clip";
    const { unmount } = render(<PanelShell user={admin}><p>Contenido</p></PanelShell>);
    const contentArea = document.querySelector(".panel-shell__content-area") as HTMLElement;
    const trigger = document.querySelector(".panel-shell__menu-button") as HTMLButtonElement;
    await user.click(trigger);
    expect(screen.getByRole("dialog", { name: "Navegación" })).toHaveAttribute("open");
    expect(document.body.style.overflow).toBe("hidden");
    expect(contentArea).toHaveAttribute("inert");

    unmount();

    expect(document.body.style.overflow).toBe("clip");
    expect(contentArea).not.toHaveAttribute("inert");
    document.body.style.overflow = "";
    Object.defineProperty(window, "innerWidth", { configurable: true, value: originalWidth });
    restore();
  });

  it("calls navigation once from the drawer and closes the modal", async () => {
    const user = userEvent.setup();
    const onNavigate = vi.fn();
    const { restore } = mockDialogMethods();
    render(<PanelShell user={admin} onNavigate={onNavigate}><p>Contenido</p></PanelShell>);
    await user.click(document.querySelector(".panel-shell__menu-button") as HTMLButtonElement);
    await user.click(within(screen.getByRole("dialog", { name: "Navegación" })).getByRole("button", { name: "Agenda" }));
    expect(onNavigate).toHaveBeenCalledExactlyOnceWith("agenda");
    expect(screen.queryByRole("dialog", { name: "Navegación" })).not.toBeInTheDocument();
    restore();
  });

  it("keeps notification and account accessible header actions functional", async () => {
    const user = userEvent.setup();
    const { container } = render(<PanelShell user={admin} notificationState={{ status: "ready", unread: 2 }}><p>Contenido</p></PanelShell>);
    // The mobile bar exposes the same bell and account names, so the desktop assertions stay scoped to the header group.
    const header = within(container.querySelector(".panel-shell__header-actions") as HTMLElement);
    await user.click(header.getByRole("button", { name: "Notificaciones (2 sin leer)" }));
    expect(screen.getByRole("dialog", { name: "Notificaciones" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cerrar notificaciones" }));
    await user.click(header.getByRole("button", { name: "Abrir menú de usuario" }));
    expect(screen.getByRole("menu", { name: "Cuenta de ana" })).toBeInTheDocument();
  });

  it("navigates to the self-profile from the account menu", async () => {
    const user = userEvent.setup();
    const onNavigate = vi.fn();
    const { container } = render(<PanelShell user={operador} onNavigate={onNavigate}><p>Contenido</p></PanelShell>);
    const header = within(container.querySelector(".panel-shell__header-actions") as HTMLElement);
    await user.click(header.getByRole("button", { name: "Abrir menú de usuario" }));
    await user.click(within(screen.getByRole("menu", { name: "Cuenta de vero" })).getByRole("menuitem", { name: "Mi perfil" }));
    expect(onNavigate).toHaveBeenCalledExactlyOnceWith("profile");
  });

  it("exposes the bell and the account affordance in the mobile header (PNL-APP-10)", async () => {
    const user = userEvent.setup();
    const onNavigate = vi.fn();
    const { container } = render(<PanelShell user={admin} notificationState={{ status: "ready", unread: 3 }} onNavigate={onNavigate}><p>Contenido</p></PanelShell>);
    const bar = within(container.querySelector(".panel-shell__mobile-bar") as HTMLElement);

    expect(bar.getByRole("button", { name: "Notificaciones (3 sin leer)" })).toBeInTheDocument();
    await user.click(bar.getByRole("button", { name: "Abrir menú de usuario" }));
    expect(bar.getByRole("menu", { name: "Cuenta de ana" })).toBeInTheDocument();

    // The popover lives in the desktop header, which is hidden below 64rem, so the mobile bell navigates instead.
    await user.click(bar.getByRole("button", { name: "Notificaciones (3 sin leer)" }));
    expect(onNavigate).toHaveBeenCalledExactlyOnceWith("notifications");
  });

  it("uses the one-line lockup in the mobile bar and the stacked lockup in the drawer", () => {
    const { container } = render(<PanelShell user={admin}><p>Contenido</p></PanelShell>);
    const bar = container.querySelector(".panel-shell__mobile-bar") as HTMLElement;
    const drawer = container.querySelector(".panel-shell__drawer") as HTMLElement;

    expect(bar.querySelector(".panel-shell__brand-image")).toHaveAttribute("src", "/panel/app/brand/lumat-logo-line.png");
    expect(drawer.querySelector(".panel-shell__brand-image")).toHaveAttribute("src", "/panel/app/brand/lumat-logo.png");
    expect(bar.querySelector(".panel-shell__menu-button")).toBe(bar.firstElementChild);
  });

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

  it("offers a named search in the drawer that filters its destinations", async () => {
    const user = userEvent.setup();
    const { restore } = mockDialogMethods();
    render(<PanelShell user={admin}><p>Contenido</p></PanelShell>);
    await user.click(document.querySelector(".panel-shell__menu-button") as HTMLButtonElement);
    const drawer = screen.getByRole("dialog", { name: "Navegación" });

    expect(within(drawer).getByRole("button", { name: "Conversaciones" })).toBeInTheDocument();
    await user.type(within(drawer).getByRole("searchbox", { name: "Buscar en el menú" }), "cliente");
    expect(within(drawer).getByRole("button", { name: "Clientes" })).toBeInTheDocument();
    expect(within(drawer).queryByRole("button", { name: "Conversaciones" })).not.toBeInTheDocument();

    await user.click(within(drawer).getByRole("button", { name: "Cerrar menú de navegación" }));
    restore();
  });

  it("expands the sidebar and focuses the field from the compact search control at desktop width", async () => {
    const user = userEvent.setup();
    const originalWidth = window.innerWidth;
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1440 });
    const { container } = render(<PanelShell user={admin}><p>Contenido</p></PanelShell>);
    const root = container.querySelector(".panel-shell") as HTMLElement;

    await user.click(container.querySelector(".panel-shell__collapse-button") as HTMLButtonElement);
    expect(root).toHaveClass("panel-shell--collapsed");

    await user.click(container.querySelector(".panel-shell__search-toggle") as HTMLButtonElement);
    expect(root).not.toHaveClass("panel-shell--collapsed");
    expect(sidebar(container).getByRole("searchbox", { name: "Buscar en el menú" })).toHaveFocus();

    Object.defineProperty(window, "innerWidth", { configurable: true, value: originalWidth });
  });

  it("opens the drawer from the compact search control at tablet width", async () => {
    const user = userEvent.setup();
    const { restore } = mockDialogMethods();
    const originalWidth = window.innerWidth;
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 768 });
    render(<PanelShell user={admin}><p>Contenido</p></PanelShell>);

    await user.click(document.querySelector(".panel-shell__search-toggle") as HTMLButtonElement);
    const drawer = screen.getByRole("dialog", { name: "Navegación" });
    expect(within(drawer).getByRole("searchbox", { name: "Buscar en el menú" })).toBeInTheDocument();

    await user.click(within(drawer).getByRole("button", { name: "Cerrar menú de navegación" }));
    Object.defineProperty(window, "innerWidth", { configurable: true, value: originalWidth });
    restore();
  });

  it("hides the back action on list routes and provides breadcrumb, notification, and account actions", async () => {
    const user = userEvent.setup();
    const logout = vi.fn();
    const { container } = render(<PanelShell user={admin} currentView="clients" onLogout={logout}><p>Contenido</p></PanelShell>);
    const header = within(container.querySelector(".panel-shell__header-actions") as HTMLElement);

    expect(screen.getByRole("navigation", { name: "Ruta de navegación" })).toHaveTextContent("Clientes");
    expect(screen.queryByRole("button", { name: "Volver" })).not.toBeInTheDocument();
    expect(header.getByRole("button", { name: "Cargando notificaciones" })).toBeInTheDocument();
    await user.click(header.getByRole("button", { name: /abrir menú de usuario/i }));
    expect(screen.getByRole("menu", { name: "Cuenta de ana" })).toBeInTheDocument();
    await user.click(within(screen.getByRole("menu", { name: "Cuenta de ana" })).getByRole("menuitem", { name: "Cerrar sesión" }));
    expect(logout).toHaveBeenCalledOnce();
  });

  it("closes the header account menu on outside click", async () => {
    const user = userEvent.setup();
    const { container } = render(<PanelShell user={admin}><p>Contenido</p></PanelShell>);
    const headerActions = container.querySelector(".panel-shell__header-actions") as HTMLElement;
    const trigger = within(headerActions).getByRole("button", { name: /abrir menú de usuario/i });

    await user.click(trigger);
    expect(screen.getByRole("menu", { name: "Cuenta de ana" })).toBeInTheDocument();
    await user.click(screen.getByText("Contenido"));

    expect(screen.queryByRole("menu", { name: "Cuenta de ana" })).not.toBeInTheDocument();
  });

  it("closes the header account menu on Escape and restores trigger focus", async () => {
    const user = userEvent.setup();
    const { container } = render(<PanelShell user={admin}><p>Contenido</p></PanelShell>);
    const headerActions = container.querySelector(".panel-shell__header-actions") as HTMLElement;
    const trigger = within(headerActions).getByRole("button", { name: /abrir menú de usuario/i });

    await user.click(trigger);
    await user.keyboard("{Escape}");

    expect(screen.queryByRole("menu", { name: "Cuenta de ana" })).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("anchors the sidebar account menu to the viewport so the sidebar clip cannot cut it", async () => {
    const user = userEvent.setup();
    render(<PanelShell user={admin} onLogout={vi.fn()}><p>Contenido</p></PanelShell>);
    await user.click(screen.getByRole("button", { name: "Más opciones de la cuenta" }));
    const menu = screen.getByRole("menu", { name: "Cuenta de ana" });
    expect(Number.parseFloat(menu.style.left)).toBeGreaterThanOrEqual(12);
    expect(Number.parseFloat(menu.style.bottom)).toBeGreaterThan(0);
  });

  it("offers Mi perfil from the sidebar account menu and navigates to it", async () => {
    const user = userEvent.setup();
    const onNavigate = vi.fn();
    render(<PanelShell user={admin} onLogout={vi.fn()} onNavigate={onNavigate}><p>Contenido</p></PanelShell>);
    await user.click(screen.getByRole("button", { name: "Más opciones de la cuenta" }));
    await user.click(screen.getByRole("menuitem", { name: "Mi perfil" }));
    expect(onNavigate).toHaveBeenCalledWith("profile");
  });

  it("renders the back action only when supplied and calls it", async () => {
    const user = userEvent.setup();
    const onBack = vi.fn();
    render(<PanelShell user={admin} currentView="clients" onBack={onBack}><p>Contenido</p></PanelShell>);
    await user.click(screen.getByRole("button", { name: "Volver" }));
    expect(onBack).toHaveBeenCalledOnce();
  });

  it("labels the dashboard breadcrumb and keeps its Panel segment unlinked", () => {
    render(<PanelShell user={admin} currentView="dashboard"><p>Contenido</p></PanelShell>);
    const breadcrumb = screen.getByRole("navigation", { name: "Ruta de navegación" });
    expect(breadcrumb).toHaveTextContent("PanelDashboard");
    expect(within(breadcrumb).queryByRole("button", { name: "Panel" })).not.toBeInTheDocument();
    expect(within(breadcrumb).getByText("Dashboard")).toHaveAttribute("aria-current", "page");
  });

  it("links Panel to Dashboard and uses the section label in the breadcrumb", () => {
    const onNavigate = vi.fn();
    render(<PanelShell user={admin} currentView="notifications" onNavigate={onNavigate}><p>Contenido</p></PanelShell>);
    const breadcrumb = within(screen.getByRole("navigation", { name: "Ruta de navegación" }));
    expect(breadcrumb.getByRole("button", { name: "Panel" })).toBeInTheDocument();
    expect(breadcrumb.getByText("Notificaciones")).toHaveAttribute("aria-current", "page");
  });

  it("shows chat to an operador while keeping privileged sections hidden", () => {
    const { container } = render(<PanelShell user={operador}><p>Contenido</p></PanelShell>);
    const rail = sidebar(container);
    expect(rail.getByRole("button", { name: "Asistente Lumat" })).toBeInTheDocument();
    for (const label of ["Base de Conocimientos", "Automatizaciones", "Configuración", "Usuarios"]) {
      expect(rail.queryByRole("button", { name: label })).not.toBeInTheDocument();
    }
    const footer = within(container.querySelector(".panel-shell__footer-nav") as HTMLElement);
    expect(footer.getByRole("button", { name: "Asistente" })).toBeInTheDocument();
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
