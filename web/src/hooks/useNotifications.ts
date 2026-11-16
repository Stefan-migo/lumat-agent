import { useCallback, useEffect, useRef, useState } from 'react';
import { listNotifications, markAllNotificationsRead, markNotificationRead } from '../api';
import type { PanelNotification } from '../types';
import { realtimeClient } from '../realtime';
import type { NotificationState } from '../components/domain/PanelShell';

const NOTIFICATION_EVENT_DEBOUNCE_MS = 600;
const READ_FAILURE = 'No pudimos marcar la notificación como leída. Inténtalo nuevamente.';
const READ_ALL_FAILURE = 'No pudimos marcar todas las notificaciones como leídas. Inténtalo nuevamente.';

export function useNotifications() {
  const [notifications, setNotifications] = useState<PanelNotification[]>([]);
  const [state, setState] = useState<NotificationState>({ status: 'loading' });
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [markAllPending, setMarkAllPending] = useState(false);
  const [markAllError, setMarkAllError] = useState<string | null>(null);
  const [pendingReadIds, setPendingReadIds] = useState<number[]>([]);
  const [readErrors, setReadErrors] = useState<Record<number, string>>({});
  const confirmedReads = useRef(new Map<number, string>());
  const optimisticReads = useRef(new Map<number, string>());
  const markAllLock = useRef(false);
  const readLocks = useRef(new Set<number>());
  const requestSequence = useRef(0);
  const mounted = useRef(true);

  const refresh = useCallback(async () => {
    const sequence = ++requestSequence.current;
    try {
      const response = await listNotifications();
      if (!mounted.current || sequence !== requestSequence.current) return;
      const merged = response.notifications.map((item) => {
        const readAt = confirmedReads.current.get(item.id) ?? optimisticReads.current.get(item.id);
        return readAt && item.read_at === null ? { ...item, read_at: readAt } : item;
      });
      setNotifications(merged);
      setState({ status: 'ready', unread: merged.filter((item) => item.read_at === null).length });
    } catch {
      if (mounted.current && sequence === requestSequence.current) setState({ status: 'error' });
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    void refresh();
    let eventTimer: ReturnType<typeof setTimeout> | null = null;
    const unsubscribe = realtimeClient.subscribe((event) => {
      if (event.type !== 'notification') return;
      if (eventTimer !== null) clearTimeout(eventTimer);
      eventTimer = setTimeout(() => { eventTimer = null; void refresh(); }, NOTIFICATION_EVENT_DEBOUNCE_MS);
    });
    const unregisterRecovery = realtimeClient.registerRecovery(async () => { await refresh(); });
    const refreshWhenVisible = () => {
      if (document.visibilityState === 'visible') void refresh();
    };
    window.addEventListener('focus', refreshWhenVisible);
    document.addEventListener('visibilitychange', refreshWhenVisible);
    realtimeClient.connect();
    return () => {
      mounted.current = false;
      if (eventTimer !== null) clearTimeout(eventTimer);
      unsubscribe();
      unregisterRecovery();
      window.removeEventListener('focus', refreshWhenVisible);
      document.removeEventListener('visibilitychange', refreshWhenVisible);
    };
  }, [refresh]);

  // The only unread count is derived from the list, never maintained as a counter.
  useEffect(() => {
    setState((current) => current.status === 'ready'
      ? { status: 'ready', unread: notifications.filter((item) => item.read_at === null).length }
      : current);
  }, [notifications]);

  const markRead = useCallback(async (id: number) => {
    const current = notifications.find((item) => item.id === id);
    if (!current || current.read_at || readLocks.current.has(id)) return;
    readLocks.current.add(id);
    const readAt = new Date().toISOString();
    optimisticReads.current.set(id, readAt);
    setPendingReadIds((ids) => [...ids, id]);
    setReadErrors((errors) => ({ ...errors, [id]: '' }));
    setNotifications((items) => items.map((item) => item.id === id ? { ...item, read_at: readAt } : item));
    try {
      const response = await markNotificationRead(id);
      const confirmedAt = response.notification.read_at ?? readAt;
      confirmedReads.current.set(id, confirmedAt);
      optimisticReads.current.delete(id);
      setNotifications((items) => items.map((item) => item.id === id ? { ...item, read_at: confirmedAt } : item));
    } catch {
      optimisticReads.current.delete(id);
      setNotifications((items) => items.map((item) => item.id === id ? { ...item, read_at: current.read_at } : item));
      setReadErrors((errors) => ({ ...errors, [id]: READ_FAILURE }));
    } finally {
      readLocks.current.delete(id);
      setPendingReadIds((ids) => ids.filter((pendingId) => pendingId !== id));
    }
  }, [notifications]);

  const markAllRead = useCallback(async () => {
    if (markAllLock.current || notifications.every((item) => item.read_at !== null)) return;
    markAllLock.current = true;
    setMarkAllPending(true);
    setMarkAllError(null);
    const previous = notifications;
    const readAt = new Date().toISOString();
    const pendingIds = previous.filter((item) => item.read_at === null).map((item) => item.id);
    pendingIds.forEach((id) => optimisticReads.current.set(id, readAt));
    setNotifications((items) => items.map((item) => ({ ...item, read_at: item.read_at ?? readAt })));
    try {
      await markAllNotificationsRead();
      pendingIds.forEach((id) => {
        confirmedReads.current.set(id, readAt);
        optimisticReads.current.delete(id);
      });
    } catch {
      pendingIds.forEach((id) => optimisticReads.current.delete(id));
      setNotifications(previous);
      setMarkAllError(READ_ALL_FAILURE);
    } finally {
      markAllLock.current = false;
      setMarkAllPending(false);
    }
  }, [notifications]);

  const visibleNotifications = unreadOnly ? notifications.filter((item) => item.read_at === null) : notifications;
  return {
    notifications: visibleNotifications,
    allNotifications: notifications,
    state,
    unreadOnly,
    setUnreadOnly,
    markAllPending,
    markAllError,
    pendingReadIds,
    readErrors,
    refresh,
    markRead,
    markAllRead,
  };
}
