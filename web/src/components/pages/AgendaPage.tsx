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
import { agendaMonthDays, agendaPeriodLabel, agendaShiftPeriod, agendaTodayKey, agendaWeekDays, formatAgendaSlot } from "../shared/agendaTime";
import { AgendaCalendar, type AgendaCalendarView } from "../shared/AgendaCalendar";
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

function stateMessage(state: AgendaPageState, retry: () => void) {
  if (state === "loading") return <StateMessage tone="info" role="status" spinner title="Cargando agenda" />;
  if (state === "denied") return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver la agenda" />;
  if (state === "stale") return <div className="agenda-recovery"><StateMessage tone="warning" role="status" title="Datos posiblemente desactualizados" detail="La agenda muestra la última información disponible." /><Button variant="secondary" onClick={retry}>Reintentar</Button></div>;
  if (state === "error") return <div className="agenda-recovery"><StateMessage tone="danger" role="alert" title="No pudimos cargar la agenda" detail="Reintenta para recuperar las visitas." /><Button variant="secondary" onClick={retry}>Reintentar</Button></div>;
  return null;
}

const columns: Column<AgendaAppointment>[] = [
  { key: "time", header: "Hora", render: (row) => formatAgendaSlot(row.starts_at, row.timezone) },
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
  const [view, setView] = useState<AgendaCalendarView>("month");
  const [anchor, setAnchor] = useState(() => agendaTodayKey(timezone));
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const periodDays = view === "month" ? agendaMonthDays(anchor, timezone) : agendaWeekDays(anchor, timezone);
  const from = periodDays[0];
  const to = periodDays[periodDays.length - 1];
  const fetchAgenda = useCallback(() => {
    return listAppointments(from, to, timezone).then((response) => response.appointments);
  }, [from, to, timezone]);
  const fetched = useAsyncData(fetchAgenda, controlledData === undefined, Date.parse(from));
  const data = updatedData ?? (controlledData === undefined ? fetched.data : controlledData);
  const state = controlledState ?? fetched.state;
  const retry = onRetry ?? fetched.retry;
  const today = agendaTodayKey(timezone);
  const appointments = data ?? [];
  const refreshAgenda = async () => {
    const response = await listAppointments(from, to, timezone);
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
  const sortedAppointments = [...appointments].sort((a, b) => a.local_start.localeCompare(b.local_start));
  const visitCounts = appointments.reduce<Record<string, number>>((counts, row) => {
    const day = localDate(row.local_start);
    counts[day] = (counts[day] ?? 0) + 1;
    return counts;
  }, {});
  const todayRows = sortedAppointments.filter((row) => localDate(row.local_start) === today);
  const upcomingRows = sortedAppointments.filter((row) => localDate(row.local_start) > today);
  const periodRows = sortedAppointments;
  const selectedRows = selectedDay ? sortedAppointments.filter((row) => localDate(row.local_start) === selectedDay) : null;
  const containsToday = periodDays.includes(today);
  const actions = (row: AgendaAppointment) => <>
    {row.status === "booked" ? <Button variant="secondary" disabled={mutatingId !== null} onClick={() => { setCancelTarget(row); setCancelFeedback(null); }}>Cancelar visita</Button> : null}
    {row.sync.status === "pending" || row.sync.status === "failed" ? <Button variant="secondary" disabled={mutatingId !== null} onClick={() => void retrySync(row.id)} aria-label="Reintentar calendario">Reintentar calendario</Button> : null}
    {cancelFeedback?.id === row.id && cancelFeedback.tone === "success" ? <span role="status"><Badge tone="success">{cancelFeedback.title}</Badge></span> : null}
    {syncFeedback?.id === row.id ? <span role={syncFeedback.tone === "danger" ? "alert" : "status"}><Badge tone={syncFeedback.tone}>{syncFeedback.title}{syncFeedback.detail ? `: ${syncFeedback.detail}` : null}</Badge></span> : null}
  </>;
  const section = (title: string, rows: AgendaAppointment[]) => rows.length > 0 ? (
    <section className="agenda-page__section" aria-labelledby={`agenda-${title.toLowerCase()}`}>
      <h2 id={`agenda-${title.toLowerCase()}`}>{title}</h2>
      <div className="agenda-page__table-wrap"><div className="data-region"><DataTable columns={columns} rows={rows} emptyMessage="No hay visitas" rowKey={(row) => String(row.id)} actions={actions} actionsHeader="Acciones" /></div></div>
    </section>
  ) : null;

  const navigate = (direction: -1 | 0 | 1) => {
    setAnchor(direction === 0 ? agendaTodayKey(timezone) : agendaShiftPeriod(anchor, view, direction, timezone));
    setSelectedDay(null);
  };
  const changeView = (nextView: AgendaCalendarView) => {
    setView(nextView);
    setSelectedDay(null);
  };
  const register = selectedRows
    ? section(agendaPeriodLabel(selectedDay ?? "", timezone), selectedRows)
    : containsToday
      ? <>{section("Hoy", todayRows)}{section("Próximas", upcomingRows)}</>
      : section("Visitas del período", periodRows);
  const showEmpty = data?.length === 0 || state === "empty" || (!selectedRows && periodRows.length === 0);

  return <PageFrame title="Agenda" meta={data ? `${appointments.length} ${appointments.length === 1 ? "visita" : "visitas"}` : undefined} state={stateMessage(state, retry)}>
    {state === "loading" || state === "error" || state === "denied" ? null : <div className="agenda-page__layout">
      <AgendaCalendar view={view} anchor={anchor} selectedDay={selectedDay} visitCounts={visitCounts} timezone={timezone} onSelectDay={setSelectedDay} onViewChange={changeView} onNavigate={navigate} today={today} />
      {showEmpty ? <div className="agenda-page__table-wrap"><EmptyState title="No hay visitas" description="No hay visitas para el período solicitado." /></div> : <section aria-label="Registro de agenda">{register}</section>}
    </div>}
    <Dialog open={cancelTarget !== null} onClose={() => { if (mutatingId === null) setCancelTarget(null); }} title={cancelTarget ? `Cancelar visita de ${cancelTarget.customer_name ?? "cliente"} — ${cancelTarget.service}` : "Cancelar visita"}>
      <p>La visita se marcará como cancelada y esta agenda no ofrece volver a reservarla.</p>
      <Textarea id="cancel-reason" label="Motivo de cancelación" value={reason} onChange={(event) => setReason(event.target.value)} />
      {cancelTarget && cancelFeedback?.id === cancelTarget.id && cancelFeedback.tone === "danger" ? <StateMessage tone="danger" role="alert" title={cancelFeedback.title} detail={cancelFeedback.detail} /> : null}
      <Button variant="secondary" disabled={mutatingId !== null} onClick={() => void cancel()}>Confirmar cancelación</Button>
    </Dialog>
  </PageFrame>;
}
