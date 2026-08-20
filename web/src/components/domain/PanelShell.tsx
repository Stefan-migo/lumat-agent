import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent, ReactNode } from "react";
import type { User } from "../../types";

export type PanelView = "dashboard" | "clients" | "conversations" | "cases" | "kb" | "settings";

interface NavigationItem {
  label: string;
  adminOnly?: boolean;
}

const NAVIGATION: Record<PanelView, NavigationItem> = {
  dashboard: { label: "Panel" },
  clients: { label: "Clientes" },
  conversations: { label: "Conversaciones" },
  cases: { label: "Casos" },
  kb: { label: "Base de conocimientos", adminOnly: true },
  settings: { label: "Configuración", adminOnly: true },
};

const PANEL_SHELL_STYLES = `
  .panel-shell,
  .panel-shell * {
    box-sizing: border-box;
  }

  .panel-shell {
    min-height: 100vh;
    background: var(--bg);
    color: var(--text);
    font-family: var(--font-sans);
  }

  .panel-shell__skip-link {
    position: fixed;
    inset: var(--space-2) auto auto var(--space-2);
    z-index: var(--z-modal);
    padding: var(--space-2) var(--space-3);
    border-radius: var(--radius-sm);
    background: var(--primary-800);
    color: var(--surface);
    transform: translateY(calc(-100% - var(--space-4)));
  }

  .panel-shell__skip-link:focus {
    transform: translateY(0);
    outline: var(--focus-ring-width) solid var(--brand-lime);
    outline-offset: var(--focus-ring-offset);
  }

  .panel-shell__mobile-bar {
    position: sticky;
    top: 0;
    z-index: 10;
    display: flex;
    min-height: calc(var(--space-8) + var(--space-8));
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    padding: var(--space-2) var(--space-4);
    border-bottom: 1px solid var(--border);
    background: var(--surface);
  }

  .panel-shell__brand {
    display: grid;
    gap: var(--space-1);
    padding: var(--space-5) var(--space-4);
    border-left: var(--space-1) solid var(--brand-lime);
    background: var(--primary-800);
    color: var(--surface);
  }

  .panel-shell__mobile-brand {
    display: grid;
    gap: 0;
  }

  .panel-shell__brand-name {
    font-size: var(--text-lg);
    font-weight: var(--weight-bold);
    line-height: var(--leading-tight);
    letter-spacing: -0.02em;
  }

  .panel-shell__brand-context {
    color: var(--brand-aqua);
    font-size: var(--text-xs);
    font-weight: var(--weight-medium);
    line-height: var(--leading-snug);
  }

  .panel-shell__mobile-brand .panel-shell__brand-name {
    color: var(--primary-800);
  }

  .panel-shell__mobile-brand .panel-shell__brand-context {
    color: var(--info);
  }

  .panel-shell__sidebar {
    display: none;
    min-width: 0;
    border-right: 1px solid var(--border);
    background: var(--surface);
  }

  .panel-shell__sidebar-inner,
  .panel-shell__drawer {
    display: flex;
    min-height: 100%;
    flex-direction: column;
    background: var(--surface);
  }

  .panel-shell__navigation {
    padding: var(--space-4) var(--space-3);
  }

  .panel-shell__navigation-list {
    display: grid;
    gap: var(--space-1);
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .panel-shell__navigation-button,
  .panel-shell__menu-button,
  .panel-shell__drawer-close {
    min-height: calc(var(--space-8) + var(--space-3));
    border: 1px solid transparent;
    border-radius: var(--radius-sm);
    font: inherit;
    font-size: var(--text-sm);
    font-weight: var(--weight-semibold);
    cursor: pointer;
  }

  .panel-shell__navigation-button {
    width: 100%;
    padding: var(--space-2) var(--space-3);
    border-left: var(--space-1) solid transparent;
    background: transparent;
    color: var(--text);
    text-align: left;
  }

  .panel-shell__navigation-button:hover {
    background: var(--table-head-bg);
  }

  .panel-shell__navigation-button[aria-current="page"] {
    border-left-color: var(--brand-lime);
    background: var(--primary-100);
    color: var(--primary-800);
  }

  .panel-shell__navigation-button:focus-visible,
  .panel-shell__menu-button:focus-visible,
  .panel-shell__drawer-close:focus-visible {
    outline: var(--focus-ring-width) solid var(--focus-ring);
    outline-offset: var(--focus-ring-offset);
  }

  .panel-shell__menu-button,
  .panel-shell__drawer-close {
    padding: var(--space-2) var(--space-3);
    border-color: var(--border-strong);
    background: var(--surface);
    color: var(--primary-800);
  }

  .panel-shell__user {
    display: grid;
    grid-template-columns: var(--space-8) minmax(0, 1fr);
    gap: var(--space-2);
    align-items: center;
    margin-top: auto;
    padding: var(--space-4);
    border-top: 1px solid var(--border);
    color: var(--text);
  }

  .panel-shell__avatar {
    display: grid;
    width: var(--space-8);
    height: var(--space-8);
    place-items: center;
    border-radius: var(--radius-md);
    background: var(--brand-aqua);
    color: var(--primary-800);
    font-size: var(--text-sm);
    font-weight: var(--weight-bold);
  }

  .panel-shell__user-copy {
    display: grid;
    min-width: 0;
    gap: var(--space-1);
  }

  .panel-shell__username {
    overflow: hidden;
    font-size: var(--text-sm);
    font-weight: var(--weight-semibold);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .panel-shell__role {
    color: var(--text-muted);
    font-size: var(--text-xs);
  }

  .panel-shell__content {
    min-width: 0;
    padding: var(--space-4);
  }

  .panel-shell__content:focus {
    outline: none;
  }

  .panel-shell__drawer-layer {
    position: fixed;
    inset: 0;
    z-index: var(--z-modal);
    background: color-mix(in srgb, var(--primary-900) 62%, transparent);
    animation: panel-backdrop-in var(--duration-base) var(--ease-out);
  }

  .panel-shell__drawer-layer[hidden] {
    display: none;
  }

  .panel-shell__drawer {
    width: min(calc(var(--space-8) * 9), calc(100vw - var(--space-8)));
    height: 100%;
    box-shadow: var(--shadow-3);
    animation: panel-drawer-in var(--duration-slow) var(--ease-out);
  }

  .panel-shell__drawer-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-2);
    padding: var(--space-3) var(--space-4);
    border-bottom: 1px solid var(--border);
  }

  .panel-shell__drawer-title {
    margin: 0;
    color: var(--text);
    font-size: var(--text-md);
  }

  @keyframes panel-drawer-in {
    from { transform: translateX(-100%); }
    to { transform: translateX(0); }
  }

  @keyframes panel-backdrop-in {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @media (min-width: 40rem) {
    .panel-shell__content {
      padding: var(--space-5);
    }
  }

  @media (min-width: 64rem) {
    .panel-shell {
      display: grid;
      grid-template-columns: calc(var(--space-8) * 6) minmax(0, 1fr);
    }

    .panel-shell__mobile-bar,
    .panel-shell__drawer-layer {
      display: none;
    }

    .panel-shell__sidebar {
      position: sticky;
      top: 0;
      display: block;
      height: 100vh;
    }

    .panel-shell__content {
      grid-column: 2;
      padding: var(--space-6);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .panel-shell__drawer,
    .panel-shell__drawer-layer {
      animation: none;
    }
  }
`;

