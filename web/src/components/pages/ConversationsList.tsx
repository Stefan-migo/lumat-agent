import { useCallback } from "react";
import { apiFetch } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { Conversation, ConversationsResponse } from "../../types";
import { StatusBadge, type Status } from "../primitives/StatusBadge";
import { DataTable, type Column } from "../../stories/pages/_shared/DataTable";
import { EmptyState } from "../../stories/pages/_shared/EmptyState";
import { PageFrame } from "../../stories/pages/_shared/PageFrame";
import { StateMessage } from "../../stories/pages/_shared/StateMessage";

export type ConversationsListState = AsyncDataState | "fatal-error";
export interface ConversationsListProps { data?: ConversationsResponse | null; state?: ConversationsListState; onRetry?: () => void; onOpenThread?: (id: number) => void; customerName?: (id: number) => string; }

const columns = (customerName?: (id: number) => string, onOpenThread?: (id: number) => void): Column<Conversation>[] => [
  { key: "id", header: "#", render: (c) => `#${c.id}` },
  { key: "customer", header: "Cliente", render: (c) => <span>{customerName?.(c.customer_id) ?? `Cliente #${c.customer_id}`} <span style={{ color: "var(--text-muted)" }}>{c.wa_phone ?? "—"}</span></span> },
  { key: "state", header: "Estado", render: (c) => <StatusBadge status={c.state as Status} /> },
  { key: "summary", header: "Resumen", render: (c) => c.summary ?? "—" },
  { key: "last", header: "Último mensaje", render: (c) => c.last_message_at?.slice(0, 10) ?? "—" },
  { key: "created", header: "Creada", render: (c) => c.created_at?.slice(0, 10) ?? "—" },
  ...(onOpenThread ? [{ key: "open", header: "", render: (c: Conversation) => <button type="button" onClick={() => onOpenThread(c.id)}>Abrir conversación #{c.id}</button> }] : []),
];

function stateMessage(state: ConversationsListState) {
  if (state === "loading") return <StateMessage tone="info" role="status" spinner title="Cargando conversaciones" />;
  if (state === "error") return <StateMessage tone="danger" role="alert" title="No pudimos cargar las conversaciones" />;
  if (state === "denied") return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver este panel" />;
  return state === "fatal-error" ? <StateMessage tone="danger" role="alert" title="No pudimos cargar las conversaciones" /> : null;
}

export function ConversationsList({ data: controlledData, state: controlledState, onRetry, onOpenThread, customerName }: ConversationsListProps = {}) {
  const fetchConversations = useCallback(() => apiFetch<ConversationsResponse>("/panel/api/conversations"), []);
  const fetched = useAsyncData(fetchConversations, controlledData === undefined);
  const data = controlledData ?? fetched.data;
  const state = controlledState ?? (controlledData !== undefined ? "ready" : fetched.state);
  const rows = data?.conversations ?? [];
  void (onRetry ?? fetched.retry);
  return <PageFrame title="Conversaciones" meta={data ? `${rows.length} conversaciones` : undefined} state={stateMessage(state)}>
    {state === "loading" ? null : data && rows.length === 0 ? <EmptyState title="No hay registros" description="No existen conversaciones para mostrar." /> : data ? <DataTable columns={columns(customerName, onOpenThread)} rows={rows} rowKey={(c) => String(c.id)} /> : null}
  </PageFrame>;
}
