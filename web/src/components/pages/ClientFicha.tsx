import { useCallback, useState, type FormEvent } from "react";
import { addClientNote, ApiError, apiFetch, archiveCustomer, changeClientState, createClientEquipment, fetchClients, listClientEquipment, mergeClient, postJson, previewClientMerge, resolveMemoryRelation, unarchiveCustomer, updateCaseAmount, updateClientEquipment, updateCustomerConsent, updateCustomerProfile, type CustomerEquipmentUpdate } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { Appointment, ClientFichaResponse, ClientMergePreview, Customer, CustomerEquipment, CustomerProfileUpdateRequest, CustomerState, Memory, MemoryRelation, MemoryRelationKind, MemoriesResponse, PendingMemoryRelationsResponse } from "../../types";
import { ClientMemories } from "../domain/ClientMemories";
import { pathForRoute } from "../domain/panelRoutes";
import { Badge } from "../primitives/Badge";
import { Avatar } from "../primitives/Avatar";
import { Button } from "../primitives/Button";
import { Card } from "../primitives/Card";
import { Dialog } from "../primitives/Dialog";
import { Input } from "../primitives/Input";
import { Menu } from "../primitives/Menu";
import { Select } from "../primitives/Select";
import { Textarea } from "../primitives/Textarea";
import { Tabs } from "../primitives/Tabs";
import { DataTable, type Column } from "../shared/DataTable";
import { CaseActions } from "../shared/CaseActions";
import { CollapsibleMessages } from "../shared/CollapsibleMessages";
import { EmptyState } from "../shared/EmptyState";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import {
  appointmentStatusLabel,
  appointmentStatusTone,
  caseStatusLabel,
  caseStatusTone,
  conversationLabel,
  customerStateLabel,
  customerStateTone,
  directionLabel,
} from "../shared/toneMaps";

const DATE_FORMAT = new Intl.DateTimeFormat("es-CL", { dateStyle: "short" });
const DATE_TIME_FORMAT = new Intl.DateTimeFormat("es-CL", { dateStyle: "short", timeStyle: "short" });
const CLP_FORMAT = new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 });
const MESSAGE_PREVIEW = 10;
const EQUIPMENT_TYPE_LABELS: Record<string, string> = { calefont: "Calefont", caldera: "Caldera", calefaccion: "Sistema de calefacción" };
const EQUIPMENT_TYPE_OPTIONS = [{ value: "", label: "Sin especificar" }, ...Object.entries(EQUIPMENT_TYPE_LABELS).map(([value, label]) => ({ value, label }))];
const MERGE_COUNT_LABELS: Record<keyof ClientMergePreview["moved"], string> = { conversations: "conversaciones", cases: "casos", customer_notes: "notas", customer_equipment: "equipos", appointments: "visitas" };
const FICHA_TABS = [{ id: "summary", label: "Resumen" }, { id: "cases", label: "Casos" }, { id: "visits", label: "Visitas" }, { id: "conversations", label: "Conversaciones" }];

const formatDate = (value: string | null | undefined) => (value ? DATE_FORMAT.format(new Date(value)) : "—");
const formatDateTime = (value: string | null | undefined) => (value ? DATE_TIME_FORMAT.format(new Date(value)) : "—");

export interface ClientFichaProps {
  customerId?: number;
  data?: ClientFichaResponse;
  memories?: Memory[];
  isSaving?: boolean;
  onRetryCalendar?: (appointmentId: number) => void;
  /** Controlled read state, so the state matrix is renderable in stories and tests
   *  without a request. A controlled state also disables the fetch. */
  state?: FichaState;
}

type FichaState = AsyncDataState | "fatal-error";
type Feedback = { tone: "success" | "danger"; title: string; detail?: string };

function stateMessage(state: FichaState) {
  if (state === "loading") return <StateMessage tone="info" role="status" spinner title="Cargando ficha" />;
  if (state === "denied") return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver este panel" />;
  if (state === "error" || state === "fatal-error") {
    return <StateMessage tone="danger" role="alert" title="No pudimos cargar la ficha" detail="Reintenta para recuperar los datos." />;
  }
  return null;
}

/** Feedback belongs beside the control that caused it, not in the page banner. */
function LocalFeedback({ feedback }: { feedback: Feedback | null }) {
  if (!feedback) return null;
  return <StateMessage tone={feedback.tone} role={feedback.tone === "danger" ? "alert" : "status"} title={feedback.title} detail={feedback.detail} />;
}

/** A data surface only when there is data: an empty DataTable already renders its own
 *  `.empty-state` surface, and nesting the two would be card-on-card. */
function surfaceClass(rowCount: number) {
  return rowCount > 0 ? "data-region" : undefined;
}

