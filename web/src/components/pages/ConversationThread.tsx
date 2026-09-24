import { useCallback, useEffect, useState } from "react";
import { ApiError, acknowledgeCase, changeConversationState, getConversation, listActiveConversations, listConversations, retryMessage, sendMessage } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { ConversationThread as ThreadData, Message } from "../../types";
import { Avatar } from "../primitives/Avatar";
import { Button } from "../primitives/Button";
import { StatusBadge } from "../primitives/StatusBadge";
import { Textarea } from "../primitives/Textarea";
import { EmptyState } from "../shared/EmptyState";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { conversationLabel } from "../shared/toneMaps";
import { realtimeClient, type ConnectionStatus } from "../../realtime";

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
    {!outbound ? <Avatar name={author} /> : null}
    <div className={`ai-agent-grammar__bubble${outbound ? " ai-agent-grammar__bubble--outbound" : ""}`}>
      <span className="ai-agent-grammar__message-meta">{author}</span>
      <span>{message.text ?? "—"}{message.media_url ? " 📎" : null}</span>
      <span className="ai-agent-grammar__message-time">{message.created_at?.slice(11, 16) ?? "—"}</span>
      {message.delivery_status === "failed" ? <span className="ai-agent-grammar__message-error" role="alert">Entrega fallida{message.delivery_error ? `: ${message.delivery_error}` : ""}</span> : null}
    </div>
    {outbound ? <Avatar name={author} /> : null}
  </div>;
}

function displayCapturedValue(value: unknown) {
  return typeof value === "object" && value !== null ? JSON.stringify(value) : String(value ?? "—");
}
const formatRecency = (value: string | null) => value ? new Intl.DateTimeFormat("es-CL", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)) : "—";

