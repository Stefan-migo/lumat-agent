import { useCallback, useState } from "react";
import { cancelAppointment, listAppointments, retryCalendarSync } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { AgendaAppointment } from "../../types";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { Dialog } from "../primitives/Dialog";
import { Textarea } from "../primitives/Textarea";
import { DataTable, type Column } from "../shared/DataTable";
import { EmptyState } from "../shared/EmptyState";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { appointmentStatusLabel, appointmentStatusTone, appointmentSyncLabel, appointmentSyncTone } from "../shared/toneMaps";

export type AgendaPageState = AsyncDataState | "stale";

export interface AgendaPageProps {
  data?: AgendaAppointment[] | null;
  state?: AgendaPageState;
  onRetry?: () => void;
  timezone?: string;
}

type ActionFeedback = { id: number; tone: "success" | "danger"; title: string; detail?: string };

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
  { key: "time", header: "Hora", render: (row) => new Intl.DateTimeFormat("es-CL", { timeZone: row.timezone, hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(new Date(row.starts_at)) },
  { key: "service", header: "Servicio", render: (row) => row.service },
  { key: "customer", header: "Cliente", render: (row) => row.customer_name ?? "—" },
  { key: "technician", header: "Técnico", render: (row) => row.technician_name ?? "—" },
  { key: "status", header: "Estado", render: (row) => <div><Badge tone={appointmentStatusTone(row.status)}>{appointmentStatusLabel(row.status)}</Badge><br /><Badge tone={appointmentSyncTone(row.sync.status)}>{appointmentSyncLabel(row.sync.status)}</Badge>{row.sync.error ? <small>{row.sync.error}</small> : null}</div> },
];

export function AgendaPage({ data: controlledData, state: controlledState, onRetry, timezone = Intl.DateTimeFormat().resolvedOptions().timeZone }: AgendaPageProps) {
  const [updatedData, setUpdatedData] = useState<AgendaAppointment[] | null>(null);
  const [cancelTarget, setCancelTarget] = useState<AgendaAppointment | null>(null);
  const [reason, setReason] = useState("");
  const [mutatingId, setMutatingId] = useState<number | null>(null);
  const [cancelFeedback, setCancelFeedback] = useState<ActionFeedback | null>(null);
  const [syncFeedback, setSyncFeedback] = useState<ActionFeedback | null>(null);
  const fetchAgenda = useCallback(() => {
    const dates = requestDates(timezone);
    return listAppointments(dates.from, dates.to, timezone).then((response) => response.appointments);
  }, [timezone]);
  const fetched = useAsyncData(fetchAgenda, controlledData === undefined);
  const data = updatedData ?? (controlledData === undefined ? fetched.data : controlledData);
  const state = controlledState ?? fetched.state;
  const retry = onRetry ?? fetched.retry;
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: timezone }).format(new Date());
  const appointments = data ?? [];
  const refreshAgenda = async () => {
    const dates = requestDates(timezone);
    const response = await listAppointments(dates.from, dates.to, timezone);
    setUpdatedData(response.appointments);
  };
  const cancel = async () => {
    if (!cancelTarget || mutatingId !== null) return;
    const appointmentId = cancelTarget.id;
    setMutatingId(appointmentId);
    setCancelFeedback(null);
    try {
      await cancelAppointment(appointmentId, reason.trim() || undefined);
      setCancelTarget(null);
      setReason("");
      await refreshAgenda();
      setCancelFeedback({ id: appointmentId, tone: "success", title: "Visita cancelada" });
    } catch (error) {
      setCancelFeedback({ id: appointmentId, tone: "danger", title: "No se pudo cancelar la visita", detail: error instanceof Error ? error.message : undefined });
    } finally {
      setMutatingId(null);
    }
  };
  const retrySync = async (id: number) => {
    if (mutatingId !== null) return;
    setMutatingId(id);
    setSyncFeedback(null);
    try {
      await retryCalendarSync(id);
      await refreshAgenda();
    } catch (error) {
      setSyncFeedback({ id, tone: "danger", title: "No se pudo sincronizar el calendario", detail: error instanceof Error ? error.message : undefined });
    } finally {
      setMutatingId(null);
    }
  };
  const todayRows = appointments.filter((row) => localDate(row.local_start) === today).sort((a, b) => a.local_start.localeCompare(b.local_start));
  const upcomingRows = appointments.filter((row) => localDate(row.local_start) !== today).sort((a, b) => a.local_start.localeCompare(b.local_start));
  const actions = (row: AgendaAppointment) => <>
    {row.status === "booked" ? <Button variant="secondary" disabled={mutatingId !== null} onClick={() => { setCancelTarget(row); setCancelFeedback(null); }}>Cancelar visita</Button> : null}
    {row.sync.status === "pending" || row.sync.status === "failed" ? <Button variant="secondary" disabled={mutatingId !== null} onClick={() => void retrySync(row.id)} aria-label="Reintentar calendario">Reintentar calendario</Button> : null}
    {cancelFeedback?.id === row.id && cancelFeedback.tone === "success" ? <StateMessage tone="success" role="status" title={cancelFeedback.title} detail={cancelFeedback.detail} /> : null}
    {syncFeedback?.id === row.id ? <StateMessage tone={syncFeedback.tone} role={syncFeedback.tone === "danger" ? "alert" : "status"} title={syncFeedback.title} detail={syncFeedback.detail} /> : null}
  </>;
  const section = (title: string, rows: AgendaAppointment[]) => (
    <section className="agenda-page__section" aria-labelledby={`agenda-${title.toLowerCase()}`}>
      <h2 id={`agenda-${title.toLowerCase()}`}>{title}</h2>
      {rows.length > 0 ? <div className="agenda-page__table-wrap"><DataTable columns={columns} rows={rows} emptyMessage="No hay visitas" rowKey={(row) => String(row.id)} actions={actions} actionsHeader="Acciones" /></div> : null}
    </section>
  );

  return <PageFrame title="Agenda" meta={data ? `${appointments.length} ${appointments.length === 1 ? "visita" : "visitas"}` : undefined} state={stateMessage(state, retry)}>
    {state === "loading" || state === "error" || state === "denied" ? null : data?.length === 0 || state === "empty" ? <div className="agenda-page__table-wrap"><EmptyState title="No hay visitas" description="No hay visitas para el período solicitado." /></div> : <>{section("Hoy", todayRows)}{section("Próximas", upcomingRows)}</>}
    <Dialog open={cancelTarget !== null} onClose={() => { if (mutatingId === null) setCancelTarget(null); }} title="Cancelar visita">
      <p>La visita no podrá volver a reservarse después de cancelarla.</p>
      <Textarea id="cancel-reason" label="Motivo de cancelación" value={reason} onChange={(event) => setReason(event.target.value)} />
      {cancelTarget && cancelFeedback?.id === cancelTarget.id && cancelFeedback.tone === "danger" ? <StateMessage tone="danger" role="alert" title={cancelFeedback.title} detail={cancelFeedback.detail} /> : null}
      <Button variant="secondary" disabled={mutatingId !== null} onClick={() => void cancel()}>Confirmar cancelación</Button>
    </Dialog>
  </PageFrame>;
}
