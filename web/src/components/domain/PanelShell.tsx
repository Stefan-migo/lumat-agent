import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent, ReactNode } from "react";
import {
  ArrowLeft,
  Bell,
  BookOpen,
  Bot,
  Calendar,
  CalendarDays,
  Check,
  CheckCheck,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Menu,
  LogOut,
  MessageSquare,
  MoreVertical,
  PanelLeft,
  Settings,
  Search,
  UserRound,
  Users,
  X,
  Zap,
  ArrowRight,
  type LucideIcon,
} from "lucide-react";
import type { PanelNotification, User } from "../../types";
import { roleLabels } from "../../roleLabels";
import { Badge } from "../primitives/Badge";
import { Avatar } from "../primitives/Avatar";
import { Icon } from "../primitives/Icon";
import { Tabs } from "../primitives/Tabs";

export function formatNotificationTime(createdAt: string | null, now = new Date()): string {
  if (!createdAt) return "";
  const elapsedSeconds = (new Date(createdAt).getTime() - now.getTime()) / 1000;
  if (!Number.isFinite(elapsedSeconds)) return "";
  const units: Array<[Intl.RelativeTimeFormatUnit, number, string]> = [
    ["year", 31_536_000, "año"], ["month", 2_592_000, "mes"], ["week", 604_800, "sem"],
    ["day", 86_400, "d"], ["hour", 3_600, "h"], ["minute", 60, "min"], ["second", 1, "s"],
  ];
  const [unit, seconds, shortUnit] = units.find(([, seconds]) => Math.abs(elapsedSeconds) >= seconds) ?? units[units.length - 1];
  const value = Math.round(elapsedSeconds / seconds);
  const relative = new Intl.RelativeTimeFormat("es-CL", { numeric: "always" }).format(value, unit);
  return relative.replace(/^hace\s+/i, "Hace ").replace(new RegExp(`\\s${unit === "month" ? "mes(es)?" : unit === "year" ? "año(s)?" : unit === "week" ? "semana(s)?" : unit === "day" ? "día(s)?" : unit === "hour" ? "hora(s)?" : unit === "minute" ? "minuto(s)?" : "segundo(s)?"}$`, "i"), ` ${shortUnit}`);
}

const NOTIFICATION_SOURCE_ICONS: Record<string, { icon: LucideIcon; tone: string }> = {
  case: { icon: UserRound, tone: "case" },
  appointment: { icon: CalendarDays, tone: "appointment" },
  customer: { icon: Users, tone: "customer" },
};

export type PanelView = "dashboard" | "clients" | "conversations" | "cases" | "notifications" | "push" | "chat" | "kb" | "settings" | "agenda" | "automation-rules" | "advanced-dashboard" | "users" | "projects" | "planning-sessions" | "profile";

interface NavigationItem {
  label: string;
  icon: LucideIcon;
  adminOnly?: boolean;
}

function PanelToggleIcon({ collapsed }: { collapsed: boolean }) {
  return <Icon icon={collapsed ? ChevronRight : ChevronLeft} />;
}

const NAVIGATION: Record<Exclude<PanelView, "cases" | "notifications" | "push" | "advanced-dashboard" | "projects" | "planning-sessions" | "profile">, NavigationItem> = {
  dashboard: { label: "Panel unificado", icon: PanelLeft },
  chat: { label: "Asistente Lumat", icon: Bot },
  conversations: { label: "Conversaciones", icon: MessageSquare },
  clients: { label: "Clientes", icon: Users },
  agenda: { label: "Agenda", icon: Calendar },
  kb: { label: "Base de Conocimientos", icon: BookOpen, adminOnly: true },
  'automation-rules': { label: "Automatizaciones", icon: Zap, adminOnly: true },
  settings: { label: "Configuración", icon: Settings, adminOnly: true },
  users: { label: "Usuarios", icon: UserRound, adminOnly: true },
};

