import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent, ReactNode } from "react";
import type { User } from "../../types";
import { Badge } from "../primitives/Badge";
import { Avatar } from "../primitives/Avatar";

export type PanelView = "dashboard" | "clients" | "conversations" | "cases" | "chat" | "kb" | "settings";

/** Shell icon wrapper: 20px, stroke-based, `currentColor`, aria-hidden.
 *  Inline SVGs on purpose — no icon library (ponytail: no new deps). */
const icon = (children: ReactNode) => (
  <svg
    viewBox="0 0 24 24"
    width={20}
    height={20}
    fill="none"
    stroke="currentColor"
    strokeWidth={2}
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    {children}
  </svg>
);

function PanelIcon() {
  return icon(
    <>
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
    </>,
  );
}

function UsersIcon() {
  return icon(
    <>
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </>,
  );
}

function ChatIcon() {
  return icon(<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />);
}

function BriefcaseIcon() {
  return icon(
    <>
      <rect x="2" y="7" width="20" height="14" rx="2" />
      <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
    </>,
  );
}

function BookIcon() {
  return icon(
    <>
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </>,
  );
}

function GearIcon() {
  return icon(
    <>
      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
      <circle cx="12" cy="12" r="3" />
    </>,
  );
}

function CollapseIcon() {
  return icon(
    <>
      <path d="m11 17-5-5 5-5" />
      <path d="m18 17-5-5 5-5" />
    </>,
  );
}

interface NavigationItem {
  label: string;
  icon: () => ReactNode;
  adminOnly?: boolean;
}

const NAVIGATION: Record<PanelView, NavigationItem> = {
  dashboard: { label: "Panel", icon: PanelIcon },
  clients: { label: "Clientes", icon: UsersIcon },
  conversations: { label: "Conversaciones", icon: ChatIcon },
  cases: { label: "Casos", icon: BriefcaseIcon },
  chat: { label: "Asistente Lumat", icon: ChatIcon, adminOnly: true },
  kb: { label: "Base de conocimientos", icon: BookIcon, adminOnly: true },
  settings: { label: "Configuración", icon: GearIcon, adminOnly: true },
};

