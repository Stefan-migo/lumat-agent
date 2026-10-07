import { useCallback, useEffect, useState } from "react";
import { Bot, CircleCheck, Clock, Copy, Info, Lock, SendHorizonal, ShieldAlert, UserRound, UserRoundPlus, WifiOff } from "lucide-react";
import { ApiError, acknowledgeCase, changeConversationState, getConversation, listActiveConversations, listConversations, retryMessage, sendMessage } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { ConversationThread as ThreadData, Message } from "../../types";
import { Avatar } from "../primitives/Avatar";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { Dialog } from "../primitives/Dialog";
import { Icon } from "../primitives/Icon";
import { Menu, type MenuItem } from "../primitives/Menu";
import { StatusBadge } from "../primitives/StatusBadge";
import { Textarea } from "../primitives/Textarea";
import { EmptyState } from "../shared/EmptyState";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { CollapsibleMessages } from "../shared/CollapsibleMessages";
import { caseStatusLabel, caseStatusTone, conversationLabel } from "../shared/toneMaps";
import { pathForRoute } from "../domain/panelRoutes";
import { realtimeClient, type ConnectionStatus } from "../../realtime";
import "./ConversationThread.css";

export interface ConversationThreadProps { conversationId?: number; data?: ThreadData | null; state?: AsyncDataState | "stale"; customerName?: (id: number) => string; refreshKey?: number; onMutate?: () => void; onBack?: () => void; interactive?: boolean; }
export function NoReplyNote() { return <StateMessage tone="info" role="status" title="Canal automático" detail="Este es un canal automático — no respondas a este mensaje (HH-5)." />; }
function messageAuthor(message: Message, customerId: number, customerName?: (id: number) => string) {
  return message.direction === "inbound"
    ? customerName?.(customerId) ?? `Cliente #${customerId}`
    : "Lumat";
}

function MessageBubble({ message, customerId, customerName }: { message: Message; customerId: number; customerName?: (id: number) => string }) {
  const author = messageAuthor(message, customerId, customerName);
  const outbound = message.direction === "outbound";
  return <div className={`ai-agent-grammar__bubble-row${outbound ? " ai-agent-grammar__bubble-row--outbound" : ""}`} data-bubble aria-label={`Mensaje ${outbound ? "saliente" : "entrante"} de ${author}`}>
    {!outbound ? <Avatar name={author} className="conversation-thread__bubble-avatar" /> : null}
    <div className="ai-agent-grammar__bubble-stack">
      <span className="ai-agent-grammar__message-meta">{author}</span>
      <div className={`ai-agent-grammar__bubble${outbound ? " ai-agent-grammar__bubble--outbound" : ""}`}>
        <span>{message.text ?? "—"}{message.media_url ? " 📎" : null}</span>
        {message.delivery_status === "failed" ? <span className="ai-agent-grammar__message-error" role="alert">Entrega fallida{message.delivery_error ? `: ${message.delivery_error}` : ""}</span> : null}
      </div>
      <span className="ai-agent-grammar__message-time">{message.created_at?.slice(11, 16) ?? "—"}</span>
    </div>
    {outbound ? <Avatar name={author} className="conversation-thread__bubble-avatar" /> : null}
  </div>;
}

