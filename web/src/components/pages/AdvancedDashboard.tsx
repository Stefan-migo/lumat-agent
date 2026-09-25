import { useCallback } from "react";
import { getAdvancedDashboard } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { AdvancedDashboardData } from "../../types";
import { StateMessage } from "../shared/StateMessage";
import { StatCard } from "../shared/StatCard";
import { PageFrame } from "../shared/PageFrame";

export interface AdvancedDashboardProps { data?: AdvancedDashboardData | null; state?: AsyncDataState; }

export function AdvancedDashboard({ data: controlledData, state: controlledState }: AdvancedDashboardProps) {
  const fetcher = useCallback(() => getAdvancedDashboard(), []);
  const fetched = useAsyncData(fetcher, controlledData === undefined);
  const data = controlledData === undefined ? fetched.data : controlledData;
  const state = controlledState ?? (controlledData !== undefined ? "ready" : fetched.state);
  const metrics = data?.metrics ?? { contacts: 0, cases: 0, appointments: 0, notification_health: {}, automation_outcomes: {} };
  const trend = data?.trend ?? [];
  const drilldown = data?.drilldown ?? [];
  const hasActivity = trend.some((bucket) => bucket.count > 0);
  const period = data?.period ?? { start: "", end: "", timezone: "" };
  const stateContent = state === "loading"
    ? <StateMessage tone="info" role="status" spinner title="Cargando indicadores operacionales" />
    : state === "denied"
      ? <StateMessage tone="danger" role="alert" title="No tienes permiso para ver este panel" />
      : state === "error"
        ? <StateMessage tone="danger" role="alert" title="No pudimos cargar los indicadores operacionales" />
        : !data
          ? <StateMessage tone="info" role="status" title="Sin actividad en este período" />
          : undefined;
  return <PageFrame title="Indicadores operacionales" meta={data ? `${period.start} – ${period.end} · ${period.timezone}` : "Indicadores operacionales del período"} state={stateContent}>
    {data ? <section className="advanced-dashboard">
      <div className="kpi-grid">
        <StatCard label="Contactos" value={metrics.contacts} />
        <StatCard label="Casos" value={metrics.cases} />
        <StatCard label="Citas" value={metrics.appointments} />
      </div>
      {!hasActivity ? <p role="status">Sin actividad en este período</p> : <ul aria-label="Tendencia diaria">
        {trend.map((bucket) => <li key={bucket.start}><span>{bucket.start}</span>: <strong>{bucket.count}</strong></li>)}
      </ul>}
      {drilldown.length > 0 ? <ul aria-label="Detalle del período">{drilldown.map((row, index) => <li key={`${row.service ?? "row"}-${index}`}>{row.service ?? "Detalle"}: {row.count ?? 0}</li>)}</ul> : null}
    </section> : null}
  </PageFrame>;
}
