import { useCallback, useState } from "react";
import { ApiError, cancelAppointment, closeAppointment, createAppointment, createCase, fetchCases, fetchClients, fetchTechnicians, listAppointments, rescheduleAppointment, retryCalendarSync } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { AgendaAppointment, Case, Customer, UserRef } from "../../types";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { Combobox } from "../primitives/Combobox";
import { Dialog } from "../primitives/Dialog";
import { Input } from "../primitives/Input";
import { Select } from "../primitives/Select";
import { Tabs } from "../primitives/Tabs";
import { Textarea } from "../primitives/Textarea";
import { DataTable, type Column } from "../shared/DataTable";
import { EmptyState } from "../shared/EmptyState";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { AgendaTimeError, agendaMonthDays, agendaPeriodLabel, agendaShiftPeriod, agendaTodayKey, agendaWeekDays, composeAgendaTime, formatAgendaSlot } from "../shared/agendaTime";
import { AgendaCalendar, type AgendaCalendarView } from "../shared/AgendaCalendar";
import { appointmentStatusLabel, appointmentStatusTone, appointmentSyncLabel, appointmentSyncTone } from "../shared/toneMaps";
import { pathForRoute } from "../domain/panelRoutes";

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
  { key: "service", header: "Servicio", render: (row) => <a className="table__link" href={pathForRoute({ view: "agenda", appointmentId: row.id })}>{row.service}</a> },
  { key: "customer", header: "Cliente", render: (row) => row.customer_name ?? "—" },
  { key: "technician", header: "Técnico", render: (row) => row.technician_name ?? "—" },
  { key: "status", header: "Estado", render: (row) => <div><Badge tone={appointmentStatusTone(row.status)}>{appointmentStatusLabel(row.status)}</Badge><br /><Badge tone={appointmentSyncTone(row.sync.status)}>{appointmentSyncLabel(row.sync.status)}</Badge>{row.sync.error ? <small>{row.sync.error}</small> : null}</div> },
];