function displayCapturedValue(value: unknown) {
  return typeof value === "object" && value !== null ? JSON.stringify(value) : String(value ?? "—");
}
// Captured data is free-form and can carry internal markers (e.g. `_pending`); hide those and
// humanize the key so the operator never reads a raw snake_case identifier.
const CAPTURED_LABELS: Record<string, string> = { name: "Nombre", comuna: "Comuna", urgencia: "Urgencia informada", urgencia_informada: "Urgencia informada", tipo_equipo: "Tipo de equipo", direccion: "Dirección", telefono: "Teléfono" };
const capturedLabel = (key: string) => CAPTURED_LABELS[key] ?? key.replace(/_/g, " ").replace(/^./, (character) => character.toUpperCase());
const capturedEntries = (data: Record<string, unknown>) => Object.entries(data).filter(([key]) => !key.startsWith("_"));
// Activity rows are persisted with a technical vocabulary (`classified` + `intent:<intent>`,
// `kb_retrieved` + `chunks:<n>`, `escalation` + `handoff:<reason>` — see app/services/realtime.py).
// Translate them into operator-facing Spanish so the chip is not raw machine text.
const ACTIVITY_LABELS: Record<string, string> = { classified: "Intención detectada", kb_retrieved: "Se consultó la base de conocimiento", escalation: "Derivado a atención humana" };
const INTENT_LABELS: Record<string, string> = { calefont: "calefón", caldera: "caldera", calefaccion: "calefacción", solicitar_visita: "solicitar una visita", valores: "valores", postventa: "postventa", consulta: "consulta", unknown: "sin determinar" };
function activityText(activity: { event: string; cause?: string | null }) {
  const base = ACTIVITY_LABELS[activity.event] ?? activity.event;
  const cause = activity.cause ?? "";
  if (activity.event === "classified" && cause.startsWith("intent:")) return `${base}: ${INTENT_LABELS[cause.slice(7)] ?? cause.slice(7)}`;
  if (activity.event === "kb_retrieved" && cause.startsWith("chunks:")) return `${base} (${cause.slice(7)} resultados)`;
  return base;
}
const formatRecency = (value: string | null) => value ? new Intl.DateTimeFormat("es-CL", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)) : "—";
const formatInitiatedDate = (value: string | null | undefined) => value ? new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", year: "numeric" }).format(new Date(value)).replace(".", "") : "—";
const MESSAGE_PREVIEW = 10;
// Case priority arrives as either the API's English enum or the domain's Spanish value.
const PRIORITY_LABELS: Record<string, string> = { high: "Prioridad alta", alta: "Prioridad alta", medium: "Prioridad normal", media: "Prioridad normal", normal: "Prioridad normal", low: "Prioridad baja", baja: "Prioridad baja" };
const priorityLabel = (value: string) => PRIORITY_LABELS[value] ?? `Prioridad ${value}`;
const priorityTone = (value: string) => value === "high" || value === "alta" ? "warning" as const : "neutral" as const;

