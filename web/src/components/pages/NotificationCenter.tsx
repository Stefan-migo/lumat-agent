import { useCallback, useState } from "react";
import { ApiError, listNotifications, markNotificationRead } from "../../api";
import { useAsyncData } from "../../hooks/useAsyncData";
import type { NotificationsResponse } from "../../types";
import { EmptyState } from "../shared/EmptyState";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";

export function NotificationCenter() {
  const [unread, setUnread] = useState(false);
  const fetcher = useCallback(() => listNotifications({ unread: unread || undefined }), [unread]);
  const data = useAsyncData<NotificationsResponse>(fetcher, true, unread ? 1 : 0);
  const rows = data.data?.notifications ?? [];
  const state = data.state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando notificaciones" /> : data.state === "error" ? <StateMessage tone="danger" role="alert" title={data.error instanceof ApiError && data.error.status === 401 ? "Sesión requerida" : "No pudimos cargar las notificaciones"} /> : null;
  return <PageFrame title="Notificaciones" meta={data.data ? `${rows.length} notificaciones` : undefined} state={state}>
    <label><input aria-label="Filtrar no leídas" type="checkbox" checked={unread} onChange={(event) => setUnread(event.target.checked)} /> Solo no leídas</label>
    {data.state === "ready" && rows.length === 0 ? <EmptyState title="No hay notificaciones" description="No existen notificaciones para mostrar." /> : <ul>{rows.map((row) => <li key={row.id}><strong>{row.title}</strong><p>{row.content}</p><small>{row.source} · {row.channel ?? "fallback"} · {row.status}</small>{row.read_at ? null : <button type="button" onClick={() => void markNotificationRead(row.id)}>Marcar como leída</button>}</li>)}</ul>}
  </PageFrame>;
}
