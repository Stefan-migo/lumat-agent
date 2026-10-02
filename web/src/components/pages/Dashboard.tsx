import { useCallback, useState } from "react";
import type { ReactNode } from "react";
import {
  AlertTriangle,
  ArrowRight,
  Calendar,
  ChevronDown,
  ChartColumn,
  Clock,
  Inbox,
  MessageSquare,
  Tag,
  Users,
  Bot,
  Settings,
  Zap,
  type LucideIcon,
} from "lucide-react";
import { getDashboardKpis, getDashboardToday, getDashboardTrend } from "../../api";
import type { DashboardToday, Kpis, Role } from "../../types";
import type { PanelView } from "../domain/PanelShell";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { StatCard } from "../shared/StatCard";
import { Icon } from "../primitives/Icon";
import { Select } from "../primitives/Select";

type IconName = "calendar" | "chevronDown" | "clock" | "message" | "users" | "agent" | "zap" | "alert" | "inbox" | "arrow" | "chart" | "tag" | "settings";

const ICONS: Record<IconName, LucideIcon> = {
  calendar: Calendar,
  chevronDown: ChevronDown,
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
  settings: Settings,
};

const MOTIVO_FALLBACK = "sin clasificar";

function motivoLabel(motivo: string | null): string {
  return motivo ?? MOTIVO_FALLBACK;
}

