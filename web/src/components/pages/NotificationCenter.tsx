import { useMemo } from 'react';
import type { PanelNotification } from '../../types';
import type { NotificationState } from '../domain/PanelShell';
import { notificationDestination } from '../domain/panelRoutes';
import { notificationChannelLabel, notificationSourcePresentation } from '../../notifications/labels';
import { Badge } from '../primitives/Badge';
import { Button } from '../primitives/Button';
import { Icon } from '../primitives/Icon';
import { EmptyState } from '../shared/EmptyState';
import { PageFrame } from '../shared/PageFrame';
import { StateMessage } from '../shared/StateMessage';
import './NotificationCenter.css';

interface NotificationCenterProps {
  notifications: PanelNotification[];
  state: NotificationState;
  unreadOnly: boolean;
  onUnreadOnlyChange: (unreadOnly: boolean) => void;
  onMarkRead: (id: number) => void | Promise<void>;
  pendingReadIds: number[];
  readErrors: Record<number, string>;
  onOpenNotification: (notification: PanelNotification) => void;
}

function formatNotificationTime(createdAt: string | null): string {
  if (!createdAt) return 'Fecha no disponible';
  const date = new Date(createdAt);
  if (!Number.isFinite(date.getTime())) return 'Fecha no disponible';
  return new Intl.DateTimeFormat('es-CL', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

export function NotificationCenter({ notifications, state, unreadOnly, onUnreadOnlyChange, onMarkRead, pendingReadIds, readErrors, onOpenNotification }: NotificationCenterProps) {
  const rows = useMemo(() => unreadOnly ? notifications.filter((row) => row.read_at === null) : notifications, [notifications, unreadOnly]);
  const error = state.status === 'error'
    ? <StateMessage tone="danger" role="alert" title="No pudimos cargar las notificaciones" />
    : null;
  const loading = state.status === 'loading'
    ? <StateMessage tone="info" role="status" spinner title="Cargando notificaciones" />
    : error;

  return <PageFrame
    title="Notificaciones"
    subtitle="Avisos de visitas, emergencias, alertas de costo y fallos de notificación."
    meta={`${rows.length} ${rows.length === 1 ? 'notificación' : 'notificaciones'}`}
    state={loading}
    className="notification-center-page"
  >
    <section className="notification-center__surface" aria-label="Centro de notificaciones">
      <div className="notification-center__toolbar">
        <label className="notification-center__filter">
          <input type="checkbox" checked={unreadOnly} onChange={(event) => onUnreadOnlyChange(event.target.checked)} />
          <span>Solo no leídas</span>
        </label>
        {state.status === 'ready' ? <span className="notification-center__count">{rows.length} {rows.length === 1 ? 'notificación' : 'notificaciones'}</span> : null}
      </div>
      {state.status === 'ready' && rows.length === 0
        ? <EmptyState
            title={unreadOnly ? 'No hay notificaciones no leídas' : 'No hay notificaciones'}
            description={unreadOnly ? 'Todas tus notificaciones están leídas.' : 'Aquí verás avisos de visitas, emergencias, alertas de costo y fallos de notificación.'}
          />
        : rows.length > 0
          ? <ul className="notification-center__list" aria-label="Notificaciones">
              {rows.map((row) => {
                const time = formatNotificationTime(row.created_at);
                const source = notificationSourcePresentation(row.source);
                const destination = notificationDestination(row.source_entity, row.source_id);
                const pending = pendingReadIds.includes(row.id);
                return <li key={row.id} className={`notification-center__row${row.read_at ? ' notification-center__row--read' : ' notification-center__row--unread'}`}>
                  <div className="notification-center__row-heading">
                    {destination
                      ? <button type="button" className="notification-center__title notification-center__open" aria-label={`${row.title}. Ir a ${destination.view === 'agenda' ? 'la visita' : 'la conversación'}`} onClick={() => onOpenNotification(row)}>{row.title}</button>
                      : <h2 className="notification-center__title">{row.title}</h2>}
                    <Badge tone={row.read_at ? 'neutral' : 'warning'} className="notification-center__status">{row.read_at ? 'Leída' : 'Sin leer'}</Badge>
                  </div>
                  <p className="notification-center__content">{row.content}</p>
                  <div className="notification-center__meta">
                    <span><Icon icon={source.icon} size="sm" aria-hidden="true" />Origen: {source.label}</span>
                    <span>Canal: {notificationChannelLabel(row.channel)}</span>
                    <time dateTime={row.created_at ?? undefined}>{time}</time>
                  </div>
                  {readErrors[row.id] ? <p className="notification-center__action-error" role="alert">{readErrors[row.id]}</p> : null}
                  {!row.read_at ? <Button
                    variant="secondary"
                    className="notification-center__read-action"
                    disabled={pending}
                    onClick={() => void onMarkRead(row.id)}
                  >{pending ? 'Marcando…' : 'Marcar como leída'}</Button> : null}
                </li>;
              })}
            </ul>
          : null}
    </section>
  </PageFrame>;
}
