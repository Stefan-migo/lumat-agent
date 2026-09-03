import { useCallback } from "react";
import { apiFetch } from "../../api";
import type { Kpis } from "../../types";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import { PageFrame } from "../../stories/pages/_shared/PageFrame";
import { StateMessage } from "../../stories/pages/_shared/StateMessage";
import { StatCard } from "../../stories/pages/_shared/StatCard";
import { AdvancedDashboard } from "./AdvancedDashboard";

export interface DashboardProps {
  data?: Kpis | null;
  state?: AsyncDataState;
  onRetry?: () => void;
}

function stateMessage(state: AsyncDataState, retry: () => void) {
  if (state === "loading") return <StateMessage tone="info" role="status" spinner title="Cargando indicadores" />;
  if (state === "empty") return <StateMessage tone="info" role="status" title="Aún no hay actividad en esta ventana" />;
  if (state === "denied") return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver este panel" />;
  if (state === "error") {
    return (
      <div>
        <StateMessage tone="danger" role="alert" title="No pudimos cargar el panel" detail="Reintenta para recuperar los indicadores." />
        <button type="button" onClick={retry}>Reintentar</button>
      </div>
    );
  }
  return null;
}

export function Dashboard({ data: controlledData, state: controlledState, onRetry }: DashboardProps) {
  const fetchKpis = useCallback(
    () => controlledData === undefined ? apiFetch<Kpis>("/panel/api/kpis") : Promise.resolve(controlledData),
    [controlledData],
  );
  const fetched = useAsyncData(fetchKpis, controlledData === undefined);
  const data = controlledData === undefined ? fetched.data : controlledData;
  const state = controlledState ?? fetched.state;
  const retry = onRetry ?? fetched.retry;
  const caption = data ? `Actividad de los últimos ${data.window_days} días · Desde ${data.window_start}` : undefined;
  const motivos = data?.motivos ?? [];

  return (
    <PageFrame title="Panel" meta={caption} state={stateMessage(state, retry)}>
      {state === "ready" && data ? (
        <>
          <section aria-label="Indicadores principales" className="kpi-grid">
            <StatCard label="Contactos" value={data.contacts} />
            <StatCard label="Derivados" value={data.derived} />
            <StatCard label="Solicitudes de visita" value={data.visit_requests} />
          </section>
          <section aria-labelledby="motivos-title">
            <h2 id="motivos-title">Motivos</h2>
            {motivos.length ? (
              <ul>
                {motivos.map(([motivo, count]) => <li key={motivo}>{motivo}: {count}</li>)}
              </ul>
            ) : <p>No hay registros</p>}
          </section>
        </>
      ) : null}
    </PageFrame>
  );
}
