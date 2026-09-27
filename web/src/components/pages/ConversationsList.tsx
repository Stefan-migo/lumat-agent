import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, acknowledgeCase, listActiveConversations, listConversations, takeConversation } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { Conversation, ConversationsResponse } from "../../types";
import { Button } from "../primitives/Button";
import { Avatar } from "../primitives/Avatar";
import { SearchInput } from "../primitives/SearchInput";
import { Tabs } from "../primitives/Tabs";
import { StatusBadge, type Status } from "../primitives/StatusBadge";
import { EmptyState } from "../shared/EmptyState";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { coalesceSnapshotRefresh, realtimeClient, type ConnectionStatus } from "../../realtime";

export type ConversationsListState = AsyncDataState | "fatal-error";
export interface ConversationsListProps { data?: ConversationsResponse | null; state?: ConversationsListState; onRetry?: () => void; onOpenThread?: (id: number) => void; onQueueTabChange?: (tab: QueueTab) => void; customerName?: (id: number) => string; refreshKey?: number; currentUserId?: number; initialQueueTab?: QueueTab; }
type QueueTab = "all" | "human" | "emergency" | "case" | "closed";

const priority = (conversation: Conversation) => conversation.emergency && !conversation.acknowledged_at ? 0 : conversation.state === "human" ? 1 : conversation.state === "closed" ? 3 : 2;
const tabRows = (rows: Conversation[], tab: QueueTab) => rows.filter((row) => tab === "all" || tab === "human" && row.state === "human" || tab === "emergency" && row.emergency || tab === "case" && row.case_id != null || tab === "closed" && row.state === "closed");
const formatRecency = (value: string | null) => value ? new Intl.DateTimeFormat("es-CL", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)) : "—";

function stateMessage(state: ConversationsListState, error: unknown) {
  if (state === "loading") return <StateMessage tone="info" role="status" spinner title="Cargando conversaciones" />;
  if (state === "error") return <StateMessage tone="danger" role="alert" title={error instanceof ApiError && error.status === 401 ? "Sesión requerida" : "No pudimos cargar las conversaciones"} />;
  if (state === "denied") return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver este panel" />;
  return state === "fatal-error" ? <StateMessage tone="danger" role="alert" title="No pudimos cargar las conversaciones" /> : null;
}

