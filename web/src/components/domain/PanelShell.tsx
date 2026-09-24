import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent, ReactNode } from "react";
import {
  Bell,
  BookOpen,
  Bot,
  Calendar,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Menu,
  MessageSquare,
  PanelLeft,
  Settings,
  UserRound,
  Users,
  X,
  Zap,
  type LucideIcon,
} from "lucide-react";
import type { PanelNotification, User } from "../../types";
import { Badge } from "../primitives/Badge";
import { Avatar } from "../primitives/Avatar";
import { Icon } from "../primitives/Icon";

export type PanelView = "dashboard" | "clients" | "conversations" | "cases" | "notifications" | "push" | "chat" | "kb" | "settings" | "agenda" | "automation-rules" | "advanced-dashboard" | "users" | "projects" | "planning-sessions";

interface NavigationItem {
  label: string;
  icon: LucideIcon;
  adminOnly?: boolean;
}

function PanelToggleIcon({ collapsed }: { collapsed: boolean }) {
  return <Icon icon={collapsed ? ChevronRight : ChevronLeft} />;
}

const NAVIGATION: Record<Exclude<PanelView, "cases" | "notifications" | "push" | "advanced-dashboard" | "projects" | "planning-sessions">, NavigationItem> = {
  dashboard: { label: "Panel unificado", icon: PanelLeft },
  chat: { label: "Asistente Lumat", icon: Bot, adminOnly: true },
  conversations: { label: "Conversaciones", icon: MessageSquare },
  clients: { label: "Clientes", icon: Users },
  agenda: { label: "Agenda", icon: Calendar },
  kb: { label: "Base de Conocimientos", icon: BookOpen, adminOnly: true },
  'automation-rules': { label: "Automatizaciones", icon: Zap, adminOnly: true },
  settings: { label: "Configuración", icon: Settings, adminOnly: true },
  users: { label: "Usuarios", icon: UserRound, adminOnly: true },
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
  notificationState?: NotificationState;
  notifications?: PanelNotification[];
  onMarkAllNotificationsRead?: () => void | Promise<void>;
  focusMode?: boolean;
  onFocusModeChange?: (focused: boolean) => void;
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
  const role = user.role === "admin" ? "Administrador" : user.role === "tecnico" ? "Técnico" : "Operador";
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
          <Icon icon={LogOut} />
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
          const glyph = NAVIGATION[view].icon;
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
                <Icon icon={glyph} />
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
  notificationState = { status: "loading" },
  notifications = [],
  onMarkAllNotificationsRead,
  focusMode: controlledFocusMode,
  onFocusModeChange,
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
  const focusTriggerRef = useRef<HTMLButtonElement>(null);
  const focusCloseRef = useRef<HTMLButtonElement>(null);
  const focusRegionRef = useRef<HTMLDivElement>(null);
  const [internalFocusMode, setInternalFocusMode] = useState(false);
  const focusMode = controlledFocusMode ?? internalFocusMode;
  const setFocusMode = (focused: boolean) => {
    if (controlledFocusMode === undefined) setInternalFocusMode(focused);
    onFocusModeChange?.(focused);
  };

  const closeFocusMode = () => {
    setFocusMode(false);
    queueMicrotask(() => focusTriggerRef.current?.focus());
  };

  const closeDrawer = () => {
    setDrawerOpen(false);
    queueMicrotask(() => menuButtonRef.current?.focus());
  };

  useEffect(() => {
    if (!focusMode) return;
    focusCloseRef.current?.focus();
    const handleEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeFocusMode();
      }
    };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [focusMode]);

  const keepFocusInFocusMode = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key !== "Tab") return;
    const focusable = [...(focusRegionRef.current?.querySelectorAll<HTMLElement>(
      'button:not([disabled]), textarea:not([disabled]), input:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
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
    if (drawerOpen) contentArea.setAttribute("inert", "");
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
    <div className={`panel-shell${collapsed ? " panel-shell--collapsed" : ""}${inspector ? " panel-shell--with-inspector" : ""}${focusMode ? " panel-shell--focus-mode" : ""}`}>
      <a className="panel-shell__skip-link" href="#panel-main-content">Saltar al contenido</a>

      <aside id="panel-shell-sidebar" className="panel-shell__sidebar panel-shell__rail" aria-label="Panel de navegación" aria-hidden={focusMode || undefined}>
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
          <Icon icon={Menu} />
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
              <Icon icon={X} />
            </button>
          </div>
          <Navigation currentView={currentView} onNavigate={handleNavigation} user={user} />
          <UserContext user={user} onLogout={onLogout} />
        </section>
      </div>

      <div ref={contentAreaRef} className="panel-shell__content-area" onKeyDown={focusMode ? keepFocusInFocusMode : undefined}>
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
                <button
                  ref={focusTriggerRef}
                  type="button"
                  className="panel-shell__header-action"
                  aria-expanded={focusMode}
                  aria-controls="panel-main-content"
                  aria-label={focusMode ? "Modo foco activo" : "Entrar en modo foco"}
                  title={focusMode ? "Modo foco activo" : "Entrar en modo foco"}
                  onClick={() => focusMode ? closeFocusMode() : setFocusMode(true)}
                >{focusMode ? "×" : "Focus"}</button>
                <div ref={notificationsRef} className="panel-shell__notifications">
               <button ref={bellRef} type="button" className="panel-shell__header-action" aria-expanded={notificationsOpen} aria-haspopup="dialog" aria-label={notificationState.status === "loading" ? "Cargando notificaciones" : notificationState.status === "error" ? "Notificaciones no disponibles" : notificationState.unread > 0 ? `Notificaciones (${notificationState.unread} sin leer)` : "Notificaciones"} title="Notificaciones" onClick={() => setNotificationsOpen((open) => !open)}>
                 <Icon icon={Bell} />
                 {notificationState.status === "ready" && notificationState.unread > 0 ? <span aria-hidden="true">{notificationState.unread}</span> : null}
               </button>
               {notificationsOpen ? <section className="panel-shell__notifications-panel" role="dialog" aria-modal="true" aria-labelledby="panel-notifications-title" onKeyDown={keepFocusInNotifications}>
                  <div className="panel-shell__notifications-heading"><h2 id="panel-notifications-title">Notificaciones</h2><button ref={notificationCloseRef} type="button" className="panel-shell__notifications-close" aria-label="Cerrar notificaciones" onClick={closeNotifications}><Icon icon={X} /></button></div>
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
         <div ref={focusRegionRef} id="panel-main-content" className="panel-shell__content" tabIndex={-1} role={focusMode ? "region" : undefined} aria-label={focusMode ? "Modo foco" : undefined}>
           {focusMode ? <button ref={focusCloseRef} type="button" className="panel-shell__focus-close" aria-label="Salir del modo foco" onClick={closeFocusMode}>Salir del modo foco</button> : null}
           {children}
        </div>
       </div>
       <nav className={`panel-shell__footer-nav${user.role === "admin" ? " panel-shell__footer-nav--admin" : ""}`} aria-label="Navegación inferior">
         {(["notifications", "dashboard", ...(user.role === "admin" ? ["chat"] : []), "conversations", "agenda"] as PanelView[]).map((view) => {
            const item = view === "notifications" ? { label: "Notificaciones", icon: Bell } : view === "dashboard" ? { label: "Panel", icon: PanelLeft } : view === "chat" ? { label: "Agente Lumat", icon: Bot } : view === "conversations" ? { label: "Conversaciones", icon: MessageSquare } : { label: "Agenda", icon: Calendar };
            return <button key={view} type="button" className={view === "chat" ? "panel-shell__footer-nav--primary" : undefined} aria-current={currentView === view ? "page" : undefined} aria-label={item.label} onClick={() => handleNavigation(view)}><Icon icon={item.icon} /><span>{item.label}</span></button>;
         })}
       </nav>
        {inspector ? <aside className="panel-shell__inspector" aria-label="Inspector operacional" aria-hidden={focusMode || undefined}>{inspector}</aside> : null}
    </div>
  );
}
