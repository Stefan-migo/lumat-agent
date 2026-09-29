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
  readonly structuredDetail?: { code?: string; message?: string; customer_id?: number; [key: string]: unknown };

  constructor(status: number, detail: string, structuredDetail?: ApiError['structuredDetail']) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.structuredDetail = structuredDetail;
  }
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const headers = options?.body instanceof FormData
    ? options.headers
    : { 'Content-Type': 'application/json', ...options?.headers };
  const res = await fetch(path, {
    credentials: 'include',
    ...options,
    headers,
  });

  if (!res.ok) {
    const raw = await res.text().catch(() => '');
    let detail = raw.trim();
    let structuredDetail: ApiError['structuredDetail'];
    try {
      const payload = JSON.parse(raw) as { detail?: unknown; candidates?: unknown };
      if (Array.isArray(payload.candidates)) structuredDetail = { candidates: payload.candidates };
      if (typeof payload.detail === 'string') {
        detail = payload.detail;
      } else if (payload.detail && typeof payload.detail === 'object' && !Array.isArray(payload.detail)) {
        structuredDetail = payload.detail as NonNullable<ApiError['structuredDetail']>;
      }
    } catch {
      // keep the raw text when the body is not JSON
    }
    throw new ApiError(res.status, detail || `${res.status} ${res.statusText}`.trim(), structuredDetail);
  }

  return (await res.json()) as T;
}

export function postJson<T>(path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: 'POST',
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}
export function patchJson<T>(path: string, body: unknown): Promise<T> {
  return apiFetch<T>(path, { method: 'PATCH', body: JSON.stringify(body) });
}

import type { DocsResponse, KbDocument, KbMutationResponse, KbSearchResponse, KbVisibility, CustomerCreateRequest, CustomerProfileUpdateRequest, CustomerMutationResponse, ClientFichaResponse, CustomerEquipment, ClientMergePreview, ClientMergeResponse } from './types';
export const uploadKbDocument = (title: string, file: File, visibility: KbVisibility) => {
  const body = new FormData();
  body.append('title', title);
  body.append('file', file);
  body.append('visibility', visibility);
  return apiFetch<KbMutationResponse>('/panel/api/kb', { method: 'POST', body });
};
export const editKbDocument = (id: number, body: { title: string; content: string }) => postJson<KbMutationResponse>(`/panel/api/kb/${id}/edit`, body);
export const disableKbDocument = (id: number) => postJson<KbMutationResponse>(`/panel/api/kb/${id}/disable`);
export const restoreKbDocument = (id: number, version: number) => postJson<KbMutationResponse>(`/panel/api/kb/${id}/restore`, { version });
export const setKbVisibility = (id: number, visibility: KbVisibility) => postJson<KbMutationResponse>(`/panel/api/kb/${id}/visibility`, { visibility });
export const refreshKbDocuments = () => apiFetch<DocsResponse>('/panel/api/kb');
export const getKbDocument = (id: number) => apiFetch<KbDocument>(`/panel/api/kb/${id}`);
export function searchKb({ q, topK, minSim }: { q: string; topK: number; minSim: number }) {
  const params = new URLSearchParams({ q, top_k: String(topK), min_sim: String(minSim) });
  return apiFetch<KbSearchResponse>(`/panel/api/kb/search?${params.toString()}`);
}

