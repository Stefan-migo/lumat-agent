import { useCallback } from "react";
import type { CSSProperties, ReactNode } from "react";
import {
  AlertTriangle,
  ArrowRight,
  Calendar,
  ChartColumn,
  Clock,
  Inbox,
  MessageSquare,
  Tag,
  Users,
  Bot,
  Zap,
  type LucideIcon,
} from "lucide-react";
import { apiFetch, getDashboardToday, getDashboardTrend } from "../../api";
import type { DashboardToday, Kpis, Role } from "../../types";
import type { PanelView } from "../domain/PanelShell";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { StatCard } from "../shared/StatCard";
import { Icon } from "../primitives/Icon";

type IconName = "calendar" | "clock" | "message" | "users" | "agent" | "zap" | "alert" | "inbox" | "arrow" | "chart" | "tag";

const ICONS: Record<IconName, LucideIcon> = {
  calendar: Calendar,
  clock: Clock,
  message: MessageSquare,
  users: Users,
  agent: Bot,
  zap: Zap,
  alert: AlertTriangle,
  inbox: Inbox,
  arrow: ArrowRight,
  chart: ChartColumn,
  tag: Tag,
};

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
  state?: DashboardState;
  onRetry?: () => void;
  role?: Role;
  onNavigate?: (view: PanelView) => void;
}

export type DashboardState = AsyncDataState | "stale" | "partial-error" | "fatal-error";
type DashboardData = Kpis & { today?: DashboardToday; todayError?: boolean; trendError?: boolean };
const emptyToday: DashboardToday = { tz: "", local_date: "", appointments_today: [], unanswered_conversations: [], urgent_cases: [] };

function stateMessage(state: DashboardState, retry: () => void) {
  if (state === "loading") return <StateMessage tone="info" role="status" spinner title="Cargando indicadores" />;
  if (state === "empty") return <StateMessage tone="info" role="status" title="Aún no hay actividad en esta ventana" />;
  if (state === "denied") return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver este panel" />;
  if (state === "stale") return <StateMessage tone="warning" role="status" title="Los datos pueden estar desactualizados" detail="Mostramos la última información disponible." />;
  if (state === "partial-error") return <StateMessage tone="warning" role="alert" title="No pudimos cargar toda la actividad" detail="Algunos indicadores pueden estar incompletos." />;
  if (state === "error" || state === "fatal-error") return <div><StateMessage tone="danger" role="alert" title="No pudimos cargar el panel" detail="Reintenta para recuperar los indicadores." /><button type="button" onClick={retry}>Reintentar</button></div>;
  return null;
}

