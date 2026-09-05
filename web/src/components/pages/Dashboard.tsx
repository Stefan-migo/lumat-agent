import { useCallback } from "react";
import { apiFetch } from "../../api";
import type { Kpis } from "../../types";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { StatCard } from "../shared/StatCard";

const DASHBOARD_STYLES = `
  .dashboard-motivos {
    display: grid;
    gap: var(--space-3);
    margin: 0;
    padding: var(--space-4);
    border: 1px solid var(--corp-border);
    border-radius: var(--radius-md);
    background: var(--corp-surface);
    box-shadow: var(--shadow-1);
    list-style: none;
  }

  .dashboard-motivos__header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--space-3);
  }

  .dashboard-motivos__label,
  .dashboard-motivos__count {
    margin: 0;
  }

  .dashboard-motivos__label {
    color: var(--corp-text);
    font-size: var(--text-md);
  }

  .dashboard-motivos__count {
    color: var(--corp-text);
    font-weight: var(--weight-semibold);
    font-variant-numeric: var(--corp-value);
  }

  .dashboard-motivos__track {
    height: var(--space-2);
    overflow: hidden;
    background: var(--primary-100);
    border-radius: var(--radius-sm);
  }

  .dashboard-motivos__bar {
    height: 100%;
    background: var(--primary-700);
  }
`;

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
  const maxMotivoCount = motivos.reduce((max, [, count]) => Math.max(max, count), 0);

  return (
    <PageFrame title="Panel" meta={caption} state={stateMessage(state, retry)}>
      <style>{DASHBOARD_STYLES}</style>
      {state === "ready" && data ? (
        <>
          <section aria-label="Indicadores principales" className="kpi-grid">
            <StatCard label="Contactos" value={data.contacts} />
            <StatCard label="Derivados" value={data.derived} accent="var(--warning)" />
            <StatCard label="Solicitudes de visita" value={data.visit_requests} accent="var(--primary-800)" />
          </section>
          <section aria-labelledby="motivos-title">
            <h2 id="motivos-title">Motivos</h2>
            {motivos.length ? (
              <ol className="dashboard-motivos">
                {motivos.map(([motivo, count]) => (
                  <li key={motivo}>
                    <div className="dashboard-motivos__header">
                      <span className="dashboard-motivos__label">{motivo}</span>
                      <span className="dashboard-motivos__count">{count}</span>
                    </div>
                    <div className="dashboard-motivos__track" aria-hidden="true">
                      <div
                        className="dashboard-motivos__bar"
                        style={{ width: `${maxMotivoCount ? (count / maxMotivoCount) * 100 : 0}%` }}
                      />
                    </div>
                  </li>
                ))}
              </ol>
            ) : <p>No hay registros</p>}
          </section>
        </>
      ) : null}
    </PageFrame>
  );
}
