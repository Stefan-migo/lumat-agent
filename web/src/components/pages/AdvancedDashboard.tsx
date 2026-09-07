import { useCallback } from "react";
import { getAdvancedDashboard } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { AdvancedDashboardData } from "../../types";
import { StateMessage } from "../shared/StateMessage";
import { StatCard } from "../shared/StatCard";

export interface AdvancedDashboardProps { data?: AdvancedDashboardData | null; state?: AsyncDataState; }

export function AdvancedDashboard({ data: controlledData, state: controlledState }: AdvancedDashboardProps) {
  const fetcher = useCallback(() => getAdvancedDashboard(), []);
  const fetched = useAsyncData(fetcher, controlledData === undefined);
  const data = controlledData === undefined ? fetched.data : controlledData;
  const state = controlledState ?? (controlledData !== undefined ? "ready" : fetched.state);
  if (state === "loading") return <StateMessage tone="info" role="status" spinner title="Cargando indicadores operacionales" />;
  if (state === "denied") return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver este panel" />;
  if (state === "error") return <StateMessage tone="danger" role="alert" title="No pudimos cargar los indicadores operacionales" />;
  if (!data) return <StateMessage tone="info" role="status" title="Sin actividad en este período" />;
  const metrics = data.metrics ?? { contacts: 0, cases: 0, appointments: 0, notification_health: {}, automation_outcomes: {} };
  const trend = data.trend ?? [];
  const drilldown = data.drilldown ?? [];
  const hasActivity = trend.some((bucket) => bucket.count > 0);
  const period = data.period ?? { start: "", end: "", timezone: "" };
  return <section aria-labelledby="advanced-dashboard-title" className="advanced-dashboard">
    <h2 id="advanced-dashboard-title">Indicadores operacionales</h2>
    <p>{period.start} – {period.end} · {period.timezone}</p>
    <div className="kpi-grid">
      <StatCard label="Contactos" value={metrics.contacts} />
      <StatCard label="Casos" value={metrics.cases} />
      <StatCard label="Citas" value={metrics.appointments} />
    </div>
    {!hasActivity ? <p role="status">Sin actividad en este período</p> : <ul aria-label="Tendencia diaria">
      {trend.map((bucket) => <li key={bucket.start}><span>{bucket.start}</span>: <strong>{bucket.count}</strong></li>)}
    </ul>}
    {drilldown.length > 0 ? <ul aria-label="Detalle del período">{drilldown.map((row, index) => <li key={`${row.service ?? "row"}-${index}`}>{row.service ?? "Detalle"}: {row.count ?? 0}</li>)}</ul> : null}
  </section>;
}
