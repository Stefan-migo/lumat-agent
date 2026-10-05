import { useCallback, useState } from "react";
import { CalendarDays, CalendarPlus, CalendarX, Check, Clock3, FileText, Globe, Plus, RefreshCw, Timer, UserRound, Wrench, X } from "lucide-react";
import { ApiError, cancelAppointment, closeAppointment, createAppointment, createCase, fetchCases, fetchClients, fetchTechnicians, listAppointments, rescheduleAppointment, retryCalendarSync } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { AgendaAppointment, Case, Customer, UserRef } from "../../types";
import { Badge } from "../primitives/Badge";
import { Card } from "../primitives/Card";
import { Button } from "../primitives/Button";
import { Combobox } from "../primitives/Combobox";
import { Dialog } from "../primitives/Dialog";
import { Input } from "../primitives/Input";
import { Menu } from "../primitives/Menu";
import { Icon } from "../primitives/Icon";
import { Select } from "../primitives/Select";
import { Tabs } from "../primitives/Tabs";
import { Textarea } from "../primitives/Textarea";
import { EmptyState } from "../shared/EmptyState";
import { AppointmentClosureDialog, type AppointmentClosureOutcome } from "../shared/AppointmentClosureDialog";
import { AppointmentRescheduleDialog, type AppointmentRescheduleForm } from "../shared/AppointmentRescheduleDialog";
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
function clientOptionLabel(client: Customer) {
  return [client.name ?? `Cliente ${client.id}`, client.email, client.phone_e164].filter(Boolean).join(" · ");
}

function stateMessage(state: AgendaPageState, retry: () => void) {
  if (state === "loading") return <StateMessage tone="info" role="status" spinner title="Cargando agenda" />;
  if (state === "denied") return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver la agenda" />;
  if (state === "stale") return <div className="agenda-recovery"><StateMessage tone="warning" role="status" title="Datos posiblemente desactualizados" detail="La agenda muestra la última información disponible." /><Button variant="secondary" onClick={retry}>Reintentar</Button></div>;
  if (state === "error") return <div className="agenda-recovery"><StateMessage tone="danger" role="alert" title="No pudimos cargar la agenda" detail="Reintenta para recuperar las visitas." /><Button variant="secondary" onClick={retry}>Reintentar</Button></div>;
  return null;
}

