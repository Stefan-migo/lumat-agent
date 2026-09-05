import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent, ReactNode } from "react";
import type { User } from "../../types";
import { Badge } from "../primitives/Badge";
import { Avatar } from "../primitives/Avatar";

export type PanelView = "dashboard" | "clients" | "conversations" | "cases" | "notifications" | "push" | "chat" | "kb" | "settings";

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

function PanelToggleIcon({ collapsed }: { collapsed: boolean }) {
  return icon(
    <>
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M9 3v18" />
      {collapsed ? <path d="m13 9 3 3-3 3" /> : <path d="m16 9-3 3 3 3" />}
    </>,
  );
}

function LogoutIcon() {
  return icon(
    <>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <path d="m16 17 5-5-5-5" />
      <path d="M21 12H9" />
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
  notifications: { label: "Notificaciones", icon: ChatIcon },
  push: { label: "Notificaciones push", icon: ChatIcon },
  chat: { label: "Asistente Lumat", icon: ChatIcon, adminOnly: true },
  kb: { label: "Base de conocimientos", icon: BookIcon, adminOnly: true },
  settings: { label: "Configuración", icon: GearIcon, adminOnly: true },
};

const BRAND_ASSET_BASE = `${import.meta.env.BASE_URL}brand`;

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
    <div
      className={mobile ? "panel-shell__mobile-brand" : "panel-shell__brand"}
      role="img"
      aria-label="Lumat, panel operativo"
    >
      {compact ? (
        <img className="panel-shell__brand-mark" src={`${BRAND_ASSET_BASE}/lumat-mark.png`} alt="" aria-hidden="true" />
      ) : (
        <img className="panel-shell__brand-image" src={`${BRAND_ASSET_BASE}/lumat-logo.png`} alt="Lumat" />
      )}
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
      <span className="panel-shell__user-identity">
        <Avatar name={user.username} className="panel-shell__user-avatar" />
        {compact ? null : (
          <span className="panel-shell__user-copy">
            <span className="panel-shell__username">{user.username}</span>
            <span className="panel-shell__role">{role}</span>
          </span>
        )}
      </span>
      {onLogout ? (
        <button
          type="button"
          className="panel-shell__logout"
          aria-label="Cerrar sesión"
          title="Cerrar sesión"
          onClick={() => void onLogout()}
        >
          <LogoutIcon />
          <span className="panel-shell__logout-label">Cerrar sesión</span>
        </button>
      ) : null}
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
      <a className="panel-shell__skip-link" href="#panel-main-content">Saltar al contenido</a>

      <aside id="panel-shell-sidebar" className="panel-shell__sidebar" aria-label="Panel de navegación">
        <div className="panel-shell__sidebar-inner">
          <Brand compact={collapsed} />
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
            <button
              type="button"
              className="panel-shell__collapse-button"
              aria-expanded={!collapsed}
              aria-controls="panel-shell-sidebar"
              aria-label={collapsed ? "Expandir panel lateral" : "Colapsar panel lateral"}
              title={collapsed ? "Expandir panel lateral" : "Colapsar panel lateral"}
              onClick={() => setCollapsed((value) => !value)}
            >
              <PanelToggleIcon collapsed={collapsed} />
            </button>
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
