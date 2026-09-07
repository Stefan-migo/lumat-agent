import { useCallback, useEffect, useState } from "react";
import { ApiError, changeConversationState, getConversation, listActiveConversations, listConversations, retryMessage, sendMessage } from "../../api";
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

export interface ConversationThreadProps { conversationId?: number; data?: ThreadData | null; state?: AsyncDataState; customerName?: (id: number) => string; refreshKey?: number; onMutate?: () => void; onBack?: () => void; interactive?: boolean; }
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
  const stateControls = conversation && <div className="ai-agent-grammar__composer-actions"><Button disabled={busy || conversation.state === "human"} onClick={() => void mutate(() => changeConversationState(conversation.id, "human", conversation.version ?? 0))}>Tomar</Button><Button variant="secondary" disabled={busy || conversation.state !== "human"} onClick={() => void mutate(() => changeConversationState(conversation.id, "bot", conversation.version ?? 0))}>Devolver</Button><Button variant="secondary" disabled={busy || conversation.state !== "human"} onClick={() => void mutate(() => changeConversationState(conversation.id, "closed", conversation.version ?? 0))}>Cerrar</Button></div>;
  const loadError = fetched.error;
  const loadTitle = loadError instanceof ApiError && loadError.status === 401 ? "Sesión requerida" : loadError instanceof ApiError && loadError.status === 403 ? "No tienes permiso para ver este panel" : "No pudimos cargar la conversación";
  return <PageFrame title={conversation ? `# ${conversation.id}` : "Conversación"} meta={conversation ? `${conversation.created_at?.slice(0, 10) ?? "—"}${customerName ? ` · ${customerName(conversation.customer_id)}` : ""}${conversation.summary ? ` · ${conversation.summary}` : ""}` : undefined} state={state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando conversación" /> : state === "error" ? <><StateMessage tone="danger" role="alert" title={loadTitle} /><Button variant="secondary" onClick={refresh}>Reintentar</Button></> : null}>
      {interactive && onBack && <Button variant="secondary" onClick={onBack}>Volver a conversaciones</Button>}
       {connection !== "connected" && <p role="status">Conexión en tiempo real: {connection === "reconnecting" ? "reconectando" : "desconectada"}. La historia persistida permanece disponible.</p>}
       {state === "loading" ? null : !data || messages.length === 0 ? <EmptyState title="No hay registros" description="Esta conversación no tiene mensajes para mostrar." /> : <div className="ai-agent-grammar__thread-area" aria-label="Mensajes de la conversación">
        {conversation ? <div className="ai-agent-grammar__header"><h2 className="ai-agent-grammar__title">Conversación · {customerName?.(conversation.customer_id) ?? `Cliente #${conversation.customer_id}`}</h2><div role="status" aria-label={conversationLabel(conversation.state)}><StatusBadge status={conversation.state as "bot" | "human" | "closed"} /></div></div> : null}
         <div className="ai-agent-grammar__bubbles">{messages.map((message) => <MessageBubble key={message.id} message={message} customerId={conversation?.customer_id ?? 0} customerName={customerName} />)}</div>
         {liveActivity.length > 0 && <div aria-label="Actividad persistida"><h3>Actividad</h3>{liveActivity.map((activity, index) => <p role="status" key={`${activity.event}-${index}`}>{activity.event}{activity.cause ? `: ${activity.cause}` : ""}{activity.actor ? ` · ${activity.actor}` : ""}</p>)}</div>}
        <NoReplyNote />
        {conversation?.state === "human" ? <div className="ai-agent-grammar__handoff" aria-label="Traspaso a atención humana">La conversación está en atención humana.</div> : null}
        {interactive && <>{messages.filter((m) => m.delivery_status === "failed").map((m) => <Button key={m.id} variant="secondary" disabled={busy} onClick={() => void mutate(() => retryMessage(m.conversation_id, m.id))}>Reintentar entrega #{m.id}</Button>)}{stateControls}{conversation?.state === "human" ? <form className="ai-agent-grammar__composer" aria-label="Responder a la conversación" onSubmit={(e) => { e.preventDefault(); if (conversationId && text.trim()) void mutate(() => sendMessage(conversationId, { text: text.trim() })); }}><span className="ai-agent-grammar__composer-hint">{windowOpen ? "Respuesta disponible · Ventana de 24 h abierta" : "Respuesta deshabilitada"}</span><Textarea label="Respuesta" value={text} disabled={!windowOpen || busy} onChange={(e) => setText(e.target.value)} /><Button type="submit" disabled={!windowOpen || busy || !text.trim()}>Enviar respuesta</Button>{!windowOpen && <p role="status" aria-label="Fuera de la ventana de 24 horas">La ventana de 24 horas está cerrada.</p>}</form> : <p role="status">Toma la conversación para responder.</p>}{mutationError && <p role="alert">La entrega falló: {mutationError}</p>}</>}
      </div>}
    </PageFrame>;
}
