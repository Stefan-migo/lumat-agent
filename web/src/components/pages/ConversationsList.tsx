import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, acknowledgeCase, listActiveConversations, listConversations, takeConversation } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { Conversation, ConversationsResponse } from "../../types";
import { Button } from "../primitives/Button";
import { SearchInput } from "../primitives/SearchInput";
import { Tabs } from "../primitives/Tabs";
import { StatusBadge, type Status } from "../primitives/StatusBadge";
import { DataTable, type Column } from "../shared/DataTable";
import { EmptyState } from "../shared/EmptyState";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { coalesceSnapshotRefresh, realtimeClient, type ConnectionStatus } from "../../realtime";

export type ConversationsListState = AsyncDataState | "fatal-error";
export interface ConversationsListProps { data?: ConversationsResponse | null; state?: ConversationsListState; onRetry?: () => void; onOpenThread?: (id: number) => void; customerName?: (id: number) => string; refreshKey?: number; }
type QueueTab = "all" | "human" | "emergency" | "case" | "closed";

const priority = (conversation: Conversation) => conversation.emergency && !conversation.acknowledged_at ? 0 : conversation.state === "human" ? 1 : conversation.state === "closed" ? 3 : 2;
const tabRows = (rows: Conversation[], tab: QueueTab) => rows.filter((row) => tab === "all" || tab === "human" && row.state === "human" || tab === "emergency" && row.emergency || tab === "case" && row.case_id != null || tab === "closed" && row.state === "closed");

function stateMessage(state: ConversationsListState, error: unknown) {
  if (state === "loading") return <StateMessage tone="info" role="status" spinner title="Cargando conversaciones" />;
  if (state === "error") return <StateMessage tone="danger" role="alert" title={error instanceof ApiError && error.status === 401 ? "Sesión requerida" : "No pudimos cargar las conversaciones"} />;
  if (state === "denied") return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver este panel" />;
  return state === "fatal-error" ? <StateMessage tone="danger" role="alert" title="No pudimos cargar las conversaciones" /> : null;
}