const BREADCRUMB_OVERRIDES: Partial<Record<PanelView, string>> = {
  dashboard: "Dashboard",
  notifications: "Notificaciones",
  push: "Notificaciones push",
  "advanced-dashboard": "Panel avanzado",
  profile: "Mi perfil",
  projects: "Proyectos",
  "planning-sessions": "Sesiones de planificación",
};

const BRAND_ASSET_BASE = `${import.meta.env.BASE_URL}brand`;

export interface PanelShellProps {
  children: ReactNode;
  currentView?: PanelView;
  breadcrumbView?: PanelView;
  drawerInitiallyOpen?: boolean;
  onNavigate?: (view: PanelView) => void;
  onBack?: () => void;
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
}

export type NotificationState = { status: "loading" } | { status: "ready"; unread: number } | { status: "error" };

/** The account affordance (avatar trigger + menu). Controlled so the desktop header and the mobile bar each own
 *  their open state without duplicating the popover markup. */
function AccountControl({ user, onLogout, onNavigate, open, onToggle }: { user: User; onLogout?: () => void | Promise<void>; onNavigate?: (view: PanelView) => void; open: boolean; onToggle: () => void }) {
  const accountRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const closeOnOutsideClick = (event: MouseEvent) => {
      if (!accountRef.current?.contains(event.target as Node)) onToggle();
    };
    const closeOnEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      onToggle();
      queueMicrotask(() => triggerRef.current?.focus());
    };
    document.addEventListener("mousedown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [onToggle, open]);
  return (
    <div ref={accountRef} className="panel-shell__account">
      <button ref={triggerRef} type="button" className="panel-shell__account-trigger" aria-label="Abrir menú de usuario" aria-expanded={open} aria-haspopup="menu" onClick={onToggle}>
        <Avatar name={user.username} className="panel-shell__account-avatar" />
        <span className="panel-shell__account-name">{user.username}</span>
        <Icon icon={ChevronDown} />
      </button>
      {open ? <div className="panel-shell__account-menu" role="menu" aria-label={`Cuenta de ${user.username}`}>
        <div className="panel-shell__account-identity">
          <Avatar name={user.username} className="panel-shell__account-menu-avatar" />
          <span className="panel-shell__account-copy"><strong>{user.username}</strong><span>{roleLabels[user.role]}</span></span>
        </div>
        <div className="panel-shell__account-divider" />
        <button type="button" className="panel-shell__account-item" role="menuitem" onClick={() => { onNavigate?.("profile"); onToggle(); }}><Icon icon={UserRound} />Mi perfil</button>
        {onLogout ? <button type="button" className="panel-shell__account-logout" role="menuitem" onClick={() => void onLogout()}><Icon icon={LogOut} />Cerrar sesión</button> : null}
      </div> : null}
    </div>
  );
}

function Brand({ mobile = false, compact = false, line = false }: { mobile?: boolean; compact?: boolean; line?: boolean }) {
  return (
    <div
      className={mobile ? `panel-shell__mobile-brand${line ? " panel-shell__mobile-brand--line" : ""}` : "panel-shell__brand"}
      role="img"
      aria-label="Lumat, panel operativo"
    >
      {compact ? (
        <img className="panel-shell__brand-mark" src={`${BRAND_ASSET_BASE}/lumat-mark.png`} alt="" aria-hidden="true" />
      ) : (
        <>
          <img className="panel-shell__brand-image" src={`${BRAND_ASSET_BASE}/${line ? "lumat-logo-line.png" : "lumat-logo.png"}`} alt="Lumat" />
          <img className="panel-shell__brand-mark" src={`${BRAND_ASSET_BASE}/lumat-mark.png`} alt="" aria-hidden="true" />
        </>
      )}
    </div>
  );
}

