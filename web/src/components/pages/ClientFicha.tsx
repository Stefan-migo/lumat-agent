import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Archive, ArrowLeftRight, BriefcaseBusiness, CalendarDays, CalendarX, CircleAlert, Clock3, Copy, Check, ChevronRight, FileText, Home, Mail, MapPin, MessageSquare, NotebookPen, Pencil, Phone, RefreshCw, ShieldCheck, Smartphone, Thermometer, UserRound, CircleDollarSign, Trash2, X, Bot, ArrowDownLeft, ArrowUpRight } from "lucide-react";
import { addClientNote, ApiError, apiFetch, archiveCustomer, cancelAppointment, changeClientState, closeAppointment, createClientEquipment, deleteClientNote, fetchClients, getConversation, listClientEquipment, mergeClient, postJson, previewClientMerge, resolveMemoryRelation, unarchiveCustomer, updateCaseAmount, updateClientEquipment, updateClientNote, updateCustomerConsent, updateCustomerProfile, type CustomerEquipmentUpdate } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { Appointment, ClientFichaResponse, ClientMergePreview, Customer, CustomerEquipment, CustomerProfileUpdateRequest, CustomerState, Memory, MemoryRelation, MemoryRelationKind, MemoriesResponse, PendingMemoryRelationsResponse } from "../../types";
import { ClientMemories } from "../domain/ClientMemories";
import { pathForRoute } from "../domain/panelRoutes";
import { Badge, type BadgeTone } from "../primitives/Badge";
import { Avatar } from "../primitives/Avatar";
import { Button } from "../primitives/Button";
import { Card } from "../primitives/Card";
import { Combobox } from "../primitives/Combobox";
import { Dialog } from "../primitives/Dialog";
import { Input } from "../primitives/Input";
import { Menu } from "../primitives/Menu";
import { Select } from "../primitives/Select";
import { Textarea } from "../primitives/Textarea";
import { Tabs } from "../primitives/Tabs";
import { Pagination } from "../primitives/Pagination";
import "./ClientFichaDialogs.css";
import { DataTable, type Column } from "../shared/DataTable";
import { EmptyState } from "../shared/EmptyState";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { Markdown } from "../shared/Markdown";
import { ConversationSummary } from "../shared/ConversationSummary";
import { plainSummary } from "../shared/markdownText";
import { ChangeCustomerStateDialog } from "../shared/ChangeCustomerStateDialog";
import { AppointmentClosureDialog, type AppointmentClosureOutcome } from "../shared/AppointmentClosureDialog";
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
const MERGE_COUNT_LABELS: Record<keyof ClientMergePreview["moved"], string> = { conversations: "conversaciones", cases: "casos", customer_notes: "notas", customer_equipment: "equipos", appointments: "visitas" };
const FICHA_TABS = [{ id: "summary", label: "Resumen" }, { id: "cases", label: "Casos" }, { id: "visits", label: "Visitas" }, { id: "conversations", label: "Conversaciones" }];

const formatDate = (value: string | null | undefined) => (value ? DATE_FORMAT.format(new Date(value)) : "—");
const formatIdentityDate = (value: string | null | undefined) => (value ? IDENTITY_DATE_FORMAT.format(new Date(value)).replace(".", "") : "—");
const formatDateTime = (value: string | null | undefined) => (value ? DATE_TIME_FORMAT.format(new Date(value)) : "—");
const TIME_FORMAT = new Intl.DateTimeFormat("es-CL", { hour: "2-digit", minute: "2-digit", hour12: false });
const CONVERSATION_TONES: Record<string, BadgeTone> = { bot: "success", human: "neutral", closed: "neutral", pending: "warning", escalated: "danger" };
const MESSAGE_TYPE_LABELS: Record<string, string> = { text: "Texto", image: "Imagen", audio: "Audio", video: "Video", document: "Documento" };
const messageTypeLabel = (value: string) => MESSAGE_TYPE_LABELS[value] ?? value;
const messageWhen = (value: string | null | undefined) => value ? `${formatIdentityDate(value)} · ${TIME_FORMAT.format(new Date(value))}` : "—";

// Visitas tab: the date cell mirrors the reference (bold day/month/year + muted clock time),
// the service is a drill-down link rendered as plain text, and the row action lives in a `...` menu.
const visitWhenCell = (row: Appointment) => (
  <div className="client-ficha__visit-when"><strong>{formatIdentityDate(row.starts_at)}</strong><span><Clock3 aria-hidden="true" />{TIME_FORMAT.format(new Date(row.starts_at))}</span></div>
);
const visitServiceCell = (row: Appointment) => (
  <a className="table__resource-name" href={pathForRoute({ view: "agenda", appointmentId: row.id })}>{row.service}</a>
);
const VISIT_COLUMNS: Column<Appointment>[] = [
  { key: "date", header: "Fecha y hora", render: visitWhenCell },
  { key: "service", header: "Servicio", render: visitServiceCell },
  { key: "status", header: "Estado", render: (row) => <Badge tone={appointmentStatusTone(row.status)}>{appointmentStatusLabel(row.status)}</Badge> },
];

