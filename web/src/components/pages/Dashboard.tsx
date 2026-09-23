import { useCallback } from "react";
import type { CSSProperties, ReactNode } from "react";
import { apiFetch, getDashboardToday, getDashboardTrend } from "../../api";
import type { DashboardToday, Kpis, Role } from "../../types";
import type { PanelView } from "../domain/PanelShell";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { StatCard } from "../shared/StatCard";

/* ---- Minimal stroke icon set (lucide-style, token-colored via currentColor) ---- */
const ICON_PATHS = {
  calendar: (<><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" /></>),
  clock: (<><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>),
  message: (<><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" /><path d="M8 12h.01M12 12h.01M16 12h.01" /></>),
  users: (<><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" /></>),
  case: (<><rect x="2" y="7" width="20" height="14" rx="2" /><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" /></>),
  agent: (<><path d="M12 3l1.9 5.7L19.6 10l-5.7 1.9L12 17.6l-1.9-5.7L4.4 10l5.7-1.9L12 3z" /><path d="M19 15l.9 2.6 2.6.9-2.6.9L19 22l-.9-2.6-2.6-.9 2.6-.9L19 15z" /></>),
  zap: <path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z" />,
  alert: (<><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><path d="M12 9v4M12 17h.01" /></>),
  inbox: (<><path d="M22 12h-6l-2 3h-4l-2-3H2" /><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" /></>),
  arrow: <path d="m9 18 6-6-6-6" />,
  chart: <path d="M18 20V10M12 20V4M6 20v-6" />,
  tag: (<><path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z" /><circle cx="7.5" cy="7.5" r=".5" fill="currentColor" /></>),
} as const;

type IconName = keyof typeof ICON_PATHS;

function Icon({ name, size = 16 }: { name: IconName; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {ICON_PATHS[name]}
    </svg>
  );
}

/* ---- Motivo -> palette accent (stable per motivo, token-only) ---- */
const MOTIVO_ACCENTS = [
  "var(--primary-700)",
  "var(--brand-forest)",
  "var(--info)",
  "var(--brand-graphite)",
  "var(--warning)",
  "color-mix(in srgb, var(--brand-cyan) 55%, var(--primary-900))",
] as const;

const MOTIVO_FALLBACK = "sin clasificar";

function motivoLabel(motivo: string | null): string {
  return motivo ?? MOTIVO_FALLBACK;
}

function motivoAccent(motivo: string | null): string {
  const label = motivoLabel(motivo);
  let hash = 0;
  for (let i = 0; i < label.length; i += 1) hash = (hash * 31 + label.charCodeAt(i)) >>> 0;
  return MOTIVO_ACCENTS[hash % MOTIVO_ACCENTS.length];
}

/* ---- Locale-safe day labels (fallback to the raw date string) ---- */
function dayLabel(localDate: string): string {
  try {
    const date = new Date(`${localDate}T12:00:00`);
    if (Number.isNaN(date.getTime())) return localDate;
    return new Intl.DateTimeFormat("es-CL", { weekday: "long", day: "numeric", month: "long" }).format(date);
  } catch {
    return localDate;
  }
}

function dayShort(start: string): string {
  try {
    const date = new Date(`${start}T12:00:00`);
    if (Number.isNaN(date.getTime())) return start.slice(5);
    return new Intl.DateTimeFormat("es-CL", { weekday: "short" }).format(date);
  } catch {
    return start.slice(5);
  }
}

export interface DashboardProps {
  data?: Kpis | null;
  state?: AsyncDataState;
  onRetry?: () => void;
  role?: Role;
  onNavigate?: (view: PanelView) => void;
}

type DashboardData = Kpis & { today?: DashboardToday };
const emptyToday: DashboardToday = { tz: "", local_date: "", appointments_today: [], unanswered_conversations: [], urgent_cases: [] };

function stateMessage(state: AsyncDataState, retry: () => void) {
  if (state === "loading") return <StateMessage tone="info" role="status" spinner title="Cargando indicadores" />;
  if (state === "empty") return <StateMessage tone="info" role="status" title="Aún no hay actividad en esta ventana" />;
  if (state === "denied") return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver este panel" />;
  if (state === "error") return <div><StateMessage tone="danger" role="alert" title="No pudimos cargar el panel" detail="Reintenta para recuperar los indicadores." /><button type="button" onClick={retry}>Reintentar</button></div>;
  return null;
}

export function Dashboard({ data: controlledData, state: controlledState, onRetry, role = "admin", onNavigate }: DashboardProps) {
  const fetchDashboard = useCallback(async (): Promise<DashboardData> => {
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const kpis = await apiFetch<Kpis>("/panel/api/kpis");
    const [today, trend] = await Promise.all([
      getDashboardToday(timezone).catch(() => emptyToday),
      getDashboardTrend(timezone).catch(() => ({ buckets: [] })),
    ]);
    return { ...kpis, today, trend: trend.buckets ?? [] };
  }, []);
  const fetched = useAsyncData(fetchDashboard, controlledData === undefined);
  const data = (controlledData === undefined ? fetched.data : controlledData) as DashboardData | null | undefined;
  const state = controlledState ?? fetched.state;
  const retry = onRetry ?? fetched.retry;
  const today = data?.today && Array.isArray(data.today.appointments_today) ? data.today : emptyToday;
  const navigate = (view: PanelView) => onNavigate?.(view);
  const cards = ["Conversaciones", "Clientes", "Agenda", "Casos"] as const;
  const viewFor = { Conversaciones: "conversations", Clientes: "clients", Agenda: "agenda", Casos: "cases" } as const;
  const iconFor: Record<string, IconName> = { Conversaciones: "message", Clientes: "users", Agenda: "calendar", Casos: "case" };
  const accents: Record<string, string> = {
    Conversaciones: "var(--primary-700)",
    Clientes: "var(--info)",
    Agenda: "color-mix(in srgb, var(--brand-cyan) 55%, var(--primary-900))",
    Casos: "var(--warning)",
  };
  const bars = data?.trend ?? [];
  const max = Math.max(...bars.map((bar) => bar.count), 1);
  const chartTotal = bars.reduce((sum, bar) => sum + bar.count, 0);
  const motivos = data?.motivos ?? [];

  const opsCard = (title: string, icon: IconName, tone: "primary" | "info" | "danger", count: number, body: ReactNode) => (
    <div className={`dashboard__card-ops dashboard__card-ops--${tone}`}>
      <div className="dashboard__card-ops__head">
        <span className="dashboard__card-ops__icon"><Icon name={icon} size={16} /></span>
        <h3>{title}</h3>
        <span className={`dashboard__card-ops__count${count > 0 ? " dashboard__card-ops__count--active" : ""}`}>{count}</span>
      </div>
      {body}
    </div>
  );

  return <PageFrame title="Panel" headerClassName="dashboard-header" meta={data ? <span className="dashboard-meta"><Icon name="calendar" size={14} />Actividad de los últimos {data.window_days} días · Desde {data.window_start}</span> : undefined} state={stateMessage(state, retry)}>
    {state === "ready" && data ? <div className="dashboard">
      <section className="dashboard__section" aria-labelledby="today-title">
        <div className="dashboard__section-head">
          <h2 id="today-title">HOY</h2>
          {today.local_date ? <span className="dashboard__day"><Icon name="calendar" size={14} />{dayLabel(today.local_date)}</span> : null}
        </div>
        <div className="dashboard__hoy">
          {opsCard("Agenda", "calendar", "primary", today.appointments_today.length,
            <ul className="dashboard__list">{today.appointments_today.length ? today.appointments_today.map((row) => (
              <li key={row.id}><button className="dashboard__row" type="button" onClick={() => navigate("agenda")} aria-label={row.customer_name ?? row.service}>
                <span className="dashboard__row__time"><Icon name="clock" size={12} />{row.local_start}</span>
                <strong>{row.service}</strong>
                <small>{row.customer_name ?? "Sin nombre"}</small>
              </button></li>
            )) : <li className="dashboard__empty"><Icon name="calendar" size={16} /><span>No hay visitas para hoy</span></li>}</ul>)}
          {opsCard("Sin respuesta", "inbox", "info", today.unanswered_conversations.length,
            <ul className="dashboard__list">{today.unanswered_conversations.length ? today.unanswered_conversations.map((row) => (
              <li key={row.id}><button className="dashboard__row" type="button" onClick={() => navigate("conversations")} aria-label={row.customer_name ?? "Conversación"}>
                <strong>{row.customer_name ?? "Sin nombre"}</strong>
                <small>{row.state}</small>
              </button></li>
            )) : <li className="dashboard__empty"><Icon name="inbox" size={16} /><span>No hay conversaciones pendientes</span></li>}</ul>)}
          {opsCard("Urgentes", "alert", "danger", today.urgent_cases.length,
            <ul className="dashboard__list">{today.urgent_cases.length ? today.urgent_cases.map((row) => (
              <li key={row.id}><button className="dashboard__row dashboard__row--urgent" type="button" onClick={() => navigate("cases")} aria-label={row.customer_name ?? "Caso urgente"}>
                <strong>{row.customer_name ?? "Sin nombre"}</strong>
                <small>{row.summary ?? row.service ?? "Caso urgente"}</small>
                <span className="dashboard__tag dashboard__tag--danger"><Icon name="alert" size={12} />Urgente</span>
              </button></li>
            )) : <li className="dashboard__empty"><Icon name="alert" size={16} /><span>No hay casos urgentes</span></li>}</ul>)}
        </div>
      </section>
      <section className="dashboard__section" aria-label="Navegación operativa">
        <div className="dashboard__section-head"><h2>Atajos</h2></div>
        <div className="dashboard__grid">
          {role === "admin" ? <button className="dashboard__card dashboard__card--agent" type="button" onClick={() => navigate("chat")} aria-label="Abrir Agente Lumat">
            <span className="dashboard__card__icon"><Icon name="agent" size={20} /></span>
            <span className="dashboard__card__label">Agente Lumat</span>
            <span className="dashboard__card__sub">Consulta, deriva o delega tareas</span>
            <span className="dashboard__card__hint">Abrir <Icon name="arrow" size={12} /></span>
          </button> : null}
          {cards.map((label) => (
            <button className="dashboard__card" type="button" key={label} onClick={() => navigate(viewFor[label])} aria-label={`Abrir ${label}`} style={{ "--bent-accent": accents[label] } as CSSProperties}>
              <span className="dashboard__card__icon"><Icon name={iconFor[label]} size={18} /></span>
              <span className="dashboard__card__label">{label}</span>
              <span className="dashboard__card__hint">Abrir <Icon name="arrow" size={12} /></span>
            </button>
          ))}
          {role === "admin" ? <button className="dashboard__card dashboard__card--wide" type="button" onClick={() => navigate("automation-rules")} aria-label="Abrir Automatizaciones" style={{ "--bent-accent": "var(--brand-graphite)" } as CSSProperties}>
            <span className="dashboard__card__icon"><Icon name="zap" size={18} /></span>
            <span className="dashboard__card__label">Automatizaciones</span>
            <span className="dashboard__card__hint">Abrir <Icon name="arrow" size={12} /></span>
          </button> : null}
        </div>
      </section>
      <section className="dashboard__section" aria-labelledby="period-title">
        <div className="dashboard__section-head"><h2 id="period-title">Período</h2></div>
        <div className="kpi-grid">
          <StatCard label="Contactos" value={data.contacts} accent="var(--primary-700)" />
          <StatCard label="Derivados" value={data.derived} accent="var(--warning)" />
          <StatCard label="Solicitudes de visita" value={data.visit_requests} accent="var(--primary-800)" />
          <StatCard label="Nuevos clientes" value={data.new_customers ?? 0} accent="var(--success)" />
        </div>
        <div className="dashboard__period">
          <div className="dashboard__chart" aria-label="Tendencia de contactos de 7 días">
            <div className="dashboard__chart__head"><Icon name="chart" size={16} /><h3>Contactos por día</h3>{bars.length ? <span className="dashboard__chart__total">{chartTotal} contactos · {bars.length} días</span> : null}</div>
            {bars.length ? <div className="dashboard__bars">{bars.map((bar) => {
              const pct = max > 0 && bar.count > 0 ? Math.max((bar.count / max) * 100, 6) : 0;
              const cls = ["dashboard__bar"];
              if (bar.count > 0 && bar.count === max) cls.push("dashboard__bar--peak");
              if (bar.start === today.local_date) cls.push("dashboard__bar--today");
              return (
                <div className="dashboard__bar-col" key={bar.start}>
                  <span className="dashboard__bar-col__value">{bar.count > 0 ? bar.count : ""}</span>
                  <span className={cls.join(" ")} style={{ height: `${pct}%` }} />
                  <span className="dashboard__bar-col__day">{dayShort(bar.start)}</span>
                </div>
              );
            })}</div> : <div className="dashboard__chart__empty"><Icon name="chart" size={16} /><span>Sin actividad registrada en el período</span></div>}
          </div>
          <div className="dashboard__motivos">
            <div className="dashboard__chart__head"><Icon name="tag" size={16} /><h3>Motivos</h3></div>
            <div className="dashboard__chips">{motivos.length ? motivos.map(([motivo, count]) => {
              const label = motivoLabel(motivo);
              return <span className="dashboard__chip" key={label} style={{ "--mot-accent": motivoAccent(motivo) } as CSSProperties}>{label} · {count}</span>;
            }) : <span className="dashboard__empty"><Icon name="tag" size={16} /><span>No hay registros</span></span>}</div>
          </div>
        </div>
      </section>
    </div> : null}
  </PageFrame>;
}