export function Dashboard({ data: controlledData, state: controlledState, onRetry, role = "admin", onNavigate }: DashboardProps) {
  const fetchDashboard = useCallback(async (): Promise<DashboardData> => {
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const kpis = await apiFetch<Kpis>("/panel/api/kpis");
    const fetchToday = (): Promise<{ today?: DashboardToday; todayError?: boolean }> =>
      getDashboardToday(timezone).then((today) => ({ today })).catch(() => ({ todayError: true }));
    const fetchTrend = (): Promise<{ trend?: { buckets: DashboardData["trend"] }; trendError?: boolean }> =>
      getDashboardTrend(timezone).then((trend) => ({ trend })).catch(() => ({ trendError: true }));
    const [todayResult, trendResult] = await Promise.all([
      fetchToday(),
      fetchTrend(),
    ]);
    return { ...kpis, today: todayResult.today, todayError: todayResult.todayError, trend: trendResult.trend?.buckets ?? [], trendError: trendResult.trendError };
  }, []);
  const fetched = useAsyncData(fetchDashboard, controlledData === undefined);
  const data = (controlledData === undefined ? fetched.data : controlledData) as DashboardData | null | undefined;
  const state = controlledState ?? fetched.state;
  const retry = onRetry ?? fetched.retry;
  const today = data?.today && Array.isArray(data.today.appointments_today) ? data.today : emptyToday;
  const hasPartialError = data?.todayError || data?.trendError;
  const navigate = (view: PanelView) => onNavigate?.(view);
  const cards = ["Conversaciones", "Clientes", "Agenda"] as const;
  const viewFor = { Conversaciones: "conversations", Clientes: "clients", Agenda: "agenda" } as const;
  const iconFor: Record<(typeof cards)[number], IconName> = { Conversaciones: "message", Clientes: "users", Agenda: "calendar" };
  const bars = data?.trend ?? [];
  const max = Math.max(...bars.map((bar) => bar.count), 1);
  const chartTotal = bars.reduce((sum, bar) => sum + bar.count, 0);
  const motivos = data?.motivos ?? [];

  const opsCard = (title: string, icon: IconName, tone: "primary" | "info" | "danger", count: number, body: ReactNode) => (
    <div className={`dashboard__card-ops dashboard__card-ops--${tone}`}>
      <div className="dashboard__card-ops__head">
        <span className="dashboard__card-ops__icon"><Icon icon={ICONS[icon]} size="sm" /></span>
        <h3>{title}</h3>
        <span className={`dashboard__card-ops__count${count > 0 ? " dashboard__card-ops__count--active" : ""}`}>{count}</span>
      </div>
      {body}
    </div>
  );

  return <PageFrame title="Panel" meta={data ? `Actividad de los últimos ${data.window_days} días · Desde ${data.window_start}` : "Actividad reciente del negocio"} state={stateMessage(state, retry)}>
    {state === "ready" && data ? <div className="dashboard">
      {hasPartialError ? stateMessage("partial-error", retry) : null}
      <section className="dashboard__section" aria-labelledby="today-title">
        <div className="dashboard__section-head">
          <h2 id="today-title">Hoy</h2>
          {today.local_date ? <span className="dashboard__day"><Icon icon={ICONS.calendar} size="sm" />{dayLabel(today.local_date)}</span> : null}
        </div>
        <div className="dashboard__hoy">
          {opsCard("Agenda", "calendar", "primary", today.appointments_today.length,
            <ul className="dashboard__list">{today.appointments_today.length ? today.appointments_today.map((row) => (
              <li key={row.id}><button className="dashboard__row" type="button" onClick={() => navigate("agenda")} aria-label={row.customer_name ?? row.service}>
                <span className="dashboard__row__time"><Icon icon={ICONS.clock} size="sm" />{row.local_start}</span>
                <strong>{row.service}</strong>
                <small>{row.customer_name ?? "Sin nombre"}</small>
              </button></li>
            )) : <li className="dashboard__empty"><Icon icon={ICONS.calendar} size="sm" /><span>No hay visitas para hoy</span></li>}</ul>)}
          {opsCard("Sin respuesta", "inbox", "info", today.unanswered_conversations.length,
            <ul className="dashboard__list">{today.unanswered_conversations.length ? today.unanswered_conversations.map((row) => (
              <li key={row.id}><button className="dashboard__row" type="button" onClick={() => navigate("conversations")} aria-label={row.customer_name ?? "Conversación"}>
                <strong>{row.customer_name ?? "Sin nombre"}</strong>
                <small>{row.state}</small>
              </button></li>
            )) : <li className="dashboard__empty"><Icon icon={ICONS.inbox} size="sm" /><span>No hay conversaciones pendientes</span></li>}</ul>)}
          {opsCard("Urgentes", "alert", "danger", today.urgent_cases.length,
            <ul className="dashboard__list">{today.urgent_cases.length ? today.urgent_cases.map((row) => (
              <li key={row.id}><button className="dashboard__row dashboard__row--urgent" type="button" onClick={() => navigate("cases")} aria-label={row.customer_name ?? "Caso urgente"}>
                <strong>{row.customer_name ?? "Sin nombre"}</strong>
                <small>{row.summary ?? row.service ?? "Caso urgente"}</small>
                <span className="dashboard__tag dashboard__tag--danger"><Icon icon={ICONS.alert} size="sm" />Urgente</span>
              </button></li>
            )) : <li className="dashboard__empty"><Icon icon={ICONS.alert} size="sm" /><span>No hay casos urgentes</span></li>}</ul>)}
        </div>
      </section>
      <section className="dashboard__section" aria-label="Navegación operativa">
        <div className="dashboard__section-head"><h2>Atajos</h2></div>
        <div className="dashboard__grid">
          <button className="dashboard__card dashboard__card--agent" type="button" onClick={() => navigate("chat")} aria-label="Abrir Agente Lumat">
            <span className="dashboard__card__icon"><Icon icon={ICONS.agent} size="md" /></span>
            <span className="dashboard__card__label">Agente Lumat</span>
            <span className="dashboard__card__sub">Consulta, deriva o delega tareas</span>
            <span className="dashboard__card__hint">Abrir <Icon icon={ICONS.arrow} size="sm" /></span>
          </button>
          {cards.map((label) => (
            <button className="dashboard__card" type="button" key={label} onClick={() => navigate(viewFor[label])} aria-label={`Abrir ${label}`}>
              <span className="dashboard__card__icon"><Icon icon={ICONS[iconFor[label]]} size="md" /></span>
              <span className="dashboard__card__label">{label}</span>
              <span className="dashboard__card__hint">Abrir <Icon icon={ICONS.arrow} size="sm" /></span>
            </button>
          ))}
          {role === "admin" ? <button className="dashboard__card dashboard__card--wide" type="button" onClick={() => navigate("automation-rules")} aria-label="Abrir Automatizaciones">
            <span className="dashboard__card__icon"><Icon icon={ICONS.zap} size="md" /></span>
            <span className="dashboard__card__label">Automatizaciones</span>
            <span className="dashboard__card__hint">Abrir <Icon icon={ICONS.arrow} size="sm" /></span>
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
            <div className="dashboard__chart__head"><Icon icon={ICONS.chart} size="sm" /><h3>Contactos por día</h3>{bars.length ? <span className="dashboard__chart__total">{chartTotal} contactos · {bars.length} días</span> : null}</div>
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
            })}</div> : <div className="dashboard__chart__empty"><Icon icon={ICONS.chart} size="sm" /><span>Sin actividad registrada en el período</span></div>}
          </div>
          <div className="dashboard__motivos">
            <div className="dashboard__chart__head"><Icon icon={ICONS.tag} size="sm" /><h3>Motivos</h3></div>
            <div className="dashboard__chips">{motivos.length ? motivos.map(([motivo, count]) => {
              const label = motivoLabel(motivo);
              return <span className="dashboard__chip" key={label} style={{ "--mot-accent": motivoAccent(motivo) } as CSSProperties}>{label} · {count}</span>;
            }) : <span className="dashboard__empty"><Icon icon={ICONS.tag} size="sm" /><span>No hay registros</span></span>}</div>
          </div>
        </div>
      </section>
    </div> : null}
  </PageFrame>;
}
