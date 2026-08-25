import { useCallback } from "react";
import { apiFetch } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { ConversationThread as ThreadData, Message } from "../../types";
import { DataTable, type Column } from "../../stories/pages/_shared/DataTable";
import { EmptyState } from "../../stories/pages/_shared/EmptyState";
import { PageFrame } from "../../stories/pages/_shared/PageFrame";
import { StateMessage } from "../../stories/pages/_shared/StateMessage";
import { conversationLabel, directionLabel } from "../../stories/pages/_shared/toneMaps";

export interface ConversationThreadProps { conversationId?: number; data?: ThreadData | null; state?: AsyncDataState; customerName?: (id: number) => string; }
export function NoReplyNote() { return <StateMessage tone="info" role="status" title="Canal automático" detail="Este es un canal automático — no respondas a este mensaje (HH-5)." />; }
const messageColumns: Column<Message>[] = [
  { key: "when", header: "Cuándo", render: (m) => m.created_at?.slice(0, 10) ?? "—" },
  { key: "direction", header: "Dirección", render: (m) => directionLabel(m.direction) },
  { key: "type", header: "Tipo", render: (m) => m.msg_type },
  { key: "content", header: "Contenido", render: (m) => <>{m.text ?? "—"}{m.media_url ? " 📎" : null}</> },
  { key: "attachment", header: "Adjunto", render: (m) => m.media_url ? "📎" : "—" },
];
export function ConversationThread({ conversationId, data: controlledData, state: controlledState, customerName }: ConversationThreadProps) {
  const fetchThread = useCallback(async () => { if (conversationId === undefined) throw new Error("conversation id is required"); return apiFetch<ThreadData>(`/panel/api/conversations/${conversationId}`); }, [conversationId]);
  const fetched = useAsyncData(fetchThread, controlledData === undefined);
  const data = controlledData ?? fetched.data;
  const state = controlledState ?? (controlledData !== undefined ? "ready" : fetched.state);
  const conversation = data?.conversation;
  const messages = data?.messages ?? [];
  return <PageFrame title={conversation ? `# ${conversation.id}` : "Conversación"} meta={conversation ? `${conversationLabel(conversation.state)} · ${conversation.created_at?.slice(0, 10) ?? "—"}${customerName ? ` · ${customerName(conversation.customer_id)}` : ""}${conversation.summary ? ` · ${conversation.summary}` : ""}` : undefined} state={state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando conversación" /> : state === "error" ? <StateMessage tone="danger" role="alert" title="No pudimos cargar la conversación" /> : null}>
    {state === "loading" ? null : !data || messages.length === 0 ? <EmptyState title="No hay registros" description="Esta conversación no tiene mensajes para mostrar." /> : <><DataTable columns={messageColumns} rows={messages} rowKey={(m) => String(m.id)} /><NoReplyNote /></>}
  </PageFrame>;
}