export function ClientFicha({ customerId, data: controlledData, memories: controlledMemories, isSaving = false, onRetryCalendar, state: controlledState }: ClientFichaProps) {
  const [activeTab, setActiveTab] = useState("summary");
  const [retryingCalendarId, setRetryingCalendarId] = useState<number | null>(null);
  const [messagesExpanded, setMessagesExpanded] = useState(false);
  const [refreshed, setRefreshed] = useState<{ ficha: ClientFichaResponse; memories: Memory[]; pendingRelations: MemoryRelation[] } | null>(null);
  const [selectedState, setSelectedState] = useState<CustomerState | null>(null);
  const [note, setNote] = useState("");
  const [mutation, setMutation] = useState<"state" | "note" | null>(null);
  const [stateFeedback, setStateFeedback] = useState<Feedback | null>(null);
  const [noteFeedback, setNoteFeedback] = useState<Feedback | null>(null);
  const [caseFeedback, setCaseFeedback] = useState<Feedback | null>(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [profile, setProfile] = useState({ name: "", email: "", comuna: "", address: "" });
  const [profileFeedback, setProfileFeedback] = useState<Feedback | null>(null);
  const [consentFeedback, setConsentFeedback] = useState<Feedback | null>(null);
  const [archiveFeedback, setArchiveFeedback] = useState<Feedback | null>(null);
  const [customerMutation, setCustomerMutation] = useState<"profile" | "consent" | "archive" | null>(null);
  const [equipmentRefresh, setEquipmentRefresh] = useState(0);
  const [equipmentOpen, setEquipmentOpen] = useState(false);
  const [editingEquipment, setEditingEquipment] = useState<CustomerEquipment | null>(null);
  const [equipmentForm, setEquipmentForm] = useState<CustomerEquipmentUpdate>({ equipment_type: "", brand: "", model: "", age: "", details: "" });
  const [equipmentMutation, setEquipmentMutation] = useState(false);
  const [equipmentFeedback, setEquipmentFeedback] = useState<Feedback | null>(null);
  const [mergeOpen, setMergeOpen] = useState(false);
  const [mergeClients, setMergeClients] = useState<Customer[]>([]);
  const [mergeOtherId, setMergeOtherId] = useState("");
  const [mergePreview, setMergePreview] = useState<ClientMergePreview | null>(null);
  const [mergeFeedback, setMergeFeedback] = useState<Feedback | null>(null);
  const [mergeLoading, setMergeLoading] = useState(false);
  const [mergedCustomerId, setMergedCustomerId] = useState<number | null>(null);
  const fichaCustomerId = mergedCustomerId ?? customerId;
  const [amountOpen, setAmountOpen] = useState(false);
  const [amountInput, setAmountInput] = useState("");
  const [amountMutation, setAmountMutation] = useState(false);
  const fetchFicha = useCallback(async () => {
    if (fichaCustomerId === undefined) throw new Error("customer id is required");
    const [ficha, memoryResponse, pendingResponse] = await Promise.all([
      apiFetch<ClientFichaResponse>(`/panel/api/clients/${fichaCustomerId}${messagesExpanded ? "" : `?messages_limit=${MESSAGE_PREVIEW}`}`),
      apiFetch<MemoriesResponse>(`/panel/api/clients/${fichaCustomerId}/memories`),
      apiFetch<PendingMemoryRelationsResponse>(`/panel/api/clients/${fichaCustomerId}/memory-relations/pending`),
    ]);
    return { ficha, memories: memoryResponse.memories, pendingRelations: pendingResponse.relations };
  }, [fichaCustomerId, messagesExpanded]);
  const fetched = useAsyncData(fetchFicha, (controlledData === undefined || mergedCustomerId !== null) && controlledState === undefined, mergedCustomerId ?? 0);
  const fetchEquipment = useCallback(async () => {
    if (fichaCustomerId === undefined) return [];
    return (await listClientEquipment(fichaCustomerId)).equipment;
  }, [fichaCustomerId]);
  const equipmentData = useAsyncData(fetchEquipment, fichaCustomerId !== undefined, equipmentRefresh + (mergedCustomerId ?? 0));
  const equipmentRows = equipmentData.data ?? [];
  const data = mergedCustomerId !== null ? fetched.data?.ficha : refreshed?.ficha ?? controlledData ?? fetched.data?.ficha;
  const memories = mergedCustomerId !== null ? fetched.data?.memories ?? [] : refreshed?.memories ?? controlledMemories ?? fetched.data?.memories ?? [];
  const pendingRelations = refreshed?.pendingRelations ?? fetched.data?.pendingRelations ?? [];
  const state: FichaState = controlledState ?? (controlledData ? "ready" : fetched.state);

  if (!data) {
    return <PageFrame title="Ficha de cliente" meta="Datos del cliente" state={stateMessage(state)}><EmptyState title="Cargando ficha" /></PageFrame>;
  }

  const { customer, history } = data;
  const activeCase = history.cases.filter((row) => row.is_open).at(-1) ?? null;
  const archivedCases = history.cases.filter((row) => row.id !== activeCase?.id);
  const appointments = history.appointments ?? [];
  const openCaseCount = history.cases.filter((row) => row.is_open).length;
  const futureAppointmentCount = appointments.filter((appointment) => appointment.status === "booked" && new Date(appointment.starts_at).getTime() > Date.now()).length;
  const upcomingAppointments = appointments.filter((appointment) => appointment.status === "booked" && new Date(appointment.starts_at).getTime() > Date.now());
  const retryCalendar = async (appointmentId: number) => {
    setRetryingCalendarId(appointmentId);
    try {
      await apiFetch(`/panel/api/appointments/${appointmentId}/calendar/sync`, { method: "POST" });
      onRetryCalendar?.(appointmentId);
    } finally {
      setRetryingCalendarId(null);
    }
  };
  const refresh = async () => {
    if (fichaCustomerId === undefined) return;
    const next = await fetchFicha();
    setRefreshed(next);
  };
  const openMerge = async () => {
    if (fichaCustomerId === undefined) return;
    setMergeOpen(true);
    setMergeFeedback(null);
    setMergePreview(null);
    setMergeOtherId("");
    try { setMergeClients((await fetchClients({ includeArchived: true })).clients.filter((client) => client.id !== fichaCustomerId)); }
    catch (error) { setMergeFeedback({ tone: "danger", title: error instanceof ApiError ? error.detail : "No pudimos cargar los clientes" }); }
  };
  const selectMergeClient = async (otherId: string) => {
    setMergeOtherId(otherId);
    setMergePreview(null);
    setMergeFeedback(null);
    if (!otherId || fichaCustomerId === undefined) return;
    try { setMergePreview(await previewClientMerge(fichaCustomerId, Number(otherId))); }
    catch (error) { setMergeFeedback({ tone: "danger", title: error instanceof ApiError ? error.detail : "No pudimos cargar la vista previa" }); }
  };
  const confirmMerge = async () => {
    if (!mergePreview || fichaCustomerId === undefined || mergeLoading) return;
    setMergeLoading(true);
    setMergeFeedback(null);
    try {
      const { survivor } = await mergeClient(fichaCustomerId, Number(mergeOtherId));
      if (mergePreview.survivor_id === fichaCustomerId) { await refresh(); setEquipmentRefresh((value) => value + 1); setMergeOpen(false); }
      else { setMergedCustomerId(survivor.id); setRefreshed(null); setMergeOpen(false); }
    } catch (error) { setMergeFeedback({ tone: "danger", title: error instanceof ApiError ? error.detail : "No pudimos fusionar los clientes" }); }
    finally { setMergeLoading(false); }
  };
  const safeError = (error: unknown, action: "estado" | "nota" | "caso" | "identidad" | "consentimiento" | "archivo" | "equipo") => {
    const labels = { estado: "el estado", nota: "la nota", caso: "el caso", identidad: "la identidad", consentimiento: "el consentimiento", archivo: "el archivo", equipo: "el equipo" };
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) return { title: `No tienes permiso para guardar ${labels[action]}` };
    if (error instanceof ApiError && (error.status === 400 || error.status === 422)) return { title: `Revisa ${labels[action]} e inténtalo de nuevo` };
    return { title: `No pudimos guardar ${labels[action]}`, detail: "Inténtalo nuevamente." };
  };
  const openEquipment = (entry?: CustomerEquipment) => {
    const current = entry ?? null;
    setEditingEquipment(current);
    setEquipmentForm({ equipment_type: current?.equipment_type ?? "", brand: current?.brand ?? "", model: current?.model ?? "", age: current?.age ?? "", details: current?.details ?? "" });
    setEquipmentFeedback(null);
    setEquipmentOpen(true);
  };
  const saveEquipment = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (customerId === undefined || equipmentMutation) return;
    setEquipmentFeedback(null);
    setEquipmentMutation(true);
    const body = Object.fromEntries(Object.entries(equipmentForm).map(([key, value]) => [key, value === "" ? null : value])) as CustomerEquipmentUpdate;
    try {
      if (editingEquipment) await updateClientEquipment(customerId, editingEquipment.id, body);
      else await createClientEquipment(customerId, body);
      setEquipmentRefresh((value) => value + 1);
      setEquipmentOpen(false);
      setEquipmentFeedback({ tone: "success", title: editingEquipment ? "Equipo actualizado" : "Equipo agregado" });
    } catch (error) { setEquipmentFeedback({ tone: "danger", ...safeError(error, "equipo") }); }
    finally { setEquipmentMutation(false); }
  };
  const saveCaseAmount = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (customerId === undefined || !activeCase || amountMutation) return;
    const amountText = amountInput.trim();
    const parsedAmount = amountText === "" ? null : Number(amountInput);
    if (parsedAmount !== null && (!Number.isFinite(parsedAmount) || parsedAmount < 0)) {
      setCaseFeedback({ tone: "danger", title: "Ingresa un monto CLP válido y no negativo" });
      return;
    }
    setAmountMutation(true);
    setCaseFeedback(null);
    try {
      await updateCaseAmount(activeCase.id, parsedAmount);
      await refresh();
      setAmountOpen(false);
    } catch (error) { setCaseFeedback({ tone: "danger", ...safeError(error, "caso") }); }
    finally { setAmountMutation(false); }
  };
  const updateCase = async (caseId: number, status: string, responsibleId: number | null) => {
    setCaseFeedback(null);
    try { await postJson(`/panel/api/cases/${caseId}/update`, { status, responsible_id: responsibleId }); await refresh(); }
    catch (error) { setCaseFeedback({ tone: "danger", ...safeError(error, "caso") }); }
  };
  const acknowledgeCase = async (caseId: number) => {
    setCaseFeedback(null);
    try { await postJson(`/panel/api/cases/${caseId}/ack`); await refresh(); }
    catch (error) { setCaseFeedback({ tone: "danger", ...safeError(error, "caso") }); }
  };
  const saveState = async () => {
    if (customerId === undefined || !selectedState || mutation) return;
    setMutation("state"); setStateFeedback(null);
    try { await changeClientState(customerId, selectedState); await refresh(); setStateFeedback({ tone: "success", title: "Estado guardado" }); }
    catch (error) { setStateFeedback({ tone: "danger", ...safeError(error, "estado") }); }
    finally { setMutation(null); }
  };
  const saveNote = async () => {
    if (customerId === undefined || !note.trim() || mutation) {
      if (!note.trim()) setNoteFeedback({ tone: "danger", title: "La nota no puede estar vacía" });
      return;
    }
    setMutation("note"); setNoteFeedback(null);
    try { await addClientNote(customerId, note.trim()); await refresh(); setNote(""); setNoteFeedback({ tone: "success", title: "Nota agregada" }); }
    catch (error) { setNoteFeedback({ tone: "danger", ...safeError(error, "nota") }); }
    finally { setMutation(null); }
  };
  const openProfile = () => {
    setProfile({ name: customer.name ?? "", email: customer.email ?? "", comuna: customer.comuna ?? "", address: customer.address ?? "" });
    setProfileFeedback(null);
    setProfileOpen(true);
  };
  const saveProfile = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (customerId === undefined || customerMutation) return;
    setProfileFeedback(null);
    const fields = ["name", "email", "comuna", "address"] as const;
    const changed = fields.filter((field) => profile[field].trim() !== (customer[field] ?? ""));
    if (changed.some((field) => !profile[field].trim())) {
      setProfileFeedback({ tone: "danger", title: "No puedes dejar vacío un campo editado", detail: "El panel no permite borrar estos datos." });
      return;
    }
    const body = Object.fromEntries(changed.map((field) => [field, profile[field].trim()])) as CustomerProfileUpdateRequest;
    if (!changed.length) { setProfileOpen(false); return; }
    setCustomerMutation("profile");
    try {
      await updateCustomerProfile(customerId, body);
      await refresh();
      setProfileOpen(false);
      setProfileFeedback({ tone: "success", title: "Identidad guardada" });
    } catch (error) { setProfileFeedback({ tone: "danger", ...safeError(error, "identidad") }); }
    finally { setCustomerMutation(null); }
  };
  const saveConsent = async () => {
    if (customerId === undefined || customerMutation) return;
    setConsentFeedback(null);
    setCustomerMutation("consent");
    try {
      await updateCustomerConsent(customerId, !customer.consent_status);
      await refresh();
      setConsentFeedback({ tone: "success", title: "Consentimiento actualizado" });
    } catch (error) { setConsentFeedback({ tone: "danger", ...safeError(error, "consentimiento") }); }
    finally { setCustomerMutation(null); }
  };
  const saveArchive = async () => {
    if (customerId === undefined || customerMutation) return;
    setArchiveFeedback(null);
    setCustomerMutation("archive");
    try {
      if (customer.archived_at) await unarchiveCustomer(customerId);
      else await archiveCustomer(customerId);
      await refresh();
      setArchiveOpen(false);
      setArchiveFeedback({ tone: "success", title: customer.archived_at ? "Cliente restaurado" : "Cliente archivado" });
    } catch (error) { setArchiveFeedback({ tone: "danger", ...safeError(error, "archivo") }); }
    finally { setCustomerMutation(null); }
  };
  const resolveRelation = async (relationId: number, relation: MemoryRelationKind) => {
    if (customerId === undefined) return;
    await resolveMemoryRelation(customerId, relationId, relation);
    await refresh();
  };
  const toggleMessages = () => { setRefreshed(null); setMessagesExpanded((value) => !value); fetched.retry(); };
  const conversationColumns: Column<(typeof history.conversations)[number]>[] = [
    { key: "id", header: "#", render: (row) => `#${row.id}` },
    { key: "state", header: "Estado", render: (row) => conversationLabel(row.state) },
    { key: "summary", header: "Resumen", render: (row) => row.summary ?? "—" },
    { key: "created", header: "Creada", render: (row) => formatDate(row.created_at) },
  ];
  const caseColumns: Column<(typeof history.cases)[number]>[] = [
    { key: "id", header: "#", render: (row) => `#${row.id}` },
    { key: "service", header: "Servicio", render: (row) => row.service },
    { key: "priority", header: "Prioridad", render: (row) => row.priority },
    { key: "status", header: "Estado", render: (row) => <Badge tone={caseStatusTone(row.status)}>{caseStatusLabel(row.status)}</Badge> },
    { key: "amount", header: "Monto CLP", render: (row) => row.amount === null ? "Sin monto registrado" : CLP_FORMAT.format(row.amount) },
    { key: "summary", header: "Resumen", render: (row) => row.summary ?? "—" },
  ];
  const messageColumns: Column<(typeof history.messages)[number]>[] = [
    { key: "conversation", header: "Conversación", render: (row) => <a className="table__link" href={pathForRoute({ view: "conversations", conversationId: row.conversation_id })}>#{row.conversation_id}</a> },
    { key: "id", header: "#", render: (row) => `#${row.id}` },
    { key: "direction", header: "Dirección", render: (row) => directionLabel(row.direction) },
    { key: "msg_type", header: "Tipo", render: (row) => row.msg_type },
    { key: "text", header: "Mensaje", render: (row) => `${row.text ?? "—"}${row.media_url ? " 📎" : ""}` },
    { key: "created", header: "Fecha", render: (row) => formatDate(row.created_at) },
  ];

  return (
    <PageFrame title="" className="client-ficha-page" state={stateMessage(state)}>
      <header className="client-ficha__identity">
        <div className="client-ficha__identity-person">
          <Avatar name={customer.name ?? customer.phone_e164 ?? "Cliente"} />
          <div>
            <h1>{customer.name ?? customer.phone_e164 ?? "—"}</h1>
            <p>Cliente desde {formatDate(customer.created_at)}</p>
          </div>
        </div>
        <div className="client-ficha__identity-actions">
          <Button variant="secondary" onClick={() => { window.location.href = pathForRoute({ view: "agenda" }); }}>Agendar visita</Button>
          <Button onClick={() => { window.location.href = pathForRoute({ view: "conversations" }); }}>Ver conversación</Button>
        </div>
      </header>
      <Tabs tabs={FICHA_TABS} activeTab={activeTab} onTabChange={setActiveTab} ariaLabel="Secciones de la ficha del cliente">
        {(activeTab) => <>
      {activeTab === "summary" ? <>
      <div className="detail-region">
        <section className="detail-region__rail" aria-label="Resumen del cliente">
          <Card title="Datos del cliente" className="client-ficha__data-card">
            <div className="client-ficha__customer-controls">
              <Avatar name={customer.name ?? customer.phone_e164 ?? "Cliente"} />
              <strong>{customer.name ?? customer.phone_e164 ?? "—"}</strong>
              {customer.archived_at ? <Badge tone="warning">Cliente archivado</Badge> : null}
            <Button variant="secondary" aria-label="Editar identidad" disabled={customerId === undefined || customerMutation !== null} onClick={openProfile}>Editar</Button>
              <Menu
                trigger="icon"
                label={`Acciones para ${customer.name ?? customer.phone_e164 ?? "cliente"}`}
                items={[
                  { value: "consent", label: "Cambiar consentimiento", disabled: customerId === undefined || customerMutation !== null },
                  { value: "merge", label: "Fusionar con otro cliente", tone: "danger", disabled: customerId === undefined || customerMutation !== null },
                  { value: "archive", label: customer.archived_at ? "Restaurar" : "Archivar", tone: "danger", disabled: customerId === undefined || customerMutation !== null },
                ]}
                onSelect={(value) => {
                  if (value === "consent") { setConsentFeedback(null); void saveConsent(); }
                  if (value === "merge") void openMerge();
                  if (value === "archive") customer.archived_at ? void saveArchive() : setArchiveOpen(true);
                }}
              />
              <LocalFeedback feedback={consentFeedback} />
              {/* The dialog owns the surface while it is open, so the same failure never renders twice. */}
              {profileOpen ? null : <LocalFeedback feedback={profileFeedback} />}
              {archiveOpen ? null : <LocalFeedback feedback={archiveFeedback} />}
            </div>
            <dl className="detail-region__facts">
              <div><dt>Teléfono</dt><dd>{customer.phone_e164 ?? "—"}</dd></div>
              <div><dt>Correo</dt><dd>{customer.email ?? "—"}</dd></div>
              <div><dt>Dirección</dt><dd>{customer.address ?? "—"}</dd></div>
              <div><dt>Comuna</dt><dd>{customer.comuna ?? "—"}</dd></div>
              <div><dt>Estado del cliente</dt><dd><Badge tone={customerStateTone(customer.state)}>{customerStateLabel(customer.state)}</Badge></dd></div>
              <div><dt>Consentimiento</dt><dd>{customer.consent_status ? "Sí" : "No"}</dd></div>
              <div><dt>Cliente desde</dt><dd>{formatDate(customer.created_at)}</dd></div>
            </dl>
            <div className="client-ficha__state-control">
              <Select
                id="client-state"
                label="Estado del cliente"
                value={selectedState ?? customer.state}
                options={(data.states ?? []).map((option) => ({ value: option, label: customerStateLabel(option) }))}
                disabled={mutation !== null || customerId === undefined}
                onChange={(event) => setSelectedState(event.target.value as CustomerState)}
              />
              <Button
                disabled={mutation !== null || customerId === undefined || !selectedState || selectedState === customer.state}
                onClick={() => void saveState()}
              >
                {mutation === "state" ? "Guardando…" : "Guardar estado"}
              </Button>
              <LocalFeedback feedback={stateFeedback} />
              {isSaving ? <p role="status">Guardando estado…</p> : null}
            </div>
          </Card>
          <Dialog open={profileOpen} onClose={() => setProfileOpen(false)} title="Editar identidad">
            <form onSubmit={(event) => void saveProfile(event)}>
              <Input label="Nombre" value={profile.name} onChange={(event) => setProfile({ ...profile, name: event.target.value })} />
              <Input label="Correo" type="email" value={profile.email} onChange={(event) => setProfile({ ...profile, email: event.target.value })} />
              <Input label="Comuna" value={profile.comuna} onChange={(event) => setProfile({ ...profile, comuna: event.target.value })} />
              <Input label="Dirección" value={profile.address} onChange={(event) => setProfile({ ...profile, address: event.target.value })} />
              <Input label="Teléfono" value={customer.phone_e164 ?? "—"} readOnly />
              <LocalFeedback feedback={profileFeedback} />
              <Button type="submit" disabled={customerMutation !== null}>{customerMutation === "profile" ? "Guardando…" : "Guardar cambios"}</Button>
            </form>
          </Dialog>
          <Dialog open={archiveOpen} onClose={() => setArchiveOpen(false)} title="Archivar cliente">
            <p>Vas a archivar a {customer.name ?? customer.phone_e164 ?? "este cliente"}.</p>
            <p>Tiene {openCaseCount} {openCaseCount === 1 ? "caso abierto" : "casos abiertos"} y {futureAppointmentCount} {futureAppointmentCount === 1 ? "visita futura" : "visitas futuras"}. Puedes continuar; estos trabajos seguirán registrados.</p>
            <LocalFeedback feedback={archiveFeedback} />
            <Button variant="danger" disabled={customerMutation !== null} onClick={() => void saveArchive()}>{customerMutation === "archive" ? "Guardando…" : "Confirmar archivo"}</Button>
          </Dialog>
          <Dialog open={mergeOpen} onClose={() => setMergeOpen(false)} title="Fusionar clientes">
            <Select id="merge-other-client" label="Otro cliente" value={mergeOtherId} options={[{ value: "", label: "Selecciona un cliente" }, ...mergeClients.map((client) => ({ value: String(client.id), label: `${client.name ?? "Sin nombre"} · ${client.phone_e164 ?? "Sin teléfono"}` }))]} onChange={(event) => void selectMergeClient(event.target.value)} />
            {mergePreview ? <>
              <p>Cliente superviviente: {mergePreview.survivor_id === customer.id ? customer.name : mergeClients.find((client) => client.id === mergePreview.survivor_id)?.name ?? `#${mergePreview.survivor_id}`}</p>
              <p>Se moverán: {Object.entries(mergePreview.moved).map(([table, count]) => `${MERGE_COUNT_LABELS[table as keyof ClientMergePreview["moved"]]}: ${count}`).join(" · ")}.</p>
              <p>{mergePreview.memory_conflicts} conflictos de memoria.</p>
              {mergePreview.scalar_conflicts.length ? <p>En conflictos de identidad, se conserva el valor del cliente superviviente: {mergePreview.scalar_conflicts.join(", ")}.</p> : null}
            </> : null}
            <LocalFeedback feedback={mergeFeedback} />
            <Button variant="danger" disabled={!mergePreview || mergeLoading} onClick={() => void confirmMerge()}>{mergeLoading ? "Fusionando…" : "Confirmar fusión"}</Button>
          </Dialog>
        </section>

        <div className="detail-region__main">
          <Card title="Caso activo" className="client-ficha__case-card">
            {activeCase ? <>
              <dl className="detail-region__facts">
                <div><dt>#</dt><dd>#{activeCase.id}</dd></div>
                <div><dt>Servicio</dt><dd>{activeCase.service}</dd></div>
                <div><dt>Prioridad</dt><dd>{activeCase.priority}</dd></div>
                <div><dt>Estado</dt><dd><Badge tone={caseStatusTone(activeCase.status)}>{caseStatusLabel(activeCase.status)}</Badge></dd></div>
                <div><dt>Responsable</dt><dd>{data.users.find((user) => user.id === activeCase.responsible_id)?.username ?? "Sin asignar"}</dd></div>
                <div><dt>Resumen</dt><dd>{activeCase.summary ?? "—"}</dd></div>
                <div><dt>Monto del servicio</dt><dd>{activeCase.amount === null ? "Sin monto registrado" : CLP_FORMAT.format(activeCase.amount)}</dd></div>
              </dl>
              <Button variant="secondary" disabled={customerId === undefined || amountMutation} onClick={() => { setAmountInput(activeCase.amount === null ? "" : String(activeCase.amount)); setAmountOpen(true); }}>Editar monto del caso</Button>
              {activeCase.emergency ? <Badge tone={activeCase.ack_by === null ? "danger" : "warning"}>{activeCase.ack_by === null ? "Emergencia sin reconocer" : `Emergencia reconocida por ${activeCase.ack_by}`}</Badge> : null}
              <details className="client-ficha__case-edit">
                <summary>Editar caso</summary>
                <CaseActions target={activeCase} users={data.users} onUpdate={updateCase} onAcknowledge={acknowledgeCase} />
              </details>
              <LocalFeedback feedback={caseFeedback} />
            </> : <EmptyState title="Sin caso activo" />}
          </Card>
          <Dialog open={amountOpen} onClose={() => setAmountOpen(false)} title="Monto del servicio">
            <form onSubmit={(event) => void saveCaseAmount(event)}>
              <Input label="Monto CLP" type="number" min="0" step="1" value={amountInput} onChange={(event) => setAmountInput(event.target.value)} />
              <p>Deja el campo vacío para quitar el monto.</p>
              <LocalFeedback feedback={caseFeedback} />
              <Button type="submit" disabled={amountMutation}>{amountMutation ? "Guardando…" : "Guardar monto"}</Button>
            </form>
          </Dialog>
          <ClientMemories memories={memories} pendingRelations={pendingRelations} onResolveRelation={resolveRelation} compact onViewAll={() => setActiveTab("conversations")} />

          <section aria-label="Equipos" className="client-ficha__equipment-slot">
            <Card title="Equipos" className="client-ficha__equipment-card">
              <Button variant="secondary" disabled={customerId === undefined || equipmentMutation} onClick={() => openEquipment()}>Agregar equipo</Button>
              {equipmentData.state === "loading" ? <p role="status">Cargando equipos…</p> : null}
              {equipmentData.state === "error" || equipmentData.state === "denied" ? <StateMessage tone="danger" role="alert" title="No pudimos cargar los equipos" /> : null}
              {equipmentRows.length ? <ul className="data-region">
                {equipmentRows.map((entry) => <li key={entry.id}>
                  <div>{entry.equipment_type ? <Badge>{EQUIPMENT_TYPE_LABELS[entry.equipment_type] ?? entry.equipment_type}</Badge> : <span>Sin especificar</span>}</div>
                  <p>{[entry.brand, entry.model, entry.age].filter(Boolean).join(" · ") || "Sin datos estructurados"}</p>
                  {entry.details ? <p>{entry.details}</p> : null}
                  <Button variant="secondary" disabled={equipmentMutation} onClick={() => openEquipment(entry)}>Editar equipo</Button>
                </li>)}
              </ul> : equipmentData.state === "empty" || equipmentData.state === "ready" ? <EmptyState title="No hay equipos registrados" /> : null}
              {equipmentOpen ? null : <LocalFeedback feedback={equipmentFeedback} />}
            </Card>
          </section>
          <Dialog open={equipmentOpen} onClose={() => setEquipmentOpen(false)} title={editingEquipment ? "Editar equipo" : "Agregar equipo"}>
            <form onSubmit={(event) => void saveEquipment(event)}>
              <Select id="equipment-type" label="Tipo" value={equipmentForm.equipment_type ?? ""} options={EQUIPMENT_TYPE_OPTIONS} onChange={(event) => setEquipmentForm({ ...equipmentForm, equipment_type: event.target.value })} />
              <Input label="Marca" value={equipmentForm.brand ?? ""} onChange={(event) => setEquipmentForm({ ...equipmentForm, brand: event.target.value })} />
              <Input label="Modelo" value={equipmentForm.model ?? ""} onChange={(event) => setEquipmentForm({ ...equipmentForm, model: event.target.value })} />
              <Input label="Antigüedad" value={equipmentForm.age ?? ""} onChange={(event) => setEquipmentForm({ ...equipmentForm, age: event.target.value })} />
              <Textarea label="Detalle capturado" value={equipmentForm.details ?? ""} onChange={(event) => setEquipmentForm({ ...equipmentForm, details: event.target.value })} />
              <LocalFeedback feedback={equipmentFeedback} />
              <Button type="submit" disabled={equipmentMutation}>{equipmentMutation ? "Guardando…" : "Guardar equipo"}</Button>
            </form>
          </Dialog>

          <Card title="Notas" className="client-ficha__notes-card">
            {data.notes.length ? data.notes.map((entry) => <p key={entry.id}>{entry.author ?? "—"} · {entry.note}</p>) : <EmptyState title="No hay notas" />}
            <Textarea
              id="new-note"
              label="Nueva nota"
              value={note}
              disabled={mutation !== null || customerId === undefined}
              onChange={(event) => setNote(event.target.value)}
            />
            <Button disabled={mutation !== null || customerId === undefined} onClick={() => void saveNote()}>
              {mutation === "note" ? "Guardando…" : "Agregar nota"}
            </Button>
            <LocalFeedback feedback={noteFeedback} />
          </Card>

          <Card title="Próximas visitas" className="client-ficha__upcoming-card">
            {upcomingAppointments.length ? <ul className="client-ficha__visits">{upcomingAppointments.map((appointment) => <li key={appointment.id}><a className="table__link" href={pathForRoute({ view: "agenda", appointmentId: appointment.id })}><span>{formatDateTime(appointment.starts_at)}</span><span>{appointment.service}</span><Badge tone={appointmentStatusTone(appointment.status)}>{appointmentStatusLabel(appointment.status)}</Badge></a></li>)}</ul> : <EmptyState title="No hay próximas visitas" />}
            <Button variant="secondary" onClick={() => { window.location.href = pathForRoute({ view: "agenda" }); }}>Ver agenda →</Button>
          </Card>

          <button type="button" className="client-ficha__history-entry" onClick={() => setActiveTab("cases")}>
            <span aria-hidden="true">◷</span><span><strong>Historial del cliente</strong><small>Visitas, conversaciones y casos anteriores</small></span><span aria-hidden="true">›</span>
          </button>

        </div>
      </div>
      </> : null}
      {activeTab === "cases" ? <div className="detail-region__main">
        {activeCase ? <Card title="Caso activo"><p>{activeCase.service} · #{activeCase.id}</p><Badge tone={caseStatusTone(activeCase.status)}>{caseStatusLabel(activeCase.status)}</Badge></Card> : null}
        <section aria-label="Casos anteriores" className="client-ficha__history-block"><h2>Casos anteriores</h2><div className={surfaceClass(archivedCases.length)}><DataTable columns={caseColumns} rows={archivedCases} rowKey={(row) => String(row.id)} /></div></section>
      </div> : null}
      {activeTab === "visits" ? <div className="detail-region__main">
        <section aria-label="Visitas" className="client-ficha__history-block"><h2>Visitas</h2>{appointments.length ? <ul className="client-ficha__visits data-region">{appointments.map((appointment: Appointment) => <li key={appointment.id}><a className="table__link" href={pathForRoute({ view: "agenda", appointmentId: appointment.id })}><span>{appointment.service}</span><span>{formatDateTime(appointment.starts_at)}</span><Badge tone={appointmentStatusTone(appointment.status)}>{appointmentStatusLabel(appointment.status)}</Badge></a>{appointment.calendar_error ? <><StateMessage tone="danger" role="alert" title="No se pudo sincronizar el calendario" detail={`${appointment.calendar_error} Reintenta la sincronización.`} /><Button variant="secondary" disabled={retryingCalendarId === appointment.id} onClick={() => void retryCalendar(appointment.id)}>Reintentar calendario</Button></> : null}</li>)}</ul> : <EmptyState title="No hay visitas" />}</section>
      </div> : null}
      {activeTab === "conversations" ? <div className="detail-region__main">
        <section aria-label="Conversaciones" className="client-ficha__history-block"><h2>Conversaciones</h2><div className={surfaceClass(history.conversations.length)}><DataTable columns={conversationColumns} rows={history.conversations} rowKey={(row) => String(row.id)} /></div></section>
        <section aria-label="Mensajes" className="client-ficha__history-block"><h2>Mensajes</h2><div className={surfaceClass(history.messages.length)}><CollapsibleMessages total={history.messages_total} expanded={messagesExpanded} onToggle={toggleMessages}><DataTable columns={messageColumns} rows={history.messages} rowKey={(row) => String(row.id)} /></CollapsibleMessages></div></section>
      </div> : null}
        </>}
      </Tabs>
    </PageFrame>
  );
}