import type { ActiveConversationsResponse, AdminUser, AdminUsersResponse, AdvancedDashboardData, AgendaResponse, AppointmentCreateRequest, AppointmentDetail, AppointmentMutationResponse, AssistantAttachment, AssistantCapabilities, AutomationRuleResponse, AutomationRulesResponse, CasesResponse, Conversation, ConversationsResponse, ConversationState, ConversationThread, Customer, Message, NotificationsResponse, PanelNotification, InternalChatResponse, InternalChatMessage, InternalChatThread, InternalChatThreadsResponse, AssistantEvent, Rule, ClientNoteMutationResponse, ClientStateMutationResponse, CustomerState, DashboardDrilldownRow, DashboardTrendBucket, DashboardToday, TechnicianAgendaResponse, ProjectsResponse, ProjectDetailResponse, ProjectCreateRequest, ProjectCreateResponse, PlanningSessionsResponse, PlanningSessionOpenResponse, PlanningSessionCloseResponse, PlanningSessionDetailResponse, MemoryRelation, MemoryRelationKind, Case, ManualCaseRequest, TechniciansResponse } from './types';
export interface ConversationFilters { state?: ConversationState; responsible_id?: number; q?: string; limit?: number; offset?: number; }
const requestId = () => globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
const command = <T>(path: string, body: unknown) => postJson<T>(path, body);
export function listConversations(filters: ConversationFilters = {}) {
  const params = new URLSearchParams();
  if (filters.state) params.set('state', filters.state);
  if (filters.responsible_id !== undefined) params.set('responsible_id', String(filters.responsible_id));
  if (filters.q) params.set('q', filters.q);
  if (filters.limit !== undefined) params.set('limit', String(filters.limit));
  if (filters.offset !== undefined) params.set('offset', String(filters.offset));
  const query = params.toString();
  return apiFetch<ConversationsResponse>(`/panel/api/conversations${query ? `?${query}` : ''}`);
}
export const takeConversation = (id: number, expected_version: number) => changeConversationState(id, 'human', expected_version);
export const acknowledgeCase = (id: number) => postJson<{ ok: true; case: unknown }>(`/panel/api/cases/${id}/ack`);
export const listActiveConversations = () => apiFetch<ActiveConversationsResponse>('/panel/api/conversations/active');
export const getConversation = (id: number, messagesLimit?: number) => apiFetch<ConversationThread>(`/panel/api/conversations/${id}${messagesLimit ? `?messages_limit=${messagesLimit}` : ""}`);
export const changeConversationState = (id: number, state: ConversationState, expected_version: number) => command<{ ok: true; conversation: Conversation }>(`/panel/api/conversations/${id}/state`, { state, expected_version, request_id: requestId() });
export const sendMessage = (id: number, body: { text: string; request_id?: string }) => command<{ ok: true; message: Message }>(`/panel/api/conversations/${id}/messages`, { ...body, request_id: body.request_id ?? requestId() });
export const retryMessage = (id: number, messageId: number) => command<{ ok: true; message: Message }>(`/panel/api/conversations/${id}/messages/${messageId}/retry`, { expected_status: 'failed', request_id: requestId() });
export interface NotificationFilters { unread?: boolean; status?: string; source?: string; }
export function listNotifications(filters: NotificationFilters = {}) { const params = new URLSearchParams(); if (filters.unread !== undefined) params.set('unread', String(filters.unread)); if (filters.status) params.set('status', filters.status); if (filters.source) params.set('source', filters.source); const query = params.toString(); return apiFetch<NotificationsResponse>(`/panel/api/notifications${query ? `?${query}` : ''}`); }
export const markNotificationRead = (id: number) => postJson<{ notification: PanelNotification }>(`/panel/api/notifications/${id}/read`);
export const markAllNotificationsRead = () => postJson<{ ok: true; read: number }>('/panel/api/notifications/read-all');
export const createChatThread = (proyecto: string) => postJson<InternalChatResponse>('/panel/api/chat/threads', { proyecto });
export const listChatThreads = (limit: number) => apiFetch<InternalChatThreadsResponse>(`/panel/api/chat/threads?limit=${encodeURIComponent(limit)}`);
export const renameChatThread = (id: number, title: string) => apiFetch<{ thread: InternalChatThread }>(`/panel/api/chat/threads/${id}`, { method: 'PATCH', body: JSON.stringify({ title }) });
export const deleteChatThread = (id: number) => apiFetch<{ ok: true }>(`/panel/api/chat/threads/${id}`, { method: 'DELETE' });
export const sendChatMessage = (id: number, content: string, attachment_ids: number[] = []) => postJson<{ message: InternalChatMessage }> (`/panel/api/chat/threads/${id}/messages`, { content, attachment_ids });
export const uploadAssistantAttachment = (id: number, file: File) => { const body = new FormData(); body.append('file', file); return apiFetch<{ attachment: AssistantAttachment }>(`/panel/api/chat/threads/${id}/attachments`, { method: 'POST', body }); };
export const getChatThread = (id: number) => apiFetch<InternalChatResponse>(`/panel/api/chat/threads/${id}`);
export const approveChatPlan = (id: number, run_id: string, token: string, reject = false) => postJson<{ status: string; message: InternalChatMessage }>(`/panel/api/chat/threads/${id}/approval`, { run_id, token, reject });
export async function streamChatEvents(id: number, runId: string, onEvent: (event: AssistantEvent) => void): Promise<void> {
  const response = await fetch(`/panel/api/chat/threads/${id}/stream?run_id=${encodeURIComponent(runId)}`, { credentials: 'include' });
  if (!response.ok || !response.body) throw new ApiError(response.status, 'No pudimos conectar con el stream del asistente');
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  const consume = (chunk: string) => {
    buffer += chunk;
    const frames = buffer.split('\n\n');
    buffer = frames.pop() ?? '';
    frames.forEach((frame) => frame.split('\n').filter((line) => line.startsWith('data: ')).forEach((line) => onEvent(JSON.parse(line.slice(6)) as AssistantEvent)));
  };
  while (true) {
    const next = await reader.read();
    if (next.done) break;
    consume(decoder.decode(next.value, { stream: true }));
  }
  consume(decoder.decode());
}
export function listAppointments(from: string, to: string, timezone: string): Promise<AgendaResponse> {
  const params = new URLSearchParams({ from, to, timezone });
  return apiFetch<AgendaResponse>(`/panel/api/appointments?${params.toString()}`);
}
export const getAppointment = (id: number) => apiFetch<AppointmentDetail>(`/panel/api/appointments/${id}`);
export function cancelAppointment(id: number, reason?: string) {
  return postJson<{ ok: true; appointment: unknown }>(`/panel/api/appointments/${id}/cancel`, { reason });
}
export function closeAppointment(id: number, outcome: "completed" | "no_show") {
  return postJson<{ ok: true; appointment: unknown }>(`/panel/api/appointments/${id}/close`, { outcome });
}
export function rescheduleAppointment(id: number, body: { local_date: string; local_time: string; timezone: string; duration_minutes: number; technician_id: number }) {
  return patchJson<{ ok: true; appointment: unknown }>(`/panel/api/appointments/${id}`, body);
}
export function retryCalendarSync(id: number) {
  return postJson<{ ok: boolean; calendar: { status: string; error: string | null } }>(`/panel/api/appointments/${id}/calendar/sync`);
}
export const createAppointment = (body: AppointmentCreateRequest) => postJson<AppointmentMutationResponse>('/panel/api/appointments', body);
export function fetchClients({ includeArchived = false, query = '' }: { includeArchived?: boolean; query?: string } = {}) {
  const params = new URLSearchParams();
  if (query) params.set('q', query);
  if (includeArchived) params.set('include_archived', 'true');
  const search = params.toString();
  return apiFetch<{ clients: Customer[] }>(`/panel/api/clients${search ? `?${search}` : ''}`);
}
export const createCustomer = (body: CustomerCreateRequest) => postJson<CustomerMutationResponse>('/panel/api/clients', body);
export const updateCustomerProfile = (id: number, body: CustomerProfileUpdateRequest) => apiFetch<CustomerMutationResponse>(`/panel/api/clients/${id}`, { method: 'PATCH', body: JSON.stringify(body) });
export const updateCustomerConsent = (id: number, consent: boolean) => postJson<CustomerMutationResponse>(`/panel/api/clients/${id}/consent`, { consent });
export const archiveCustomer = (id: number) => postJson<CustomerMutationResponse>(`/panel/api/clients/${id}/archive`);
export const unarchiveCustomer = (id: number) => postJson<CustomerMutationResponse>(`/panel/api/clients/${id}/unarchive`);
export const getClientFicha = (id: number) => apiFetch<ClientFichaResponse>(`/panel/api/clients/${id}`);
export const previewClientMerge = (id: number, otherId: number) => apiFetch<ClientMergePreview>(`/panel/api/clients/${id}/merge-preview?with=${otherId}`);
export const mergeClient = (id: number, otherId: number) => postJson<ClientMergeResponse>(`/panel/api/clients/${id}/merge`, { other_id: otherId });
export const fetchCases = () => apiFetch<CasesResponse>('/panel/api/cases');
export const createCase = (body: ManualCaseRequest) => postJson<{ ok: true; case: Case }>('/panel/api/cases', body);
export const updateCaseAmount = (id: number, amount: number | null) => postJson<{ ok: true; case: Case }>(`/panel/api/cases/${id}/update`, { amount });
export const changeClientState = (id: number, state: CustomerState) => postJson<ClientStateMutationResponse>(`/panel/api/clients/${id}/state`, { state });
export const addClientNote = (id: number, note: string) => postJson<ClientNoteMutationResponse>(`/panel/api/clients/${id}/notes`, { note });
export type CustomerEquipmentUpdate = Partial<Pick<CustomerEquipment, 'equipment_type' | 'brand' | 'model' | 'age' | 'details'>>;
export const listClientEquipment = (clientId: number) => apiFetch<{ equipment: CustomerEquipment[] }>(`/panel/api/clients/${clientId}/equipment`);
export const createClientEquipment = (clientId: number, body: CustomerEquipmentUpdate) => postJson<{ equipment: CustomerEquipment }>(`/panel/api/clients/${clientId}/equipment`, body);
export const updateClientEquipment = (clientId: number, equipmentId: number, body: CustomerEquipmentUpdate) => patchJson<{ equipment: CustomerEquipment }>(`/panel/api/clients/${clientId}/equipment/${equipmentId}`, body);
export const resolveMemoryRelation = (customerId: number, relationId: number, relation: MemoryRelationKind) => postJson<{ ok: true; relation: MemoryRelation }>(`/panel/api/clients/${customerId}/memory-relations/${relationId}`, { relation });
export const listAutomationRules = () => apiFetch<AutomationRulesResponse>('/panel/api/automation-rules');
export const getAutomationRule = (id: number) => apiFetch<AutomationRuleResponse>(`/panel/api/automation-rules/${id}`);
export const createAutomationRule = (rule: Omit<Rule, 'id' | 'enabled' | 'created_by' | 'created_at' | 'updated_at'>) => postJson<AutomationRuleResponse>('/panel/api/automation-rules', rule);
export const updateAutomationRule = (id: number, rule: Omit<Rule, 'id' | 'enabled' | 'created_by' | 'created_at' | 'updated_at'>) => apiFetch<AutomationRuleResponse>(`/panel/api/automation-rules/${id}`, { method: 'PATCH', body: JSON.stringify(rule) });
export const enableAutomationRule = (id: number) => postJson<{ ok: true; rule: Rule }>(`/panel/api/automation-rules/${id}/enable`);
export const disableAutomationRule = (id: number) => postJson<{ ok: true; rule: Rule }>(`/panel/api/automation-rules/${id}/disable`);
export function getAdvancedDashboard(): Promise<AdvancedDashboardData> {
  const end = new Date();
  const start = new Date(end.getTime() - 7 * 24 * 60 * 60 * 1000);
  const params = new URLSearchParams({ start: start.toISOString(), end: end.toISOString(), timezone: Intl.DateTimeFormat().resolvedOptions().timeZone, metric: 'cases', bucket: 'day' });
  const base = params.toString();
  const drilldown = new URLSearchParams({ ...Object.fromEntries(params), bucket_start: start.toISOString().slice(0, 10) });
  return Promise.all([
    apiFetch<Pick<AdvancedDashboardData, 'period' | 'metrics'>>(`/panel/api/dashboard/summary?${base}`),
    apiFetch<{ buckets: DashboardTrendBucket[] }>(`/panel/api/dashboard/trend?${base}`),
    apiFetch<{ rows: DashboardDrilldownRow[] }>(`/panel/api/dashboard/drilldown?${drilldown}`),
  ]).then(([summary, trend, drilldownResponse]) => ({ ...summary, trend: trend.buckets, drilldown: drilldownResponse.rows }));
}