export function AgendaPage({ data: controlledData, state: controlledState, onRetry, timezone = Intl.DateTimeFormat().resolvedOptions().timeZone }: AgendaPageProps) {
  const [updatedData, setUpdatedData] = useState<AgendaAppointment[] | null>(null);
  const [cancelTarget, setCancelTarget] = useState<AgendaAppointment | null>(null);
  const [closeTarget, setCloseTarget] = useState<AgendaAppointment | null>(null);
  const [rescheduleTarget, setRescheduleTarget] = useState<AgendaAppointment | null>(null);
  const [rescheduleForm, setRescheduleForm] = useState({ local_date: "", local_time: "", duration_minutes: "60", technician_id: "" });
  const [rescheduleFeedback, setRescheduleFeedback] = useState<{ tone: "success" | "danger"; title: string; detail?: string } | null>(null);
  const [reason, setReason] = useState("");
  const [mutatingId, setMutatingId] = useState<number | null>(null);
  const [cancelFeedback, setCancelFeedback] = useState<ActionFeedback | null>(null);
  const [closeFeedback, setCloseFeedback] = useState<ActionFeedback | null>(null);
  const [syncFeedback, setSyncFeedback] = useState<ActionFeedback | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [createBusy, setCreateBusy] = useState(false);
  const [createFeedback, setCreateFeedback] = useState<{ tone: "danger" | "success"; title: string; detail?: string } | null>(null);
  const [clients, setClients] = useState<Customer[]>([]);
  const [cases, setCases] = useState<Case[]>([]);
  const [technicians, setTechnicians] = useState<UserRef[]>([]);
  const [createForm, setCreateForm] = useState({ customer_id: "", case_id: "", technician_id: "", service: "", local_date: "", local_time: "09:00", duration_minutes: "60" });
  const [view, setView] = useState<AgendaCalendarView>("month");
  const [anchor, setAnchor] = useState(() => agendaTodayKey(timezone));
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [registerView, setRegisterView] = useState("active");
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
  const close = async (outcome: "completed" | "no_show") => {
    if (!closeTarget || mutatingId !== null) return;
    const appointmentId = closeTarget.id;
    setMutatingId(appointmentId);
    setCloseFeedback(null);
    try {
      await closeAppointment(appointmentId, outcome);
      setCloseTarget(null);
      await refreshAgenda();
      setCloseFeedback({ id: appointmentId, tone: "success", title: outcome === "completed" ? "Visita completada" : "Visita marcada como no asistida" });
    } catch (error) {
      setCloseFeedback({ id: appointmentId, tone: "danger", title: "No se pudo registrar el resultado", detail: error instanceof Error ? error.message : "Intenta nuevamente." });
    } finally {
      setMutatingId(null);
    }
  };
  const reschedule = async () => {
    if (!rescheduleTarget || mutatingId !== null) return;
    if (!rescheduleForm.technician_id || !rescheduleForm.local_date || !rescheduleForm.local_time || Number(rescheduleForm.duration_minutes) <= 0) {
      setRescheduleFeedback({ tone: "danger", title: "Completa todos los campos de la reprogramación" });
      return;
    }
    setMutatingId(rescheduleTarget.id);
    setRescheduleFeedback(null);
    try {
      await rescheduleAppointment(rescheduleTarget.id, { ...composeAgendaTime(rescheduleForm.local_date, rescheduleForm.local_time, rescheduleTarget.timezone), duration_minutes: Number(rescheduleForm.duration_minutes), technician_id: Number(rescheduleForm.technician_id) });
      setRescheduleTarget(null);
      await refreshAgenda();
      setRescheduleFeedback({ tone: "success", title: "Visita reprogramada" });
    } catch (error) {
      setRescheduleFeedback({ tone: "danger", title: "No se pudo reprogramar la visita", detail: error instanceof Error ? error.message : "Intenta nuevamente." });
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
  const openCreate = async () => {
    setCreateOpen(true);
    setCreateFeedback(null);
    setCreateForm((form) => ({ ...form, local_date: form.local_date || from }));
    try {
      const [clientResponse, caseResponse, technicianResponse] = await Promise.all([fetchClients(), fetchCases(), fetchTechnicians()]);
      setClients(clientResponse.clients);
      setCases(caseResponse.cases);
      setTechnicians(technicianResponse.technicians);
    } catch (error) {
      setCreateFeedback({ tone: "danger", title: "No pudimos cargar las opciones de la visita", detail: error instanceof Error ? error.message : undefined });
    }
  };
  const create = async () => {
    if (createBusy) return;
    const customerId = Number(createForm.customer_id);
    const caseId = Number(createForm.case_id);
    const technicianId = Number(createForm.technician_id);
    if (!customerId || !caseId || !technicianId || !createForm.service?.trim() || !createForm.local_date || !createForm.local_time || Number(createForm.duration_minutes) <= 0) {
      setCreateFeedback({ tone: "danger", title: "Completa todos los campos de la visita" });
      return;
    }
    setCreateBusy(true);
    setCreateFeedback(null);
    try {
      const localTime = composeAgendaTime(createForm.local_date, createForm.local_time, timezone);
      await createAppointment({ ...localTime, service: createForm.service.trim(), customer_id: customerId, case_id: caseId, technician_id: technicianId, duration_minutes: Number(createForm.duration_minutes) });
      setCreateOpen(false);
      await refreshAgenda();
      setCreateFeedback({ tone: "success", title: "Visita creada" });
    } catch (error) {
      if (error instanceof AgendaTimeError) {
        const title = error.code === "nonexistent_local_time"
          ? "Esa hora no existe ese día por el cambio de horario de verano"
          : "Esa hora se repite ese día por el cambio de horario de verano";
        setCreateFeedback({ tone: "danger", title });
      } else {
        let code = "";
        if (error instanceof ApiError) {
          try { code = String((JSON.parse(error.detail) as { code?: string }).code ?? ""); } catch { /* raw detail */ }
        }
        const title = error instanceof ApiError && error.status === 409 && ["appointment_conflict", "technician_unavailable"].includes(code)
          ? "Ese técnico ya tiene una visita a esa hora"
          : code === "invalid_local_time" ? "Elige una hora local válida" : error instanceof ApiError ? error.detail : "No pudimos crear la visita";
        setCreateFeedback({ tone: "danger", title });
      }
    } finally {
      setCreateBusy(false);
    }
  };
  const createManualCase = async (query: string) => {
    if (createBusy) return;
    const customerId = Number(createForm.customer_id);
    if (!customerId) {
      setCreateFeedback({ tone: "danger", title: "Selecciona un cliente antes de crear un caso" });
      return;
    }
    setCreateBusy(true);
    setCreateFeedback(null);
    try {
      const response = await createCase({ customer_id: customerId, service: query });
      const createdCase = { ...response.case, customer: clients.find((client) => client.id === customerId)! };
      setCases((items) => [...items, createdCase]);
      field("case_id", String(response.case.id));
      if (!createForm.service.trim()) field("service", query);
    } catch (error) {
      setCreateFeedback({ tone: "danger", title: "No se pudo crear el caso", detail: error instanceof Error ? error.message : undefined });
    } finally {
      setCreateBusy(false);
    }
  };
  const sortedAppointments = [...appointments].sort((a, b) => a.local_start.localeCompare(b.local_start));
  const visitCounts = appointments.reduce<Record<string, number>>((counts, row) => {
    const day = localDate(row.local_start);
    counts[day] = (counts[day] ?? 0) + 1;
    return counts;
  }, {});
  const nonActiveRows = sortedAppointments.filter((row) => ["cancelled", "completed", "no_show"].includes(row.status));
  const activeRows = sortedAppointments.filter((row) => !["cancelled", "completed", "no_show"].includes(row.status));
  const todayRows = activeRows.filter((row) => localDate(row.local_start) === today);
  const upcomingRows = activeRows.filter((row) => localDate(row.local_start) > today);
  const periodRows = activeRows;
  const selectedRows = registerView === "active" && selectedDay ? activeRows.filter((row) => localDate(row.local_start) === selectedDay) : null;
  const containsToday = periodDays.includes(today);
  const actions = (row: AgendaAppointment) => <>
    {row.status === "booked" ? <Button variant="secondary" disabled={mutatingId !== null} onClick={() => { setRescheduleTarget(row); setRescheduleForm({ local_date: row.local_start.slice(0, 10), local_time: row.local_start.slice(11, 16), duration_minutes: String(row.duration_minutes ?? 60), technician_id: String(row.technician_id ?? "") }); setRescheduleFeedback(null); void fetchTechnicians().then((response) => setTechnicians(response.technicians)).catch((error) => setRescheduleFeedback({ tone: "danger", title: "No pudimos cargar las opciones de la visita", detail: error instanceof Error ? error.message : undefined })); }}>Reprogramar</Button> : null}
    {row.status === "booked" ? <Button variant="secondary" disabled={mutatingId !== null} onClick={() => { setCancelTarget(row); setCancelFeedback(null); }}>Cancelar visita</Button> : null}
    {row.status === "booked" ? <Button variant="secondary" disabled={mutatingId !== null} onClick={() => { setCloseTarget(row); setCloseFeedback(null); }}>Cerrar visita</Button> : null}
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
  const register = registerView === "non-active"
    ? section("Visitas no activas", nonActiveRows)
    : selectedRows
      ? section(agendaPeriodLabel(selectedDay ?? "", timezone), selectedRows)
      : containsToday
        ? <>{section("Hoy", todayRows)}{section("Próximas", upcomingRows)}</>
        : section("Visitas del período", periodRows);
  const renderedRows = registerView === "non-active" ? nonActiveRows : selectedRows ?? (containsToday ? [...todayRows, ...upcomingRows] : periodRows);
  const showEmpty = data?.length === 0 || state === "empty" || renderedRows.length === 0;

  const field = (key: keyof typeof createForm, value: string) => setCreateForm((form) => ({ ...form, [key]: value }));
  return <PageFrame title="Agenda" meta={data ? `${appointments.length} ${appointments.length === 1 ? "visita" : "visitas"}` : "Visitas de la agenda"} actions={<Button onClick={() => void openCreate()}>Nueva visita</Button>} state={stateMessage(state, retry)}>
    {createFeedback?.tone === "success" ? <StateMessage tone="success" role="status" title={createFeedback.title} /> : null}
    {closeFeedback?.tone === "success" ? <StateMessage tone="success" role="status" title={closeFeedback.title} /> : null}
    {rescheduleFeedback?.tone === "success" ? <StateMessage tone="success" role="status" title={rescheduleFeedback.title} /> : null}
    {state === "loading" || state === "error" || state === "denied" ? null : <div className="agenda-page__layout">
      <AgendaCalendar view={view} anchor={anchor} selectedDay={selectedDay} visitCounts={visitCounts} timezone={timezone} onSelectDay={setSelectedDay} onViewChange={changeView} onNavigate={navigate} today={today} />
      <section aria-label="Registro de agenda"><Tabs tabs={[{ id: "active", label: "Activas" }, { id: "non-active", label: "No activas" }]} activeTab={registerView} onTabChange={setRegisterView} ariaLabel="Filtro del registro de visitas">{() => showEmpty ? <div className="agenda-page__table-wrap"><EmptyState title="No hay visitas" description="No hay visitas para el período solicitado." /></div> : register}</Tabs></section>
    </div>}
    <Dialog open={cancelTarget !== null} onClose={() => { if (mutatingId === null) setCancelTarget(null); }} title={cancelTarget ? `Cancelar visita de ${cancelTarget.customer_name ?? "cliente"} — ${cancelTarget.service}` : "Cancelar visita"}>
      <p>La visita se marcará como cancelada y esta agenda no ofrece volver a reservarla.</p>
      <Textarea id="cancel-reason" label="Motivo de cancelación" value={reason} onChange={(event) => setReason(event.target.value)} />
      {cancelTarget && cancelFeedback?.id === cancelTarget.id && cancelFeedback.tone === "danger" ? <StateMessage tone="danger" role="alert" title={cancelFeedback.title} detail={cancelFeedback.detail} /> : null}
      <Button variant="secondary" disabled={mutatingId !== null} onClick={() => void cancel()}>Confirmar cancelación</Button>
    </Dialog>
    <Dialog open={closeTarget !== null} onClose={() => { if (mutatingId === null) setCloseTarget(null); }} title={closeTarget ? `Cerrar visita de ${closeTarget.customer_name ?? "cliente"} — ${closeTarget.service}` : "Cerrar visita"}>
      <p>Registra el resultado de la visita. Esta acción no se puede revertir desde la agenda.</p>
      {closeTarget && closeFeedback?.id === closeTarget.id && closeFeedback.tone === "danger" ? <StateMessage tone="danger" role="alert" title={closeFeedback.title} detail={closeFeedback.detail} /> : null}
      <Button variant="secondary" disabled={mutatingId !== null} onClick={() => void close("completed")}>Completar</Button>
      <Button variant="secondary" disabled={mutatingId !== null} onClick={() => void close("no_show")}>No asistió</Button>
    </Dialog>
    <Dialog open={rescheduleTarget !== null} onClose={() => { if (mutatingId === null) setRescheduleTarget(null); }} title="Reprogramar visita">
      {rescheduleTarget ? <div>
        <Input label="Fecha local" type="date" value={rescheduleForm.local_date} onChange={(event) => setRescheduleForm((form) => ({ ...form, local_date: event.target.value }))} />
        <Input label="Hora local" type="time" value={rescheduleForm.local_time} onChange={(event) => setRescheduleForm((form) => ({ ...form, local_time: event.target.value }))} />
        <Input label="Duración (minutos)" type="number" min="1" value={rescheduleForm.duration_minutes} onChange={(event) => setRescheduleForm((form) => ({ ...form, duration_minutes: event.target.value }))} />
        <Select label="Técnico" value={rescheduleForm.technician_id} onChange={(event) => setRescheduleForm((form) => ({ ...form, technician_id: event.target.value }))} options={[{ value: "", label: "Selecciona un técnico" }, ...technicians.map((user) => ({ value: String(user.id), label: user.username }))]} />
        {rescheduleFeedback?.tone === "danger" ? <StateMessage tone="danger" role="alert" title={rescheduleFeedback.title} detail={rescheduleFeedback.detail} /> : null}
        <Button variant="secondary" disabled={mutatingId !== null} onClick={() => void reschedule()}>{mutatingId === rescheduleTarget?.id ? "Reprogramando…" : "Confirmar reprogramación"}</Button>
      </div> : null}
    </Dialog>
    <Dialog open={createOpen} onClose={() => { if (!createBusy) setCreateOpen(false); }} title="Crear visita">
      <div className="agenda-create-form">
        <Select label="Cliente" value={createForm.customer_id} onChange={(event) => { field("customer_id", event.target.value); field("case_id", ""); }} options={[{ value: "", label: "Selecciona un cliente" }, ...clients.map((client) => ({ value: String(client.id), label: client.name ?? client.phone_e164 ?? `Cliente ${client.id}` }))]} />
        <Combobox label="Caso" value={createForm.case_id || null} onChange={(value) => { field("case_id", value); const selected = cases.find((item) => item.id === Number(value)); if (selected?.service && !createForm.service) field("service", selected.service); }} onCreate={createBusy ? undefined : (query) => void createManualCase(query)} options={cases.filter((item) => !createForm.customer_id || item.customer?.id === Number(createForm.customer_id)).map((item) => ({ value: String(item.id), label: `${item.service ?? "Caso sin servicio"} (#${item.id})` }))} />
        <Select label="Técnico" value={createForm.technician_id} onChange={(event) => field("technician_id", event.target.value)} options={[{ value: "", label: "Selecciona un técnico" }, ...technicians.map((user) => ({ value: String(user.id), label: user.username }))]} />
        <Input label="Servicio" value={createForm.service} onChange={(event) => field("service", event.target.value)} />
        <Input label="Fecha local" type="date" value={createForm.local_date} onChange={(event) => field("local_date", event.target.value)} />
        <Input label="Hora local" type="time" value={createForm.local_time} onChange={(event) => field("local_time", event.target.value)} />
        <Input label="Duración (minutos)" type="number" min="1" value={createForm.duration_minutes} onChange={(event) => field("duration_minutes", event.target.value)} />
        <Input label="Zona horaria" value={timezone} readOnly />
        {createFeedback?.tone === "danger" ? <StateMessage tone="danger" role="alert" title={createFeedback.title} detail={createFeedback.detail} /> : null}
        <Button variant="secondary" disabled={createBusy} onClick={() => void create()}>{createBusy ? "Creando…" : "Crear visita"}</Button>
      </div>
    </Dialog>
  </PageFrame>;
}