export function AgendaPage({ data: controlledData, state: controlledState, onRetry, timezone = Intl.DateTimeFormat().resolvedOptions().timeZone }: AgendaPageProps) {
  const [updatedData, setUpdatedData] = useState<AgendaAppointment[] | null>(null);
  const [cancelTarget, setCancelTarget] = useState<AgendaAppointment | null>(null);
  const [closeTarget, setCloseTarget] = useState<AgendaAppointment | null>(null);
  const [closeOutcome, setCloseOutcome] = useState<AppointmentClosureOutcome>("completed");
  const [rescheduleTarget, setRescheduleTarget] = useState<AgendaAppointment | null>(null);
  const [rescheduleForm, setRescheduleForm] = useState<AppointmentRescheduleForm>({ local_date: "", local_time: "", duration_minutes: "60", technician_id: "" });
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
  const selectedRows = selectedDay ? (registerView === "active" ? activeRows : nonActiveRows).filter((row) => localDate(row.local_start) === selectedDay) : null;
  const containsToday = periodDays.includes(today);
  const openReschedule = (row: AgendaAppointment) => { setRescheduleTarget(row); setRescheduleForm({ local_date: row.local_start.slice(0, 10), local_time: row.local_start.slice(11, 16), duration_minutes: String(row.duration_minutes ?? 60), technician_id: String(row.technician_id ?? "") }); setRescheduleFeedback(null); void fetchTechnicians().then((response) => setTechnicians(response.technicians)).catch((error) => setRescheduleFeedback({ tone: "danger", title: "No pudimos cargar las opciones de la visita", detail: error instanceof Error ? error.message : undefined })); };
  const section = (title: string, rows: AgendaAppointment[], isToday = selectedDay === today) => rows.length > 0 ? (
    <section className="agenda-page__section" aria-labelledby={`agenda-${title.toLowerCase()}`}>
      <h2 id={`agenda-${title.toLowerCase()}`} className="agenda-page__section-heading"><span>{title}</span>{isToday ? <Badge tone="success">Hoy</Badge> : null}</h2>
       <div className="agenda-page__cards">{rows.map((row) => <Card key={row.id} className="agenda-page__visit-card">
         <div className="agenda-page__visit-heading"><time dateTime={row.local_start}><Icon icon={Clock3} size="sm" /><span>{formatAgendaSlot(row.starts_at, row.timezone)}</span></time><div className="agenda-page__visit-title"><a href={pathForRoute({ view: "agenda", appointmentId: row.id })}>{row.service}</a><Badge tone={appointmentStatusTone(row.status)}>{appointmentStatusLabel(row.status)}</Badge></div>
           <Menu label={`Acciones para ${row.service}`} trigger="icon" disabled={mutatingId !== null} items={[
             ...(row.status === "booked" ? [{ value: "reschedule", label: "Reprogramar", icon: CalendarDays }, { value: "cancel", label: "Cancelar visita", icon: X, tone: "danger" as const }, { value: "close", label: "Cerrar visita", icon: Check }] : []),
             ...(row.sync.status === "pending" || row.sync.status === "failed" ? [{ value: "retry", label: "Reintentar calendario", icon: RefreshCw }] : []),
             ]} onSelect={(action) => { if (action === "reschedule") openReschedule(row); if (action === "cancel") { setCancelTarget(row); setCancelFeedback(null); } if (action === "close") { setCloseTarget(row); setCloseOutcome("completed"); setCloseFeedback(null); } if (action === "retry") void retrySync(row.id); }} />
        </div>
        <dl className="agenda-page__visit-details"><div><dt>Cliente</dt><dd>{row.customer_name ?? "—"}</dd></div><div><dt>Técnico</dt><dd>{row.technician_name ?? "—"}</dd></div></dl>
        <div className="agenda-page__sync"><Badge tone={appointmentSyncTone(row.sync.status)}>{appointmentSyncLabel(row.sync.status)}</Badge>{row.sync.error ? <small>{row.sync.error}</small> : null}</div>
        {cancelFeedback?.id === row.id && cancelFeedback.tone === "success" ? <span role="status"><Badge tone="success">{cancelFeedback.title}</Badge></span> : null}
        {syncFeedback?.id === row.id ? <span role={syncFeedback.tone === "danger" ? "alert" : "status"}><Badge tone={syncFeedback.tone}>{syncFeedback.title}{syncFeedback.detail ? `: ${syncFeedback.detail}` : null}</Badge></span> : null}
      </Card>)}</div>
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
        ? section(agendaPeriodLabel(today, timezone), [...todayRows, ...upcomingRows], true)
        : section("Visitas del período", periodRows);
  const renderedRows = registerView === "non-active" ? nonActiveRows : selectedRows ?? (containsToday ? [...todayRows, ...upcomingRows] : periodRows);
  const showEmpty = data?.length === 0 || state === "empty" || renderedRows.length === 0;

  const field = (key: keyof typeof createForm, value: string) => setCreateForm((form) => ({ ...form, [key]: value }));
  const headerCount = data ? <Badge tone="success">{appointments.length} {appointments.length === 1 ? "visita" : "visitas"}</Badge> : null;
  return <PageFrame title="Agenda" titleAdornment={headerCount} meta={data ? undefined : "Visitas de la agenda"} subtitle="Organiza las visitas y consulta la disponibilidad." actions={<Button onClick={() => void openCreate()}><Plus />Nueva visita</Button>} state={stateMessage(state, retry)}>
    {createFeedback?.tone === "success" ? <StateMessage tone="success" role="status" title={createFeedback.title} /> : null}
    {closeFeedback?.tone === "success" ? <StateMessage tone="success" role="status" title={closeFeedback.title} /> : null}
    {rescheduleFeedback?.tone === "success" ? <StateMessage tone="success" role="status" title={rescheduleFeedback.title} /> : null}
    {state === "loading" || state === "error" || state === "denied" ? null : <div className="agenda-page__layout">
      <AgendaCalendar view={view} anchor={anchor} selectedDay={selectedDay} visitCounts={visitCounts} timezone={timezone} onSelectDay={setSelectedDay} onViewChange={changeView} onNavigate={navigate} today={today} />
      <section aria-label="Registro de agenda"><Tabs tabs={[{ id: "active", label: "Activas" }, { id: "non-active", label: "No activas" }]} activeTab={registerView} onTabChange={setRegisterView} ariaLabel="Filtro del registro de visitas">{() => showEmpty ? <EmptyState title="No hay visitas" description="No hay visitas para el período solicitado." /> : register}</Tabs></section>
    </div>}
    <Dialog open={cancelTarget !== null} onClose={() => { if (mutatingId === null) setCancelTarget(null); }} title="Cancelar visita" icon={CalendarX} description="Indica el motivo de la cancelación de esta visita.">
      {cancelTarget ? <div className="appointment-detail__selected-visit"><Icon icon={CalendarDays} /><div><strong>{cancelTarget.customer_name ?? "Cliente sin nombre"}</strong><time dateTime={cancelTarget.local_start}>{agendaPeriodLabel(localDate(cancelTarget.local_start), cancelTarget.timezone)} · {formatAgendaSlot(cancelTarget.starts_at, cancelTarget.timezone)}</time><span>Visita seleccionada</span></div></div> : null}
      <Textarea id="cancel-reason" label="Motivo de cancelación" value={reason} onChange={(event) => setReason(event.target.value)} />
      <p className="appointment-detail__closure-warning">Esta acción no se puede revertir desde la agenda.</p>
      {cancelTarget && cancelFeedback?.id === cancelTarget.id && cancelFeedback.tone === "danger" ? <StateMessage tone="danger" role="alert" title={cancelFeedback.title} detail={cancelFeedback.detail} /> : null}
      <div className="appointment-detail__dialog-footer">
        <Button variant="secondary" disabled={mutatingId !== null} onClick={() => setCancelTarget(null)}>Cancelar</Button>
        <Button disabled={mutatingId !== null} onClick={() => void cancel()}>Confirmar cancelación</Button>
      </div>
    </Dialog>
    {closeTarget ? <AppointmentClosureDialog
      open={closeTarget !== null}
      onClose={() => setCloseTarget(null)}
      customerName={closeTarget.customer_name ?? "Cliente sin nombre"}
      appointmentDateTime={closeTarget.local_start}
      dateTimeLabel={`${agendaPeriodLabel(localDate(closeTarget.local_start), closeTarget.timezone)} · ${formatAgendaSlot(closeTarget.starts_at, closeTarget.timezone)}`}
      outcome={closeOutcome}
      onOutcomeChange={setCloseOutcome}
      onSubmit={() => void close(closeOutcome)}
      mutating={mutatingId !== null}
      feedback={closeFeedback?.id === closeTarget.id && closeFeedback.tone === "danger" ? closeFeedback : null}
    /> : null}
    {rescheduleTarget ? <AppointmentRescheduleDialog
      open={rescheduleTarget !== null}
      onClose={() => setRescheduleTarget(null)}
      appointment={rescheduleTarget}
      technicianLabel={rescheduleTarget.technician_name ?? (rescheduleTarget.technician_id ? `Técnico #${rescheduleTarget.technician_id}` : "Técnico no asignado")}
      technicians={technicians}
      form={rescheduleForm}
      onChange={(key, value) => setRescheduleForm((form) => ({ ...form, [key]: value }))}
      onSubmit={() => void reschedule()}
      mutating={mutatingId !== null}
      feedback={rescheduleFeedback?.tone === "danger" ? rescheduleFeedback : null}
    /> : null}
    <Dialog open={createOpen} onClose={() => { if (!createBusy) setCreateOpen(false); }} title="Nueva visita" icon={CalendarPlus} description="Completa los datos para agendar una visita.">
      <div className="agenda-create-form">
        <section className="agenda-create-form__section" aria-labelledby="agenda-create-visit-heading">
          <h3 id="agenda-create-visit-heading">Datos de la visita</h3>
          <div className="agenda-create-form__row agenda-create-form__row--identity">
            <div className="agenda-create-form__icon-field"><Icon icon={UserRound} className="agenda-create-form__leading-icon" /><Combobox label="Cliente" placeholder="Busca por nombre, correo o teléfono" options={clients.map((client) => ({ value: String(client.id), label: clientOptionLabel(client) }))} value={createForm.customer_id || null} onChange={(value) => { field("customer_id", value); field("case_id", ""); }} /></div>
            <div className="agenda-create-form__icon-field"><Icon icon={FileText} className="agenda-create-form__leading-icon" /><Combobox label="Caso vinculado" disabled={!createForm.customer_id} value={createForm.case_id || null} onChange={(value) => { field("case_id", value); const selected = cases.find((item) => item.id === Number(value)); if (selected?.service && !createForm.service) field("service", selected.service); }} onCreate={createBusy ? undefined : (query) => void createManualCase(query)} options={cases.filter((item) => item.customer?.id === Number(createForm.customer_id)).map((item) => ({ value: String(item.id), label: `${item.service ?? "Caso sin servicio"} (#${item.id})` }))} /></div>
          </div>
          <div className="agenda-create-form__row agenda-create-form__row--visit">
            <Input label="Servicio" icon={FileText} value={createForm.service} onChange={(event) => field("service", event.target.value)} />
            <div className="agenda-create-form__icon-field"><Icon icon={Wrench} className="agenda-create-form__leading-icon" /><Select label="Técnico" className="agenda-create-form__select--icon" value={createForm.technician_id} onChange={(event) => field("technician_id", event.target.value)} options={[{ value: "", label: "Selecciona un técnico" }, ...technicians.map((user) => ({ value: String(user.id), label: user.username }))]} /></div>
          </div>
        </section>
        <section className="agenda-create-form__section" aria-labelledby="agenda-create-schedule-heading">
          <h3 id="agenda-create-schedule-heading">Fecha y horario</h3>
          <div className="agenda-create-form__row agenda-create-form__row--schedule">
            <Input label="Fecha" icon={CalendarDays} type="date" value={createForm.local_date} onChange={(event) => field("local_date", event.target.value)} />
            <Input label="Hora" icon={Clock3} type="time" value={createForm.local_time} onChange={(event) => field("local_time", event.target.value)} />
            <Input label="Duración" icon={Timer} type="number" min="1" value={createForm.duration_minutes} onChange={(event) => field("duration_minutes", event.target.value)} />
          </div>
          <div className="agenda-create-form__icon-field agenda-create-form__timezone"><Icon icon={Globe} className="agenda-create-form__leading-icon" /><Select label="Zona horaria" className="agenda-create-form__select--icon" value={timezone} disabled options={[{ value: timezone, label: timezone }]} /><small>{timezone}</small></div>
        </section>
        {createFeedback?.tone === "danger" ? <StateMessage tone="danger" role="alert" title={createFeedback.title} detail={createFeedback.detail} /> : null}
        <div className="agenda-create-form__actions">
          <Button variant="secondary" disabled={createBusy} onClick={() => { if (!createBusy) setCreateOpen(false); }}>Cancelar</Button>
          <Button disabled={createBusy} onClick={() => void create()}><Icon icon={CalendarPlus} size="sm" />{createBusy ? "Creando…" : "Crear visita"}</Button>
        </div>
      </div>
    </Dialog>
  </PageFrame>;
}
