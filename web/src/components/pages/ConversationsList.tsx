import { useCallback, useEffect, useId, useMemo, useState } from "react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Check, ChevronDown, ChevronRight, UserRound, UserRoundPlus, WifiOff, X } from "lucide-react";
import { ApiError, acknowledgeCase, changeConversationState, listActiveConversations, listConversations, takeConversation } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { Conversation, ConversationsResponse } from "../../types";
import { Button } from "../primitives/Button";
import { Badge } from "../primitives/Badge";
import { Avatar } from "../primitives/Avatar";
import { Icon } from "../primitives/Icon";
import { Menu, type MenuItem } from "../primitives/Menu";
import { SearchInput } from "../primitives/SearchInput";
import { Tabs } from "../primitives/Tabs";
import { Pagination } from "../primitives/Pagination";
import { StatusBadge, type Status } from "../primitives/StatusBadge";
import { DataTable, type Column } from "../shared/DataTable";
import { EmptyState } from "../shared/EmptyState";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { plainSummary } from "../shared/markdownText";
import { coalesceSnapshotRefresh, realtimeClient, type ConnectionStatus } from "../../realtime";
import "./ConversationsList.css";

export type ConversationsListState = AsyncDataState | "fatal-error";
export type QueueTab = "all" | "human" | "emergency" | "case" | "closed";
export type QueueAssignee = "all" | "mine";
export interface ConversationsQueueContext { tab: QueueTab; query: string; assignee: QueueAssignee; page: number; }
export interface ConversationsListProps { data?: ConversationsResponse | null; state?: ConversationsListState; onRetry?: () => void; onOpenThread?: (id: number) => void; onQueueTabChange?: (tab: QueueTab) => void; onQueueContextChange?: (context: ConversationsQueueContext) => void; customerName?: (id: number) => string; refreshKey?: number; currentUserId?: number; initialQueueTab?: QueueTab; queueTab?: QueueTab; initialQueueContext?: ConversationsQueueContext; compact?: boolean; selectedConversationId?: number | null; }