export function ConversationsList({ data: controlledData, state: controlledState, onRetry, onOpenThread, customerName, refreshKey = 0 }: ConversationsListProps = {}) {
  const [tab, setTab] = useState<QueueTab>("all");
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [requestRevision, setRequestRevision] = useState(0);
  const [selectedId, setSelectedId] = useState<number>();
  const [busyId, setBusyId] = useState<number>();
  const fetchConversations = useCallback(() => query || offset ? listConversations({ q: query, limit: 20, offset }) : listConversations(), [query, offset, refreshKey]);
  const fetched = useAsyncData(fetchConversations, controlledData === undefined, refreshKey + requestRevision);
  const data = controlledData ?? fetched.data;
  const state = controlledState ?? (controlledData !== undefined ? "ready" : fetched.state);
  const retry = onRetry ?? fetched.retry;
  const rows = useMemo(() => [...(data?.items ?? data?.conversations ?? [])].sort((a, b) => priority(a) - priority(b) || (b.last_message_at ?? "").localeCompare(a.last_message_at ?? "") || b.id - a.id), [data]);
  const visibleRows = tabRows(rows, tab);
  const counts = data?.counts ?? { all: rows.length, human: rows.filter((r) => r.state === "human").length, emergency: rows.filter((r) => r.emergency).length, case: rows.filter((r) => r.case_id != null).length, closed: rows.filter((r) => r.state === "closed").length };
  const [connection, setConnection] = useState<ConnectionStatus>("disconnected");

  useEffect(() => {
    if (controlledData !== undefined) return;
    const snapshotRefresh = coalesceSnapshotRefresh(retry);
    const unsubscribe = realtimeClient.subscribe((event) => { if (["conversation", "message"].includes(event.type)) retry(); if (event.type === "snapshot") snapshotRefresh(); });
    const unsubscribeStatus = realtimeClient.subscribeStatus(setConnection);
    const unregisterRecovery = realtimeClient.registerRecovery(async () => { await Promise.all([listConversations({ q: query, limit: 20, offset }), listActiveConversations()]); retry(); });
    realtimeClient.connect();
    return () => { unsubscribe(); unsubscribeStatus(); unregisterRecovery(); snapshotRefresh.cancel(); };
  }, [controlledData, offset, query, retry]);

  const runAction = async (id: number, action: () => Promise<unknown>) => { setBusyId(id); try { await action(); retry(); } finally { setBusyId(undefined); } };
  const columns: Column<Conversation>[] = [
    { key: "id", header: "#", render: (c) => <span data-testid={`conversation-row-${c.id}`} aria-current={selectedId === c.id ? "page" : undefined}>#{c.id}</span> },
    { key: "customer", header: "Cliente", render: (c) => <span>{c.customer?.name ?? customerName?.(c.customer_id) ?? `Cliente #${c.customer_id}`} <span style={{ color: "var(--text-muted)" }}>{c.customer?.phone_e164 ?? c.wa_phone ?? "—"}</span></span> },
    { key: "priority", header: "Prioridad", render: (c) => c.emergency ? <StatusBadge status="escalated" label="Emergencia" /> : c.case_priority ?? "—" },
    { key: "state", header: "Estado", render: (c) => <StatusBadge status={c.state as Status} /> },
    { key: "summary", header: "Resumen", render: (c) => c.summary ?? "—" },
    { key: "last", header: "Último mensaje", render: (c) => c.last_message_at?.slice(0, 10) ?? "—" },
    { key: "actions", header: "Acciones", render: (c) => <span>{c.state === "bot" ? <Button disabled={busyId === c.id} onClick={() => void runAction(c.id, () => takeConversation(c.id, c.version ?? 0))}>Tomar</Button> : null}{c.emergency && !c.acknowledged_at && c.case_id !== null ? <Button variant="secondary" disabled={busyId === c.id} onClick={() => void runAction(c.id, () => acknowledgeCase(c.case_id!))}>Reconocer</Button> : null}{onOpenThread ? <Button variant="secondary" onClick={() => { setSelectedId(c.id); onOpenThread(c.id); }}>Abrir conversación #{c.id}</Button> : null}</span> },
  ];
  const tabs = [{ id: "all", label: `Todas ${counts.all}` }, { id: "human", label: `Humanas ${counts.human}` }, { id: "emergency", label: `Emergencias ${counts.emergency}` }, { id: "case", label: `Casos ${counts.case}` }, { id: "closed", label: `Cerradas ${counts.closed}` }];
  const page = Math.floor(offset / 20) + 1;
  return <PageFrame title="Conversaciones" meta={data ? `${data.total ?? rows.length} conversaciones` : undefined} state={stateMessage(state, fetched.error)}>
    {connection !== "connected" ? <p role="status">Conexión en tiempo real: {connection === "reconnecting" ? "reconectando" : "desconectada"}. Los datos seguirán disponibles.</p> : null}
    <section className="ai-agent-grammar__filters" aria-label="Filtros de conversaciones"><SearchInput aria-label="Buscar conversaciones" placeholder="Buscar cliente, teléfono o resumen" onSearch={(value) => { setQuery(value); setOffset(0); setRequestRevision((revision) => revision + 1); }} /><Button variant="secondary" onClick={retry}>Reintentar</Button></section>
    <Tabs tabs={tabs} activeTab={tab} onTabChange={(value) => setTab(value as QueueTab)} ariaLabel="Cola de conversaciones">{() => state === "loading" ? null : visibleRows.length === 0 ? <EmptyState title={data?.items === undefined ? "No hay registros" : "No hay conversaciones"} description="No existen conversaciones para mostrar." /> : <DataTable columns={columns} rows={visibleRows} rowKey={(c) => String(c.id)} />}</Tabs>
    <nav className="pagination" aria-label="Paginación de conversaciones"><Button variant="secondary" className="pagination__button" disabled={offset === 0} onClick={() => { setOffset(Math.max(0, offset - 20)); setRequestRevision((revision) => revision + 1); }}>Anterior</Button><span aria-current="page">Página {page}</span><Button variant="secondary" className="pagination__button" disabled={!data || offset + (data.limit ?? 20) >= (data.total ?? 0)} onClick={() => { setOffset(offset + 20); setRequestRevision((revision) => revision + 1); }}>Siguiente</Button></nav>
  </PageFrame>;
}