function UserContext({ user, compact = false, onLogout, onNavigate }: { user: User; compact?: boolean; onLogout?: () => void | Promise<void>; onNavigate?: (view: PanelView) => void }) {
  const role = roleLabels[user.role];
  const [optionsOpen, setOptionsOpen] = useState(false);
  const [optionsPosition, setOptionsPosition] = useState<{ left: number; bottom: number } | null>(null);
  const optionsRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);

  const openOptions = (trigger: HTMLButtonElement) => {
    triggerRef.current = trigger;
    // The sidebar clips its descendants (`overflow: hidden`) and does not scroll, so an absolutely
    // positioned menu is cut at the sidebar edge. Position it against the viewport instead: that escapes
    // the clip, lets the card overlay the content, and clamping keeps it on screen.
    const rect = trigger.getBoundingClientRect();
    const rootFontSize = Number.parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
    const width = Math.min(20 * rootFontSize, window.innerWidth - 24);
    const margin = 12;
    const left = Math.min(Math.max(margin, rect.left), Math.max(margin, window.innerWidth - width - margin));
    setOptionsPosition({ left, bottom: window.innerHeight - rect.top + 8 });
    setOptionsOpen(true);
  };

  const closeOptions = () => {
    setOptionsOpen(false);
    queueMicrotask(() => triggerRef.current?.focus());
  };

  useEffect(() => {
    if (!optionsOpen) return;
    const closeOnOutsideClick = (event: MouseEvent) => {
      if (!optionsRef.current?.contains(event.target as Node)) setOptionsOpen(false);
    };
    const closeOnEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      closeOptions();
    };
    document.addEventListener("mousedown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [optionsOpen]);

  return (
    <div
      className="panel-shell__user"
      aria-label={compact ? `${user.username} — ${role}` : undefined}
      title={compact ? `${user.username} — ${role}` : undefined}
    >
      {/* The identity itself opens the account options, which is what makes the control reachable in the
          compact tiers where the overflow button is hidden (S7). */}
      <button
        type="button"
        className="panel-shell__user-trigger"
        aria-haspopup="menu"
        aria-expanded={optionsOpen}
        aria-label={compact ? `Opciones de ${user.username}` : undefined}
        onClick={(event) => openOptions(event.currentTarget)}
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
      </button>
      {onLogout ? (
        <button
          type="button"
          className="panel-shell__user-options-trigger"
          aria-haspopup="menu"
          aria-expanded={optionsOpen}
          aria-label="Más opciones de la cuenta"
          title="Más opciones de la cuenta"
          onClick={(event) => openOptions(event.currentTarget)}
        >
          <Icon icon={MoreVertical} />
        </button>
      ) : null}
      {optionsOpen && (onLogout || onNavigate) ? (
        <div ref={optionsRef} className="panel-shell__user-options" role="menu" aria-label={`Cuenta de ${user.username}`} style={optionsPosition ? { left: optionsPosition.left, bottom: optionsPosition.bottom } : undefined}>
          <div className="panel-shell__account-identity">
            <Avatar name={user.username} className="panel-shell__account-menu-avatar" />
            <span className="panel-shell__account-copy"><strong>{user.username}</strong><span>{role}</span></span>
          </div>
          <div className="panel-shell__account-divider" />
          {onNavigate ? <button type="button" className="panel-shell__account-item" role="menuitem" onClick={() => { setOptionsOpen(false); onNavigate?.("profile"); }}><Icon icon={UserRound} />Mi perfil</button> : null}
          <button
            type="button"
            className="panel-shell__account-logout"
            role="menuitem"
            onClick={() => {
              setOptionsOpen(false);
              void onLogout?.();
            }}
          >
            <Icon icon={LogOut} />
            Cerrar sesión
          </button>
        </div>
      ) : null}
    </div>
  );
}

function Navigation({
  currentView,
  onNavigate,
  user,
  collapsed = false,
  search = "",
}: Pick<PanelShellProps, "currentView" | "onNavigate" | "user"> & { collapsed?: boolean; search?: string }) {
  const items = (Object.keys(NAVIGATION) as Array<keyof typeof NAVIGATION>).filter(
    (view) => (!NAVIGATION[view].adminOnly || user.role === "admin")
      && NAVIGATION[view].label.toLocaleLowerCase("es-CL").includes(search.toLocaleLowerCase("es-CL")),
  );
  const groups: Array<[string, typeof items]> = [
    ["General", items.filter((view) => view === "dashboard")],
    ["Operación", items.filter((view) => ["chat", "conversations", "clients", "agenda"].includes(view))],
    ["Administración", items.filter((view) => NAVIGATION[view].adminOnly)],
  ];

  return (
    <nav className="panel-shell__navigation" aria-label="Navegación principal">
      {groups.map(([group, views]) => views.length > 0 ? (
        <section className="panel-shell__navigation-group" role="group" aria-label={group} key={group}>
          {collapsed ? null : <h2 className="panel-shell__group-title">{group}</h2>}
          <ul className="panel-shell__navigation-list">
            {views.map((view) => (
              <li key={view}>
                <button
                  type="button"
                  className="panel-shell__navigation-button"
                  aria-current={currentView === view ? "page" : undefined}
                  aria-label={collapsed ? NAVIGATION[view].label : undefined}
                  title={collapsed ? NAVIGATION[view].label : undefined}
                  onClick={() => onNavigate?.(view)}
                >
                  <Icon icon={NAVIGATION[view].icon} />
                  {collapsed ? null : <span className="panel-shell__nav-label">{NAVIGATION[view].label}</span>}
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : null)}
    </nav>
  );
}

export function PanelShell({
  children,
  currentView = "dashboard",
  breadcrumbView,
  drawerInitiallyOpen = false,
  onNavigate,
  onBack,
  user,
  statusBadge,
  onLogout,
  inspector,
  notificationState = { status: "loading" },
  notifications = [],
  onMarkAllNotificationsRead,
}: PanelShellProps) {
  const currentBreadcrumbView = breadcrumbView ?? currentView;
  const [drawerOpen, setDrawerOpen] = useState(drawerInitiallyOpen);
  const [collapsed, setCollapsed] = useState(false);
  const [navigationSearch, setNavigationSearch] = useState("");
  const [pendingSearchFocus, setPendingSearchFocus] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const [mobileAccountOpen, setMobileAccountOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const drawerTriggerRef = useRef<HTMLElement | null>(null);
  const drawerOpenedWidthRef = useRef(window.innerWidth);
  const desktopTriggerRef = useRef<HTMLButtonElement>(null);
  const drawerRef = useRef<HTMLDialogElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const contentAreaRef = useRef<HTMLDivElement>(null);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [notificationTab, setNotificationTab] = useState("all");
  const notificationsRef = useRef<HTMLDivElement>(null);
  const bellRef = useRef<HTMLButtonElement>(null);
  const notificationCloseRef = useRef<HTMLButtonElement>(null);
  const closeDrawer = () => {
    if (drawerRef.current?.open) drawerRef.current.close();
    setDrawerOpen(false);
    queueMicrotask(() => {
      const trigger = drawerOpenedWidthRef.current < 1024 && window.innerWidth >= 1024
        ? desktopTriggerRef.current
        : drawerTriggerRef.current?.isConnected ? drawerTriggerRef.current : menuButtonRef.current;
      trigger?.focus();
    });
  };

  const openDrawer = (trigger: HTMLElement) => {
    drawerTriggerRef.current = trigger;
    drawerOpenedWidthRef.current = window.innerWidth;
    setDrawerOpen(true);
  };

  // The compact search control behaves by tier (S5): the desktop collapsed sidebar expands and focuses the
  // field, while the tablet rail opens the drawer, where the shared filter already lives (S8).
  const activateCompactSearch = (trigger: HTMLButtonElement) => {
    if (window.innerWidth >= 1024) {
      setPendingSearchFocus(true);
      setCollapsed(false);
      return;
    }
    openDrawer(trigger);
  };

  useEffect(() => {
    if (!pendingSearchFocus || collapsed) return;
    searchInputRef.current?.focus();
    setPendingSearchFocus(false);
  }, [pendingSearchFocus, collapsed]);

  useEffect(() => {
    const contentArea = contentAreaRef.current;
    const dialog = drawerRef.current;
    if (!drawerOpen || !dialog || !contentArea) return;

    const previousOverflow = document.body.style.overflow;
    const previousInert = contentArea.hasAttribute("inert");
    document.body.style.overflow = "hidden";
    contentArea.setAttribute("inert", "");
    if (!dialog.open) dialog.showModal();
    dialog.querySelector<HTMLButtonElement>(".panel-shell__drawer-close")?.focus();
    const handleResize = () => {
      if (window.innerWidth >= 1024) closeDrawer();
    };
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      if (dialog.open) dialog.close();
      if (previousInert) contentArea.setAttribute("inert", "");
      else contentArea.removeAttribute("inert");
      document.body.style.overflow = previousOverflow;
    };
  }, [drawerOpen]);

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

  // One label for the bell wherever it renders (desktop header popover, mobile bar navigation).
  const bellLabel = notificationState.status === "loading"
    ? "Cargando notificaciones"
    : notificationState.status === "error"
      ? "Notificaciones no disponibles"
      : notificationState.unread > 0
        ? `Notificaciones (${notificationState.unread} sin leer)`
        : "Notificaciones";

  return (
    <div className={`panel-shell${collapsed ? " panel-shell--collapsed" : ""}${inspector ? " panel-shell--with-inspector" : ""}`}>
      <a className="panel-shell__skip-link" href="#panel-main-content">Saltar al contenido</a>

      <aside id="panel-shell-sidebar" className="panel-shell__sidebar panel-shell__rail" aria-label="Panel de navegación">
        <div className="panel-shell__sidebar-inner">
          <button type="button" className="panel-shell__tablet-menu" aria-label="Abrir menú de navegación" aria-expanded={drawerOpen} aria-controls="panel-navigation-drawer" onClick={(event) => openDrawer(event.currentTarget)}>
            <Icon icon={Menu} />
          </button>
          <div className="panel-shell__sidebar-header">
            <Brand compact={collapsed} />
            <button
              ref={desktopTriggerRef}
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
          </div>
          {!collapsed ? <label className="panel-shell__search">
            <Icon icon={Search} />
            <input ref={searchInputRef} type="search" aria-label="Buscar en el menú" placeholder="Buscar" value={navigationSearch} onChange={(event) => setNavigationSearch(event.target.value)} />
          </label> : null}
          {/* Icon-only search affordance for the compact tiers, where the field above is not rendered (desktop
              collapsed) or is hidden (tablet rail). It looks like the other rail icons — no button frame (S5). */}
          <button type="button" className="panel-shell__search-toggle" aria-label="Buscar en el menú" title="Buscar en el menú" onClick={(event) => activateCompactSearch(event.currentTarget)}>
            <Icon icon={Search} />
          </button>
          <Navigation currentView={currentView} onNavigate={handleNavigation} user={user} collapsed={collapsed} search={navigationSearch} />
          <UserContext user={user} compact={collapsed} onLogout={onLogout} onNavigate={handleNavigation} />
        </div>
      </aside>

      <header className="panel-shell__mobile-bar">
        <button
          ref={menuButtonRef}
          type="button"
          className="panel-shell__menu-button"
          aria-expanded={drawerOpen}
          aria-controls="panel-navigation-drawer"
          aria-label="Abrir menú de navegación"
          title="Abrir menú de navegación"
          onClick={(event) => openDrawer(event.currentTarget)}
        >
          <Icon icon={Menu} />
        </button>
        <Brand mobile line />
        <div className="panel-shell__mobile-actions">
          {/* PNL-APP-10: the header exposes the bell and the avatar at every tier. The mobile popover lives inside
              the desktop header (hidden below 64rem), so the mobile bell navigates to the notification center. */}
          <button type="button" className="panel-shell__header-action" aria-label={bellLabel} title="Notificaciones" onClick={() => handleNavigation("notifications")}>
            <Icon icon={Bell} />
            {notificationState.status === "ready" && notificationState.unread > 0 ? <span aria-hidden="true">{notificationState.unread}</span> : null}
          </button>
          <AccountControl user={user} onLogout={onLogout} onNavigate={handleNavigation} open={mobileAccountOpen} onToggle={() => setMobileAccountOpen((open) => !open)} />
        </div>
      </header>

      <dialog
          ref={drawerRef}
          id="panel-navigation-drawer"
          className="panel-shell__drawer-layer"
          data-testid="panel-drawer-backdrop"
          aria-label="Navegación"
          aria-modal="true"
          onKeyDown={(event) => { if (event.key === "Escape") { event.preventDefault(); closeDrawer(); } }}
          onCancel={(event) => { event.preventDefault(); closeDrawer(); }}
          onMouseDown={(event) => { if (event.target === event.currentTarget) closeDrawer(); }}
          onClick={(event) => { if (event.target === event.currentTarget) closeDrawer(); }}
        >
        <section className="panel-shell__drawer">
          <div className="panel-shell__drawer-heading">
            <Brand mobile />
            <button type="button" className="panel-shell__drawer-close" aria-label="Cerrar menú de navegación" title="Cerrar menú de navegación" onClick={closeDrawer}>
              <Icon icon={X} />
            </button>
          </div>
          {/* The drawer shares the sidebar's filter so both surfaces narrow the same destination list (S8). */}
          <label className="panel-shell__search">
            <Icon icon={Search} />
            <input type="search" aria-label="Buscar en el menú" placeholder="Buscar" value={navigationSearch} onChange={(event) => setNavigationSearch(event.target.value)} />
          </label>
          <Navigation currentView={currentView} onNavigate={handleNavigation} user={user} search={navigationSearch} />
          <UserContext user={user} onLogout={onLogout} onNavigate={handleNavigation} />
        </section>
      </dialog>

      <div ref={contentAreaRef} className="panel-shell__content-area">
        <div className="panel-shell__header-row">
          <header className="panel-shell__header" aria-label="Encabezado de la vista">
            {onBack ? <button type="button" className="panel-shell__back" aria-label="Volver" title="Volver" onClick={onBack}>
              <Icon icon={ArrowLeft} />
            </button> : null}
             <nav className="panel-shell__breadcrumbs" aria-label="Ruta de navegación">
               <ol>
                  {currentBreadcrumbView === "dashboard" ? <><li>Panel</li><li aria-current="page">Dashboard</li></> : <>
                    <li><button type="button" onClick={() => handleNavigation("dashboard")}>Panel</button></li>
                    <li aria-current="page">{BREADCRUMB_OVERRIDES[currentBreadcrumbView] ?? NAVIGATION[currentBreadcrumbView as keyof typeof NAVIGATION]?.label ?? "Panel"}</li>
                 </>}
               </ol>
             </nav>
              <div className="panel-shell__header-actions">
                <div ref={notificationsRef} className="panel-shell__notifications">
                <button ref={bellRef} type="button" className="panel-shell__header-action" aria-expanded={notificationsOpen} aria-haspopup="dialog" aria-label={bellLabel} title="Notificaciones" onClick={() => { setAccountOpen(false); setNotificationsOpen((open) => !open); }}>
                 <Icon icon={Bell} />
                 {notificationState.status === "ready" && notificationState.unread > 0 ? <span aria-hidden="true">{notificationState.unread}</span> : null}
               </button>
                {notificationsOpen ? <section className="panel-shell__notifications-panel" role="dialog" aria-modal="true" aria-labelledby="panel-notifications-title" onKeyDown={keepFocusInNotifications}>
                  <div className="panel-shell__notifications-heading"><div className="panel-shell__notifications-title"><h2 id="panel-notifications-title">Notificaciones</h2>{notificationState.status === "ready" && notificationState.unread > 0 ? <span className="panel-shell__notifications-new">{notificationState.unread} nuevas</span> : null}</div><button ref={notificationCloseRef} type="button" className="panel-shell__notifications-close" aria-label="Cerrar notificaciones" onClick={closeNotifications}><Icon icon={X} /></button></div>
                  {(() => {
                    const unread = notifications.filter((notification) => notification.read_at === null);
                    const visible = (notificationTab === "unread" ? unread : notifications).slice(0, 5);
                    return <>
                      {notifications.length > 0 ? <div className="panel-shell__notifications-toolbar">
                        <Tabs ariaLabel="Filtrar notificaciones" activeTab={notificationTab} onTabChange={setNotificationTab} tabs={[
                          { id: "all", label: "Todas" }, { id: "unread", label: <>No leídas <span className="panel-shell__notifications-count">{unread.length}</span></> },
                        ]}>{() => null}</Tabs>
                        {unread.length > 0 ? <button type="button" className="panel-shell__notifications-mark-all" onClick={() => void onMarkAllNotificationsRead?.()}><Icon icon={CheckCheck} />Marcar todas como leídas</button> : null}
                      </div> : null}
                      <ul className="panel-shell__notifications-list">
                        {visible.map((notification) => {
                          const source = NOTIFICATION_SOURCE_ICONS[notification.source] ?? { icon: Bell, tone: "default" };
                          return <li key={notification.id} className={`panel-shell__notification${notification.read_at === null ? " panel-shell__notification--unread" : ""}`}>
                            <span className={`panel-shell__notification-icon panel-shell__notification-icon--${source.tone}`}><Icon icon={source.icon} /></span>
                            {notification.read_at === null ? <span className="panel-shell__notification-dot" aria-label="No leída" /> : null}
                            <div className="panel-shell__notification-copy"><strong>{notification.title}</strong><p>{notification.content}</p></div>
                            <small>{formatNotificationTime(notification.created_at)}</small>
                            {/* PanelNotification has no destination entity id; rows intentionally do not navigate. */}
                          </li>;
                        })}
                        {notifications.length === 0 ? <li className="panel-shell__notification-empty"><span className="panel-shell__notification-empty-icon"><Icon icon={Bell} /><Icon icon={Check} /></span><strong>No tienes notificaciones</strong><p>Aquí verás las novedades de tus conversaciones, visitas y documentos.</p></li> : visible.length === 0 ? <li className="panel-shell__notification-empty"><strong>No hay notificaciones no leídas</strong></li> : null}
                      </ul>
                      {notifications.length > 0 ? <div className="panel-shell__notifications-footer"><button type="button" onClick={() => { closeNotifications(); handleNavigation("notifications"); }}>Ver todas las notificaciones<Icon icon={ArrowRight} /></button></div> : null}
                    </>;
                  })()}
                </section> : null}
                </div>
                 <span className="panel-shell__header-divider" aria-hidden="true" />
                 <AccountControl user={user} onLogout={onLogout} onNavigate={handleNavigation} open={accountOpen} onToggle={() => { setNotificationsOpen(false); setAccountOpen((open) => !open); }} />
             </div>
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
        {/* Mobile tabs use short display labels so all five fit without clipping. The destination itself keeps its
            canonical label in NAVIGATION, which is what the sidebar, the drawer and the breadcrumb render. */}
        <nav className="panel-shell__footer-nav" aria-label="Navegación inferior">
          {(["dashboard", "conversations", "chat", "agenda", "clients"] as PanelView[]).map((view) => {
            const item = view === "dashboard" ? { label: "Panel", icon: PanelLeft } : view === "chat" ? { label: "Asistente", icon: Bot } : view === "conversations" ? { label: "Chats", icon: MessageSquare } : view === "agenda" ? { label: "Agenda", icon: Calendar } : { label: "Clientes", icon: Users };
            return <button key={view} type="button" className={view === "chat" ? "panel-shell__footer-nav--primary" : undefined} aria-current={currentView === view ? "page" : undefined} aria-label={item.label} onClick={() => handleNavigation(view)}><Icon icon={item.icon} /><span>{item.label}</span></button>;
         })}
       </nav>
        {inspector ? <aside className="panel-shell__inspector" aria-label="Inspector operacional">{inspector}</aside> : null}
    </div>
  );
}