const priority = (conversation: Conversation) => conversation.emergency && !conversation.acknowledged_at ? 0 : conversation.state === "human" ? 1 : conversation.state === "closed" ? 3 : 2;
const tabFilters = (tab: QueueTab) => ({
  ...(tab === "human" ? { state: "human" as const } : tab === "closed" ? { state: "closed" as const } : { exclude_closed: true }),
  ...(tab === "emergency" ? { emergency: true } : {}),
  ...(tab === "case" ? { has_case: true } : {}),
});
const formatActivityDate = (value: string) => new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", year: "numeric" }).format(new Date(value)).replace(".", "");
const formatActivityTime = (value: string) => new Intl.DateTimeFormat("es-CL", { hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date(value));
const activityCell = (value: string | null) => value ? <time className="conversations-list__activity" dateTime={value}><span>{formatActivityDate(value)}</span><span className="conversations-list__activity-time">{formatActivityTime(value)}</span></time> : "—";
const priorityBadge = (conversation: Conversation) => {
  if (conversation.case_priority === "alta") return <Badge tone="warning">Prioridad alta</Badge>;
  if (conversation.case_priority === "media") return <Badge tone="neutral">Prioridad normal</Badge>;
  if (conversation.case_priority === "baja") return <Badge tone="neutral">Prioridad baja</Badge>;
  return null;
};
const conversationBadges = (conversation: Conversation) => <span className="conversations-list__status"><StatusBadge status={conversation.state as Status} />{priorityBadge(conversation)}{conversation.emergency ? <StatusBadge status="escalated" label="Emergencia" /> : null}</span>;
const queueTabLabels: Record<Exclude<QueueTab, "all">, string> = { human: "Atención humana", emergency: "Emergencias", case: "Con caso", closed: "Cerradas" };

function stateMessage(state: ConversationsListState, error: unknown) {
  if (state === "loading") return <StateMessage tone="info" role="status" spinner title="Cargando conversaciones" />;
  if (state === "error") return <StateMessage tone="danger" role="alert" title={error instanceof ApiError && error.status === 401 ? "Sesión requerida" : "No pudimos cargar las conversaciones"} />;
  if (state === "denied") return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver este panel" />;
  return state === "fatal-error" ? <StateMessage tone="danger" role="alert" title="No pudimos cargar las conversaciones" /> : null;
}

export function ConversationsList({ data: controlledData, state: controlledState, onRetry, onOpenThread, onQueueTabChange, onQueueContextChange, customerName, refreshKey = 0, currentUserId, initialQueueTab = "all", queueTab, initialQueueContext, compact = false, selectedConversationId }: ConversationsListProps = {}) {
  const cardId = useId();
  const [localTab, setTab] = useState<QueueTab>(() => initialQueueContext?.tab ?? initialQueueTab);
  const tab = queueTab ?? localTab;
  const [query, setQuery] = useState(() => initialQueueContext?.query ?? "");
  const [assignment, setAssignment] = useState<QueueAssignee>(() => initialQueueContext?.assignee ?? "all");
  const [offset, setOffset] = useState(() => initialQueueContext?.tab === tab ? (Math.max(1, initialQueueContext.page) - 1) * 10 : 0);
  const [offsetTab, setOffsetTab] = useState(tab);
  if (offsetTab !== tab) {
    setOffsetTab(tab);
    setOffset(0);
  }
  const [searchResetKey, setSearchResetKey] = useState(0);
  const [requestRevision, setRequestRevision] = useState(0);
  const [localSelectedId, setSelectedId] = useState<number>();
  const selectedId = selectedConversationId === undefined ? localSelectedId : selectedConversationId;
  const [busyId, setBusyId] = useState<number>();
  const filters = useMemo(() => ({ ...tabFilters(tab), q: query || undefined, responsible_id: assignment === "mine" ? currentUserId : undefined, limit: 10, offset }), [tab, query, assignment, currentUserId, offset]);
  const fetchConversations = useCallback(() => listConversations(filters), [filters, refreshKey]);
  const fetchKey = `${refreshKey}:${requestRevision}:${JSON.stringify(filters)}`.split("").reduce((hash, char) => (hash * 31 + char.charCodeAt(0)) >>> 0, 0);
  const fetched = useAsyncData(fetchConversations, controlledData === undefined, fetchKey);
  const data = controlledData ?? fetched.data;
  const state = controlledState ?? (controlledData !== undefined ? "ready" : fetched.state);
  const retry = onRetry ?? fetched.retry;
  const rows = useMemo(() => [...(data?.items ?? data?.conversations ?? [])].sort((a, b) => priority(a) - priority(b) || (b.last_message_at ?? "").localeCompare(a.last_message_at ?? "") || b.id - a.id), [data]);
  const visibleRows = rows;
  const counts = data?.counts ?? { all: rows.length, human: rows.filter((r) => r.state === "human").length, emergency: rows.filter((r) => r.emergency).length, case: rows.filter((r) => r.case_id != null).length, closed: rows.filter((r) => r.state === "closed").length };
  const [connection, setConnection] = useState<ConnectionStatus>("disconnected");

  useEffect(() => {
    if (controlledData !== undefined) return;
    const snapshotRefresh = coalesceSnapshotRefresh(retry);
    const unsubscribe = realtimeClient.subscribe((event) => { if (["conversation", "message"].includes(event.type)) retry(); if (event.type === "snapshot") snapshotRefresh(); });
    const unsubscribeStatus = realtimeClient.subscribeStatus(setConnection);
    const unregisterRecovery = realtimeClient.registerRecovery(async () => { await Promise.all([listConversations(filters), listActiveConversations()]); retry(); });
    realtimeClient.connect();
    return () => { unsubscribe(); unsubscribeStatus(); unregisterRecovery(); snapshotRefresh.cancel(); };
  }, [controlledData, filters, retry]);

  const runAction = async (id: number, action: () => Promise<unknown>) => { setBusyId(id); try { await action(); retry(); } finally { setBusyId(undefined); } };
  const nameFor = (c: Conversation) => c.customer?.name ?? customerName?.(c.customer_id) ?? `Cliente #${c.customer_id}`;
  const openThread = (c: Conversation) => { setSelectedId(c.id); onOpenThread?.(c.id); };
  const menuItems = (c: Conversation): MenuItem[] => [
    ...(c.emergency && !c.acknowledged_at && c.case_id != null ? [{ value: "acknowledge", label: "Reconocer emergencia" }] : []),
    ...(c.state === "human"
      ? [
          { value: "to-bot", label: "Devolver al agente" },
          { value: "close", label: "Cerrar conversación" },
        ]
      : []),
  ];
  const rowActions = (c: Conversation) => <div className="table__actions conversations-list__actions">
    {c.state === "bot" ? <Button variant="secondary" disabled={busyId === c.id} onClick={() => void runAction(c.id, () => takeConversation(c.id, c.version ?? 0))}><UserRoundPlus aria-hidden="true" />Tomar conversación</Button> : null}
    {menuItems(c).length ? <Menu trigger="icon" align="end" collisionPadding={8} label={`Acciones para ${nameFor(c)}`} disabled={busyId === c.id} items={menuItems(c)} onSelect={(value) => {
      if (value === "acknowledge") void runAction(c.id, () => acknowledgeCase(c.case_id!));
      else if (value === "to-bot") void runAction(c.id, () => changeConversationState(c.id, "bot", c.version ?? 0));
      else if (value === "close") void runAction(c.id, () => changeConversationState(c.id, "closed", c.version ?? 0));
    }} /> : null}
  </div>;
  const columns: Column<Conversation>[] = [
    { key: "identity", header: "Cliente y conversación", width: "38%", render: (c) => {
      const name = nameFor(c);
      return <div className="table__resource"><Avatar name={name} className="table__resource-avatar" /><div className="table__resource-body"><button type="button" className="table__resource-name conversations-list__identity" data-testid={`conversation-row-${c.id}`} aria-label={`Abrir conversación #${c.id}`} aria-current={selectedId === c.id ? "page" : undefined} onClick={() => openThread(c)}>{name}</button><span className="table__resource-meta">{c.customer?.phone_e164 ?? c.wa_phone ?? "—"} · #{c.id}</span><span className="conversations-list__summary">{c.summary ? plainSummary(c.summary) : "Sin resumen disponible"}</span></div></div>;
    } },
    { key: "state", header: "Estado y prioridad", render: conversationBadges },
    { key: "case", header: "Caso", render: (c) => c.case_id != null ? <Badge tone="neutral">Caso #{c.case_id}</Badge> : "—" },
    { key: "activity", header: "Última actividad", render: (c) => activityCell(c.last_message_at) },
  ];
  const tabs = [
    { id: "all", label: <>Todas <span>{counts.all}</span></> },
    { id: "human", label: <>Atención humana <span>{counts.human}</span></> },
    { id: "emergency", label: <>Emergencias <span>{counts.emergency}</span></> },
    { id: "case", label: <>Con caso <span>{counts.case}</span></> },
    { id: "closed", label: <>Cerradas <span>{counts.closed}</span></> },
  ];
  const total = data?.total ?? rows.length;
  const limit = data?.limit ?? 10;
  const page = Math.floor(offset / limit) + 1;
  const pageCount = Math.max(1, Math.ceil(total / limit));
  const rangeStart = total === 0 ? 0 : offset + 1;
  const rangeEnd = Math.min(offset + visibleRows.length, total);
  const clearSearch = () => { setQuery(""); setOffset(0); setSearchResetKey((key) => key + 1); };
  const clearAssignee = () => { setAssignment("all"); setOffset(0); };
  const changeTab = (nextTab: QueueTab) => { setTab(nextTab); setOffset(0); onQueueTabChange?.(nextTab); };
  const clearFilters = () => { clearAssignee(); if (tab !== "all") changeTab("all"); };
  const activeFilters = [
    ...(tab === "all" ? [] : [{ label: queueTabLabels[tab], remove: () => changeTab("all") }]),
    ...(query ? [{ label: `Búsqueda: ${query}`, text: "Búsqueda", remove: clearSearch }] : []),
    ...(assignment === "mine" ? [{ label: "Asignadas a mí", remove: clearAssignee }] : []),
  ];
  useEffect(() => { onQueueContextChange?.({ tab, query, assignee: assignment, page }); }, [assignment, onQueueContextChange, page, query, tab]);
  const emptyState = activeFilters.length
    ? <EmptyState title="No encontramos conversaciones con estos filtros" description={query ? "Prueba otra búsqueda o elimina el texto ingresado." : "Quita los filtros para volver a la bandeja completa."} action={<Button variant="secondary" onClick={query ? clearSearch : clearFilters}>{query ? "Limpiar búsqueda" : "Quitar filtros"}</Button>} />
    : <EmptyState title={data?.items === undefined ? "No hay registros" : "No hay conversaciones"} description="No existen conversaciones para mostrar." />;
  return <PageFrame className="conversations-page" title="Conversaciones" titleAdornment={<Badge>{total}</Badge>} subtitle="Revisa y gestiona la atención de tus clientes." meta={data ? undefined : "Cola de conversaciones"} state={stateMessage(state, fetched.error)}>
      {connection !== "connected" ? <p className="conversations-offline" role="status"><Icon icon={WifiOff} aria-hidden="true" /><strong>{connection === "reconnecting" ? "Reconectando la conexión en tiempo real." : "Sin conexión en tiempo real."}</strong><span>Los datos guardados siguen disponibles.</span></p> : null}
      <section className="conversations-list__queue" aria-label="Filtros de conversaciones"><Tabs tabs={tabs} activeTab={tab} onTabChange={(value) => changeTab(value as QueueTab)} ariaLabel="Cola de conversaciones">{() => <div className="table-card conversations-list__card">
        <div className="table-toolbar"><SearchInput key={searchResetKey} defaultValue={query} aria-label="Buscar conversaciones" placeholder="Buscar cliente, teléfono o resumen" onSearch={(value) => { setQuery(value); setOffset(0); setRequestRevision((revision) => revision + 1); }} />{currentUserId !== undefined ? <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <button type="button" className="conversations-list__filter" aria-label={`Filtrar por responsable: ${assignment === "all" ? "Todos" : "Asignadas a mí"}`}><Icon icon={UserRound} size="sm" aria-hidden="true" /><span className="conversations-list__filter-label">Responsable:</span><span className="conversations-list__filter-value">{assignment === "all" ? "Todos" : "Asignadas a mí"}</span><ChevronDown aria-hidden="true" /></button>
          </DropdownMenu.Trigger>
          <DropdownMenu.Portal>
            <DropdownMenu.Content className="menu__content conversations-list__filter-menu" align="start" sideOffset={4} collisionPadding={8}>
              <DropdownMenu.RadioGroup value={assignment} onValueChange={(value) => { setAssignment(value as QueueAssignee); setOffset(0); setRequestRevision((revision) => revision + 1); }}>
                <DropdownMenu.RadioItem className="menu__item" value="all">Todos<DropdownMenu.ItemIndicator className="conversations-list__filter-check"><Check aria-hidden="true" /></DropdownMenu.ItemIndicator></DropdownMenu.RadioItem>
                <DropdownMenu.RadioItem className="menu__item" value="mine">Asignadas a mí<DropdownMenu.ItemIndicator className="conversations-list__filter-check"><Check aria-hidden="true" /></DropdownMenu.ItemIndicator></DropdownMenu.RadioItem>
              </DropdownMenu.RadioGroup>
            </DropdownMenu.Content>
          </DropdownMenu.Portal>
        </DropdownMenu.Root> : null}{state === "error" || state === "fatal-error" || state === "denied" ? <Button variant="secondary" onClick={retry}>Reintentar</Button> : null}</div>
        {activeFilters.length ? <div className="conversations-list__applied-filters" role="group" aria-label="Filtros aplicados">{activeFilters.map((filter) => <button key={filter.label} type="button" className="conversations-list__filter-chip" aria-label={`Quitar filtro ${filter.label}`} onClick={filter.remove}><span>{"text" in filter ? filter.text : filter.label}</span><Icon icon={X} size="sm" aria-hidden="true" /></button>)}</div> : null}
        {state === "ready" && visibleRows.length === 0 ? emptyState : state === "ready" ? <>{!compact ? <div className="table-card__desktop"><DataTable columns={columns} rows={visibleRows} rowKey={(c) => String(c.id)} actions={rowActions} /></div> : null}<ul className={`table-cards ${compact ? "conversations-list__compact" : "table-cards--mobile"}`} aria-label="Lista de conversaciones">
          {visibleRows.map((c) => {
            const name = nameFor(c);
            const descriptionId = `${cardId}-${c.id}`;
            return <li key={c.id} className="table-card__item conversations-list__mobile-card" data-testid={`conversation-card-${c.id}`}>
              <button
                type="button"
                className="conversations-list__open"
                aria-label={`Abrir conversación de ${name}`}
                aria-describedby={descriptionId}
                aria-current={selectedId === c.id ? "page" : undefined}
                onClick={() => openThread(c)}
              >
                <Avatar name={name} className="table__resource-avatar" />
                <span className="conversations-list__row-copy">
                  <span className="conversations-list__row-name">{name}</span>
                  <span id={descriptionId} className="conversations-list__row-details">
                    <span className="conversations-list__summary">{c.summary ? plainSummary(c.summary) : "Sin resumen disponible"}</span>
                    <span className="conversations-list__mobile-meta">
                      {conversationBadges(c)}
                      {c.case_id != null ? <span className="conversations-list__case">Caso #{c.case_id}</span> : null}
                      {activityCell(c.last_message_at)}
                    </span>
                  </span>
                </span>
                <Icon icon={ChevronRight} size="sm" />
              </button>
              {rowActions(c)}
            </li>;
          })}
        </ul></> : null}
        {state === "ready" ? <footer className="table-footer"><span className="table-footer__count">Mostrando {rangeStart}–{rangeEnd} de {total} conversaciones</span>{pageCount > 1 ? <Pagination page={page} pageCount={pageCount} onPageChange={(nextPage) => setOffset((nextPage - 1) * limit)} ariaLabel="Paginación de conversaciones" /> : null}</footer> : null}
      </div>}</Tabs></section>
   </PageFrame>;
}
