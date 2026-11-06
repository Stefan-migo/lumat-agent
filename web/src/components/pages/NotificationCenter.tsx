import { useCallback, useState } from "react";
import { ApiError, listNotifications, markNotificationRead } from "../../api";
import { useAsyncData } from "../../hooks/useAsyncData";
import type { PanelNotification, NotificationsResponse } from "../../types";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { EmptyState } from "../shared/EmptyState";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import "./NotificationCenter.css";

interface NotificationCenterProps {
  onNotificationRead?: (id: number, readAt: string | null) => void;
}

function formatNotificationTime(createdAt: string | null): string {
  if (!createdAt) return "Fecha no disponible";
  const date = new Date(createdAt);
  if (!Number.isFinite(date.getTime())) return "Fecha no disponible";
  return new Intl.DateTimeFormat("es-CL", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

function notificationSourceLabel(source: string): string {
  // Only these four values are emitted today (`scheduling.py`, `emergency.py`, `costs.py`,
  // `notifications.py`). Anything else is humanised instead of printed raw, because the page is
  // operator-facing and DESIGN_SYSTEM forbids exposing machine identifiers.
  const labels: Record<string, string> = {
    appointment: "Agenda", emergencia: "Emergencias", cost_alert: "Costos", notification_failure: "Fallos de notificación",
  };
  return labels[source] ?? source.replace(/_/g, " ").replace(/^./, (character) => character.toUpperCase());
}

function notificationChannelLabel(channel: string | null): string {
  if (!channel) return "Sin canal";
  const labels: Record<string, string> = { panel: "Panel", push: "Notificación push", email: "Correo electrónico", whatsapp: "WhatsApp", fallback: "Canal alternativo" };
  return labels[channel] ?? channel.replace(/_/g, " ").replace(/^./, (character) => character.toUpperCase());
}

export function NotificationCenter({ onNotificationRead }: NotificationCenterProps) {
  const [unread, setUnread] = useState(false);
  const [optimisticReadAt, setOptimisticReadAt] = useState<Record<number, string>>({});
  const [pendingIds, setPendingIds] = useState<number[]>([]);
  const [actionErrors, setActionErrors] = useState<Record<number, string>>({});
  const fetcher = useCallback(() => listNotifications({ unread: unread || undefined }), [unread]);
  const data = useAsyncData<NotificationsResponse>(fetcher, true, unread ? 1 : 0);
  const rows = (data.data?.notifications ?? []).map((row): PanelNotification => ({
    ...row,
    read_at: optimisticReadAt[row.id] ?? row.read_at,
  })).filter((row) => !unread || row.read_at === null);
  const state = data.state === "loading"
    ? <StateMessage tone="info" role="status" spinner title="Cargando notificaciones" />
    : data.state === "denied"
      ? <StateMessage tone="warning" role="alert" title="No tienes permiso para ver las notificaciones" />
      : data.state === "error"
        ? <StateMessage tone="danger" role="alert" title={data.error instanceof ApiError && data.error.status === 401 ? "Sesión requerida" : "No pudimos cargar las notificaciones"} />
        : null;

  const markRead = async (row: PanelNotification) => {
    if (pendingIds.includes(row.id)) return;
    const readAt = new Date().toISOString();
    setPendingIds((current) => [...current, row.id]);
    setActionErrors((current) => ({ ...current, [row.id]: "" }));
    setOptimisticReadAt((current) => ({ ...current, [row.id]: readAt }));
    onNotificationRead?.(row.id, readAt);
    try {
      const response = await markNotificationRead(row.id);
      const reconciledReadAt = response.notification.read_at ?? readAt;
      setOptimisticReadAt((current) => ({ ...current, [row.id]: reconciledReadAt }));
      onNotificationRead?.(row.id, reconciledReadAt);
    } catch {
      setOptimisticReadAt((current) => {
        const next = { ...current };
        delete next[row.id];
        return next;
      });
      onNotificationRead?.(row.id, row.read_at);
      setActionErrors((current) => ({ ...current, [row.id]: "No pudimos marcar la notificación como leída. Inténtalo nuevamente." }));
    } finally {
      setPendingIds((current) => current.filter((id) => id !== row.id));
    }
  };

  return <PageFrame
    title="Notificaciones"
    subtitle="Revisa las novedades de tus conversaciones, visitas y documentos."
    meta={data.data ? `${rows.length} notificaciones` : "Notificaciones del panel"}
    state={state}
    className="notification-center-page"
  >
    <section className="notification-center__surface" aria-label="Centro de notificaciones">
      <div className="notification-center__toolbar">
        <label className="notification-center__filter">
          <input type="checkbox" checked={unread} onChange={(event) => setUnread(event.target.checked)} />
          <span>Solo no leídas</span>
        </label>
        {data.data ? <span className="notification-center__count">{rows.length} {rows.length === 1 ? "notificación" : "notificaciones"}</span> : null}
      </div>
      {data.state === "ready" && rows.length === 0
        ? <EmptyState
            title={unread ? "No hay notificaciones no leídas" : "No hay notificaciones"}
            description={unread ? "Todas tus notificaciones están leídas." : "Aquí verás las novedades de tus conversaciones, visitas y documentos."}
          />
        : rows.length > 0
          ? <ul className="notification-center__list" aria-label="Notificaciones">
              {rows.map((row) => {
                const time = formatNotificationTime(row.created_at);
                return <li key={row.id} className={`notification-center__row${row.read_at ? " notification-center__row--read" : " notification-center__row--unread"}`}>
                  <div className="notification-center__row-heading">
                    <h2 className="notification-center__title">{row.title}</h2>
                    <Badge tone={row.read_at ? "neutral" : "warning"} className="notification-center__status">{row.read_at ? "Leída" : "Sin leer"}</Badge>
                  </div>
                  <p className="notification-center__content">{row.content}</p>
                  <div className="notification-center__meta">
                    <span>Origen: {notificationSourceLabel(row.source)}</span>
                    <span>Canal: {notificationChannelLabel(row.channel)}</span>
                    <time dateTime={row.created_at ?? undefined}>{time}</time>
                  </div>
                  {actionErrors[row.id] ? <p className="notification-center__action-error" role="alert">{actionErrors[row.id]}</p> : null}
                  {!row.read_at ? <Button
                    variant="secondary"
                    className="notification-center__read-action"
                    disabled={pendingIds.includes(row.id)}
                    onClick={() => void markRead(row)}
                  >{pendingIds.includes(row.id) ? "Marcando…" : "Marcar como leída"}</Button> : null}
                </li>;
              })}
            </ul>
          : null}
    </section>
  </PageFrame>;
}
