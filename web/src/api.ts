/** Thin JSON fetch layer for the panel SPA (PDW-AUTH-1, PDW-AUTH-3, D4).
 *
 * Same-origin only: `credentials: 'include'` round-trips the HttpOnly session
 * cookie over the Vite proxy in dev and the nginx static host in prod. The
 * JSON-401 deps never issue redirects (D4), so the SPA never follows one to
 * the HTML login page (PDW-AUTH-1). No CORS (D1).
 */

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const res = await fetch(path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

  if (!res.ok) {
    const raw = await res.text().catch(() => '');
    let detail = raw.trim();
    try {
      const payload = JSON.parse(raw) as { detail?: unknown };
      if (typeof payload.detail === 'string') {
        detail = payload.detail;
      }
    } catch {
      // keep the raw text when the body is not JSON
    }
    throw new ApiError(res.status, detail || `${res.status} ${res.statusText}`.trim());
  }

  return (await res.json()) as T;
}

export function postJson<T>(path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: 'POST',
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

import type { AdvancedDashboardData, AgendaResponse, Conversation, ConversationsResponse, ConversationState, ConversationThread, Message, NotificationsResponse, PanelNotification, InternalChatResponse, InternalChatMessage } from './types';
export interface ConversationFilters { state?: ConversationState; responsible_id?: number; }
const requestId = () => globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
const command = <T>(path: string, body: unknown) => postJson<T>(path, body);
export function listConversations(filters: ConversationFilters = {}) {
  const params = new URLSearchParams();
  if (filters.state) params.set('state', filters.state);
  if (filters.responsible_id !== undefined) params.set('responsible_id', String(filters.responsible_id));
  const query = params.toString();
  return apiFetch<ConversationsResponse>(`/panel/api/conversations${query ? `?${query}` : ''}`);
}
export const getConversation = (id: number) => apiFetch<ConversationThread>(`/panel/api/conversations/${id}`);
export const changeConversationState = (id: number, state: ConversationState, expected_version: number) => command<{ ok: true; conversation: Conversation }>(`/panel/api/conversations/${id}/state`, { state, expected_version, request_id: requestId() });
export const sendMessage = (id: number, body: { text: string; request_id?: string }) => command<{ ok: true; message: Message }>(`/panel/api/conversations/${id}/messages`, { ...body, request_id: body.request_id ?? requestId() });
export const retryMessage = (id: number, messageId: number) => command<{ ok: true; message: Message }>(`/panel/api/conversations/${id}/messages/${messageId}/retry`, { expected_status: 'failed', request_id: requestId() });
export interface NotificationFilters { unread?: boolean; status?: string; source?: string; }
export function listNotifications(filters: NotificationFilters = {}) { const params = new URLSearchParams(); if (filters.unread !== undefined) params.set('unread', String(filters.unread)); if (filters.status) params.set('status', filters.status); if (filters.source) params.set('source', filters.source); const query = params.toString(); return apiFetch<NotificationsResponse>(`/panel/api/notifications${query ? `?${query}` : ''}`); }
export const markNotificationRead = (id: number) => postJson<{ notification: PanelNotification }>(`/panel/api/notifications/${id}/read`);
export const createChatThread = () => postJson<InternalChatResponse>('/panel/api/chat/threads', {});
export const sendChatMessage = (id: number, content: string) => postJson<{ message: InternalChatMessage }> (`/panel/api/chat/threads/${id}/messages`, { content });
export const getChatThread = (id: number) => apiFetch<InternalChatResponse>(`/panel/api/chat/threads/${id}`);
export function listAppointments(from: string, to: string, timezone: string): Promise<AgendaResponse> {
  const params = new URLSearchParams({ from, to, timezone });
  return apiFetch<AgendaResponse>(`/panel/api/appointments?${params.toString()}`);
}
export function cancelAppointment(id: number, reason?: string) {
  return postJson<{ ok: true; appointment: unknown }>(`/panel/api/appointments/${id}/cancel`, { reason });
}
export function retryCalendarSync(id: number) {
  return postJson<{ ok: boolean; calendar: { status: string; error: string | null } }>(`/panel/api/appointments/${id}/calendar/sync`);
}
export function getAdvancedDashboard(): Promise<AdvancedDashboardData> {
  const end = new Date();
  const start = new Date(end.getTime() - 7 * 24 * 60 * 60 * 1000);
  const params = new URLSearchParams({ start: start.toISOString(), end: end.toISOString(), timezone: Intl.DateTimeFormat().resolvedOptions().timeZone, metric: 'cases', bucket: 'day' });
  const base = params.toString();
  return Promise.all([
    apiFetch<Pick<AdvancedDashboardData, 'period' | 'metrics'>>(`/panel/api/dashboard/summary?${base}`),
    apiFetch<Pick<AdvancedDashboardData, 'trend'>>(`/panel/api/dashboard/trend?${base}`),
  ]).then(([summary, trend]) => ({ ...summary, ...trend }));
}