export function ConversationsList({ data: controlledData, state: controlledState, onRetry, onOpenThread, onQueueTabChange, customerName, refreshKey = 0, currentUserId, initialQueueTab = "all" }: ConversationsListProps = {}) {
  const [tab, setTab] = useState<QueueTab>(initialQueueTab);
  useEffect(() => setTab(initialQueueTab), [initialQueueTab]);
  const [query, setQuery] = useState("");
  const [assignment, setAssignment] = useState<"all" | "mine">("all");
  const [offset, setOffset] = useState(0);
  const [requestRevision, setRequestRevision] = useState(0);
  const [selectedId, setSelectedId] = useState<number>();
  const [busyId, setBusyId] = useState<number>();
  const fetchConversations = useCallback(() => query || offset || assignment === "mine" ? listConversations({ q: query || undefined, responsible_id: assignment === "mine" ? currentUserId : undefined, limit: 20, offset }) : listConversations(), [assignment, currentUserId, query, offset, refreshKey]);
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
    const unregisterRecovery = realtimeClient.registerRecovery(async () => { await Promise.all([listConversations({ q: query || undefined, responsible_id: assignment === "mine" ? currentUserId : undefined, limit: 20, offset }), listActiveConversations()]); retry(); });
    realtimeClient.connect();
    return () => { unsubscribe(); unsubscribeStatus(); unregisterRecovery(); snapshotRefresh.cancel(); };
  }, [assignment, controlledData, currentUserId, offset, query, retry]);

  const runAction = async (id: number, action: () => Promise<unknown>) => { setBusyId(id); try { await action(); retry(); } finally { setBusyId(undefined); } };
  const tabs = [
    { id: "all", label: <>Todas <span className="conversations-queue__count">{counts.all}</span></> },
    { id: "human", label: <>Humanas <span className="conversations-queue__count">{counts.human}</span></> },
    { id: "emergency", label: <>Emergencias <span className={`conversations-queue__count${counts.emergency > 0 ? " conversations-queue__count--danger" : ""}`}>{counts.emergency}</span></> },
    { id: "case", label: <>Casos <span className="conversations-queue__count">{counts.case}</span></> },
    { id: "closed", label: <>Cerradas <span className="conversations-queue__count">{counts.closed}</span></> },
  ];
   const limit = data?.limit ?? 20;
   const page = Math.floor(offset / limit) + 1;
   const pageCount = data?.total != null && data.limit != null ? Math.max(1, Math.ceil(data.total / data.limit)) : undefined;
  return <PageFrame className="conversations-page" title="Conversaciones" meta={data ? `${data.total ?? rows.length} ${data.total === 1 ? "conversación" : "conversaciones"}` : "Cola de conversaciones"} state={stateMessage(state, fetched.error)}>
     {connection !== "connected" ? <p className="realtime-status realtime-status--info" role="status"><span aria-hidden="true">ⓘ</span>Conexión en tiempo real: {connection === "reconnecting" ? "reconectando" : "desconectada"}. Los datos seguirán disponibles.</p> : null}
     <section className="ai-agent-grammar__filters conversations-queue__toolbar" aria-label="Filtros de conversaciones"><SearchInput aria-label="Buscar conversaciones" placeholder="Buscar cliente, teléfono o resumen" onSearch={(value) => { setQuery(value); setOffset(0); setRequestRevision((revision) => revision + 1); }} />{currentUserId !== undefined ? <label className="conversations-queue__assignment"><span className="conversations-queue__assignment-label">Responsable</span><select aria-label="Filtrar por responsable" value={assignment} onChange={(event) => { setAssignment(event.target.value as "all" | "mine"); setOffset(0); setRequestRevision((revision) => revision + 1); }}><option value="all">Todas</option><option value="mine">Asignadas a mí</option></select></label> : null}{state === "error" || state === "fatal-error" || state === "denied" ? <Button variant="secondary" onClick={retry}>Reintentar</Button> : null}</section>
      <Tabs tabs={tabs} activeTab={tab} onTabChange={(value) => { const nextTab = value as QueueTab; setTab(nextTab); onQueueTabChange?.(nextTab); }} ariaLabel="Cola de conversaciones">{() => state === "loading" ? null : visibleRows.length === 0 ? <EmptyState title={data?.items === undefined ? "No hay registros" : "No hay conversaciones"} description="No existen conversaciones para mostrar." /> : <ul className="conversations-queue" role="list">{visibleRows.map((c) => {
       const selected = selectedId === c.id;
       const urgent = Boolean(c.emergency && !c.acknowledged_at);
        const name = c.customer?.name ?? customerName?.(c.customer_id) ?? `Cliente #${c.customer_id}`;
        return <li key={c.id} className={`conversations-queue__row${selected ? " conversations-queue__row--selected" : ""}${urgent ? " conversations-queue__row--urgent" : ""}`}>
          <span className="conversations-queue__rail" aria-hidden="true" />
          <Avatar name={name} className="conversations-queue__avatar" />
          <div className="conversations-queue__body">
            <div className="conversations-queue__headline">
              <button type="button" className="conversations-queue__identity" data-testid={`conversation-row-${c.id}`} aria-label={`Abrir conversación #${c.id}`} aria-current={selected ? "page" : undefined} onClick={() => { setSelectedId(c.id); onOpenThread?.(c.id); }}>
                <strong>{name}</strong>
              </button>
              <div className="conversations-queue__badges"><StatusBadge status={c.state as Status} />{c.emergency ? <StatusBadge status="escalated" label="Emergencia" /> : null}{c.case_priority && !c.emergency ? <span className="conversations-queue__priority">{c.case_priority}</span> : null}{c.case_id != null ? <span className="conversations-queue__case">Caso #{c.case_id}</span> : null}</div>
            </div>
            <p className="conversations-queue__meta"><span>{c.customer?.phone_e164 ?? c.wa_phone ?? "—"}</span> · <span className="conversations-queue__reference">#{c.id}</span></p>
            <p className="conversations-queue__summary">{c.summary ?? "—"}</p>
          </div>
          <div className="conversations-queue__trailing">
            <time className="conversations-queue__time" dateTime={c.last_message_at ?? undefined}>{formatRecency(c.last_message_at)}</time>
            <div className="conversations-queue__actions">{onOpenThread ? <Button variant="secondary" className="conversations-queue__open" onClick={() => { setSelectedId(c.id); onOpenThread(c.id); }}>Abrir</Button> : null}{c.state === "bot" ? <Button disabled={busyId === c.id} onClick={() => void runAction(c.id, () => takeConversation(c.id, c.version ?? 0))}>Tomar conversación</Button> : null}{c.emergency && !c.acknowledged_at && c.case_id != null ? <Button variant="secondary" disabled={busyId === c.id} onClick={() => void runAction(c.id, () => acknowledgeCase(c.case_id!))}>Reconocer emergencia</Button> : null}</div>
          </div>
        </li>;
     })}</ul>}</Tabs>
      <nav className="pagination" aria-label="Paginación de conversaciones"><Button variant="secondary" className="pagination__button" disabled={offset === 0} onClick={() => { setOffset(Math.max(0, offset - 20)); setRequestRevision((revision) => revision + 1); }}>Anterior</Button><span className="pagination__current">Página {page}{pageCount ? ` de ${pageCount}` : ""}</span><Button variant="secondary" className="pagination__button" disabled={!data || offset + (data.limit ?? 20) >= (data.total ?? 0)} onClick={() => { setOffset(offset + 20); setRequestRevision((revision) => revision + 1); }}>Siguiente</Button></nav>
  </PageFrame>;
}