export const getDashboardToday = (timezone: string) => apiFetch<DashboardToday>(`/panel/api/dashboard/today?timezone=${encodeURIComponent(timezone)}`);
export const getDashboardTrend = (timezone: string) => {
  const end = new Date();
  const start = new Date(end.getTime() - 7 * 24 * 60 * 60 * 1000);
  const params = new URLSearchParams({ start: start.toISOString(), end: end.toISOString(), timezone, metric: 'contacts' });
  return apiFetch<{ buckets: DashboardTrendBucket[] }>(`/panel/api/dashboard/trend?${params}`);
};

export const fetchTechnicianAgenda = () => apiFetch<TechnicianAgendaResponse>('/panel/api/technician/agenda');
export const getAssistantCapabilities = () => apiFetch<AssistantCapabilities>('/panel/api/assistant/capabilities');
export const fetchUsers = () => apiFetch<AdminUsersResponse>('/panel/api/users');
export const fetchTechnicians = () => apiFetch<TechniciansResponse>('/panel/api/technicians');
export const createUser = (body: { username: string; password: string; role: AdminUser['role'] }) => postJson<{ user: AdminUser }>('/panel/api/users', body);
export const toggleUserActive = (id: number) => postJson<{ user: AdminUser }>(`/panel/api/users/${id}/toggle-active`);
export const resetUserPassword = (id: number, password: string) => postJson<{ user: AdminUser }>(`/panel/api/users/${id}/reset-password`, { password });
export const listProjects = () => apiFetch<ProjectsResponse>('/panel/api/projects');
export const createProject = (body: ProjectCreateRequest) => postJson<ProjectCreateResponse>('/panel/api/projects', body);
export const getProject = (slug: string) => apiFetch<ProjectDetailResponse>(`/panel/api/projects/${encodeURIComponent(slug)}`);
export const listPlanningSessions = () => apiFetch<PlanningSessionsResponse>('/panel/api/planning/sessions');
export const getPlanningSession = (slug: string) => apiFetch<PlanningSessionDetailResponse>(`/panel/api/planning/sessions/${encodeURIComponent(slug)}`);
export const openPlanningSession = (topic: string, threadId?: number) => postJson<PlanningSessionOpenResponse>('/panel/api/planning/sessions', { topic, ...(threadId === undefined ? {} : { thread_id: threadId }) });
export const closePlanningSession = (slug: string) => postJson<PlanningSessionCloseResponse>(`/panel/api/planning/sessions/${encodeURIComponent(slug)}/close`);
export const reopenPlanningSession = (slug: string) => postJson<PlanningSessionOpenResponse>(`/panel/api/planning/sessions/${encodeURIComponent(slug)}/reopen`);
