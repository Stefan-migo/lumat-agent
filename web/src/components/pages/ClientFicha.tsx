import { useCallback, useState, type FormEvent } from "react";
import { Archive, ArrowLeftRight, BriefcaseBusiness, CalendarDays, CircleAlert, Clock3, Copy, FileText, Home, Mail, MapPin, MessageSquare, NotebookPen, Pencil, Phone, RefreshCw, ShieldCheck, Smartphone, UserRound, CircleDollarSign } from "lucide-react";
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
import "./ClientFichaDialogs.css";
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
const IDENTITY_DATE_FORMAT = new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", year: "numeric" });
const DATE_TIME_FORMAT = new Intl.DateTimeFormat("es-CL", { dateStyle: "short", timeStyle: "short" });
const CLP_FORMAT = new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 });
const MESSAGE_PREVIEW = 10;
const EQUIPMENT_TYPE_LABELS: Record<string, string> = { calefont: "Calefont", caldera: "Caldera", calefaccion: "Sistema de calefacción" };
const EQUIPMENT_TYPE_OPTIONS = [{ value: "", label: "Ej. Calefont" }, ...Object.entries(EQUIPMENT_TYPE_LABELS).map(([value, label]) => ({ value, label }))];
const MERGE_COUNT_LABELS: Record<keyof ClientMergePreview["moved"], string> = { conversations: "conversaciones", cases: "casos", customer_notes: "notas", customer_equipment: "equipos", appointments: "visitas" };
const FICHA_TABS = [{ id: "summary", label: "Resumen" }, { id: "cases", label: "Casos" }, { id: "visits", label: "Visitas" }, { id: "conversations", label: "Conversaciones" }];

const formatDate = (value: string | null | undefined) => (value ? DATE_FORMAT.format(new Date(value)) : "—");
const formatIdentityDate = (value: string | null | undefined) => (value ? IDENTITY_DATE_FORMAT.format(new Date(value)).replace(".", "") : "—");
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

