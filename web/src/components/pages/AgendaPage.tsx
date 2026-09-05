import { useCallback } from "react";
import { listAppointments } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { AgendaAppointment } from "../../types";
import { Badge } from "../primitives/Badge";
import { DataTable, type Column } from "../shared/DataTable";
import { EmptyState } from "../shared/EmptyState";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";

export type AgendaPageState = AsyncDataState | "stale";

export interface AgendaPageProps {
  data?: AgendaAppointment[] | null;
  state?: AgendaPageState;
  onRetry?: () => void;
  timezone?: string;
}

const PAGE_STYLES = `
  .agenda-page__section { display: grid; gap: var(--space-3); min-width: 0; }
  .agenda-page__table-wrap { min-width: 0; overflow-x: auto; }
`;

function localDate(value: string) { return value.slice(0, 10); }

function requestDates(timezone: string) {
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: timezone }).format(new Date());
  const end = new Date(`${today}T12:00:00Z`);
  end.setUTCDate(end.getUTCDate() + 30);
  return { from: today, to: end.toISOString().slice(0, 10) };
}

function stateMessage(state: AgendaPageState, retry: () => void) {
  if (state === "loading") return <StateMessage tone="info" role="status" spinner title="Cargando agenda" />;
  if (state === "denied") return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver la agenda" />;
  if (state === "stale") return <div><StateMessage tone="warning" role="status" title="Datos posiblemente desactualizados" detail="La agenda muestra la última información disponible." /><button type="button" onClick={retry}>Reintentar</button></div>;
  if (state === "error") return <div><StateMessage tone="danger" role="alert" title="No pudimos cargar la agenda" detail="Reintenta para recuperar las visitas." /><button type="button" onClick={retry}>Reintentar</button></div>;
  return null;
}

const columns: Column<AgendaAppointment>[] = [
  { key: "time", header: "Hora", render: (row) => new Intl.DateTimeFormat("es-CL", { timeZone: row.timezone, hour: "2-digit", minute: "2-digit" }).format(new Date(row.starts_at)) },
  { key: "service", header: "Servicio", render: (row) => row.service },
  { key: "customer", header: "Cliente", render: (row) => row.customer_name ?? "—" },
  { key: "technician", header: "Técnico", render: (row) => row.technician_name ?? "—" },
  { key: "status", header: "Estado", render: (row) => <Badge>{row.status}</Badge> },
];

export function AgendaPage({ data: controlledData, state: controlledState, onRetry, timezone = Intl.DateTimeFormat().resolvedOptions().timeZone }: AgendaPageProps) {
  const fetchAgenda = useCallback(() => {
    const dates = requestDates(timezone);
    return listAppointments(dates.from, dates.to, timezone).then((response) => response.appointments);
  }, [timezone]);
  const fetched = useAsyncData(fetchAgenda, controlledData === undefined);
  const data = controlledData === undefined ? fetched.data : controlledData;
  const state = controlledState ?? fetched.state;
  const retry = onRetry ?? fetched.retry;
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: timezone }).format(new Date());
  const appointments = data ?? [];
  const todayRows = appointments.filter((row) => localDate(row.local_start) === today).sort((a, b) => a.local_start.localeCompare(b.local_start));
  const upcomingRows = appointments.filter((row) => localDate(row.local_start) !== today).sort((a, b) => a.local_start.localeCompare(b.local_start));
  const section = (title: string, rows: AgendaAppointment[]) => (
    <section className="agenda-page__section" aria-labelledby={`agenda-${title.toLowerCase()}`}>
      <h2 id={`agenda-${title.toLowerCase()}`}>{title}</h2>
      <div className="agenda-page__table-wrap"><DataTable columns={columns} rows={rows} emptyMessage="No hay visitas" rowKey={(row) => String(row.id)} /></div>
    </section>
  );

  return <PageFrame title="Agenda" meta={data ? `${appointments.length} visitas` : undefined} state={stateMessage(state, retry)}>
    <style>{PAGE_STYLES}</style>
    {state === "loading" || state === "error" || state === "denied" ? null : data?.length === 0 || state === "empty" ? <div className="agenda-page__table-wrap"><EmptyState title="No hay visitas" description="No hay visitas para el período solicitado." /></div> : <>{section("Hoy", todayRows)}{section("Próximas", upcomingRows)}</>}
  </PageFrame>;
}