export interface PanelShellProps {
  children: ReactNode;
  currentView?: PanelView;
  drawerInitiallyOpen?: boolean;
  onNavigate?: (view: PanelView) => void;
  user: User;
}

function Brand({ mobile = false }: { mobile?: boolean }) {
  return (
    <div className={mobile ? "panel-shell__mobile-brand" : "panel-shell__brand"} aria-label="Lumat, panel operativo">
      <span className="panel-shell__brand-name">Lumat</span>
      <span className="panel-shell__brand-context">Panel operativo</span>
    </div>
  );
}

function UserContext({ user }: { user: User }) {
  const role = user.role === "admin" ? "Administrador" : "Operador";
  return (
    <div className="panel-shell__user">
      <span className="panel-shell__avatar" aria-hidden="true">{user.username.slice(0, 1).toUpperCase()}</span>
      <span className="panel-shell__user-copy">
        <span className="panel-shell__username">{user.username}</span>
        <span className="panel-shell__role">{role}</span>
      </span>
    </div>
  );
}

function Navigation({
  currentView,
  onNavigate,
  user,
}: Pick<PanelShellProps, "currentView" | "onNavigate" | "user">) {
  const items = (Object.keys(NAVIGATION) as PanelView[]).filter(
    (view) => !NAVIGATION[view].adminOnly || user.role === "admin",
  );

  return (
    <nav className="panel-shell__navigation" aria-label="Navegación principal">
      <ul className="panel-shell__navigation-list">
        {items.map((view) => (
          <li key={view}>
            <button
              type="button"
              className="panel-shell__navigation-button"
              aria-current={currentView === view ? "page" : undefined}
              onClick={() => onNavigate?.(view)}
            >
              {NAVIGATION[view].label}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}

export function PanelShell({
  children,
  currentView = "dashboard",
  drawerInitiallyOpen = false,
  onNavigate,
  user,
}: PanelShellProps) {
  const [drawerOpen, setDrawerOpen] = useState(drawerInitiallyOpen);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const drawerRef = useRef<HTMLElement>(null);

  const closeDrawer = () => {
    setDrawerOpen(false);
    queueMicrotask(() => menuButtonRef.current?.focus());
  };

  useEffect(() => {
    if (drawerOpen) closeButtonRef.current?.focus();
  }, [drawerOpen]);

  useEffect(() => {
    if (!drawerOpen) return;
    const handleEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") closeDrawer();
    };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [drawerOpen]);

  const keepFocusInDrawer = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key !== "Tab") return;
    const focusable = [...(drawerRef.current?.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
    ) ?? [])];
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const handleNavigation = (view: PanelView) => {
    onNavigate?.(view);
    if (drawerOpen) closeDrawer();
  };

  return (
    <div className="panel-shell">
      <style>{PANEL_SHELL_STYLES}</style>
      <a className="panel-shell__skip-link" href="#panel-main-content">Saltar al contenido</a>

      <aside className="panel-shell__sidebar" aria-label="Panel de navegación">
        <div className="panel-shell__sidebar-inner">
          <Brand />
          <Navigation currentView={currentView} onNavigate={handleNavigation} user={user} />
          <UserContext user={user} />
        </div>
      </aside>

      <header className="panel-shell__mobile-bar">
        <Brand mobile />
        <button
          ref={menuButtonRef}
          type="button"
          className="panel-shell__menu-button"
          aria-expanded={drawerOpen}
          aria-controls="panel-navigation-drawer"
          onClick={() => setDrawerOpen(true)}
        >
          Menú
        </button>
      </header>

      <div
        className="panel-shell__drawer-layer"
        data-testid="panel-drawer-backdrop"
        hidden={!drawerOpen}
        onMouseDown={(event) => {
          if (event.target === event.currentTarget) closeDrawer();
        }}
      >
        <section
          ref={drawerRef}
          id="panel-navigation-drawer"
          className="panel-shell__drawer"
          role="dialog"
          aria-modal="true"
          aria-labelledby="panel-navigation-title"
          onKeyDown={keepFocusInDrawer}
        >
          <Brand />
          <div className="panel-shell__drawer-heading">
            <h2 id="panel-navigation-title" className="panel-shell__drawer-title">Navegación</h2>
            <button ref={closeButtonRef} type="button" className="panel-shell__drawer-close" onClick={closeDrawer}>
              Cerrar
            </button>
          </div>
          <Navigation currentView={currentView} onNavigate={handleNavigation} user={user} />
          <UserContext user={user} />
        </section>
      </div>

      <div id="panel-main-content" className="panel-shell__content" tabIndex={-1}>
        {children}
      </div>
    </div>
  );
}