export function ClientFicha({ customerId, data: controlledData, memories: controlledMemories, onRetryCalendar, state: controlledState }: ClientFichaProps) {
  const [activeTab, setActiveTab] = useState("summary");
  const [historyOpen, setHistoryOpen] = useState(false);
  const [caseEditorOpen, setCaseEditorOpen] = useState(false);
  const [retryingCalendarId, setRetryingCalendarId] = useState<number | null>(null);
  const [messagesExpanded, setMessagesExpanded] = useState(false);
  const [refreshed, setRefreshed] = useState<{ ficha: ClientFichaResponse; memories: Memory[]; pendingRelations: MemoryRelation[] } | null>(null);
  const [selectedState, setSelectedState] = useState<CustomerState | null>(null);
  const [stateDialogOpen, setStateDialogOpen] = useState(false);
  const [consentDialogOpen, setConsentDialogOpen] = useState(false);
  const [selectedConsent, setSelectedConsent] = useState<boolean | null>(null);
  const [note, setNote] = useState("");
  const [noteComposerOpen, setNoteComposerOpen] = useState(false);
  const [mutation, setMutation] = useState<"state" | "note" | null>(null);
  const [stateFeedback, setStateFeedback] = useState<Feedback | null>(null);
  const [noteFeedback, setNoteFeedback] = useState<Feedback | null>(null);
  const [caseFeedback, setCaseFeedback] = useState<Feedback | null>(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [profile, setProfile] = useState({ name: "", email: "", comuna: "", address: "" });
  const [caseEdit, setCaseEdit] = useState({ status: "", responsibleId: "" });
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
    try { await postJson(`/panel/api/cases/${caseId}/update`, { status, responsible_id: responsibleId }); await refresh(); return true; }
    catch (error) { setCaseFeedback({ tone: "danger", ...safeError(error, "caso") }); return false; }
  };
  const openCaseEditor = () => {
    if (!activeCase) return;
    setCaseEdit({ status: activeCase.status, responsibleId: activeCase.responsible_id === null ? "" : String(activeCase.responsible_id) });
    setCaseFeedback(null);
    setCaseEditorOpen(true);
  };
  const saveCaseEdit = async () => {
    if (!activeCase || !caseEdit.status) return;
    if (await updateCase(activeCase.id, caseEdit.status, caseEdit.responsibleId ? Number(caseEdit.responsibleId) : null)) setCaseEditorOpen(false);
  };
  const acknowledgeCase = async (caseId: number) => {
    setCaseFeedback(null);
    try { await postJson(`/panel/api/cases/${caseId}/ack`); await refresh(); }
    catch (error) { setCaseFeedback({ tone: "danger", ...safeError(error, "caso") }); }
  };
  const saveState = async () => {
    if (customerId === undefined || !selectedState || selectedState === customer.state || mutation) return;
    setMutation("state"); setStateFeedback(null);
    try { await changeClientState(customerId, selectedState); await refresh(); setStateDialogOpen(false); setStateFeedback({ tone: "success", title: "Estado guardado" }); }
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
    if (customerId === undefined || selectedConsent === null || customerMutation) return;
    setConsentFeedback(null);
    setCustomerMutation("consent");
    try {
      await updateCustomerConsent(customerId, selectedConsent);
      await refresh();
      setConsentDialogOpen(false);
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
          <Avatar className="client-ficha__hero-avatar" name={customer.name ?? customer.phone_e164 ?? "Cliente"} />
          <div>
            <h1>{customer.name ?? customer.phone_e164 ?? "—"}</h1>
            <p>Cliente desde el {formatIdentityDate(customer.created_at)}</p>
          </div>
        </div>
        <div className="client-ficha__identity-actions">
          <Button variant="secondary" onClick={() => { window.location.href = pathForRoute({ view: "agenda" }); }}><CalendarDays /> Agendar visita</Button>
          <Button onClick={() => { window.location.href = pathForRoute({ view: "conversations" }); }}><MessageSquare /> Ver conversación</Button>
        </div>
      </header>
      <Tabs tabs={FICHA_TABS} activeTab={activeTab} onTabChange={setActiveTab} ariaLabel="Secciones de la ficha del cliente">
        {(activeTab) => <>
      {activeTab === "summary" ? <>
      <div className="detail-region">
        <section className="detail-region__rail" aria-label="Resumen del cliente">
          <Card className="client-ficha__data-card">
            <header className="client-ficha__card-heading"><h2>Datos del cliente</h2><div className="client-ficha__customer-controls">
              {customer.archived_at ? <Badge tone="warning">Cliente archivado</Badge> : null}
              <Menu
                trigger="icon"
                label={`Acciones para ${customer.name ?? customer.phone_e164 ?? "cliente"}`}
                items={[
                  { value: "edit", label: "Editar", icon: Pencil, disabled: customerId === undefined || customerMutation !== null },
                  { value: "state", label: "Cambiar estado", icon: RefreshCw, disabled: customerId === undefined || customerMutation !== null },
                  { value: "consent", label: "Cambiar consentimiento", icon: ShieldCheck, disabled: customerId === undefined || customerMutation !== null },
                  { value: "merge", label: "Fusionar con otro cliente", icon: ArrowLeftRight, tone: "danger", disabled: customerId === undefined || customerMutation !== null },
                  { value: "archive", label: customer.archived_at ? "Restaurar" : "Archivar", icon: Archive, tone: "danger", disabled: customerId === undefined || customerMutation !== null },
                ]}
                onSelect={(value) => {
                  if (value === "edit") openProfile();
                  if (value === "state") { setSelectedState((customer.allowed_transitions ?? [])[0] ?? null); setStateFeedback(null); setStateDialogOpen(true); }
                  if (value === "consent") { setSelectedConsent(customer.consent_status); setConsentFeedback(null); setConsentDialogOpen(true); }
                  if (value === "merge") void openMerge();
                  if (value === "archive") customer.archived_at ? void saveArchive() : setArchiveOpen(true);
                }}
              />
              <LocalFeedback feedback={consentDialogOpen ? null : consentFeedback} />
              <LocalFeedback feedback={stateDialogOpen ? null : stateFeedback} />
              {/* The dialog owns the surface while it is open, so the same failure never renders twice. */}
              {profileOpen ? null : <LocalFeedback feedback={profileFeedback} />}
              {archiveOpen ? null : <LocalFeedback feedback={archiveFeedback} />}
            </div></header>
            <dl className="detail-region__facts client-ficha__contact-facts">
              <div><dt>Teléfono</dt><dd>{customer.phone_e164 ?? "—"}<Button className="client-ficha__copy-button" aria-label="Copiar teléfono" onClick={() => void navigator.clipboard?.writeText(customer.phone_e164 ?? "") }><Copy/></Button></dd></div>
              <div><dt>Correo</dt><dd>{customer.email ?? "—"}<Button className="client-ficha__copy-button" aria-label="Copiar correo" onClick={() => void navigator.clipboard?.writeText(customer.email ?? "") }><Copy/></Button></dd></div>
              <div><dt>Dirección</dt><dd>{customer.address ?? "—"}{customer.comuna ? <><br/>{customer.comuna}</> : null}<Button className="client-ficha__copy-button" aria-label="Copiar dirección" onClick={() => void navigator.clipboard?.writeText([customer.address, customer.comuna].filter(Boolean).join(", "))}><Copy/></Button></dd></div>
              <div className="client-ficha__customer-state"><dt>Estado del cliente</dt><dd><Badge tone={customerStateTone(customer.state)}>{customerStateLabel(customer.state)}</Badge></dd></div>
              <div><dt>Consentimiento</dt><dd>{customer.consent_status ? "Sí" : "No"}</dd></div>
            </dl>
          </Card>
          <Dialog open={stateDialogOpen} onClose={() => setStateDialogOpen(false)} title="Cambiar estado del cliente" icon={RefreshCw} description="Selecciona el nuevo estado para este cliente.">
            <div className="client-ficha-dialog">
              <div className="client-ficha-dialog__context"><Avatar name={customer.name ?? customer.phone_e164 ?? "Cliente"} /><div><strong>{customer.name ?? customer.phone_e164 ?? "Cliente"}</strong><span>Cliente desde el {formatIdentityDate(customer.created_at)}</span></div><div className="client-ficha-dialog__current"><span>Estado actual</span><Badge tone={customerStateTone(customer.state)}>{customerStateLabel(customer.state)}</Badge></div></div>
              <div className="client-ficha-dialog__options"><strong>Nuevo estado</strong><div role="radiogroup" aria-label="Nuevo estado">{(customer.allowed_transitions ?? []).map((value) => <Button key={value} type="button" role="radio" aria-checked={selectedState === value} variant="secondary" className={selectedState === value ? "client-ficha-dialog__option is-selected" : "client-ficha-dialog__option"} disabled={mutation !== null} onClick={() => setSelectedState(value)}><strong>{customerStateLabel(value)}</strong><span className="client-ficha-dialog__radio" aria-hidden="true" /></Button>)}</div>{!(customer.allowed_transitions ?? []).length ? <p role="status">Este cliente no tiene transiciones de estado disponibles.</p> : null}</div>
              {(customer.allowed_transitions ?? []).length ? <div className="client-ficha-dialog__transition"><span>Cambio de estado</span><Badge tone={customerStateTone(customer.state)}>{customerStateLabel(customer.state)}</Badge><span aria-hidden="true">→</span><Badge tone={customerStateTone(selectedState ?? customer.state)}>{customerStateLabel(selectedState ?? customer.state)}</Badge></div> : null}
              <LocalFeedback feedback={stateFeedback} />
              <footer><Button variant="secondary" onClick={() => setStateDialogOpen(false)}>Cancelar</Button>{(customer.allowed_transitions ?? []).length ? <Button disabled={mutation !== null || customerId === undefined || !selectedState || selectedState === customer.state} onClick={() => void saveState()}>{mutation === "state" ? "Guardando…" : "Guardar estado"}</Button> : null}</footer>
            </div>
          </Dialog>
          <Dialog open={consentDialogOpen} onClose={() => setConsentDialogOpen(false)} title="Cambiar consentimiento" icon={ShieldCheck} description="Registra la elección expresada por el cliente.">
            <div className="client-ficha-dialog">
              <div className="client-ficha-dialog__context"><Avatar name={customer.name ?? customer.phone_e164 ?? "Cliente"} /><div><strong>{customer.name ?? customer.phone_e164 ?? "Cliente"}</strong><span>Cliente desde el {formatIdentityDate(customer.created_at)}</span></div><div className="client-ficha-dialog__current"><span>Consentimiento actual</span><Badge tone={customer.consent_status ? "success" : "neutral"}>{customer.consent_status ? "Sí" : "No"}</Badge></div></div>
              <div className="client-ficha-dialog__options"><strong>Nuevo consentimiento</strong><div role="radiogroup" aria-label="Nuevo consentimiento">{[[true, "Sí", "El cliente acepta ser contactado por la tarde."], [false, "No", "El cliente prefiere no ser contactado."]].map(([value, label, detail]) => <Button key={String(value)} type="button" role="radio" aria-checked={selectedConsent === value} variant="secondary" className={selectedConsent === value ? "client-ficha-dialog__option is-selected" : "client-ficha-dialog__option"} disabled={customerMutation !== null} onClick={() => setSelectedConsent(value as boolean)}><span className="client-ficha-dialog__option-copy"><strong>{label}</strong><span>{detail}</span></span><span className="client-ficha-dialog__radio" aria-hidden="true" /></Button>)}</div></div>
              <LocalFeedback feedback={consentFeedback} />
              <footer><Button variant="secondary" onClick={() => setConsentDialogOpen(false)}>Cancelar</Button><Button disabled={customerMutation !== null || customerId === undefined || selectedConsent === null} onClick={() => void saveConsent()}>{customerMutation === "consent" ? "Guardando…" : "Guardar consentimiento"}</Button></footer>
            </div>
          </Dialog>
          <Dialog open={profileOpen} onClose={() => setProfileOpen(false)} title="Editar datos del cliente" icon={UserRound} description="Actualiza su información de contacto." size="wide">
            <form onSubmit={(event) => void saveProfile(event)}>
              <div className="client-ficha-dialog__profile-row"><Input label="Nombre" icon={UserRound} value={profile.name} onChange={(event) => setProfile({ ...profile, name: event.target.value })} /><Input label="Teléfono *" icon={Phone} value={customer.phone_e164 ?? "—"} readOnly /></div>
              <Input label="Correo (opcional)" icon={Mail} type="email" value={profile.email} onChange={(event) => setProfile({ ...profile, email: event.target.value })} />
              <Input label="Comuna (opcional)" icon={MapPin} value={profile.comuna} onChange={(event) => setProfile({ ...profile, comuna: event.target.value })} />
              <Input label="Dirección (opcional)" icon={Home} value={profile.address} onChange={(event) => setProfile({ ...profile, address: event.target.value })} />
              <LocalFeedback feedback={profileFeedback} />
              <footer><Button type="button" variant="secondary" onClick={() => setProfileOpen(false)}>Cancelar</Button><Button type="submit" disabled={customerMutation !== null}>{customerMutation === "profile" ? "Guardando…" : "Guardar cambios"}</Button></footer>
            </form>
          </Dialog>
          <Dialog open={archiveOpen} onClose={() => setArchiveOpen(false)} title="Archivar cliente" icon={Archive} description="El cliente dejará de aparecer en la lista habitual.">
            <div className="client-ficha-dialog">
              <div className="client-ficha-dialog__context"><Avatar name={customer.name ?? customer.phone_e164 ?? "Cliente"} /><div><strong>{customer.name ?? customer.phone_e164 ?? "Cliente"}</strong><span>Cliente desde el {formatIdentityDate(customer.created_at)}</span></div></div>
              <section className="client-ficha-dialog__archive-info" aria-label="Información del cliente"><strong>Información del cliente</strong><div className="client-ficha-dialog__archive-stats"><div><FileText /><strong>{openCaseCount}</strong><span>{openCaseCount === 1 ? "caso abierto" : "casos abiertos"}</span></div><div><CalendarDays /><strong>{futureAppointmentCount}</strong><span>{futureAppointmentCount === 1 ? "visita futura" : "visitas futuras"}</span></div></div></section>
              <p className="client-ficha-dialog__warning"><CircleAlert aria-hidden="true" />Estos trabajos seguirán registrados.</p>
              <LocalFeedback feedback={archiveFeedback} />
              <footer><Button variant="secondary" onClick={() => setArchiveOpen(false)}>Cancelar</Button><Button variant="danger" disabled={customerMutation !== null} onClick={() => void saveArchive()}>{customerMutation === "archive" ? "Guardando…" : "Archivar cliente"}</Button></footer>
            </div>
          </Dialog>
          <Dialog open={mergeOpen} onClose={() => setMergeOpen(false)} title="Fusionar clientes" icon={ArrowLeftRight} description="Revisa las fichas antes de confirmar." size="wide">
            <div className="client-ficha-dialog client-ficha-dialog__merge">
              <div className="client-ficha-dialog__merge-current"><strong>Cliente actual</strong><div><Avatar name={customer.name ?? customer.phone_e164 ?? "Cliente"} /><span><b>{customer.name ?? customer.phone_e164 ?? "Cliente"}</b><small>Cliente desde el {formatIdentityDate(customer.created_at)}</small></span><span className="client-ficha-dialog__merge-phone"><Phone />{customer.phone_e164 ?? "—"}</span></div></div>
              <Select id="merge-other-client" label="Otro cliente" value={mergeOtherId} options={[{ value: "", label: "Buscar por nombre o teléfono…" }, ...mergeClients.map((client) => ({ value: String(client.id), label: `${client.name ?? "Sin nombre"} · ${client.phone_e164 ?? "Sin teléfono"}` }))]} onChange={(event) => void selectMergeClient(event.target.value)} />
              <div className="client-ficha-dialog__merge-cards"><section><strong>Ficha actual</strong><div><Avatar name={customer.name ?? customer.phone_e164 ?? "Cliente"} /><span><b>{customer.name ?? customer.phone_e164 ?? "Cliente"}</b><small>{customer.phone_e164 ?? "—"}</small></span></div></section><section><strong>Otra ficha</strong><div><Avatar name={mergeClients.find((client) => String(client.id) === mergeOtherId)?.name ?? "Sin seleccionar"} /><span><b>{mergeClients.find((client) => String(client.id) === mergeOtherId)?.name ?? "Sin seleccionar"}</b><small>{mergeClients.find((client) => String(client.id) === mergeOtherId)?.phone_e164 ?? "—"}</small></span></div></section></div>
              <p className="client-ficha-dialog__warning"><CircleAlert aria-hidden="true" />Comprueba que ambas fichas correspondan a la misma persona.</p>
              {mergePreview ? <p className="client-ficha-dialog__merge-preview">Vista previa: se moverán {Object.entries(mergePreview.moved).map(([table, count]) => `${MERGE_COUNT_LABELS[table as keyof ClientMergePreview["moved"]]}: ${count}`).join(" · ")}; {mergePreview.memory_conflicts} conflictos de memoria{mergePreview.scalar_conflicts.length ? `; se conservan los datos del cliente superviviente en ${mergePreview.scalar_conflicts.join(", ")}` : ""}.</p> : null}
              <LocalFeedback feedback={mergeFeedback} />
              <footer><Button variant="secondary" onClick={() => setMergeOpen(false)}>Cancelar</Button><Button variant="danger" disabled={!mergePreview || mergeLoading} onClick={() => void confirmMerge()}>{mergeLoading ? "Fusionando…" : "Confirmar fusión"}</Button></footer>
            </div>
          </Dialog>
        </section>

        <div className="detail-region__main">
          <Card className="client-ficha__case-card">
            {activeCase ? <>
                <div className="client-ficha__case-eyebrow"><span className="client-ficha__status-dot"/> CASO ACTIVO <span>#{activeCase.id}</span><Menu trigger="icon" label="Acciones del caso" items={[{ value: "edit", label: "Editar caso", icon: BriefcaseBusiness }, { value: "amount", label: "Definir monto", icon: CircleDollarSign }]} onSelect={(value) => value === "amount" ? (setAmountInput(activeCase.amount === null ? "" : String(activeCase.amount)), setAmountOpen(true)) : openCaseEditor()} /></div>
              <h2 className="client-ficha__case-title">{activeCase.service}</h2>
              <div className="client-ficha__case-badges"><Badge tone={caseStatusTone(activeCase.status)}>{caseStatusLabel(activeCase.status)}</Badge><Badge tone="warning">Prioridad {activeCase.priority}</Badge></div>
              <p>{activeCase.summary ?? "—"}</p>
                <div className="client-ficha__case-details"><div><small>Responsable</small><strong><Avatar name={data.users.find((user) => user.id === activeCase.responsible_id)?.username ?? "Sin asignar"} /> {data.users.find((user) => user.id === activeCase.responsible_id)?.username ?? "Sin asignar"}</strong></div><div><small>Monto del servicio</small><strong>{activeCase.amount === null ? "Sin registrar" : CLP_FORMAT.format(activeCase.amount)}</strong></div></div>
              {activeCase.emergency ? <Badge tone={activeCase.ack_by === null ? "danger" : "warning"}>{activeCase.ack_by === null ? "Emergencia sin reconocer" : `Emergencia reconocida por ${activeCase.ack_by}`}</Badge> : null}
               <LocalFeedback feedback={caseEditorOpen || amountOpen ? null : caseFeedback} />
            </> : <EmptyState title="Sin caso activo" />}
          </Card>
          <Dialog open={caseEditorOpen && activeCase !== null} onClose={() => setCaseEditorOpen(false)} title="Editar caso" icon={BriefcaseBusiness} description="Actualiza el estado y el responsable.">
            {activeCase ? <div className="client-ficha-dialog">
              <div className="client-ficha-dialog__case-context"><Avatar name={customer.name ?? customer.phone_e164 ?? "Cliente"}/><div><strong>{customer.name ?? customer.phone_e164 ?? "Cliente"}</strong><span>#{activeCase.id} · {activeCase.service}</span></div></div>
              <Select label="Estado" value={caseEdit.status} onChange={(event) => setCaseEdit({ ...caseEdit, status: event.target.value })} options={[{value:"abierto",label:"Abierto"},{value:"en_evaluacion",label:"En evaluación"},{value:"escalado",label:"Escalado"},{value:"cerrado",label:"Cerrado"}]}/>
              <Select label="Responsable" value={caseEdit.responsibleId} onChange={(event) => setCaseEdit({ ...caseEdit, responsibleId: event.target.value })} options={[{value:"",label:"Sin asignar"},...data.users.map((user) => ({value:String(user.id),label:user.username}))]}/>
              <LocalFeedback feedback={caseFeedback}/><footer><Button variant="secondary" onClick={() => setCaseEditorOpen(false)}>Cancelar</Button>{activeCase.emergency && activeCase.ack_by === null ? <Button variant="secondary" onClick={() => void acknowledgeCase(activeCase.id)}>Reconocer</Button> : null}<Button onClick={() => void saveCaseEdit()}>Guardar cambios</Button></footer>
            </div> : null}
          </Dialog>
          <Dialog open={amountOpen} onClose={() => setAmountOpen(false)} title="Definir monto del caso" icon={CircleDollarSign} description="Registra el monto del servicio asociado al caso.">
            <form onSubmit={(event) => void saveCaseAmount(event)}>
              {activeCase ? <div className="client-ficha-dialog__case-context"><Avatar name={customer.name ?? customer.phone_e164 ?? "Cliente"}/><div><strong>{customer.name ?? customer.phone_e164 ?? "Cliente"}</strong><span>#{activeCase.id} · {activeCase.service}</span></div><div className="client-ficha-dialog__current"><span>Monto actual:</span><strong>{activeCase.amount === null ? "Sin registrar" : CLP_FORMAT.format(activeCase.amount)}</strong></div></div> : null}
              <div className="client-ficha-dialog__amount"><span aria-hidden="true">$</span><Input label="Monto del servicio" type="number" min="0" step="1" value={amountInput} onChange={(event) => setAmountInput(event.target.value)} helper="Ingresa el monto en pesos chilenos."/><span aria-hidden="true">CLP</span></div>
              <LocalFeedback feedback={caseFeedback} />
              <footer><Button type="button" variant="secondary" onClick={() => setAmountOpen(false)}>Cancelar</Button><Button type="submit" disabled={amountMutation}>{amountMutation ? "Guardando…" : "Guardar monto"}</Button></footer>
            </form>
          </Dialog>
          <ClientMemories memories={memories} pendingRelations={pendingRelations} onResolveRelation={resolveRelation} compact conversationId={history.conversations[0]?.id} onViewAll={() => setActiveTab("conversations")} />

          <section aria-label="Equipos" className="client-ficha__equipment-slot">
             <Card className="client-ficha__equipment-card">
               <header className="client-ficha__card-heading"><h2>Equipos</h2><Button variant="secondary" disabled={customerId === undefined || equipmentMutation} onClick={() => openEquipment()}>＋ Agregar equipo</Button></header>
              {equipmentData.state === "loading" ? <p role="status">Cargando equipos…</p> : null}
              {equipmentData.state === "error" || equipmentData.state === "denied" ? <StateMessage tone="danger" role="alert" title="No pudimos cargar los equipos" /> : null}
              {equipmentRows.length ? <ul className="data-region">
                {equipmentRows.map((entry) => <li key={entry.id}>
                  <div>{entry.equipment_type ? <Badge>{EQUIPMENT_TYPE_LABELS[entry.equipment_type] ?? entry.equipment_type}</Badge> : <span>Sin especificar</span>}</div>
                  <p>{[entry.brand, entry.model, entry.age].filter(Boolean).join(" · ") || "Sin datos estructurados"}</p>
                  {entry.details ? <p>{entry.details}</p> : null}
                  <Button variant="secondary" disabled={equipmentMutation} onClick={() => openEquipment(entry)}>Editar equipo</Button>
                </li>)}
              </ul> : equipmentData.state === "empty" || equipmentData.state === "ready" ? <div className="client-ficha__equipment-empty"><div className="client-ficha__equipment-illustration" aria-hidden="true">♧</div><EmptyState title="Sin equipos registrados"/><Button variant="secondary" disabled={customerId === undefined || equipmentMutation} onClick={() => openEquipment()}>Agregar equipo</Button></div> : null}
              {equipmentOpen ? null : <LocalFeedback feedback={equipmentFeedback} />}
            </Card>
          </section>
          <Dialog open={equipmentOpen} onClose={() => setEquipmentOpen(false)} title={editingEquipment ? "Editar equipo" : "Agregar equipo"} icon={Smartphone} description="Registra un equipo asociado al cliente.">
            <form className="client-ficha-dialog" onSubmit={(event) => void saveEquipment(event)}>
              <Select id="equipment-type" label="Tipo de equipo" value={equipmentForm.equipment_type ?? ""} options={EQUIPMENT_TYPE_OPTIONS} onChange={(event) => setEquipmentForm({ ...equipmentForm, equipment_type: event.target.value })} />
              <Input label="Marca (opcional)" placeholder="Ej. Marca del equipo" value={equipmentForm.brand ?? ""} onChange={(event) => setEquipmentForm({ ...equipmentForm, brand: event.target.value })} />
              <Input label="Modelo (opcional)" placeholder="Modelo del equipo" value={equipmentForm.model ?? ""} onChange={(event) => setEquipmentForm({ ...equipmentForm, model: event.target.value })} />
              <LocalFeedback feedback={equipmentFeedback} />
              <footer><Button type="button" variant="secondary" onClick={() => setEquipmentOpen(false)}>Cancelar</Button><Button type="submit" disabled={equipmentMutation}>{equipmentMutation ? "Guardando…" : editingEquipment ? "Guardar equipo" : "Agregar equipo"}</Button></footer>
            </form>
          </Dialog>

          <Card className="client-ficha__notes-card">
            <header className="client-ficha__card-heading"><h2>Notas</h2><Button variant="secondary" aria-expanded={noteComposerOpen} disabled={customerId === undefined || mutation !== null} onClick={() => setNoteComposerOpen(true)}>⊕ Agregar nota</Button></header>
            {data.notes.length ? data.notes.map((entry) => <article className="client-ficha__note-row" key={entry.id}><Avatar name={entry.author ?? "Operador"}/><div><strong>{entry.author ?? "—"}</strong><small>{formatDate(entry.created_at)}</small></div><p>{entry.note}</p><Menu trigger="icon" label="Acciones de nota" items={[{value:"copy",label:"Copiar nota"}]} onSelect={()=>void navigator.clipboard?.writeText(entry.note)}/></article>) : <EmptyState title="No hay notas" />}
          </Card>
          <Dialog open={noteComposerOpen} onClose={() => setNoteComposerOpen(false)} title="Agregar nota" icon={NotebookPen} description="Registra una nota asociada al cliente.">
            <form className="client-ficha-dialog" onSubmit={(event) => { event.preventDefault(); void saveNote(); }}>
              <div className="client-ficha-dialog__context"><Avatar name={customer.name ?? customer.phone_e164 ?? "Cliente"}/><div><strong>{customer.name ?? customer.phone_e164 ?? "Cliente"}</strong><span>Cliente desde el {formatIdentityDate(customer.created_at)}</span></div><span className="client-ficha-dialog__context-phone"><Phone aria-hidden="true"/>{customer.phone_e164 ?? "—"}</span></div>
              <Textarea id="new-note" label="Nota" placeholder="Escribe información útil para el seguimiento del cliente…" value={note} disabled={mutation !== null || customerId === undefined} onChange={(event) => setNote(event.target.value)} />
              <p className="client-ficha-dialog__helper">La nota quedará asociada a esta ficha.</p>
              <LocalFeedback feedback={noteFeedback} />
              <footer><Button type="button" variant="secondary" onClick={() => setNoteComposerOpen(false)}>Cancelar</Button><Button type="submit" disabled={mutation !== null || customerId === undefined}>{mutation === "note" ? "Guardando…" : "Guardar nota"}</Button></footer>
            </form>
          </Dialog>

          <Card className="client-ficha__upcoming-card">
            <header className="client-ficha__card-heading"><h2>Próximas visitas</h2><Button variant="secondary" onClick={() => { window.location.href = pathForRoute({ view: "agenda" }); }}>Ver agenda →</Button></header>
            {upcomingAppointments.length ? <ul className="client-ficha__visits">{upcomingAppointments.map((appointment) => { const date = new Date(appointment.starts_at); return <li key={appointment.id}><a className="client-ficha__upcoming-row" href={pathForRoute({ view: "agenda", appointmentId: appointment.id })}><span className="client-ficha__date-tile"><strong>{date.getDate().toString().padStart(2, "0")}</strong><small>{new Intl.DateTimeFormat("es-CL", { month: "short" }).format(date).replace(".", "").toUpperCase()}</small></span><span>{appointment.service}</span><span><Clock3/>{new Intl.DateTimeFormat("es-CL",{hour:"2-digit",minute:"2-digit"}).format(date)}</span><Badge tone={appointmentStatusTone(appointment.status)}>{appointmentStatusLabel(appointment.status)}</Badge></a></li>; })}</ul> : <EmptyState title="No hay próximas visitas" />}
          </Card>

          <button type="button" className="client-ficha__history-entry" onClick={() => setHistoryOpen(true)}>
            <Clock3 aria-hidden="true"/><span><strong>Historial del cliente</strong><small>Visitas, conversaciones y casos anteriores</small></span><span aria-hidden="true">›</span>
          </button>

        </div>
      </div>
      </> : null}
       {activeTab === "cases" ? <div className="detail-region">
         <section className="detail-region__main"><Card title="Casos del cliente" description="Caso activo e historial de atención.">{activeCase ? <div className="client-ficha__case-inline"><span className="client-ficha__status-dot"/> CASO ACTIVO <strong>{activeCase.service}</strong><Badge tone={caseStatusTone(activeCase.status)}>{caseStatusLabel(activeCase.status)}</Badge><Badge tone="warning">Prioridad {activeCase.priority}</Badge><p>{activeCase.summary}</p><Button variant="secondary" onClick={() => setCaseEditorOpen((open) => !open)}>Editar caso</Button>{caseEditorOpen ? <CaseActions target={activeCase} users={data.users} onUpdate={async (...args) => { await updateCase(...args); }} onAcknowledge={acknowledgeCase}/> : null}</div> : <EmptyState title="Sin caso activo"/>}</Card><section aria-label="Casos anteriores" className="client-ficha__history-block"><Card title="Casos anteriores"><div className={surfaceClass(archivedCases.length)}><DataTable columns={caseColumns} rows={archivedCases} rowKey={(row) => String(row.id)} /></div><p>Mostrando {archivedCases.length} {archivedCases.length === 1 ? "caso anterior" : "casos anteriores"}</p></Card></section></section>
      </div> : null}
      {activeTab === "visits" ? <div className="detail-region__main">
        <section aria-label="Próximas visitas" className="client-ficha__history-block"><h2>Visitas</h2><Card title="Próximas visitas" description="Visitas pendientes de este cliente.">{upcomingAppointments.length ? <div className="data-region"><DataTable columns={[{key:"date",header:"Fecha y hora",render:(row: Appointment)=><><strong>{formatDate(row.starts_at)}</strong><br/><Clock3/> {new Intl.DateTimeFormat("es-CL",{hour:"2-digit",minute:"2-digit"}).format(new Date(row.starts_at))}</>},{key:"service",header:"Servicio",render:(row: Appointment)=><a href={pathForRoute({view:"agenda",appointmentId:row.id})}>{row.service}</a>},{key:"status",header:"Estado",render:(row: Appointment)=><Badge tone={appointmentStatusTone(row.status)}>{appointmentStatusLabel(row.status)}</Badge>},{key:"actions",header:"Acciones",render:(row: Appointment)=><Button variant="secondary" onClick={()=>{window.location.href=pathForRoute({view:"agenda",appointmentId:row.id})}}>Reprogramar</Button>}] as Column<Appointment>[]} rows={upcomingAppointments} rowKey={(row)=>String(row.id)}/></div>:<EmptyState title="No hay próximas visitas"/>}</Card><Card title="Historial de visitas"><DataTable columns={[{key:"date",header:"Fecha y hora",render:(row: Appointment)=><>{formatDate(row.starts_at)}<br/><Clock3/> {formatDateTime(row.starts_at)}</>},{key:"service",header:"Servicio",render:(row: Appointment)=><a href={pathForRoute({view:"agenda",appointmentId:row.id})}>{row.service}</a>},{key:"status",header:"Estado",render:(row: Appointment)=><Badge tone={appointmentStatusTone(row.status)}>{appointmentStatusLabel(row.status)}</Badge>}] as Column<Appointment>[]} rows={appointments.filter(row=>!upcomingAppointments.includes(row))} rowKey={(row)=>String(row.id)} /></Card>{appointments.some((appointment)=>appointment.calendar_error) ? appointments.filter((appointment)=>appointment.calendar_error).map((appointment)=><div key={appointment.id}><StateMessage tone="danger" role="alert" title="No se pudo sincronizar el calendario" detail={`${appointment.calendar_error} Reintenta la sincronización.`}/><Button variant="secondary" disabled={retryingCalendarId===appointment.id} onClick={()=>void retryCalendar(appointment.id)}>Reintentar calendario</Button></div>):null}</section>
      </div> : null}
      {activeTab === "conversations" ? <div className="detail-region__main">
        <section aria-label="Conversaciones" className="client-ficha__history-block"><Card title="Conversaciones del cliente"><div className={surfaceClass(history.conversations.length)}><DataTable columns={[...conversationColumns,{key:"actions",header:"Acciones",render:(row)=><Button variant="secondary" onClick={()=>{window.location.href=pathForRoute({view:"conversations",conversationId:row.id})}}>Abrir conversación</Button>}] as Column<(typeof history.conversations)[number]>[]} rows={history.conversations} rowKey={(row) => String(row.id)} /></div></Card></section>
        <section aria-label="Mensajes" className="client-ficha__history-block"><h2>Mensajes de la conversación #{history.conversations[0]?.id ?? "—"}</h2><p>Historial de mensajes del hilo seleccionado.</p><div className={surfaceClass(history.messages.length)}><CollapsibleMessages total={history.messages_total} expanded={messagesExpanded} onToggle={toggleMessages}><DataTable columns={messageColumns} rows={history.messages} rowKey={(row) => String(row.id)} /></CollapsibleMessages></div></section>
      </div> : null}
        </>}
      </Tabs>
      <Dialog open={historyOpen} onClose={() => setHistoryOpen(false)} title="Historial del cliente" icon={Clock3} description="Visitas, conversaciones y casos anteriores">
        <Card title="Casos anteriores"><DataTable columns={caseColumns} rows={archivedCases} rowKey={(row) => String(row.id)} /></Card>
        <Card title="Visitas"><DataTable columns={[{key:"service",header:"Servicio",render:(row: Appointment)=>row.service},{key:"date",header:"Fecha",render:(row: Appointment)=>formatDateTime(row.starts_at)},{key:"status",header:"Estado",render:(row: Appointment)=><Badge tone={appointmentStatusTone(row.status)}>{appointmentStatusLabel(row.status)}</Badge>}] as Column<Appointment>[]} rows={appointments} rowKey={(row)=>String(row.id)}/></Card>
        <Card title="Conversaciones"><DataTable columns={conversationColumns} rows={history.conversations} rowKey={(row)=>String(row.id)}/></Card>
      </Dialog>
    </PageFrame>
  );
}
