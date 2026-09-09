import { useCallback } from "react";
import type { ReactNode } from "react";
import { apiFetch, getDashboardToday, getDashboardTrend } from "../../api";
import type { DashboardToday, Kpis } from "../../types";
import type { PanelView } from "../domain/PanelShell";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { StatCard } from "../shared/StatCard";

const STYLES = `.dashboard { display:grid; gap:var(--space-5); } .dashboard__section { display:grid; gap:var(--space-3); } .dashboard__grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:var(--space-3); } .dashboard__grid--admin { grid-template-columns:repeat(4,minmax(0,1fr)); } .dashboard__card,.dashboard__row { border:1px solid var(--corp-border); border-radius:var(--radius-md); background:var(--corp-surface); padding:var(--space-4); text-align:left; } .dashboard__card { min-height:5rem; } .dashboard__card--agent { grid-row:span 2; grid-column:span 2; } .dashboard__rows { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:var(--space-3); } .dashboard__list { display:grid; gap:var(--space-2); margin:0; padding:0; list-style:none; } .dashboard__row { width:100%; } .dashboard__row small,.dashboard__row strong { display:block; } .dashboard__trend { display:flex; align-items:end; gap:var(--space-2); height:4rem; padding:var(--space-3); border:1px solid var(--corp-border); border-radius:var(--radius-md); } .dashboard__bar { flex:1; min-width:var(--space-2); background:var(--primary-700); border-radius:var(--radius-sm) var(--radius-sm) 0 0; } .dashboard__chips { display:flex; flex-wrap:wrap; gap:var(--space-2); } .dashboard__chip { padding:var(--space-2) var(--space-3); border-radius:999px; background:var(--corp-surface); border:1px solid var(--corp-border); } @media (max-width: 760px) { .dashboard__rows,.dashboard__grid,.dashboard__grid--admin { grid-template-columns:1fr 1fr; } .dashboard__card--agent { grid-column:span 2; } }`;

export interface DashboardProps {
  data?: Kpis | null;
  state?: AsyncDataState;
  onRetry?: () => void;
  role?: "admin" | "operador";
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
  const bars = data?.trend ?? [];
  const max = Math.max(...bars.map((bar) => bar.count), 1);
  const motivos = data?.motivos ?? [];
  const section = (title: string, rows: ReactNode) => <section className="dashboard__section" aria-labelledby={`today-${title}`}><h3 id={`today-${title}`}>{title}</h3>{rows}</section>;

  return <PageFrame title="Panel" meta={data ? `Actividad de los últimos ${data.window_days} días · Desde ${data.window_start}` : undefined} state={stateMessage(state, retry)}>
    <style>{STYLES}</style>
    {state === "ready" && data ? <div className="dashboard">
      <section className="dashboard__section" aria-labelledby="today-title"><h2 id="today-title">HOY</h2><div className="dashboard__rows">
        {section("Agenda", <ul className="dashboard__list">{today.appointments_today.length ? today.appointments_today.map((row) => <li key={row.id}><button className="dashboard__row" type="button" onClick={() => navigate("agenda")} aria-label={row.customer_name ?? row.service}><strong>{row.local_start} · {row.service}</strong><small>{row.customer_name ?? "Sin nombre"}</small></button></li>) : <li>No hay visitas para hoy</li>}</ul>)}
        {section("Sin respuesta", <ul className="dashboard__list">{today.unanswered_conversations.length ? today.unanswered_conversations.map((row) => <li key={row.id}><button className="dashboard__row" type="button" onClick={() => navigate("conversations")} aria-label={row.customer_name ?? "Conversación"}><strong>{row.customer_name ?? "Sin nombre"}</strong><small>{row.state}</small></button></li>) : <li>No hay conversaciones pendientes</li>}</ul>)}
        {section("Urgentes", <ul className="dashboard__list">{today.urgent_cases.length ? today.urgent_cases.map((row) => <li key={row.id}><button className="dashboard__row" type="button" onClick={() => navigate("cases")} aria-label={row.customer_name ?? "Caso urgente"}><strong>{row.customer_name ?? "Sin nombre"}</strong><small>{row.summary ?? row.service ?? "Caso urgente"}</small></button></li>) : <li>No hay casos urgentes</li>}</ul>)}
      </div></section>
      <section className="dashboard__section" aria-label="Navegación operativa"><h2>Atajos</h2><div className={role === "admin" ? "dashboard__grid dashboard__grid--admin" : "dashboard__grid"}>{role === "admin" ? <button className="dashboard__card dashboard__card--agent" type="button" onClick={() => navigate("chat")}>Agente Lumat</button> : null}{cards.map((label) => <button className="dashboard__card" type="button" key={label} onClick={() => navigate(viewFor[label])}>{label}</button>)}{role === "admin" ? <button className="dashboard__card" type="button" onClick={() => navigate("automation-rules")}>Automatizaciones</button> : null}</div></section>
      <section className="dashboard__section" aria-labelledby="period-title"><h2 id="period-title">Período</h2><div className="kpi-grid"><StatCard label="Contactos" value={data.contacts} accent="var(--primary-700)" /><StatCard label="Derivados" value={data.derived} accent="var(--warning)" /><StatCard label="Solicitudes de visita" value={data.visit_requests} accent="var(--primary-800)" /><StatCard label="Nuevos clientes" value={data.new_customers ?? 0} accent="var(--success)" /></div><div className="dashboard__trend" aria-label="Tendencia de contactos de 7 días">{bars.map((bar) => <span className="dashboard__bar" key={bar.start} style={{ height: `${Math.max((bar.count / max) * 100, 4)}%` }} />)}</div><div><h3>Motivos</h3><div className="dashboard__chips">{motivos.length ? motivos.map(([motivo, count]) => <span className="dashboard__chip" key={motivo}>{motivo} · {count}</span>) : <span>No hay registros</span>}</div></div></section>
    </div> : null}
  </PageFrame>;
}