function ConversationContext({ conversation }: { conversation: NonNullable<ThreadData["conversation"]> }) {
  const customer = conversation.customer;
  const caseData = conversation.case;
  return <aside className="ai-agent-grammar__inspector" aria-label="Inspector de conversación">
      {customer ? <section aria-labelledby="conversation-customer-heading"><h2 id="conversation-customer-heading">Cliente</h2><dl><div className="ai-agent-grammar__detail"><dt>Nombre</dt><dd>{customer.name ?? "Sin nombre"}</dd></div><div className="ai-agent-grammar__detail"><dt>Teléfono</dt><dd>{customer.phone_e164 ?? conversation.wa_phone ?? "Sin teléfono"}</dd></div></dl></section> : null}
      {caseData ? <section aria-labelledby="conversation-case-heading"><h2 id="conversation-case-heading">Caso</h2><dl><div className="ai-agent-grammar__detail"><dt>Servicio</dt><dd>{caseData.service}</dd></div><div className="ai-agent-grammar__detail"><dt>Estado</dt><dd>{conversation.case_status ?? caseData.status}</dd></div><div className="ai-agent-grammar__detail"><dt>Prioridad</dt><dd>{conversation.case_priority ?? caseData.priority}</dd></div><div className="ai-agent-grammar__detail"><dt>Emergencia</dt><dd>{conversation.emergency ? "Sí" : "No"}</dd></div><div className="ai-agent-grammar__detail"><dt>Reconocimiento</dt><dd>{conversation.acknowledged_at ? "Reconocida" : "Pendiente"}</dd></div>{caseData.summary ? <div className="ai-agent-grammar__detail"><dt>Resumen</dt><dd>{caseData.summary}</dd></div> : null}</dl></section> : null}
      {conversation.captured_data && Object.keys(conversation.captured_data).length > 0 ? <details open><summary>Datos capturados</summary><dl>{Object.entries(conversation.captured_data).map(([key, value]) => <div className="ai-agent-grammar__detail" key={key}><dt>{key}</dt><dd>{displayCapturedValue(value)}</dd></div>)}</dl></details> : null}
  </aside>;
}
export function ConversationThread({ conversationId, data: controlledData, state: controlledState, customerName, refreshKey = 0, onMutate, onBack, interactive = false }: ConversationThreadProps) {
  const [text, setText] = useState("");
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [connection, setConnection] = useState<ConnectionStatus>("disconnected");
  const [liveActivity, setLiveActivity] = useState<Array<{ event: string; cause?: string | null; actor?: string | null }>>([]);
  const fetchThread = useCallback(async () => { if (conversationId === undefined) throw new Error("conversation id is required"); return getConversation(conversationId); }, [conversationId, refreshKey]);
  const fetched = useAsyncData(fetchThread, controlledData === undefined, refreshKey);
  const data = controlledData ?? fetched.data;
  const state = controlledState ?? (controlledData !== undefined ? "ready" : fetched.state);
  const conversation = data?.conversation;
  const messages = data?.messages ?? [];
  const refresh = fetched.retry;
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
  const stateControls = conversation ? <><Button disabled={busy || conversation.state === "human"} onClick={() => void mutate(() => changeConversationState(conversation.id, "human", conversation.version ?? 0))}>Tomar conversación</Button><Button variant="secondary" disabled={busy || conversation.state !== "human"} onClick={() => void mutate(() => changeConversationState(conversation.id, "bot", conversation.version ?? 0))}>Devolver al agente</Button><Button variant="secondary" disabled={busy || conversation.state !== "human"} onClick={() => void mutate(() => changeConversationState(conversation.id, "closed", conversation.version ?? 0))}>Cerrar conversación</Button></> : null;
  const loadError = fetched.error;
  const loadTitle = loadError instanceof ApiError && loadError.status === 401 ? "Sesión requerida" : loadError instanceof ApiError && loadError.status === 403 ? "No tienes permiso para ver este panel" : "No pudimos cargar la conversación";
  const displayName = conversation ? (conversation.customer?.name ?? customerName?.(conversation.customer_id) ?? `Cliente #${conversation.customer_id}`) : undefined;
  return <PageFrame className="conversations-page" headerClassName="dashboard-header" title="Conversación" meta={conversation ? <span className="dashboard-meta">#{conversation.id} · {displayName} · {conversation.created_at?.slice(0, 10) ?? "—"}</span> : undefined} state={state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando conversación" /> : state === "error" ? <><StateMessage tone="danger" role="alert" title={loadTitle} /><Button variant="secondary" onClick={refresh}>Reintentar</Button></> : state === "stale" ? <StateMessage tone="warning" role="status" title="Datos posiblemente desactualizados" detail="Mostramos la información disponible." /> : null}>
      {interactive && onBack ? <div className="conversation-back"><Button variant="secondary" onClick={onBack}>Volver a conversaciones</Button></div> : null}
        {connection !== "connected" && <p className="realtime-status realtime-status--info" role="status"><span aria-hidden="true">ⓘ</span>Conexión en tiempo real: {connection === "reconnecting" ? "reconectando" : "desconectada"}. La historia persistida permanece disponible.</p>}
       {state === "loading" ? null : !data || messages.length === 0 ? <EmptyState title="No hay registros" description="Esta conversación no tiene mensajes para mostrar." /> : <div className="conversation-workspace">
         <main className="ai-agent-grammar__main" aria-label="Conversación">
          {conversation ? <header className="ai-agent-grammar__header"><div role="status" aria-label={conversationLabel(conversation.state)}><StatusBadge status={conversation.state as "bot" | "human" | "closed"} /></div><div className="ai-agent-grammar__header-actions">{interactive ? stateControls : null}{conversation.case && conversation.emergency && !conversation.acknowledged_at && conversation.case_id != null ? <Button variant="secondary" className="emergency-action" disabled={busy} onClick={() => void mutate(() => acknowledgeCase(conversation.case_id!))}>Reconocer emergencia</Button> : null}</div><span className="ai-agent-grammar__freshness">Actualizado {formatRecency(conversation.last_message_at)}</span><span className={`ai-agent-grammar__window${windowOpen ? "" : " ai-agent-grammar__window--closed"}`}>{windowOpen ? "Respuesta disponible" : "Fuera de la ventana de 24 horas"}</span></header> : null}
         <section className="ai-agent-grammar__thread-area" aria-label="Mensajes de la conversación">
          <div className="ai-agent-grammar__bubbles">{messages.map((message) => <MessageBubble key={message.id} message={message} customerId={conversation?.customer_id ?? 0} customerName={customerName} />)}</div>
          {liveActivity.length > 0 ? <div className="ai-agent-grammar__activity-list" aria-label="Actividad persistida">{liveActivity.map((activity, index) => <div className="ai-agent-grammar__activity" role="status" key={`${activity.event}-${index}`}><span aria-hidden="true">✦</span><span className="ai-agent-grammar__activity-chip">{activity.event}{activity.cause ? `: ${activity.cause}` : ""}{activity.actor ? ` · ${activity.actor}` : ""}</span></div>)}</div> : null}
         {!interactive ? <NoReplyNote /> : null}
         {conversation?.state === "human" ? <div className="ai-agent-grammar__handoff" aria-label="Traspaso a atención humana">La conversación está en atención humana.</div> : null}
         </section>
         {interactive ? <div className="ai-agent-grammar__composer-zone">
           {messages.filter((m) => m.delivery_status === "failed").map((m) => <Button key={m.id} variant="secondary" disabled={busy} onClick={() => void mutate(() => retryMessage(m.conversation_id, m.id))}>Reintentar entrega #{m.id}</Button>)}
           {conversation?.state === "human" ? <form className="ai-agent-grammar__composer" aria-label="Responder a la conversación" onSubmit={(e) => { e.preventDefault(); if (conversationId && text.trim()) void mutate(() => sendMessage(conversationId, { text: text.trim() })); }}><span className="ai-agent-grammar__composer-hint">{windowOpen ? "Respuesta disponible · Ventana de 24 h abierta" : "Respuesta deshabilitada"}</span><Textarea label="Respuesta" value={text} disabled={!windowOpen || busy} onChange={(e) => setText(e.target.value)} /><div className="ai-agent-grammar__composer-actions"><Button type="submit" disabled={!windowOpen || busy || !text.trim()}>Enviar respuesta</Button>{!windowOpen ? <span className="ai-agent-grammar__reason">La ventana de 24 horas está cerrada.</span> : null}</div>{!windowOpen && <p role="status" aria-label="Fuera de la ventana de 24 horas">La ventana de 24 horas está cerrada.</p>}</form> : <p role="status">Toma la conversación para responder.</p>}
           {mutationError && <p role="alert">La entrega falló: {mutationError}</p>}
         </div> : null}
          </main>{conversation ? <ConversationContext conversation={conversation} /> : null}</div>}
    </PageFrame>;
}
