import { useCallback, useState } from "react";
import { ApiError, changeConversationState, getConversation, retryMessage, sendMessage } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { ConversationThread as ThreadData, Message } from "../../types";
import { DataTable, type Column } from "../../stories/pages/_shared/DataTable";
import { EmptyState } from "../../stories/pages/_shared/EmptyState";
import { PageFrame } from "../../stories/pages/_shared/PageFrame";
import { StateMessage } from "../../stories/pages/_shared/StateMessage";
import { conversationLabel, directionLabel } from "../../stories/pages/_shared/toneMaps";

export interface ConversationThreadProps { conversationId?: number; data?: ThreadData | null; state?: AsyncDataState; customerName?: (id: number) => string; refreshKey?: number; onMutate?: () => void; onBack?: () => void; interactive?: boolean; }
export function NoReplyNote() { return <StateMessage tone="info" role="status" title="Canal automático" detail="Este es un canal automático — no respondas a este mensaje (HH-5)." />; }
const messageColumns: Column<Message>[] = [
  { key: "when", header: "Cuándo", render: (m) => m.created_at?.slice(0, 10) ?? "—" },
  { key: "direction", header: "Dirección", render: (m) => directionLabel(m.direction) },
  { key: "type", header: "Tipo", render: (m) => m.msg_type },
  { key: "content", header: "Contenido", render: (m) => <>{m.text ?? "—"}{m.media_url ? " 📎" : null}{m.delivery_status ? ` · ${m.delivery_status}` : null}</> },
  { key: "attachment", header: "Adjunto", render: (m) => m.media_url ? "📎" : "—" },
];
export function ConversationThread({ conversationId, data: controlledData, state: controlledState, customerName, refreshKey = 0, onMutate, onBack, interactive = false }: ConversationThreadProps) {
  const [text, setText] = useState("");
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const fetchThread = useCallback(async () => { if (conversationId === undefined) throw new Error("conversation id is required"); return getConversation(conversationId); }, [conversationId, refreshKey]);
  const fetched = useAsyncData(fetchThread, controlledData === undefined, refreshKey);
  const data = controlledData ?? fetched.data;
  const state = controlledState ?? (controlledData !== undefined ? "ready" : fetched.state);
  const conversation = data?.conversation;
  const messages = data?.messages ?? [];
  const refresh = fetched.retry;
  const windowOpen = conversation?.reply_window_open === true;
  const mutate = async (action: () => Promise<unknown>) => { setBusy(true); setMutationError(null); try { await action(); setText(""); onMutate?.(); refresh(); } catch (error) { setMutationError(error instanceof ApiError ? `${error.status}: ${error.detail}` : "No se pudo completar la acción"); } finally { setBusy(false); } };
  const stateControls = conversation && <div><button type="button" disabled={busy || conversation.state === "human"} onClick={() => mutate(() => changeConversationState(conversation.id, "human", conversation.version ?? 0))}>Tomar</button><button type="button" disabled={busy || conversation.state !== "human"} onClick={() => mutate(() => changeConversationState(conversation.id, "bot", conversation.version ?? 0))}>Devolver</button><button type="button" disabled={busy || conversation.state !== "human"} onClick={() => mutate(() => changeConversationState(conversation.id, "closed", conversation.version ?? 0))}>Cerrar</button></div>;
  const loadError = fetched.error;
  const loadTitle = loadError instanceof ApiError && loadError.status === 401 ? "Sesión requerida" : loadError instanceof ApiError && loadError.status === 403 ? "No tienes permiso para ver este panel" : "No pudimos cargar la conversación";
  return <PageFrame title={conversation ? `# ${conversation.id}` : "Conversación"} meta={conversation ? `${conversationLabel(conversation.state)} · ${conversation.created_at?.slice(0, 10) ?? "—"}${customerName ? ` · ${customerName(conversation.customer_id)}` : ""}${conversation.summary ? ` · ${conversation.summary}` : ""}` : undefined} state={state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando conversación" /> : state === "error" ? <><StateMessage tone="danger" role="alert" title={loadTitle} /><button type="button" onClick={refresh}>Reintentar</button></> : null}>
     {interactive && onBack && <button type="button" onClick={onBack}>Volver a conversaciones</button>}
     {state === "loading" ? null : !data || messages.length === 0 ? <EmptyState title="No hay registros" description="Esta conversación no tiene mensajes para mostrar." /> : <><DataTable columns={messageColumns} rows={messages} rowKey={(m) => String(m.id)} /><NoReplyNote />{interactive && <>{messages.filter((m) => m.delivery_status === "failed").map((m) => <button key={m.id} type="button" disabled={busy} onClick={() => mutate(() => retryMessage(m.conversation_id, m.id))}>Reintentar entrega #{m.id}</button>)}{stateControls}<form onSubmit={(e) => { e.preventDefault(); if (conversationId && text.trim()) void mutate(() => sendMessage(conversationId, { text: text.trim() })); }}><label>Respuesta<textarea aria-label="Respuesta" value={text} disabled={!windowOpen || busy} onChange={(e) => setText(e.target.value)} /></label><button type="submit" disabled={!windowOpen || busy || !text.trim()}>Enviar</button></form>{!windowOpen && <p role="status">La ventana de 24 horas está cerrada.</p>}{mutationError && <p role="alert">La entrega falló: {mutationError}</p>}</>}</>}
  </PageFrame>;
}