function ConversationContext({ conversation }: { conversation: NonNullable<ThreadData["conversation"]> }) {
  const customer = conversation.customer;
  const caseData = conversation.case;
  const phone = customer?.phone_e164 ?? conversation.wa_phone ?? null;
  const caseStatus = conversation.case_status ?? caseData?.status ?? null;
  const casePriority = conversation.case_priority ?? caseData?.priority ?? null;
  const captured = conversation.captured_data ?? {};
  const capturedRows = capturedEntries(captured);
  // The capture flow can leave location unanswered while the customer's ficha already knows it.
  // Fall back to the profile so the operator never sees an empty section for known data.
  const capturedKeys = new Set(Object.keys(captured).map((key) => key.toLowerCase()));
  const profileRows: Array<[string, string]> = [];
  if (customer?.comuna && !capturedKeys.has("comuna")) profileRows.push(["Comuna", customer.comuna]);
  if (customer?.address && !capturedKeys.has("direccion") && !capturedKeys.has("address")) profileRows.push(["Dirección", customer.address]);
  return <aside className="ai-agent-grammar__inspector" aria-label="Inspector de conversación">
      {customer ? <section className="conversation-context__section" aria-labelledby="conversation-customer-heading">
        <h2 id="conversation-customer-heading">Cliente</h2>
        <div className="conversation-context__customer">
          <Avatar name={customer.name ?? phone ?? "Cliente"} />
          <div className="conversation-context__customer-body">
            <strong>{customer.name ?? "Sin nombre"}</strong>
            <span className="conversation-context__phone">{phone ?? "Sin teléfono"}{phone ? <button type="button" className="conversation-context__copy" aria-label="Copiar teléfono" onClick={() => void navigator.clipboard?.writeText(phone)}><Copy aria-hidden="true" /></button> : null}</span>
          </div>
        </div>
      </section> : null}
      {caseData ? <section className="conversation-context__section" aria-labelledby="conversation-case-heading">
        <div className="conversation-context__case-head"><h2 id="conversation-case-heading">Caso vinculado</h2>{conversation.case_id != null ? <a className="conversation-context__case-link" href={pathForRoute({ view: "clients", clientId: conversation.customer_id, clientTab: "cases" })}>Ver caso <span aria-hidden="true">→</span></a> : null}</div>
        <p className="conversation-context__case-title">{caseData.service}</p>
        <div className="conversation-context__badges">{caseStatus ? <Badge tone={caseStatusTone(caseStatus)}>{caseStatusLabel(caseStatus)}</Badge> : null}{casePriority ? <Badge tone={priorityTone(casePriority)}>{priorityLabel(casePriority)}</Badge> : null}</div>
        {caseData.summary ? <p className="conversation-context__case-summary">{caseData.summary}</p> : null}
        <dl><div className="ai-agent-grammar__detail"><dt>Emergencia</dt><dd>{conversation.emergency ? "Sí" : "No"}</dd></div><div className="ai-agent-grammar__detail"><dt>Reconocimiento</dt><dd>{conversation.acknowledged_at ? "Reconocida" : "Pendiente"}</dd></div></dl>
      </section> : null}
      {capturedRows.length > 0 || profileRows.length > 0 ? <details open><summary>Datos capturados</summary><dl>{capturedRows.map(([key, value]) => <div className="ai-agent-grammar__detail" key={key}><dt>{capturedLabel(key)}</dt><dd>{displayCapturedValue(value)}</dd></div>)}{profileRows.map(([label, value]) => <div className="ai-agent-grammar__detail" key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl></details> : null}
  </aside>;
}
export function ConversationThread({ conversationId, data: controlledData, state: controlledState, customerName, refreshKey = 0, onMutate, onBack, interactive = false }: ConversationThreadProps) {
  const [text, setText] = useState("");
  const [messagesExpanded, setMessagesExpanded] = useState(false);
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [infoOpen, setInfoOpen] = useState(false);
  const [connection, setConnection] = useState<ConnectionStatus>("disconnected");
  const [liveActivity, setLiveActivity] = useState<Array<{ event: string; cause?: string | null; actor?: string | null }>>([]);
  const fetchThread = useCallback(async () => { if (conversationId === undefined) throw new Error("conversation id is required"); return getConversation(conversationId, messagesExpanded ? undefined : MESSAGE_PREVIEW); }, [conversationId, messagesExpanded, refreshKey]);
  const fetched = useAsyncData(fetchThread, controlledData === undefined, refreshKey);
  const data = controlledData ?? fetched.data;
  const state = controlledState ?? (controlledData !== undefined ? "ready" : fetched.state);
  const conversation = data?.conversation;
  const messages = data?.messages ?? [];
  const refresh = fetched.retry;
  const toggleMessages = () => { setMessagesExpanded((value) => !value); refresh(); };
  useEffect(() => {
    if (controlledData !== undefined || conversationId === undefined) return;
    const unsubscribe = realtimeClient.subscribe((event) => {
      if (event.type !== "snapshot" && event.conversation_id !== conversationId) return;
      if (event.type === "activity") setLiveActivity((current) => [...current, event.data as { event: string; cause?: string | null; actor?: string | null }]);
      if (event.type === "snapshot") {
        const activity = (event.data as { activity?: Array<{ conversation_id?: number; event: string; cause?: string | null; actor?: string | null }> }).activity ?? [];
        setLiveActivity(activity.filter((item) => item.conversation_id === conversationId));
      }
      if (event.type === "message" || event.type === "conversation" || event.type === "snapshot") refresh();
    });
    const unsubscribeStatus = realtimeClient.subscribeStatus(setConnection);
    const unregisterRecovery = realtimeClient.registerRecovery(async () => {
      await Promise.all([getConversation(conversationId), listConversations(), listActiveConversations()]);
      refresh();
    });
    realtimeClient.connect();
    return () => { unsubscribe(); unsubscribeStatus(); unregisterRecovery(); };
  }, [controlledData, conversationId, refresh]);
  const windowOpen = conversation?.reply_window_open === true;
  const mutate = async (action: () => Promise<unknown>) => { setBusy(true); setMutationError(null); try { await action(); setText(""); onMutate?.(); refresh(); } catch (error) { setMutationError(error instanceof ApiError ? `${error.status}: ${error.detail}` : "No se pudo completar la acción"); } finally { setBusy(false); } };
  const acknowledgesEmergency = Boolean(conversation?.case && conversation?.emergency && !conversation.acknowledged_at && conversation.case_id != null);
  const conversationMenuItems = (options: { includeTake?: boolean; includeInfo?: boolean } = {}): MenuItem[] => conversation ? [
    ...(options.includeInfo ? [{ value: "info", label: "Información del chat", icon: Info }] : []),
    ...(options.includeTake ? [{ value: "human", label: "Tomar conversación", icon: UserRoundPlus, disabled: busy || conversation.state === "human" }] : []),
    { value: "bot", label: "Devolver al agente", icon: Bot, disabled: busy || conversation.state !== "human" },
    { value: "closed", label: "Cerrar conversación", icon: CircleCheck, disabled: busy || conversation.state !== "human" },
    ...(acknowledgesEmergency ? [{ value: "acknowledge", label: "Reconocer emergencia", icon: ShieldAlert, disabled: busy }] : []),
  ] : [];
  const runMenuAction = (value: string) => {
    if (value === "info") { setInfoOpen(true); return; }
    if (!conversation) return;
    if (value === "human") void mutate(() => changeConversationState(conversation.id, "human", conversation.version ?? 0));
    else if (value === "bot") void mutate(() => changeConversationState(conversation.id, "bot", conversation.version ?? 0));
    else if (value === "closed") void mutate(() => changeConversationState(conversation.id, "closed", conversation.version ?? 0));
    else if (value === "acknowledge" && conversation.case_id != null) void mutate(() => acknowledgeCase(conversation.case_id!));
    // Any other value is deliberately ignored: an unknown menu action must never mutate state
    // (previously anything unexpected fell through to emergency acknowledgement).
  };
  const desktopActions = conversation ? <><Button disabled={busy || conversation.state === "human"} onClick={() => void mutate(() => changeConversationState(conversation.id, "human", conversation.version ?? 0))}><UserRoundPlus aria-hidden="true" />Tomar conversación</Button><Menu trigger="icon" align="end" collisionPadding={8} label="Acciones de la conversación" disabled={busy} items={conversationMenuItems()} onSelect={runMenuAction} /></> : null;
  const mobileActions = conversation ? <Menu trigger="icon" align="end" collisionPadding={8} label="Más acciones de la conversación" disabled={busy} items={conversationMenuItems({ includeTake: true, includeInfo: true })} onSelect={runMenuAction} /> : null;
  const loadError = fetched.error;
  const loadTitle = loadError instanceof ApiError && loadError.status === 401 ? "Sesión requerida" : loadError instanceof ApiError && loadError.status === 403 ? "No tienes permiso para ver este panel" : "No pudimos cargar la conversación";
  const displayName = conversation ? (conversation.customer?.name ?? customerName?.(conversation.customer_id) ?? `Cliente #${conversation.customer_id}`) : undefined;
  return <PageFrame className="conversations-page conversation-thread-page" title="" state={state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando conversación" /> : state === "error" ? <><StateMessage tone="danger" role="alert" title={loadTitle} /><Button variant="secondary" onClick={refresh}>Reintentar</Button></> : state === "stale" ? <StateMessage tone="warning" role="status" title="Datos posiblemente desactualizados" detail="Mostramos la información disponible." /> : null}>
      {conversation ? <header className="conversation-thread__identity">
        <div className="conversation-thread__identity-person">
          <Avatar className="conversation-thread__hero-avatar" name={displayName ?? "Conversación"} />
          <div>
            <div className="conversation-thread__identity-title"><h1>{displayName}</h1><div role="status" aria-label={conversationLabel(conversation.state)}><StatusBadge status={conversation.state as "bot" | "human" | "closed"} /></div></div>
            <p>Conversación #{conversation.id} · Iniciada el {formatInitiatedDate(conversation.created_at)}</p>
          </div>
        </div>
      </header> : null}
      {interactive ? <div className="conversation-thread__actions-row">
        {onBack ? <Button variant="secondary" onClick={onBack}>Volver a conversaciones</Button> : null}
        {conversation ? <Button variant="secondary" onClick={() => { window.location.href = pathForRoute({ view: "clients", clientId: conversation.customer_id }); }}><UserRound aria-hidden="true" />Ver ficha del cliente</Button> : null}
      </div> : null}
        {connection !== "connected" ? <p className="conversations-offline" role="status"><Icon icon={WifiOff} aria-hidden="true" /><strong>{connection === "reconnecting" ? "Reconectando la conexión en tiempo real." : "Sin conexión en tiempo real."}</strong><span>El histórico guardado sigue disponible.</span></p> : null}
       {state === "loading" ? null : !data || messages.length === 0 ? <EmptyState title="No hay registros" description="Esta conversación no tiene mensajes para mostrar." /> : <div className="conversation-workspace">
         <main className="ai-agent-grammar__main" aria-label="Conversación">
          {conversation ? <header className="ai-agent-grammar__header"><div className="ai-agent-grammar__header-copy"><h2>Historial de mensajes</h2><span className="ai-agent-grammar__freshness">Actualizada el {formatRecency(conversation.last_message_at)}</span></div><div className="conversation-thread__actions-desktop">{interactive ? desktopActions : null}</div><div className="conversation-thread__actions-mobile">{interactive ? mobileActions : null}</div>{!interactive ? <span className={`ai-agent-grammar__window${windowOpen ? "" : " ai-agent-grammar__window--closed"}`}>{windowOpen ? "Respuesta disponible" : "Fuera de la ventana de 24 horas"}</span> : null}</header> : null}
         <section className="ai-agent-grammar__thread-area" aria-label="Mensajes de la conversación">
           <CollapsibleMessages total={data.messages_total ?? messages.length} expanded={messagesExpanded} onToggle={toggleMessages}><div className="ai-agent-grammar__bubbles">{messages.map((message) => <MessageBubble key={message.id} message={message} customerId={conversation?.customer_id ?? 0} customerName={(id) => conversation?.customer?.name ?? customerName?.(id) ?? `Cliente #${id}`} />)}</div></CollapsibleMessages>
          {liveActivity.length > 0 ? <div className="ai-agent-grammar__activity-list" aria-label="Actividad persistida">{liveActivity.map((activity, index) => <div className="ai-agent-grammar__activity" role="status" key={`${activity.event}-${index}`}><span aria-hidden="true">✦</span><span className="ai-agent-grammar__activity-chip">{activityText(activity)}</span></div>)}</div> : null}
         {!interactive ? <NoReplyNote /> : null}
         {conversation?.state === "human" ? <div className="ai-agent-grammar__handoff" aria-label="Traspaso a atención humana">La conversación está en atención humana.</div> : null}
         </section>
         {interactive ? <div className="ai-agent-grammar__composer-zone">
           {messages.filter((m) => m.delivery_status === "failed").map((m) => <Button key={m.id} variant="secondary" disabled={busy} onClick={() => void mutate(() => retryMessage(m.conversation_id, m.id))}>Reintentar entrega #{m.id}</Button>)}
           {conversation?.state === "human" ? <form className={`ai-agent-grammar__composer${windowOpen ? "" : " ai-agent-grammar__composer--locked"}`} aria-label="Responder a la conversación" onSubmit={(e) => { e.preventDefault(); if (conversationId && text.trim()) void mutate(() => sendMessage(conversationId, { text: text.trim() })); }}>
             {!windowOpen ? <div className="ai-agent-grammar__window-warning" role="status" aria-label="Fuera de la ventana de 24 horas"><Icon icon={Clock} aria-hidden="true" /><div><strong>Fuera de la ventana de 24 horas</strong><span>El envío de mensajes no está disponible.</span></div></div> : null}
             <div className="ai-agent-grammar__composer-row"><div className="ai-agent-grammar__composer-field">{!windowOpen ? <Icon icon={Lock} aria-hidden="true" className="ai-agent-grammar__composer-lock" /> : null}<Textarea label="Respuesta" rows={windowOpen ? undefined : 1} placeholder={windowOpen ? undefined : "Respuesta no disponible"} value={text} disabled={!windowOpen || busy} onChange={(e) => setText(e.target.value)} /></div><Button type="submit" aria-label="Enviar respuesta" disabled={!windowOpen || busy || !text.trim()}><SendHorizonal aria-hidden="true" /></Button></div>
             {!windowOpen ? <p className="ai-agent-grammar__closed-note">Conversación cerrada</p> : null}
           </form> : <div className="ai-agent-grammar__composer ai-agent-grammar__composer--locked">
             <div className="ai-agent-grammar__window-warning" role="status" aria-label="Fuera de la ventana de 24 horas"><Icon icon={Clock} aria-hidden="true" /><div><strong>Fuera de la ventana de 24 horas</strong><span>El envío de mensajes no está disponible.</span></div></div>
             <div className="ai-agent-grammar__composer-row"><div className="ai-agent-grammar__composer-field"><Icon icon={Lock} aria-hidden="true" className="ai-agent-grammar__composer-lock" /><Textarea label="Respuesta" rows={1} placeholder="Respuesta no disponible" value="" disabled onChange={() => {}} /></div><Button aria-label="Enviar respuesta" disabled><SendHorizonal aria-hidden="true" /></Button></div>
             <p className="ai-agent-grammar__closed-note">{conversation?.state === "closed" ? "Conversación cerrada" : "Toma la conversación para responder."}</p>
           </div>}
           {mutationError && <p role="alert">La entrega falló: {mutationError}</p>}
         </div> : null}
           </main>{conversation ? <ConversationContext conversation={conversation} /> : null}</div>}
      {interactive && conversation && infoOpen ? <Dialog open onClose={() => setInfoOpen(false)} title="Información del chat" variant="sheet"><ConversationContext conversation={conversation} /></Dialog> : null}
    </PageFrame>;
}