export interface ClientFichaProps {
  customerId?: number;
  /** Ficha tab to open with (deep link from a conversation's "Ver caso"). */
  initialTab?: string;
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
type FichaCase = ClientFichaResponse["history"]["cases"][number];

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

function CopyButton({ value, label }: { value: string; label: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    await navigator.clipboard?.writeText(value);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };
  return <span className="client-ficha__copy"><Button className="client-ficha__copy-button" aria-label={label} onClick={() => void copy()}>{copied ? <Check /> : <Copy />}</Button>{copied ? <span className="client-ficha__copy-hint" role="status">Copiado</span> : null}</span>;
}

/** A data surface only when there is data: an empty DataTable already renders its own
 *  `.empty-state` surface, and nesting the two would be card-on-card. */
function surfaceClass(rowCount: number) {
  return rowCount > 0 ? "data-region" : undefined;
}
const priorityLabel = (priority: string | null) => priority ? priority.charAt(0).toUpperCase() + priority.slice(1) : "—";

export function ClientFicha({ customerId, initialTab, data: controlledData, memories: controlledMemories, onRetryCalendar, state: controlledState }: ClientFichaProps) {
  const [activeTab, setActiveTab] = useState(initialTab ?? "summary");
  const [archivedCasePage, setArchivedCasePage] = useState(1);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [memoriesOpen, setMemoriesOpen] = useState(false);
  const [caseEditTarget, setCaseEditTarget] = useState<FichaCase | null>(null);
  const [retryingCalendarId, setRetryingCalendarId] = useState<number | null>(null);
  const [refreshed, setRefreshed] = useState<{ ficha: ClientFichaResponse; memories: Memory[]; pendingRelations: MemoryRelation[] } | null>(null);
  const [selectedState, setSelectedState] = useState<CustomerState | null>(null);
  const [stateDialogOpen, setStateDialogOpen] = useState(false);
  const [consentDialogOpen, setConsentDialogOpen] = useState(false);
  const [selectedConsent, setSelectedConsent] = useState<boolean | null>(null);
  const [note, setNote] = useState("");
  const [noteComposerOpen, setNoteComposerOpen] = useState(false);
  const [editingNote, setEditingNote] = useState<{ id: number; note: string } | null>(null);
  const [deletingNote, setDeletingNote] = useState<number | null>(null);
  const [copiedNoteId, setCopiedNoteId] = useState<number | null>(null);
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
  const [amountTarget, setAmountTarget] = useState<FichaCase | null>(null);
  const [amountInput, setAmountInput] = useState("");
  const [amountMutation, setAmountMutation] = useState(false);
  const [visitCancelTarget, setVisitCancelTarget] = useState<Appointment | null>(null);
  const [visitCancelReason, setVisitCancelReason] = useState("");
  const [visitCloseTarget, setVisitCloseTarget] = useState<Appointment | null>(null);
  const [visitCloseOutcome, setVisitCloseOutcome] = useState<AppointmentClosureOutcome>("completed");
  const [visitMutation, setVisitMutation] = useState(false);
  const [visitFeedback, setVisitFeedback] = useState<Feedback | null>(null);
  const [selectedConversationId, setSelectedConversationId] = useState<number | null>(null);
  const fetchFicha = useCallback(async () => {
    if (fichaCustomerId === undefined) throw new Error("customer id is required");
    const [ficha, memoryResponse, pendingResponse] = await Promise.all([
      apiFetch<ClientFichaResponse>(`/panel/api/clients/${fichaCustomerId}?messages_limit=${MESSAGE_PREVIEW}`),
      apiFetch<MemoriesResponse>(`/panel/api/clients/${fichaCustomerId}/memories`),
      apiFetch<PendingMemoryRelationsResponse>(`/panel/api/clients/${fichaCustomerId}/memory-relations/pending`),
    ]);
    return { ficha, memories: memoryResponse.memories, pendingRelations: pendingResponse.relations };
  }, [fichaCustomerId]);
  const fetched = useAsyncData(fetchFicha, (controlledData === undefined || mergedCustomerId !== null) && controlledState === undefined, mergedCustomerId ?? 0);
  const fetchEquipment = useCallback(async () => {
    if (fichaCustomerId === undefined) return [];
    return (await listClientEquipment(fichaCustomerId)).equipment;
  }, [fichaCustomerId]);
  const equipmentData = useAsyncData(fetchEquipment, fichaCustomerId !== undefined, equipmentRefresh + (mergedCustomerId ?? 0));
  const equipmentRows = equipmentData.data ?? [];
  const data = mergedCustomerId !== null ? fetched.data?.ficha : refreshed?.ficha ?? controlledData ?? fetched.data?.ficha;
  const caseCount = data?.history.cases.length ?? 0;
  const archivedCaseCount = Math.max(0, caseCount - Number(data?.history.cases.some((row) => row.is_open) ?? false));
  const archivedCasePageCount = Math.ceil(archivedCaseCount / 5);
  useEffect(() => setArchivedCasePage(1), [fichaCustomerId, caseCount]);
  useEffect(() => setArchivedCasePage((page) => Math.min(page, Math.max(1, archivedCasePageCount))), [archivedCasePageCount]);
  const memories = mergedCustomerId !== null ? fetched.data?.memories ?? [] : refreshed?.memories ?? controlledMemories ?? fetched.data?.memories ?? [];
  const pendingRelations = refreshed?.pendingRelations ?? fetched.data?.pendingRelations ?? [];
  const state: FichaState = controlledState ?? (controlledData ? "ready" : fetched.state);
  // The Mensajes card is scoped to one conversation: a selector picks it and we load that
  // thread's last `MESSAGE_PREVIEW` messages (the full thread lives behind `Abrir conversación`).
  const conversationList = data?.history.conversations ?? [];
  const defaultConversationId = conversationList.length ? conversationList[conversationList.length - 1].id : null;
  const activeConversationId = selectedConversationId ?? defaultConversationId;
  const conversationThread = useAsyncData(
    async () => activeConversationId === null ? null : await getConversation(activeConversationId, MESSAGE_PREVIEW),
    activeConversationId !== null,
    activeConversationId ?? 0,
  );

  if (!data) {
    return <PageFrame title="Ficha de cliente" meta="Datos del cliente" state={stateMessage(state)}><EmptyState title="Cargando ficha" /></PageFrame>;
  }

  const { customer, history } = data;
  const activeCase = history.cases.filter((row) => row.is_open).at(-1) ?? null;
  const archivedCases = history.cases.filter((row) => row.id !== activeCase?.id);
  const currentArchivedCasePage = Math.min(archivedCasePage, Math.max(1, archivedCasePageCount));
  const visibleArchivedCases = archivedCases.slice((currentArchivedCasePage - 1) * 5, currentArchivedCasePage * 5);
  const archivedRangeStart = archivedCases.length ? (currentArchivedCasePage - 1) * 5 + 1 : 0;
  const archivedRangeEnd = Math.min(currentArchivedCasePage * 5, archivedCases.length);
  const appointments = history.appointments ?? [];
  const openCaseCount = history.cases.filter((row) => row.is_open).length;
  const futureAppointmentCount = appointments.filter((appointment) => appointment.status === "booked" && new Date(appointment.starts_at).getTime() > Date.now()).length;
  const upcomingAppointments = appointments.filter((appointment) => appointment.status === "booked" && new Date(appointment.starts_at).getTime() > Date.now());
  const finishedAppointments = appointments.filter((row) => !upcomingAppointments.includes(row));
  // "Turno" = the 1-based order of the message within the selected conversation. We load the
  // last `MESSAGE_PREVIEW` messages, so the first shown turn is offset by the thread length.
  const conversationMessages = conversationThread.data?.messages ?? [];
  const conversationTotal = conversationThread.data?.messages_total ?? 0;
  const messageTurns = new Map<number, number>();
  conversationMessages.forEach((message, index) => messageTurns.set(message.id, conversationTotal - conversationMessages.length + index + 1));
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
  const cancelVisit = async () => {
    if (!visitCancelTarget || visitMutation) return;
    setVisitMutation(true);
    setVisitFeedback(null);
    try {
      await cancelAppointment(visitCancelTarget.id, visitCancelReason.trim() || undefined);
      setVisitCancelTarget(null);
      setVisitCancelReason("");
      await refresh();
    } catch (error) { setVisitFeedback({ tone: "danger", title: "No se pudo cancelar la visita", detail: error instanceof Error ? error.message : undefined }); }
    finally { setVisitMutation(false); }
  };
  const closeVisit = async () => {
    if (!visitCloseTarget || visitMutation) return;
    setVisitMutation(true);
    setVisitFeedback(null);
    try {
      await closeAppointment(visitCloseTarget.id, visitCloseOutcome);
      setVisitCloseTarget(null);
      await refresh();
    } catch (error) { setVisitFeedback({ tone: "danger", title: "No se pudo registrar el resultado", detail: error instanceof Error ? error.message : "Intenta nuevamente." }); }
    finally { setVisitMutation(false); }
  };
  const visitRowMenu = (row: Appointment) => (
    <Menu trigger="icon" label={`Acciones de la visita #${row.id}`} items={[{ value: "reschedule", label: "Reprogramar", icon: CalendarDays }, { value: "cancel", label: "Cancelar visita", icon: X, tone: "danger" }, { value: "close", label: "Cerrar visita", icon: Check }]} onSelect={(value) => {
      if (value === "reschedule") window.location.href = pathForRoute({ view: "agenda", appointmentId: row.id });
      if (value === "cancel") { setVisitCancelReason(""); setVisitFeedback(null); setVisitCancelTarget(row); }
      if (value === "close") { setVisitCloseOutcome("completed"); setVisitFeedback(null); setVisitCloseTarget(row); }
    }} />
  );
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
    if (customerId === undefined || !amountTarget || amountMutation) return;
    const amountText = amountInput.trim();
    const parsedAmount = amountText === "" ? null : Number(amountInput);
    if (parsedAmount !== null && (!Number.isFinite(parsedAmount) || parsedAmount < 0)) {
      setCaseFeedback({ tone: "danger", title: "Ingresa un monto CLP válido y no negativo" });
      return;
    }
    setAmountMutation(true);
    setCaseFeedback(null);
    try {
      await updateCaseAmount(amountTarget.id, parsedAmount);
      await refresh();
      setAmountTarget(null);
    } catch (error) { setCaseFeedback({ tone: "danger", ...safeError(error, "caso") }); }
    finally { setAmountMutation(false); }
  };
  const updateCase = async (caseId: number, status: string, responsibleId: number | null) => {
    setCaseFeedback(null);
    try { await postJson(`/panel/api/cases/${caseId}/update`, { status, responsible_id: responsibleId }); await refresh(); return true; }
    catch (error) { setCaseFeedback({ tone: "danger", ...safeError(error, "caso") }); return false; }
  };
  const openCaseEditor = (target: FichaCase | null = activeCase) => {
    if (!target) return;
    setCaseEditTarget(target);
    setCaseEdit({ status: target.status, responsibleId: target.responsible_id === null ? "" : String(target.responsible_id) });
    setCaseFeedback(null);
  };
  const openAmountEditor = (target: FichaCase) => {
    setAmountInput(target.amount === null ? "" : String(target.amount));
    setAmountTarget(target);
    setCaseFeedback(null);
  };
  const saveCaseEdit = async () => {
    if (!caseEditTarget || !caseEdit.status) return;
    if (await updateCase(caseEditTarget.id, caseEdit.status, caseEdit.responsibleId ? Number(caseEdit.responsibleId) : null)) setCaseEditTarget(null);
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
  const saveEditedNote = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (customerId === undefined || !editingNote || mutation) return;
    if (!editingNote.note.trim()) { setNoteFeedback({ tone: "danger", title: "La nota no puede estar vacía" }); return; }
    setMutation("note"); setNoteFeedback(null);
    try { await updateClientNote(customerId, editingNote.id, editingNote.note.trim()); await refresh(); setEditingNote(null); setNoteFeedback({ tone: "success", title: "Nota actualizada" }); }
    catch (error) { setNoteFeedback({ tone: "danger", ...safeError(error, "nota") }); }
    finally { setMutation(null); }
  };
  const confirmDeleteNote = async () => {
    if (customerId === undefined || deletingNote === null || mutation) return;
    setMutation("note"); setNoteFeedback(null);
    try { await deleteClientNote(customerId, deletingNote); await refresh(); setDeletingNote(null); setNoteFeedback({ tone: "success", title: "Nota eliminada" }); }
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
  const conversationColumns: Column<(typeof history.conversations)[number]>[] = [
    { key: "id", header: "Conversación", render: (row) => `#${row.id}` },
    { key: "state", header: "Estado", render: (row) => <Badge tone={CONVERSATION_TONES[row.state] ?? "neutral"}><Bot aria-hidden="true" />{conversationLabel(row.state)}</Badge> },
    { key: "summary", header: "Resumen", render: (row) => row.summary ? plainSummary(row.summary) : "—" },
    { key: "created", header: "Creada", render: (row) => formatIdentityDate(row.created_at) },
  ];
  const caseColumns: Column<(typeof history.cases)[number]>[] = [
    { key: "id", header: "#", render: (row) => `#${row.id}` },
    { key: "service", header: "Servicio", render: (row) => row.service },
    { key: "priority", header: "Prioridad", render: (row) => row.priority },
    { key: "status", header: "Estado", render: (row) => <Badge tone={caseStatusTone(row.status)}>{caseStatusLabel(row.status)}</Badge> },
    { key: "amount", header: "Monto CLP", render: (row) => row.amount === null ? "Sin monto registrado" : CLP_FORMAT.format(row.amount) },
    { key: "summary", header: "Resumen", render: (row) => row.summary ? plainSummary(row.summary) : "—" },
  ];
  const archivedCaseColumns: Column<FichaCase>[] = [
    { key: "id", header: "#", render: (row) => `#${row.id}` },
    { key: "service", header: "Servicio", render: (row) => row.service },
    { key: "priority", header: "Prioridad", render: (row) => row.priority ? <Badge tone="warning">{priorityLabel(row.priority)}</Badge> : "—" },
    { key: "status", header: "Estado", render: (row) => <Badge tone={caseStatusTone(row.status)}>{caseStatusLabel(row.status)}</Badge> },
    { key: "responsible", header: "Responsable", render: (row) => data.users.find((user) => user.id === row.responsible_id)?.username ?? "Sin asignar" },
    { key: "amount", header: "Monto CLP", render: (row) => row.amount === null ? "Sin registrar" : CLP_FORMAT.format(row.amount) },
  ];
  const messageColumns: Column<(typeof history.messages)[number]>[] = [
    { key: "conversation", header: "Conversación", render: (row) => <a className="table__link" href={pathForRoute({ view: "conversations", conversationId: row.conversation_id })}>#{row.conversation_id}</a> },
    { key: "id", header: "Turno", render: (row) => messageTurns.get(row.id) ?? 1 },
    { key: "direction", header: "Dirección", render: (row) => <Badge tone={row.direction === "inbound" ? "success" : "neutral"}>{row.direction === "inbound" ? <ArrowDownLeft aria-hidden="true" /> : <ArrowUpRight aria-hidden="true" />}{directionLabel(row.direction)}</Badge> },
    { key: "msg_type", header: "Tipo", render: (row) => messageTypeLabel(row.msg_type) },
    { key: "text", header: "Mensaje", render: (row) => `${row.text ?? "—"}${row.media_url ? " 📎" : ""}` },
    { key: "created", header: "Fecha", render: (row) => messageWhen(row.created_at) },
  ];
  const activeCaseBody = activeCase ? <>
    <div className="client-ficha__case-eyebrow"><span className="client-ficha__status-dot"/> CASO ACTIVO <span>#{activeCase.id}</span><Menu trigger="icon" label="Acciones del caso" items={[{ value: "edit", label: "Editar caso", icon: BriefcaseBusiness }, { value: "amount", label: "Definir monto", icon: CircleDollarSign }]} onSelect={(value) => value === "amount" ? openAmountEditor(activeCase) : openCaseEditor(activeCase)} /></div>
    <h2 className="client-ficha__case-title">{activeCase.service}</h2><div className="client-ficha__case-badges"><Badge tone={caseStatusTone(activeCase.status)}>{caseStatusLabel(activeCase.status)}</Badge><Badge tone="warning">Prioridad {activeCase.priority}</Badge></div><div className="client-ficha__case-summary"><ConversationSummary summary={activeCase.summary ?? "—"} fallback={<Markdown content={activeCase.summary ?? "—"} />} /></div>
    <div className="client-ficha__case-details"><div><small>Responsable</small><strong><Avatar name={data.users.find((user) => user.id === activeCase.responsible_id)?.username ?? "Sin asignar"} /> {data.users.find((user) => user.id === activeCase.responsible_id)?.username ?? "Sin asignar"}</strong></div><div><small>Monto del servicio</small><strong>{activeCase.amount === null ? "Sin registrar" : CLP_FORMAT.format(activeCase.amount)}</strong></div></div>
    {activeCase.emergency ? <Badge tone={activeCase.ack_by === null ? "danger" : "warning"}>{activeCase.ack_by === null ? "Emergencia sin reconocer" : `Emergencia reconocida por ${activeCase.ack_by}`}</Badge> : null}<LocalFeedback feedback={caseEditTarget || amountTarget ? null : caseFeedback} />
  </> : <EmptyState title="Sin caso activo" />;
  const archivedCaseMenu = (row: FichaCase) => (
    <Menu trigger="icon" label={`Acciones del caso #${row.id}`} items={[{ value: "edit", label: "Editar caso", icon: BriefcaseBusiness }, { value: "amount", label: "Definir monto", icon: CircleDollarSign }]} onSelect={(value) => value === "amount" ? openAmountEditor(row) : openCaseEditor(row)} />
  );
  const customerDataCard = (
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
      </div></header>
      <dl className="detail-region__facts client-ficha__contact-facts">
        <div><dt>Teléfono</dt><dd>{customer.phone_e164 ?? "—"}<CopyButton value={customer.phone_e164 ?? ""} label="Copiar teléfono" /></dd></div>
        <div><dt>Correo</dt><dd>{customer.email ?? "—"}<CopyButton value={customer.email ?? ""} label="Copiar correo" /></dd></div>
        <div><dt>Dirección</dt><dd>{customer.address ?? "—"}{customer.comuna ? <><br/>{customer.comuna}</> : null}<CopyButton value={[customer.address, customer.comuna].filter(Boolean).join(", ")} label="Copiar dirección" /></dd></div>
        <div className="client-ficha__customer-state"><dt>Estado del cliente</dt><dd><Badge tone={customerStateTone(customer.state)}>{customerStateLabel(customer.state)}</Badge></dd></div>
        <div><dt>Consentimiento</dt><dd>{customer.consent_status ? "Sí" : "No"}</dd></div>
      </dl>
      <div className="client-ficha__local-feedback">
        <LocalFeedback feedback={consentDialogOpen ? null : consentFeedback} />
        <LocalFeedback feedback={stateDialogOpen ? null : stateFeedback} />
        {profileOpen ? null : <LocalFeedback feedback={profileFeedback} />}
        {archiveOpen ? null : <LocalFeedback feedback={archiveFeedback} />}
      </div>
    </Card>
  );
  const customerDialogs = <>
    <ChangeCustomerStateDialog open={stateDialogOpen} onClose={() => setStateDialogOpen(false)} customer={customer} subtitle={`Cliente desde el ${formatIdentityDate(customer.created_at)}`} selectedState={selectedState} onSelect={setSelectedState} onSave={() => void saveState()} busy={mutation !== null || customerId === undefined || selectedState === customer.state} feedback={<LocalFeedback feedback={stateFeedback} />} />
    <Dialog open={consentDialogOpen} onClose={() => setConsentDialogOpen(false)} title="Cambiar consentimiento" icon={ShieldCheck} description="Registra la elección expresada por el cliente.">
      <div className="client-ficha-dialog">
        <div className="client-ficha-dialog__context"><Avatar name={customer.name ?? customer.phone_e164 ?? "Cliente"} /><div><strong>{customer.name ?? customer.phone_e164 ?? "Cliente"}</strong><span>Cliente desde el {formatIdentityDate(customer.created_at)}</span></div><div className="client-ficha-dialog__current"><span>Consentimiento actual</span><Badge tone={customer.consent_status ? "success" : "neutral"}>{customer.consent_status ? "Sí" : "No"}</Badge></div></div>
        <div className="client-ficha-dialog__options"><strong>Nuevo consentimiento</strong><div role="radiogroup" aria-label="Nuevo consentimiento">{[[true, "Sí", "El cliente acepta ser contactado por la tarde."], [false, "No", "El cliente prefiere no ser contactado."]].map(([value, label, detail]) => <Button key={String(value)} type="button" role="radio" aria-checked={selectedConsent === value} variant="secondary" className={selectedConsent === value ? "client-ficha-dialog__option is-selected" : "client-ficha-dialog__option"} disabled={customerMutation !== null} onClick={() => setSelectedConsent(value as boolean)}><span className="client-ficha-dialog__option-copy"><strong>{label}</strong><span>{detail}</span></span><span className="client-ficha-dialog__radio" aria-hidden="true" /></Button>)}</div></div>
        <LocalFeedback feedback={consentFeedback} />
        <footer><Button variant="secondary" onClick={() => setConsentDialogOpen(false)}>Cancelar</Button><Button disabled={customerMutation !== null || customerId === undefined || selectedConsent === null} onClick={() => void saveConsent()}>{customerMutation === "consent" ? "Guardando…" : "Guardar consentimiento"}</Button></footer>
      </div>
    </Dialog>
    <Dialog open={profileOpen} onClose={() => setProfileOpen(false)} title="Editar datos del cliente" icon={UserRound} description="Actualiza su información de contacto.">
      <form className="client-ficha-dialog client-ficha-dialog__profile-form" onSubmit={(event) => void saveProfile(event)}>
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
    <Dialog open={mergeOpen} onClose={() => setMergeOpen(false)} title="Fusionar clientes" icon={ArrowLeftRight} description="Revisa las fichas antes de confirmar.">
      <div className="client-ficha-dialog client-ficha-dialog__merge">
        <div className="client-ficha-dialog__merge-current"><strong>Cliente actual</strong><div><Avatar name={customer.name ?? customer.phone_e164 ?? "Cliente"} /><span><b>{customer.name ?? customer.phone_e164 ?? "Cliente"}</b><small>Cliente desde el {formatIdentityDate(customer.created_at)}</small></span><span className="client-ficha-dialog__merge-phone"><Phone />{customer.phone_e164 ?? "—"}</span></div></div>
        <Combobox id="merge-other-client" label="Otro cliente" placeholder="Buscar por nombre o teléfono…" value={mergeOtherId || null} onChange={(value) => void selectMergeClient(value)} options={mergeClients.map((client) => ({ value: String(client.id), label: `${client.name ?? "Sin nombre"} · ${client.phone_e164 ?? "Sin teléfono"}` }))} />
        <div className="client-ficha-dialog__merge-cards"><section>{mergePreview ? <strong>{mergePreview.survivor_id === fichaCustomerId ? "Se conserva" : "Se fusiona"}</strong> : <strong>Ficha actual</strong>}<div><Avatar name={customer.name ?? customer.phone_e164 ?? "Cliente"} /><span><b>{customer.name ?? customer.phone_e164 ?? "Cliente"}</b><small>{customer.phone_e164 ?? "—"}</small></span></div></section><section>{mergePreview ? <strong>{mergePreview.survivor_id === Number(mergeOtherId) ? "Se conserva" : "Se fusiona"}</strong> : <strong>Otra ficha</strong>}<div><Avatar name={mergeClients.find((client) => String(client.id) === mergeOtherId)?.name ?? "Sin seleccionar"} /><span><b>{mergeClients.find((client) => String(client.id) === mergeOtherId)?.name ?? "Sin seleccionar"}</b><small>{mergeClients.find((client) => String(client.id) === mergeOtherId)?.phone_e164 ?? "—"}</small></span></div></section></div>
        <p className="client-ficha-dialog__warning"><CircleAlert aria-hidden="true" />Comprueba que ambas fichas correspondan a la misma persona.</p>
        {mergePreview ? <p className="client-ficha-dialog__merge-preview">Vista previa: se moverán {Object.entries(mergePreview.moved).map(([table, count]) => `${MERGE_COUNT_LABELS[table as keyof ClientMergePreview["moved"]]}: ${count}`).join(" · ")}; {mergePreview.memory_conflicts} conflictos de memoria{mergePreview.scalar_conflicts.length ? `; se conservan los datos del cliente superviviente en ${mergePreview.scalar_conflicts.join(", ")}` : ""}.</p> : null}
        <LocalFeedback feedback={mergeFeedback} />
        <footer><Button variant="secondary" onClick={() => setMergeOpen(false)}>Cancelar</Button><Button variant="danger" disabled={!mergePreview || mergeLoading} onClick={() => void confirmMerge()}>{mergeLoading ? "Fusionando…" : "Confirmar fusión"}</Button></footer>
      </div>
    </Dialog>
    <Dialog open={caseEditTarget !== null} onClose={() => setCaseEditTarget(null)} title="Editar caso" icon={BriefcaseBusiness} description="Actualiza el estado y el responsable.">
      {caseEditTarget ? <div className="client-ficha-dialog client-ficha-dialog__case-edit">
        <div className="client-ficha-dialog__case-context"><Avatar name={customer.name ?? customer.phone_e164 ?? "Cliente"}/><div><strong>{customer.name ?? customer.phone_e164 ?? "Cliente"}</strong><span>#{caseEditTarget.id} · {caseEditTarget.service}</span></div></div>
        <Select label="Estado" value={caseEdit.status} onChange={(event) => setCaseEdit({ ...caseEdit, status: event.target.value })} options={[{value:"abierto",label:"Abierto"},{value:"en_evaluacion",label:"En evaluación"},{value:"escalado",label:"Escalado"},{value:"cerrado",label:"Cerrado"}]}/>
        <Select label="Responsable" value={caseEdit.responsibleId} onChange={(event) => setCaseEdit({ ...caseEdit, responsibleId: event.target.value })} options={[{value:"",label:"Sin asignar"},...data.users.map((user) => ({value:String(user.id),label:user.username}))]}/>
        <LocalFeedback feedback={caseFeedback}/><footer><Button variant="secondary" onClick={() => setCaseEditTarget(null)}>Cancelar</Button>{caseEditTarget.emergency && caseEditTarget.ack_by === null ? <Button variant="secondary" onClick={() => void acknowledgeCase(caseEditTarget.id)}>Reconocer</Button> : null}<Button onClick={() => void saveCaseEdit()}>Guardar cambios</Button></footer>
      </div> : null}
    </Dialog>
    <Dialog open={amountTarget !== null} onClose={() => setAmountTarget(null)} title="Definir monto del caso" icon={CircleDollarSign} description="Registra el monto del servicio asociado al caso.">
      <form className="client-ficha-dialog client-ficha-dialog__amount-form" onSubmit={(event) => void saveCaseAmount(event)}>
        {amountTarget ? <div className="client-ficha-dialog__case-context"><Avatar name={customer.name ?? customer.phone_e164 ?? "Cliente"}/><div><strong>{customer.name ?? customer.phone_e164 ?? "Cliente"}</strong><span>#{amountTarget.id} · {amountTarget.service}</span></div><div className="client-ficha-dialog__current"><span>Monto actual:</span><strong>{amountTarget.amount === null ? "Sin registrar" : CLP_FORMAT.format(amountTarget.amount)}</strong></div></div> : null}
        <div className="client-ficha-dialog__amount-field"><label htmlFor="case-amount">Monto del servicio</label><div className="client-ficha-dialog__amount"><span aria-hidden="true">$</span><input id="case-amount" type="number" min="0" step="1" value={amountInput} placeholder="0" onChange={(event) => setAmountInput(event.target.value)} /><span aria-hidden="true">CLP</span></div><p className="client-ficha-dialog__helper">Ingresa el monto en pesos chilenos.</p></div>
        <LocalFeedback feedback={caseFeedback} />
        <footer><Button type="button" variant="secondary" onClick={() => setAmountTarget(null)}>Cancelar</Button><Button type="submit" disabled={amountMutation}>{amountMutation ? "Guardando…" : "Guardar monto"}</Button></footer>
      </form>
    </Dialog>
  </>;

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
          {customerDataCard}
        </section>

        <div className="detail-region__main">
          <div className="client-ficha__summary-column client-ficha__summary-column--left">
          <ClientMemories memories={memories} pendingRelations={pendingRelations} onResolveRelation={resolveRelation} compact conversationId={history.conversations[0]?.id} onViewAll={() => setMemoriesOpen(true)} />
          <Dialog open={memoriesOpen} onClose={() => setMemoriesOpen(false)} title="Memorias del cliente" icon={MessageSquare} size="wide">
            {memoriesOpen ? <div className="client-ficha__memories-dialog"><ClientMemories bare memories={memories} pendingRelations={pendingRelations} onResolveRelation={resolveRelation} /></div> : null}
          </Dialog>
          <Card className="client-ficha__notes-card">
            <header className="client-ficha__card-heading"><h2>Notas</h2><Button variant="secondary" aria-expanded={noteComposerOpen} disabled={customerId === undefined || mutation !== null} onClick={() => setNoteComposerOpen(true)}>⊕ Agregar nota</Button></header>
            {data.notes.length ? data.notes.map((entry) => <article className="client-ficha__note-row" key={entry.id}><Avatar name={entry.author ?? "Operador"}/><div><strong>{entry.author ?? "—"}</strong><small>{formatDate(entry.created_at)}</small></div><p>{entry.note}</p><span className="client-ficha__note-actions"><Menu trigger="icon" label="Acciones de nota" items={[{value:"edit",label:"Editar",icon:Pencil},{value:"delete",label:"Eliminar",icon:Trash2,tone:"danger"},{value:"copy",label:"Copiar nota",icon:Copy}]} onSelect={(value)=>{ if(value==="copy") { void navigator.clipboard?.writeText(entry.note); setCopiedNoteId(entry.id); window.setTimeout(() => setCopiedNoteId((current) => current === entry.id ? null : current), 1500); } if(value==="edit") { setEditingNote({ id: entry.id, note: entry.note }); setNoteFeedback(null); } if(value==="delete") { setDeletingNote(entry.id); setNoteFeedback(null); } }}/>{copiedNoteId === entry.id ? <span className="client-ficha__copy-hint" role="status">Copiado</span> : null}</span></article>) : <EmptyState title="No hay notas" />}
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
          <Dialog open={editingNote !== null} onClose={() => setEditingNote(null)} title="Editar nota" icon={NotebookPen} description="Actualiza la nota asociada al cliente.">
            {editingNote ? <form className="client-ficha-dialog" onSubmit={(event) => void saveEditedNote(event)}>
              <div className="client-ficha-dialog__context"><Avatar name={customer.name ?? customer.phone_e164 ?? "Cliente"}/><div><strong>{customer.name ?? customer.phone_e164 ?? "Cliente"}</strong><span>Cliente desde el {formatIdentityDate(customer.created_at)}</span></div><span className="client-ficha-dialog__context-phone"><Phone aria-hidden="true"/>{customer.phone_e164 ?? "—"}</span></div>
              <Textarea id="edit-note" label="Nota" value={editingNote.note} disabled={mutation !== null || customerId === undefined} onChange={(event) => setEditingNote({ ...editingNote, note: event.target.value })} />
              <LocalFeedback feedback={editingNote ? noteFeedback : null} />
              <footer><Button type="button" variant="secondary" onClick={() => setEditingNote(null)}>Cancelar</Button><Button type="submit" disabled={mutation !== null || customerId === undefined}>{mutation === "note" ? "Guardando…" : "Guardar cambios"}</Button></footer>
            </form> : null}
          </Dialog>
          <Dialog open={deletingNote !== null} onClose={() => setDeletingNote(null)} title="Eliminar nota" icon={Trash2} description="Esta acción no se puede deshacer.">
            <div className="client-ficha-dialog"><div className="client-ficha-dialog__context"><Avatar name={customer.name ?? customer.phone_e164 ?? "Cliente"}/><div><strong>{customer.name ?? customer.phone_e164 ?? "Cliente"}</strong><span>Cliente desde el {formatIdentityDate(customer.created_at)}</span></div></div><LocalFeedback feedback={deletingNote !== null ? noteFeedback : null}/><footer><Button variant="secondary" onClick={() => setDeletingNote(null)}>Cancelar</Button><Button variant="danger" disabled={mutation !== null || customerId === undefined} onClick={() => void confirmDeleteNote()}>{mutation === "note" ? "Eliminando…" : "Eliminar nota"}</Button></footer></div>
          </Dialog>
          <Card className="client-ficha__upcoming-card">
            <header className="client-ficha__card-heading"><h2>Próximas visitas</h2><Button variant="secondary" onClick={() => { window.location.href = pathForRoute({ view: "agenda" }); }}>Ver agenda →</Button></header>
            {upcomingAppointments.length ? <ul className="client-ficha__visits">{upcomingAppointments.map((appointment) => { const date = new Date(appointment.starts_at); return <li key={appointment.id}><a className="client-ficha__upcoming-row" href={pathForRoute({ view: "agenda", appointmentId: appointment.id })}><span className="client-ficha__date-tile"><strong>{date.getDate().toString().padStart(2, "0")}</strong><small>{new Intl.DateTimeFormat("es-CL", { month: "short" }).format(date).replace(".", "").toUpperCase()}</small></span><span>{appointment.service}</span><span><Clock3/>{new Intl.DateTimeFormat("es-CL",{hour:"2-digit",minute:"2-digit"}).format(date)}</span><Badge tone={appointmentStatusTone(appointment.status)}>{appointmentStatusLabel(appointment.status)}</Badge></a></li>; })}</ul> : <EmptyState title="No hay próximas visitas" />}
          </Card>
          </div>
          <div className="client-ficha__summary-column client-ficha__summary-column--right">
          <Card className="client-ficha__case-card">
            {activeCaseBody}
          </Card>
          <section aria-label="Equipos" className="client-ficha__equipment-slot">
             <Card className="client-ficha__equipment-card">
               <header className="client-ficha__card-heading"><h2>Equipos</h2><Button variant="secondary" disabled={customerId === undefined || equipmentMutation} onClick={() => openEquipment()}>＋ Agregar equipo</Button></header>
              {equipmentData.state === "loading" ? <p role="status">Cargando equipos…</p> : null}
              {equipmentData.state === "error" || equipmentData.state === "denied" ? <StateMessage tone="danger" role="alert" title="No pudimos cargar los equipos" /> : null}
              {equipmentRows.length ? <ul className="client-ficha__equipment-list">
                 {equipmentRows.map((entry) => <li className="client-ficha__equipment-row" key={entry.id}>
                   <div className="client-ficha__equipment-eyebrow">{entry.equipment_type ? <Badge>{EQUIPMENT_TYPE_LABELS[entry.equipment_type] ?? entry.equipment_type}</Badge> : <span>Sin especificar</span>}</div>
                   <strong>{[entry.brand, entry.model, entry.age].filter(Boolean).join(" · ") || "Sin datos estructurados"}</strong>
                   {entry.details ? <p>{entry.details}</p> : null}
                   <Button variant="secondary" disabled={equipmentMutation} onClick={() => openEquipment(entry)}>Editar equipo</Button>
                 </li>)}
               </ul> : equipmentData.state === "empty" || equipmentData.state === "ready" ? <div className="client-ficha__equipment-empty"><Thermometer aria-hidden="true" /><strong>Sin equipos registrados</strong><Button variant="secondary" disabled={customerId === undefined || equipmentMutation} onClick={() => openEquipment()}>Agregar equipo</Button></div> : null}
              {equipmentOpen ? null : <LocalFeedback feedback={equipmentFeedback} />}
            </Card>
          </section>
          <Dialog open={equipmentOpen} onClose={() => setEquipmentOpen(false)} title={editingEquipment ? "Editar equipo" : "Agregar equipo"} icon={Smartphone} description="Registra un equipo asociado al cliente.">
            <form className="client-ficha-dialog" onSubmit={(event) => void saveEquipment(event)}>
              <Input id="equipment-type" label="Tipo de equipo" placeholder="Ej. Calefont" value={equipmentForm.equipment_type ?? ""} onChange={(event) => setEquipmentForm({ ...equipmentForm, equipment_type: event.target.value })} />
              <Input label="Marca (opcional)" placeholder="Ej. Marca del equipo" value={equipmentForm.brand ?? ""} onChange={(event) => setEquipmentForm({ ...equipmentForm, brand: event.target.value })} />
              <Input label="Modelo (opcional)" placeholder="Modelo del equipo" value={equipmentForm.model ?? ""} onChange={(event) => setEquipmentForm({ ...equipmentForm, model: event.target.value })} />
              <LocalFeedback feedback={equipmentFeedback} />
              <footer><Button type="button" variant="secondary" onClick={() => setEquipmentOpen(false)}>Cancelar</Button><Button type="submit" disabled={equipmentMutation}>{equipmentMutation ? "Guardando…" : editingEquipment ? "Guardar equipo" : "Agregar equipo"}</Button></footer>
            </form>
          </Dialog>

          <button type="button" className="client-ficha__history-entry" onClick={() => setHistoryOpen(true)}>
            <Clock3 aria-hidden="true"/><span><strong>Historial del cliente</strong><small>Visitas, conversaciones y casos anteriores</small></span><ChevronRight aria-hidden="true" />
          </button>
          </div>
        </div>
      </div>
      </> : null}
        {activeTab === "cases" ? <div className="detail-region detail-region--cases">
          <Card className="client-ficha__case-card client-ficha__case-card--primary" title="Caso activo"><div className="client-ficha__case-panel">{activeCaseBody}</div></Card>
          {customerDataCard}
          <section aria-label="Casos anteriores" className="client-ficha__history-block client-ficha__archived-cases"><Card title="Casos anteriores">
            {archivedCases.length ? <>
              <div className="data-region table-card__desktop"><DataTable columns={archivedCaseColumns} rows={visibleArchivedCases} actions={archivedCaseMenu} rowKey={(row) => String(row.id)} /></div>
              <ul className="table-cards table-cards--mobile client-ficha__archived-cards" aria-label="Lista de casos anteriores">
                {visibleArchivedCases.map((row) => <li className="table-card__item client-ficha__archived-card" key={row.id}>
                  <div className="client-ficha__archived-card-head"><strong>#{row.id}</strong><span>{row.service}</span>{archivedCaseMenu(row)}</div>
                  <div className="client-ficha__archived-card-badges">{row.priority ? <Badge tone="warning">{priorityLabel(row.priority)}</Badge> : null}<Badge tone={caseStatusTone(row.status)}>{caseStatusLabel(row.status)}</Badge></div>
                  <div className="client-ficha__archived-card-facts"><div><small>Responsable</small><strong>{data.users.find((user) => user.id === row.responsible_id)?.username ?? "Sin asignar"}</strong></div><div><small>Monto CLP</small><strong>{row.amount === null ? "Sin registrar" : CLP_FORMAT.format(row.amount)}</strong></div></div>
                </li>)}
              </ul>
            </> : <EmptyState title="No hay casos anteriores" />}
            <footer className="table-footer"><span className="table-footer__count">Mostrando {archivedRangeStart}–{archivedRangeEnd} de {archivedCases.length} casos anteriores</span>{archivedCasePageCount > 1 ? <Pagination page={currentArchivedCasePage} pageCount={archivedCasePageCount} onPageChange={setArchivedCasePage} ariaLabel="Paginación de casos anteriores" /> : null}</footer>
          </Card></section>
        </div> : null}
      {activeTab === "visits" ? <div className="detail-region__main">
        <section aria-label="Próximas visitas" className="client-ficha__history-block"><Card title="Próximas visitas" description="Visitas pendientes de este cliente.">{upcomingAppointments.length ? <>
          <div className="data-region table-card__desktop"><DataTable columns={VISIT_COLUMNS} rows={upcomingAppointments} actions={visitRowMenu} rowKey={(row)=>String(row.id)}/></div>
          <ul className="table-cards table-cards--mobile client-ficha__visit-cards" aria-label="Lista de próximas visitas">
            {upcomingAppointments.map((row) => <li className="table-card__item client-ficha__visit-card" key={row.id}><div className="client-ficha__visit-card-main">{visitWhenCell(row)}{visitServiceCell(row)}<Badge tone={appointmentStatusTone(row.status)}>{appointmentStatusLabel(row.status)}</Badge></div><div className="client-ficha__visit-card-actions">{visitRowMenu(row)}</div></li>)}
          </ul>
        </> : <EmptyState title="No hay próximas visitas"/>}</Card><Card title="Historial de visitas">{finishedAppointments.length ? <>
          <div className="table-card__desktop"><DataTable columns={VISIT_COLUMNS} rows={finishedAppointments} rowKey={(row)=>String(row.id)} /></div>
          <ul className="table-cards table-cards--mobile client-ficha__visit-cards" aria-label="Lista del historial de visitas">
            {finishedAppointments.map((row) => <li className="table-card__item client-ficha__visit-card" key={row.id}><div className="client-ficha__visit-card-main">{visitWhenCell(row)}{visitServiceCell(row)}<Badge tone={appointmentStatusTone(row.status)}>{appointmentStatusLabel(row.status)}</Badge></div></li>)}
          </ul>
        </> : <EmptyState title="No hay visitas en el historial" />}</Card>{appointments.some((appointment)=>appointment.calendar_error) ? appointments.filter((appointment)=>appointment.calendar_error).map((appointment)=><div key={appointment.id}><StateMessage tone="danger" role="alert" title="No se pudo sincronizar el calendario" detail={`${appointment.calendar_error} Reintenta la sincronización.`}/><Button variant="secondary" disabled={retryingCalendarId===appointment.id} onClick={()=>void retryCalendar(appointment.id)}>Reintentar calendario</Button></div>):null}</section>
      </div> : null}
      {activeTab === "conversations" ? <div className="detail-region__main">
        <section aria-label="Conversaciones" className="client-ficha__history-block"><Card title="Conversaciones del cliente">
          {history.conversations.length ? <>
            <div className={surfaceClass(history.conversations.length)}><div className="table-card__desktop client-ficha__conversations-table"><DataTable columns={[...conversationColumns,{key:"actions",header:"Acciones",render:(row)=><Button variant="secondary" onClick={()=>{window.location.href=pathForRoute({view:"conversations",conversationId:row.id})}}>Abrir conversación</Button>}] as Column<(typeof history.conversations)[number]>[]} rows={history.conversations} rowKey={(row) => String(row.id)} /></div></div>
            <ul className="table-cards table-cards--mobile client-ficha__conversation-cards" aria-label="Lista de conversaciones">
              {history.conversations.map((row) => <li className="table-card__item client-ficha__conversation-card" key={row.id}>
                <div className="client-ficha__conversation-card-head"><strong>#{row.id}</strong><Badge tone={CONVERSATION_TONES[row.state] ?? "neutral"}><Bot aria-hidden="true" />{conversationLabel(row.state)}</Badge></div>
                {row.summary ? <p>{plainSummary(row.summary)}</p> : null}
                <div className="client-ficha__conversation-card-foot"><span>{formatIdentityDate(row.created_at)}</span><Button variant="secondary" onClick={() => { window.location.href = pathForRoute({ view: "conversations", conversationId: row.id }); }}>Abrir conversación</Button></div>
              </li>)}
            </ul>
          </> : <EmptyState title="No hay conversaciones" />}
        </Card></section>
        <section aria-label="Mensajes" className="client-ficha__history-block"><Card title={`Mensajes de la conversación #${activeConversationId ?? "—"}`} description="Historial de mensajes del hilo seleccionado.">
          {history.conversations.length > 1 ? <div className="client-ficha__messages-toolbar"><Select label="Conversación" value={activeConversationId === null ? "" : String(activeConversationId)} options={history.conversations.map((row) => ({ value: String(row.id), label: `#${row.id} · ${conversationLabel(row.state)}${row.summary ? ` · ${plainSummary(row.summary)}` : ""}` }))} onChange={(event) => setSelectedConversationId(Number(event.target.value))} /></div> : null}
          {conversationMessages.length ? <>
            <div className={surfaceClass(conversationMessages.length)}><div className="table-card__desktop client-ficha__messages-table"><DataTable columns={messageColumns} rows={conversationMessages} rowKey={(row) => String(row.id)} /></div></div>
            <ul className="table-cards table-cards--mobile client-ficha__message-cards" aria-label="Lista de mensajes">
              {conversationMessages.map((row) => <li className="table-card__item client-ficha__message-card" key={row.id}>
                <div className="client-ficha__message-card-head"><Badge tone={row.direction === "inbound" ? "success" : "neutral"}>{row.direction === "inbound" ? <ArrowDownLeft aria-hidden="true" /> : <ArrowUpRight aria-hidden="true" />}{directionLabel(row.direction)}</Badge><span>{messageWhen(row.created_at)}</span></div>
                <p>{row.text ?? "—"}{row.media_url ? " 📎" : ""}</p>
                <small>Turno {messageTurns.get(row.id) ?? 1} · {messageTypeLabel(row.msg_type)}</small>
              </li>)}
            </ul>
          </> : <EmptyState title="No hay mensajes" />}
          <p>Mostrando {conversationMessages.length} mensaje{conversationMessages.length === 1 ? "" : "s"}{conversationTotal > conversationMessages.length ? ` de ${conversationTotal}` : ""}</p>
        </Card></section>
      </div> : null}
        </>}
      </Tabs>
      {customerDialogs}
      <Dialog open={visitCancelTarget !== null} onClose={() => { if (!visitMutation) setVisitCancelTarget(null); }} title="Cancelar visita" icon={CalendarX} description="Indica el motivo de la cancelación de esta visita.">
        {visitCancelTarget ? <div className="client-ficha-dialog">
          <div className="client-ficha-dialog__context"><Avatar name={customer.name ?? customer.phone_e164 ?? "Cliente"} /><div><strong>{customer.name ?? customer.phone_e164 ?? "Cliente"}</strong><span>{formatIdentityDate(visitCancelTarget.starts_at)} · {TIME_FORMAT.format(new Date(visitCancelTarget.starts_at))}</span></div></div>
          <Textarea id="visit-cancel-reason" label="Motivo de cancelación" value={visitCancelReason} disabled={visitMutation} onChange={(event) => setVisitCancelReason(event.target.value)} />
          <LocalFeedback feedback={visitFeedback} />
          <footer><Button variant="secondary" disabled={visitMutation} onClick={() => setVisitCancelTarget(null)}>Cancelar</Button><Button variant="danger" disabled={visitMutation} onClick={() => void cancelVisit()}>{visitMutation ? "Cancelando…" : "Confirmar cancelación"}</Button></footer>
        </div> : null}
      </Dialog>
      {visitCloseTarget ? <AppointmentClosureDialog open={visitCloseTarget !== null} onClose={() => setVisitCloseTarget(null)} customerName={customer.name ?? customer.phone_e164 ?? "Cliente"} appointmentDateTime={visitCloseTarget.starts_at} dateTimeLabel={`${formatIdentityDate(visitCloseTarget.starts_at)} · ${TIME_FORMAT.format(new Date(visitCloseTarget.starts_at))}`} outcome={visitCloseOutcome} onOutcomeChange={setVisitCloseOutcome} onSubmit={() => void closeVisit()} mutating={visitMutation} feedback={visitFeedback} /> : null}
      <Dialog open={historyOpen} onClose={() => setHistoryOpen(false)} title="Historial del cliente" icon={Clock3} description="Visitas, conversaciones y casos anteriores" size="wide">
        <div className="client-ficha__history-dialog">
          <Card title="Casos anteriores"><div className="client-ficha__history-table"><DataTable columns={caseColumns} rows={archivedCases} rowKey={(row) => String(row.id)} /></div></Card>
          <Card title="Visitas"><div className="client-ficha__history-table"><DataTable columns={[{key:"service",header:"Servicio",render:(row: Appointment)=>row.service},{key:"date",header:"Fecha",render:(row: Appointment)=>formatDateTime(row.starts_at)},{key:"status",header:"Estado",render:(row: Appointment)=><Badge tone={appointmentStatusTone(row.status)}>{appointmentStatusLabel(row.status)}</Badge>}] as Column<Appointment>[]} rows={appointments} rowKey={(row)=>String(row.id)}/></div></Card>
          <Card title="Conversaciones"><div className="client-ficha__history-table"><DataTable columns={conversationColumns} rows={history.conversations} rowKey={(row)=>String(row.id)}/></div></Card>
        </div>
      </Dialog>
    </PageFrame>
  );
}