const PANEL_SHELL_STYLES = `
  .panel-shell,
  .panel-shell * {
    box-sizing: border-box;
  }

  .panel-shell {
    min-height: 100vh;
    background: var(--corp-bg);
    color: var(--corp-fg);
    font-family: var(--font-sans);
  }

  .panel-shell__skip-link {
    position: fixed;
    inset: var(--space-2) auto auto var(--space-2);
    z-index: var(--z-modal);
    padding: var(--space-2) var(--space-3);
    border-radius: var(--radius-sm);
    background: var(--corp-primary);
    color: var(--corp-primary-fg);
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
    border-bottom: 1px solid var(--corp-border);
    background: var(--corp-surface);
  }

  .panel-shell__brand {
    display: grid;
    gap: var(--space-1);
    padding: var(--space-5) var(--space-4);
    border-left: var(--space-1) solid var(--brand-lime);
    background: var(--corp-primary);
    color: var(--corp-primary-fg);
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
    color: var(--corp-primary);
  }

  .panel-shell__mobile-brand .panel-shell__brand-context {
    color: var(--corp-accent);
  }

  .panel-shell__sidebar {
    display: none;
    min-width: 0;
    overflow: hidden;
    border-right: 1px solid color-mix(in srgb, var(--corp-primary-fg) 25%, transparent);
    background: var(--corp-primary);
  }

  /* Desktop sidebar renders as one continuous dark-green panel; the mobile
   * drawer keeps the cream base (split from the shared rule below). */
  .panel-shell__sidebar-inner {
    display: flex;
    min-width: 0;
    min-height: 100%;
    flex-direction: column;
    background: var(--corp-primary);
  }

  .panel-shell__drawer {
    display: flex;
    min-height: 100%;
    flex-direction: column;
    background: var(--corp-bg);
  }

  /* Sidebar controls on the dark green: white text, green hover, lime
   * focus ring (the shared --focus-ring would be invisible on green).
   * Scoped to the sidebar — the drawer keeps the cream/dark styling. */
  .panel-shell__sidebar .panel-shell__navigation-button {
    color: var(--corp-primary-fg);
  }

  /* ponytail: --corp-surface-hover resolves light (--table-head-bg), so the
   * dark-green sidebar needs a brand-scale hover that the contract slot cannot
   * provide. Shell-scoped exception: --primary-700 stays on the brand scale
   * (hex-free), the same lane the active --primary-900 and lime focus use. */
  .panel-shell__sidebar .panel-shell__navigation-button:hover {
    background: var(--primary-700);
  }

  .panel-shell__sidebar .panel-shell__navigation-button[aria-current="page"] {
    background: var(--primary-900);
    color: var(--corp-primary-fg);
  }

  .panel-shell__sidebar .panel-shell__collapse-button:focus-visible,
  .panel-shell__sidebar .panel-shell__navigation-button:focus-visible {
    outline: var(--focus-ring-width) solid var(--brand-lime);
    outline-offset: var(--focus-ring-offset);
  }

  .panel-shell__sidebar .panel-shell__user {
    border-top-color: color-mix(in srgb, var(--corp-primary-fg) 25%, transparent);
    color: var(--corp-primary-fg);
  }

  .panel-shell__sidebar .panel-shell__role {
    color: var(--brand-aqua);
  }

  .panel-shell__navigation {
    min-width: 0;
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
  .panel-shell__collapse-button,
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
    display: flex;
    align-items: center;
    gap: var(--space-2);
    width: 100%;
    padding: var(--space-2) var(--space-3);
    border-left: var(--space-1) solid transparent;
    background: transparent;
    color: var(--corp-fg);
  }

  .panel-shell__navigation-button svg {
    flex: none;
  }

  .panel-shell__nav-label {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .panel-shell__navigation-button:hover {
    background: var(--corp-surface-hover);
  }

  .panel-shell__navigation-button[aria-current="page"] {
    border-left-color: var(--brand-lime);
    background: var(--primary-100);
    color: var(--corp-primary);
  }

  /* Desktop sidebar collapse toggle: small ghost square icon button
   * (WAI-ARIA disclosure pattern — text equivalent lives in aria-label).
   * Bug 1: the shared 44px min-height (calc(space-8 + space-3)) is escaped by
   * an explicit 2.25rem while the 2.5rem box keeps a >=40px hit target. */
  .panel-shell__collapse-button {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 2.5rem;
    height: 2.5rem;
    min-height: 2.25rem;
    margin: 0 var(--space-3) var(--space-3);
    padding: 0;
    background: transparent;
    color: var(--corp-primary-fg);
  }

  .panel-shell__collapse-button:hover {
    background: var(--primary-700);
  }

  .panel-shell__navigation-button:focus-visible,
  .panel-shell__collapse-button:focus-visible,
  .panel-shell__menu-button:focus-visible,
  .panel-shell__drawer-close:focus-visible {
    outline: var(--focus-ring-width) solid var(--focus-ring);
    outline-offset: var(--focus-ring-offset);
  }

  .panel-shell__menu-button,
  .panel-shell__drawer-close {
    padding: var(--space-2) var(--space-3);
    border-color: var(--border-strong);
    background: var(--corp-surface);
    color: var(--corp-primary);
  }

  .panel-shell__user {
    display: grid;
    grid-template-columns: var(--space-8) minmax(0, 1fr);
    gap: var(--space-2);
    align-items: center;
    margin-top: auto;
    padding: var(--space-4);
    border-top: 1px solid var(--corp-border);
    color: var(--corp-fg);
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
    color: var(--corp-fg-muted);
    font-size: var(--text-xs);
  }

  .panel-shell__content-area {
    display: grid;
    grid-template-rows: auto minmax(0, 1fr);
    min-width: 0;
    min-height: 0;
  }

  .panel-shell__header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    padding-right: var(--space-4);
    background: var(--corp-surface);
    border-bottom: 1px solid var(--corp-border);
  }

  .panel-shell__header {
    display: flex;
    flex: 1;
    min-width: 0;
    align-items: center;
    padding: var(--space-4) var(--space-6);
    color: var(--corp-fg);
  }

  .panel-shell__header-badge {
    display: flex;
    align-items: center;
    gap: var(--space-2);
  }

  .panel-shell__header-title {
    margin: 0;
    font-size: var(--text-lg);
    font-weight: var(--weight-semibold);
    line-height: var(--leading-tight);
    letter-spacing: -0.01em;
    color: var(--corp-fg);
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
    border-bottom: 1px solid var(--corp-border);
  }

  .panel-shell__drawer-title {
    margin: 0;
    color: var(--corp-fg);
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

    .panel-shell__content-area {
      grid-column: 2;
    }

    .panel-shell__content {
      padding: var(--space-6);
    }

    /* Collapsed (icon-only) sidebar: narrow column, centered marks. */
    .panel-shell--collapsed {
      grid-template-columns: calc(var(--space-8) * 3) minmax(0, 1fr);
    }

    .panel-shell--collapsed .panel-shell__brand {
      justify-items: center;
      padding: var(--space-5) var(--space-2);
    }

    .panel-shell--collapsed .panel-shell__navigation {
      padding: var(--space-4) var(--space-2);
    }

    .panel-shell--collapsed .panel-shell__navigation-button {
      justify-content: center;
      padding: var(--space-2);
    }

    .panel-shell--collapsed .panel-shell__collapse-button {
      align-self: center;
      margin-bottom: var(--space-3);
    }

    .panel-shell--collapsed .panel-shell__collapse-button svg {
      transform: rotate(180deg);
    }

    .panel-shell--collapsed .panel-shell__user {
      grid-template-columns: 1fr;
      justify-items: center;
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
  onLogout?: () => void | Promise<void>;
  user: User;
  /** Optional badge/chip rendered to the right of the panel header (e.g. a
   *  stale-data indicator). Kept narrow on purpose — full banner copy still
   *  belongs in the page content, not the chrome. */
  statusBadge?: ReactNode;
}

function Brand({ mobile = false, compact = false }: { mobile?: boolean; compact?: boolean }) {
  return (
    <div className={mobile ? "panel-shell__mobile-brand" : "panel-shell__brand"} aria-label="Lumat, panel operativo">
      <span className="panel-shell__brand-name">{compact ? "L" : "Lumat"}</span>
      {compact ? null : <span className="panel-shell__brand-context">Panel operativo</span>}
    </div>
  );
}

function UserContext({ user, compact = false, onLogout }: { user: User; compact?: boolean; onLogout?: () => void | Promise<void> }) {
  const role = user.role === "admin" ? "Administrador" : "Operador";
  return (
    <div
      className="panel-shell__user"
      aria-label={compact ? `${user.username} — ${role}` : undefined}
      title={compact ? `${user.username} — ${role}` : undefined}
    >
      <Avatar name={user.username} className="panel-shell__user-avatar" />
      {compact ? null : (
        <span className="panel-shell__user-copy">
          <span className="panel-shell__username">{user.username}</span>
          <span className="panel-shell__role">{role}</span>
          {onLogout ? <button type="button" onClick={() => void onLogout()}>Cerrar sesión</button> : null}
        </span>
      )}
    </div>
  );
}

function Navigation({
  currentView,
  onNavigate,
  user,
  collapsed = false,
}: Pick<PanelShellProps, "currentView" | "onNavigate" | "user"> & { collapsed?: boolean }) {
  const items = (Object.keys(NAVIGATION) as PanelView[]).filter(
    (view) => !NAVIGATION[view].adminOnly || user.role === "admin",
  );

  return (
    <nav className="panel-shell__navigation" aria-label="Navegación principal">
      <ul className="panel-shell__navigation-list">
        {items.map((view) => {
          const Icon = NAVIGATION[view].icon;
          return (
            <li key={view}>
              <button
                type="button"
                className="panel-shell__navigation-button"
                aria-current={currentView === view ? "page" : undefined}
                aria-label={collapsed ? NAVIGATION[view].label : undefined}
                title={collapsed ? NAVIGATION[view].label : undefined}
                onClick={() => onNavigate?.(view)}
              >
                <Icon />
                {collapsed ? null : <span className="panel-shell__nav-label">{NAVIGATION[view].label}</span>}
              </button>
            </li>
          );
        })}
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
  statusBadge,
  onLogout,
}: PanelShellProps) {
  const [drawerOpen, setDrawerOpen] = useState(drawerInitiallyOpen);
  const [collapsed, setCollapsed] = useState(false);
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
    <div className={`panel-shell${collapsed ? " panel-shell--collapsed" : ""}`}>
      <style>{PANEL_SHELL_STYLES}</style>
      <a className="panel-shell__skip-link" href="#panel-main-content">Saltar al contenido</a>

      <aside id="panel-shell-sidebar" className="panel-shell__sidebar" aria-label="Panel de navegación">
        <div className="panel-shell__sidebar-inner">
          <Brand compact={collapsed} />
          <button
            type="button"
            className="panel-shell__collapse-button"
            aria-expanded={!collapsed}
            aria-controls="panel-shell-sidebar"
            aria-label={collapsed ? "Expandir menú" : "Colapsar menú"}
            title={collapsed ? "Expandir menú" : "Colapsar menú"}
            onClick={() => setCollapsed((value) => !value)}
          >
            <CollapseIcon />
          </button>
          <Navigation currentView={currentView} onNavigate={handleNavigation} user={user} collapsed={collapsed} />
          <UserContext user={user} compact={collapsed} onLogout={onLogout} />
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
          <UserContext user={user} onLogout={onLogout} />
        </section>
      </div>

      <div className="panel-shell__content-area">
        <div className="panel-shell__header-row">
          <header className="panel-shell__header" aria-label="Encabezado de la vista">
            <h2 className="panel-shell__header-title">{NAVIGATION[currentView].label}</h2>
          </header>
          {statusBadge ? (
            <div className="panel-shell__header-badge">
              <Badge>{statusBadge}</Badge>
            </div>
          ) : null}
        </div>
        <div id="panel-main-content" className="panel-shell__content" tabIndex={-1}>
          {children}
        </div>
      </div>
    </div>
  );
}
