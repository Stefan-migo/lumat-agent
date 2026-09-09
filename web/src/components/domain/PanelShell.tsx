import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent, ReactNode } from "react";
import type { PanelNotification, User } from "../../types";
import { Badge } from "../primitives/Badge";
import { Avatar } from "../primitives/Avatar";

export type PanelView = "dashboard" | "clients" | "conversations" | "cases" | "notifications" | "push" | "chat" | "kb" | "settings" | "agenda" | "automation-rules" | "advanced-dashboard";
export type ConversationTab = "conversations" | "cases";

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

function AssistantIcon() {
  return icon(<><path d="M12 3a7 7 0 0 0-7 7v4a4 4 0 0 0 4 4h6a4 4 0 0 0 4-4v-4a7 7 0 0 0-7-7Z" /><path d="M9 12h.01M15 12h.01M9 16h6" /></>);
}

function AutomationIcon() {
  return icon(<><path d="M6 4v16M18 4v16M6 8h12M6 16h12" /><circle cx="6" cy="4" r="2" /><circle cx="18" cy="20" r="2" /></>);
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

function CalendarIcon() {
  return icon(
    <>
      <rect x="3" y="4" width="18" height="17" rx="2" />
      <path d="M16 2v4M8 2v4M3 10h18" />
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

function BellIcon() {
  return icon(<><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" /><path d="M10 21h4" /></>);
}

function MenuIcon() {
  return icon(<><path d="M4 6h16M4 12h16M4 18h16" /></>);
}

function CloseIcon() {
  return icon(<path d="M18 6 6 18M6 6l12 12" />);
}

interface NavigationItem {
  label: string;
  icon: () => ReactNode;
  adminOnly?: boolean;
}

const NAVIGATION: Record<Exclude<PanelView, "cases" | "notifications" | "push" | "advanced-dashboard">, NavigationItem> = {
  dashboard: { label: "Panel unificado", icon: PanelIcon },
  chat: { label: "Asistente Lumat", icon: AssistantIcon, adminOnly: true },
  conversations: { label: "Conversaciones", icon: ChatIcon },
  clients: { label: "Clientes", icon: UsersIcon },
  agenda: { label: "Agenda", icon: CalendarIcon },
  kb: { label: "Base de Conocimientos", icon: BookIcon, adminOnly: true },
  'automation-rules': { label: "Automatizaciones", icon: AutomationIcon, adminOnly: true },
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
  inspector?: ReactNode;
  conversationTab?: ConversationTab;
  onConversationTabChange?: (tab: ConversationTab) => void;
  notificationState?: NotificationState;
  notifications?: PanelNotification[];
  onMarkAllNotificationsRead?: () => void | Promise<void>;
}

export type NotificationState = { status: "loading" } | { status: "ready"; unread: number } | { status: "error" };

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
  const items = (Object.keys(NAVIGATION) as Array<keyof typeof NAVIGATION>).filter(
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
  inspector,
  conversationTab,
  onConversationTabChange,
  notificationState = { status: "loading" },
  notifications = [],
  onMarkAllNotificationsRead,
}: PanelShellProps) {
  const [drawerOpen, setDrawerOpen] = useState(drawerInitiallyOpen);
  const [collapsed, setCollapsed] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const drawerRef = useRef<HTMLElement>(null);
  const contentAreaRef = useRef<HTMLDivElement>(null);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const notificationsRef = useRef<HTMLDivElement>(null);
  const bellRef = useRef<HTMLButtonElement>(null);
  const notificationCloseRef = useRef<HTMLButtonElement>(null);

  const closeDrawer = () => {
    setDrawerOpen(false);
    queueMicrotask(() => menuButtonRef.current?.focus());
  };

  useEffect(() => {
    if (drawerOpen) closeButtonRef.current?.focus();
  }, [drawerOpen]);

  useEffect(() => {
    const contentArea = contentAreaRef.current;
    if (!contentArea) return;

    if (!drawerOpen) {
      contentArea.removeAttribute("inert");
      document.body.style.overflow = "";
      return;
    }

    const previousOverflow = document.body.style.overflow;
    contentArea.setAttribute("inert", "");
    document.body.style.overflow = "hidden";
    const handleEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") closeDrawer();
    };
    const handleResize = () => {
      if (window.innerWidth >= 1024) closeDrawer();
    };
    document.addEventListener("keydown", handleEscape);
    window.addEventListener("resize", handleResize);
    return () => {
      document.removeEventListener("keydown", handleEscape);
      window.removeEventListener("resize", handleResize);
      contentArea.removeAttribute("inert");
      document.body.style.overflow = previousOverflow;
    };
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

  const closeNotifications = () => {
    setNotificationsOpen(false);
    queueMicrotask(() => bellRef.current?.focus());
  };

  const keepFocusInNotifications = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      closeNotifications();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = [...(notificationsRef.current?.querySelectorAll<HTMLElement>('button:not([disabled]), [href], [tabindex]:not([tabindex="-1"])') ?? [])];
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

  useEffect(() => {
    if (!notificationsOpen) return;
    notificationCloseRef.current?.focus();
    const closeOnOutsideClick = (event: MouseEvent) => {
      if (!notificationsRef.current?.contains(event.target as Node)) closeNotifications();
    };
    document.addEventListener("mousedown", closeOnOutsideClick);
    return () => document.removeEventListener("mousedown", closeOnOutsideClick);
  }, [notificationsOpen]);

  const handleNavigation = (view: PanelView) => {
    onNavigate?.(view);
    if (drawerOpen) closeDrawer();
  };

  return (
    <div className={`panel-shell${collapsed ? " panel-shell--collapsed" : ""}${inspector ? " panel-shell--with-inspector" : ""}`}>
      <a className="panel-shell__skip-link" href="#panel-main-content">Saltar al contenido</a>

      <aside id="panel-shell-sidebar" className="panel-shell__sidebar panel-shell__rail" aria-label="Panel de navegación">
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
          aria-label="Abrir menú de navegación"
          title="Abrir menú de navegación"
          onClick={() => setDrawerOpen(true)}
        >
          <MenuIcon />
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
          aria-label="Navegación"
          aria-modal="true"
          onKeyDown={keepFocusInDrawer}
        >
          <div className="panel-shell__drawer-heading">
            <Brand mobile />
            <button ref={closeButtonRef} type="button" className="panel-shell__drawer-close" aria-label="Cerrar menú de navegación" title="Cerrar menú de navegación" onClick={closeDrawer}>
              <CloseIcon />
            </button>
          </div>
          <Navigation currentView={currentView} onNavigate={handleNavigation} user={user} />
          <UserContext user={user} onLogout={onLogout} />
        </section>
      </div>

      <div ref={contentAreaRef} className="panel-shell__content-area">
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
             <nav className="panel-shell__breadcrumbs" aria-label="Ruta de navegación">
               <ol>
                 {currentView === "dashboard" ? <li aria-current="page">Panel unificado</li> : <>
                   <li><button type="button" onClick={() => handleNavigation("dashboard")}>Panel</button></li>
                   <li aria-current="page">{NAVIGATION[currentView as keyof typeof NAVIGATION]?.label ?? (currentView === "notifications" ? "Notificaciones" : "Panel")}</li>
                 </>}
               </ol>
             </nav>
             <div className="panel-shell__header-actions">
               <div ref={notificationsRef} className="panel-shell__notifications">
               <button ref={bellRef} type="button" className="panel-shell__header-action" aria-expanded={notificationsOpen} aria-haspopup="dialog" aria-label={notificationState.status === "loading" ? "Cargando notificaciones" : notificationState.status === "error" ? "Notificaciones no disponibles" : notificationState.unread > 0 ? `Notificaciones (${notificationState.unread} sin leer)` : "Notificaciones"} title="Notificaciones" onClick={() => setNotificationsOpen((open) => !open)}>
                 <BellIcon />
                 {notificationState.status === "ready" && notificationState.unread > 0 ? <span aria-hidden="true">{notificationState.unread}</span> : null}
               </button>
               {notificationsOpen ? <section className="panel-shell__notifications-panel" role="dialog" aria-modal="true" aria-labelledby="panel-notifications-title" onKeyDown={keepFocusInNotifications}>
                 <div className="panel-shell__notifications-heading"><h2 id="panel-notifications-title">Notificaciones</h2><button ref={notificationCloseRef} type="button" className="panel-shell__notifications-close" aria-label="Cerrar notificaciones" onClick={closeNotifications}><CloseIcon /></button></div>
                 <ul className="panel-shell__notifications-list">
                   {notifications.slice(0, 5).map((notification) => <li key={notification.id} className={notification.read_at === null ? "panel-shell__notification panel-shell__notification--unread" : "panel-shell__notification"}><span className="panel-shell__notification-dot" aria-hidden="true" /><strong>{notification.title}</strong><p>{notification.content}</p><small>{notification.source} · {notification.created_at ?? "Sin fecha"}</small></li>)}
                   {notifications.length === 0 ? <li className="panel-shell__notification-empty">No hay notificaciones.</li> : null}
                 </ul>
                 <div className="panel-shell__notifications-footer"><button type="button" onClick={() => void onMarkAllNotificationsRead?.()}>Marcar todas como leídas</button><button type="button" onClick={() => { closeNotifications(); handleNavigation("notifications"); }}>Ver todas las notificaciones</button></div>
               </section> : null}
               </div>
             </div>
          </header>
          {statusBadge ? (
            <div className="panel-shell__header-badge">
              <Badge>{statusBadge}</Badge>
            </div>
          ) : null}
        </div>
        {currentView === "conversations" && conversationTab && onConversationTabChange ? (
          <div role="group" aria-label="Sección de conversaciones" className="panel-shell__conversation-tabs">
            {(["conversations", "cases"] as const).map((tab) => (
              <button
                key={tab}
                type="button"
                aria-pressed={conversationTab === tab}
                onClick={() => onConversationTabChange(tab)}
              >
                {tab === "conversations" ? "Conversaciones" : "Casos"}
              </button>
            ))}
          </div>
        ) : null}
        <div id="panel-main-content" className="panel-shell__content" tabIndex={-1}>
          {children}
        </div>
       </div>
       <nav className={`panel-shell__footer-nav${user.role === "admin" ? " panel-shell__footer-nav--admin" : ""}`} aria-label="Navegación inferior">
         {(["notifications", "dashboard", ...(user.role === "admin" ? ["chat"] : []), "conversations", "agenda"] as PanelView[]).map((view) => {
           const item = view === "notifications" ? { label: "Notificaciones", Icon: BellIcon } : view === "dashboard" ? { label: "Panel", Icon: PanelIcon } : view === "chat" ? { label: "Agente Lumat", Icon: AssistantIcon } : view === "conversations" ? { label: "Conversaciones", Icon: ChatIcon } : { label: "Agenda", Icon: CalendarIcon };
           return <button key={view} type="button" className={view === "chat" ? "panel-shell__footer-nav--primary" : undefined} aria-current={currentView === view ? "page" : undefined} aria-label={item.label} onClick={() => handleNavigation(view)}><item.Icon /><span>{item.label}</span></button>;
         })}
       </nav>
       {inspector ? <aside className="panel-shell__inspector" aria-label="Inspector operacional">{inspector}</aside> : null}
    </div>
  );
}