/* ---- Locale-safe day labels (fallback to the raw date string) ---- */
function dayLabel(localDate: string): string {
  try {
    const date = new Date(`${localDate}T12:00:00`);
    if (Number.isNaN(date.getTime())) return localDate;
    return new Intl.DateTimeFormat("es-CL", { weekday: "long", day: "numeric", month: "long" }).format(date).replace(/^./, (letter) => letter.toLocaleUpperCase("es-CL"));
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

function periodStartLabel(start: string): string {
  try {
    const date = new Date(`${start}T12:00:00`);
    if (Number.isNaN(date.getTime())) return start;
    return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", year: "numeric" }).format(date);
  } catch {
    return start;
  }
}

function shortDate(start: string): string {
  try {
    const date = new Date(`${start}T12:00:00`);
    if (Number.isNaN(date.getTime())) return start;
    return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short" }).format(date);
  } catch {
    return start;
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
  if (state === "error" || state === "fatal-error") return <div><StateMessage tone="danger" role="alert" title="No pudimos cargar el panel" detail="Reintenta para recuperar los indicadores." /><button className="dashboard__retry-button" type="button" onClick={retry}>Reintentar</button></div>;
  return null;
}

export function Dashboard({ data: controlledData, state: controlledState, onRetry, role = "admin", onNavigate }: DashboardProps) {
  const [windowDays, setWindowDays] = useState(7);
  const fetchDashboard = useCallback(async (): Promise<DashboardData> => {
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const kpis = await getDashboardKpis(windowDays);
    const fetchToday = (): Promise<{ today?: DashboardToday; todayError?: boolean }> =>
      getDashboardToday(timezone).then((today) => ({ today })).catch(() => ({ todayError: true }));
    const fetchTrend = (): Promise<{ trend?: { buckets: DashboardData["trend"] }; trendError?: boolean }> =>
      getDashboardTrend(timezone, windowDays).then((trend) => ({ trend })).catch(() => ({ trendError: true }));
    const [todayResult, trendResult] = await Promise.all([
      fetchToday(),
      fetchTrend(),
    ]);
    return { ...kpis, today: todayResult.today, todayError: todayResult.todayError, trend: trendResult.trend?.buckets ?? [], trendError: trendResult.trendError };
  }, [windowDays]);
  const fetched = useAsyncData(fetchDashboard, controlledData === undefined, windowDays);
  const data = (controlledData === undefined ? fetched.data : controlledData) as DashboardData | null | undefined;
  const state = controlledState ?? fetched.state;
  const retry = onRetry ?? fetched.retry;
  const today = data?.today && Array.isArray(data.today.appointments_today) ? data.today : emptyToday;
  const hasPartialError = data?.todayError || data?.trendError;
  const navigate = (view: PanelView) => onNavigate?.(view);
  const cards = ["Conversaciones", "Clientes", "Agenda", "Configuración"] as const;
  const viewFor = { Conversaciones: "conversations", Clientes: "clients", Agenda: "agenda", Configuración: "settings" } as const;
  const iconFor: Record<(typeof cards)[number], IconName> = { Conversaciones: "message", Clientes: "users", Agenda: "calendar", Configuración: "settings" };
  const bars = data?.trend ?? [];
  const labelInterval = Math.ceil(bars.length / 7);
  const max = Math.max(...bars.map((bar) => bar.count), 1);
  const axisMax = Math.max(max + 1, 4);
  const ticks = Array.from({ length: axisMax + 1 }, (_, index) => axisMax - index);
  const chartTotal = bars.reduce((sum, bar) => sum + bar.count, 0);
  const rangeEnd = bars.at(-1)?.start ?? today.local_date;
  const rangeEndYear = rangeEnd ? new Date(`${rangeEnd}T12:00:00`).getFullYear() : new Date().getFullYear();
  const rangeLabel = data?.window_start && rangeEnd ? `${shortDate(data.window_start)} – ${shortDate(rangeEnd)} ${rangeEndYear}` : "";
  const motivos = data?.motivos ?? [];

  const opsCard = (title: string, icon: IconName, tone: "primary" | "info" | "danger", count: number, action: string, view: PanelView, body: ReactNode, showCount = true) => (
    <div className={`dashboard__card-ops dashboard__card-ops--${tone}`}>
      <div className="dashboard__card-ops__head">
        <span className="dashboard__card-ops__icon"><Icon icon={ICONS[icon]} size="sm" /></span>
        <h3>{title}</h3>
        {showCount && count > 0 ? <span className={`dashboard__card-ops__count${count > 0 ? " dashboard__card-ops__count--active" : ""}`}>{count}</span> : null}
      </div>
      {body}
      <button className="dashboard__card-ops__link" type="button" onClick={() => navigate(view)}>{action}<Icon icon={ICONS.arrow} size="sm" /></button>
    </div>
  );

  return <PageFrame title="Dashboard" meta={data ? `Actividad de los últimos ${data.window_days} días · Desde ${periodStartLabel(data.window_start)}` : "Actividad reciente del negocio"} state={stateMessage(state, retry)}>
    {state === "ready" && data ? <div className="dashboard">
      {hasPartialError ? stateMessage("partial-error", retry) : null}
      <section className="dashboard__section" aria-labelledby="today-title">
        <div className="dashboard__section-head">
          <h2 id="today-title">Hoy</h2>
          {today.local_date ? <span className="dashboard__day"><Icon icon={ICONS.calendar} size="sm" />{dayLabel(today.local_date)}</span> : null}
        </div>
        <div className="dashboard__hoy">
          {opsCard("Agenda de hoy", "calendar", "primary", today.appointments_today.length, "Ver agenda", "agenda",
            <ul className="dashboard__list">{today.appointments_today.length ? today.appointments_today.slice(0, 3).map((row) => (
              <li key={row.id}><button className="dashboard__row" type="button" onClick={() => navigate("agenda")} aria-label={row.customer_name ?? row.service}>
                <span className="dashboard__row__time"><Icon icon={ICONS.clock} size="sm" />{row.local_start}</span>
                <strong>{row.service}</strong>
                <small>{row.customer_name ?? "Sin nombre"}</small>
              </button></li>
            )) : <li className="dashboard__empty"><Icon icon={ICONS.calendar} size="sm" /><span>No hay visitas para hoy</span></li>}</ul>)}
          {opsCard("Sin respuesta", "inbox", "info", today.unanswered_conversations.length, "Ver conversaciones", "conversations",
            <div className="dashboard__metric-content"><strong className="dashboard__metric-value">{today.unanswered_conversations.length}</strong><ul className="dashboard__list">{today.unanswered_conversations.length ? today.unanswered_conversations.slice(0, 3).map((row) => (
              <li key={row.id}><button className="dashboard__row" type="button" onClick={() => navigate("conversations")} aria-label={row.customer_name ?? "Conversación"}>
                <strong>{row.customer_name ?? "Sin nombre"}</strong>
                <small>{row.state}</small>
              </button></li>
            )) : <li className="dashboard__empty"><Icon icon={ICONS.inbox} size="sm" /><span>No hay conversaciones pendientes</span></li>}</ul></div>, false)}
          {opsCard("Urgentes", "alert", "danger", today.urgent_cases.length, "Ver casos", "cases",
            <div className="dashboard__metric-content"><strong className="dashboard__metric-value">{today.urgent_cases.length}</strong><ul className="dashboard__list">{today.urgent_cases.length ? today.urgent_cases.slice(0, 3).map((row) => (
              <li key={row.id}><button className="dashboard__row dashboard__row--urgent" type="button" onClick={() => navigate("cases")} aria-label={row.customer_name ?? "Caso urgente"}>
                <span className="dashboard__row__head">
                  <strong>{row.customer_name ?? "Sin nombre"}</strong>
                  <span className="dashboard__tag dashboard__tag--danger"><Icon icon={ICONS.alert} size="sm" />Urgente</span>
                </span>
                <small className="dashboard__row__summary">{row.summary ?? row.service ?? "Caso urgente"}</small>
              </button></li>
            )) : <li className="dashboard__empty"><Icon icon={ICONS.alert} size="sm" /><span>No hay casos urgentes</span></li>}</ul></div>, false)}
        </div>
      </section>
      <section className="dashboard__section" aria-label="Navegación operativa">
        <div className="dashboard__section-head dashboard__shortcuts-head"><h2>Accesos rápidos</h2></div>
        <div className="dashboard__grid">
          <button className="dashboard__card dashboard__card--agent" type="button" onClick={() => navigate("chat")} aria-label="Abrir asistente">
            <span className="dashboard__card__icon"><Icon icon={ICONS.agent} size="md" /></span>
            <span className="dashboard__card__copy"><span className="dashboard__card__label">Asistente Lumat</span>
              <span className="dashboard__card__sub">Consulta, deriva o delega tareas.</span></span>
            <span className="dashboard__card__hint dashboard__card__hint--desktop">Abrir asistente <Icon icon={ICONS.arrow} size="sm" /></span>
            <span className="dashboard__card__hint dashboard__card__hint--mobile" aria-hidden="true"><Icon icon={ICONS.arrow} size="sm" /></span>
          </button>
          {cards.map((label) => (
            <button className="dashboard__card" type="button" key={label} onClick={() => navigate(viewFor[label])} aria-label={`Abrir ${label}`}>
              <span className="dashboard__card__icon"><Icon icon={ICONS[iconFor[label]]} size="md" /></span>
              <span className="dashboard__card__label">{label === "Configuración" ? <><span className="dashboard__label-desktop">Configuración</span><span className="dashboard__label-mobile">Config</span></> : label}</span>
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
        <div className="dashboard__section-head dashboard__period-head">
          <h2 id="period-title">Actividad del período</h2>
          <div className="dashboard__period-control">
            <div className="dashboard__period-pill">
              <Icon icon={ICONS.calendar} size="sm" />
              <Select
                className="dashboard__period-select"
                label="Período de actividad"
                aria-label="Período de actividad"
                value={windowDays}
                onChange={(event) => setWindowDays(Number(event.target.value))}
                options={[
                  { value: "7", label: "Últimos 7 días" },
                  { value: "14", label: "Últimos 14 días" },
                  { value: "30", label: "Últimos 30 días" },
                ]}
              />
              <Icon icon={ICONS.chevronDown} size="sm" />
            </div>
            {data.window_start ? <span className="dashboard__period-caption">Desde el {periodStartLabel(data.window_start)}</span> : null}
          </div>
        </div>
        <div className="kpi-grid">
          <StatCard label="Contactos" value={data.contacts} accent="var(--primary-700)" />
          <StatCard label="Derivados" value={data.derived} accent="var(--warning)" />
          <StatCard label="Solicitudes de visita" value={data.visit_requests} accent="var(--primary-800)" />
          <StatCard label="Nuevos clientes" value={data.new_customers ?? 0} accent="var(--success)" />
        </div>
        <div className="dashboard__period">
          <div className="dashboard__chart" aria-label={`Tendencia de contactos de ${windowDays} días`}>
            <div className="dashboard__chart__head"><Icon icon={ICONS.chart} size="sm" /><h3>Contactos por día</h3><span className="dashboard__chart__total">{chartTotal} contactos · {bars.length} días</span></div>
            {bars.some((bar) => bar.count > 0) ? <div className="dashboard__chart__body">
              <div className="dashboard__plot">
                <div className="dashboard__plot__axis" aria-hidden="true">{ticks.map((tick) => <span key={tick}>{tick}</span>)}</div>
                <div className="dashboard__plot__area">
                  <div className="dashboard__plot__grid" aria-hidden="true">{ticks.map((tick) => <span key={tick} />)}</div>
                  <div className="dashboard__bars">{bars.map((bar) => {
                    const pct = bar.count > 0 ? Math.max((bar.count / axisMax) * 100, 1) : 0;
              const cls = ["dashboard__bar"];
              if (bar.count > 0 && bar.count === max) cls.push("dashboard__bar--peak");
              if (bar.start === today.local_date) cls.push("dashboard__bar--today");
              return (
                <div className="dashboard__bar-col" key={bar.start}>
                  <span className={cls.join(" ")} style={{ height: `${pct}%` }} />
                </div>
              );
                  })}</div>
                </div>
              </div>
              <div className="dashboard__bar-labels" aria-hidden="true">{bars.map((bar, index) => index % labelInterval === 0
                ? <span className="dashboard__bar-col__day" key={bar.start}>{dayShort(bar.start)}</span>
                : <span className="dashboard__bar-label-spacer" key={bar.start} />)}</div>
            </div> : <div className="dashboard__chart__empty"><Icon icon={ICONS.chart} size="sm" /><span><strong>Sin contactos en este período</strong><br />La actividad aparecerá aquí cuando se registren contactos.</span></div>}
            {bars.some((bar) => bar.count > 0) ? <div className="dashboard__chart__foot"><span className="dashboard__chart__range"><Icon icon={ICONS.calendar} size="sm" />{rangeLabel}</span><span className="dashboard__chart__hint">Cada barra representa un día.</span></div> : null}
          </div>
          <div className="dashboard__motivos">
            <div className="dashboard__chart__head dashboard__motivos__head"><Icon icon={ICONS.tag} size="sm" /><div className="dashboard__motivos__titles"><h3>Motivos de contacto</h3><span className="dashboard__motivos__sub">Ordenados por frecuencia</span></div></div>
            <div className="dashboard__motivos-list">{motivos.length ? motivos.map(([motivo, count]) => {
              const label = motivoLabel(motivo);
              return <div className="dashboard__motivo" key={label}><span>{label}</span><span className="dashboard__motivo-count">{count}</span></div>;
            }) : <span className="dashboard__empty"><Icon icon={ICONS.tag} size="sm" /><span>No hay registros</span></span>}</div>
            <div className="dashboard__motivos__foot"><span>{chartTotal} contactos en el período</span></div>
          </div>
        </div>
      </section>
    </div> : null}
  </PageFrame>;
}
