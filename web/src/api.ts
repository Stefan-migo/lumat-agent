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

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

async function apiFetchBlobResponse(path: string): Promise<Response> {
  const res = await fetch(path, { credentials: 'include' });
  if (!res.ok) {
    const raw = await res.text().catch(() => '');
    let detail = raw.trim();
    try {
      const payload = JSON.parse(raw) as { detail?: unknown };
      if (typeof payload.detail === 'string') detail = payload.detail;
    } catch {
      // Keep the raw text when the body is not JSON.
    }
    throw new ApiError(res.status, detail || `${res.status} ${res.statusText}`.trim());
  }
  return res;
}

async function apiFetchBlob(path: string): Promise<Blob> {
  return (await apiFetchBlobResponse(path)).blob();
}

export function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export function postJson<T>(path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: 'POST',
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}
export interface ModelApiKeyStatus { configured: boolean; source: 'env' | 'panel' | 'none'; masked: string; }
export interface ModelApiKeyResponse { ok: true; model_api_key: ModelApiKeyStatus; }
export interface SaveModelApiKeyResponse extends ModelApiKeyResponse { validation: 'valid' | 'no_balance'; }
export const getModelApiKeyStatus = () => apiFetch<{ model_api_key: ModelApiKeyStatus }>('/panel/api/settings').then(({ model_api_key }) => model_api_key);
export const saveModelApiKey = (api_key: string) => postJson<SaveModelApiKeyResponse>('/panel/api/settings/model_api_key', { api_key });
export const deleteModelApiKey = () => apiFetch<ModelApiKeyResponse>('/panel/api/settings/model_api_key', { method: 'DELETE' });
export interface SmtpPasswordStatus { configured: boolean; masked: string; }
export interface EmailSettingsResponse { ok: true; email: SmtpEmailSettings; }
export interface SmtpPasswordResponse { ok: true; email: { password: SmtpPasswordStatus }; }
export const saveEmailSettings = (body: Omit<SmtpEmailSettings, 'password'>) =>
  postJson<EmailSettingsResponse>('/panel/api/settings/email', body);
export const saveSmtpPassword = (password: string) =>
  postJson<SmtpPasswordResponse>('/panel/api/settings/email/password', { password });
export const deleteSmtpPassword = () =>
  apiFetch<SmtpPasswordResponse>('/panel/api/settings/email/password', { method: 'DELETE' });
export const fetchPushConfig = () => apiFetch<{ public_key: string | null }>('/panel/api/push-config');
export const savePushSubscription = (subscription: { endpoint: string; p256dh: string; auth: string; user_agent?: string }) =>
  postJson('/panel/api/push-subscription', subscription);
export const deletePushSubscription = (endpoint: string) =>
  apiFetch<{ ok: true }>(`/panel/api/push-subscription?endpoint=${encodeURIComponent(endpoint)}`, { method: 'DELETE' });
export function patchJson<T>(path: string, body: unknown): Promise<T> {
  return apiFetch<T>(path, { method: 'PATCH', body: JSON.stringify(body) });
}
export function putJson<T>(path: string, body: unknown): Promise<T> {
  return apiFetch<T>(path, { method: 'PUT', body: JSON.stringify(body) });
}

import type { DocsResponse, KbDocument, KbMutationResponse, KbSearchResponse, KbVisibility, CustomerCreateRequest, CustomerProfileUpdateRequest, CustomerMutationResponse, ClientFichaResponse, CustomerEquipment, ClientMergePreview, ClientMergeResponse, ProjectFile, ProjectFilesResponse, ProjectFolder, ProjectFoldersResponse, SmtpEmailSettings } from './types';
export const uploadKbDocument = (title: string, file: File, visibility: KbVisibility, projectId?: number) => {
  const body = new FormData();
  body.append('title', title);
  body.append('file', file);
  body.append('visibility', visibility);
  if (projectId !== undefined) body.append('project_id', String(projectId));
  return apiFetch<KbMutationResponse>('/panel/api/kb', { method: 'POST', body });
};
export const editKbDocument = (id: number, body: { title: string; content: string }) => postJson<KbMutationResponse>(`/panel/api/kb/${id}/edit`, body);
export const disableKbDocument = (id: number) => postJson<KbMutationResponse>(`/panel/api/kb/${id}/disable`);
export const enableKbDocument = (id: number) => postJson<KbMutationResponse>(`/panel/api/kb/${id}/enable`);
export const restoreKbDocument = (id: number, version: number) => postJson<KbMutationResponse>(`/panel/api/kb/${id}/restore`, { version });
export const setKbVisibility = (id: number, visibility: KbVisibility) => postJson<KbMutationResponse>(`/panel/api/kb/${id}/visibility`, { visibility });
export const deleteKbDocument = (id: number) => apiFetch<KbMutationResponse>(`/panel/api/kb/${id}`, { method: 'DELETE' });
export const refreshKbDocuments = (projectId?: number) =>
  apiFetch<DocsResponse>(
    projectId === undefined ? '/panel/api/kb' : `/panel/api/kb?project_id=${projectId}`,
  );
export const getKbDocument = (id: number) => apiFetch<KbDocument>(`/panel/api/kb/${id}`);
export function searchKb({ q, topK, minSim }: { q: string; topK: number; minSim: number }) {
  const params = new URLSearchParams({ q, top_k: String(topK), min_sim: String(minSim) });
  return apiFetch<KbSearchResponse>(`/panel/api/kb/search?${params.toString()}`);
}

import type { ActiveConversationsResponse, ActiveRunsResponse, AdminUser, AdminUserProfileUpdate, AdminUsersResponse, AdvancedDashboardData, AgendaResponse, AppointmentCreateRequest, AppointmentDetail, AppointmentMutationResponse, AssistantAttachment, AssistantCapabilities, AutomationInstallationResponse, AutomationInstallationsResponse, AutomationRecipesResponse, AutomationRuleResponse, AutomationRulesResponse, CasesResponse, ChatbotMetrics, ChatbotSignalConversations, Conversation, ConversationsResponse, ConversationState, ConversationThread, Customer, Message, NotificationsResponse, PanelNotification, InternalChatResponse, InternalChatMessage, InternalChatThread, InternalChatThreadSummary, InternalChatThreadsResponse, AssistantEvent, Rule, ClientNoteMutationResponse, ClientStateMutationResponse, CustomerState, DashboardDrilldownRow, DashboardTrendBucket, DashboardToday, Kpis, BulkAppointmentCloseResponse, AppointmentClosureOutcome, OverdueAppointmentsResponse, TechnicianAgendaResponse, TechnicianAppointmentDetail, TechnicianVisitState, ProjectsResponse, ProjectDetailResponse, ProjectCreateRequest, ProjectCreateResponse, ProjectConfigUpdate, ProjectAgentsResponse, MemoryRelation, MemoryRelationKind, Case, ManualCaseRequest, TechniciansResponse, TechnicianScheduleEntry, TechnicianScheduleResponse, SelfPasswordChange, SelfProfile, SelfProfileUpdate, SelfProfileUpdateResponse, SkillsCatalogResponse, ThreadToolPolicy, ThreadResources, ThreadResourcesSelection, StopThreadRunResponse } from './types';
export interface ConversationFilters { state?: ConversationState; responsible_id?: number; q?: string; exclude_closed?: boolean; emergency?: boolean; has_case?: boolean; limit?: number; offset?: number; }
const requestId = () => globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
const command = <T>(path: string, body: unknown) => postJson<T>(path, body);
export function listConversations(filters: ConversationFilters = {}) {
  const params = new URLSearchParams();
  if (filters.state) params.set('state', filters.state);
  if (filters.responsible_id !== undefined) params.set('responsible_id', String(filters.responsible_id));
  if (filters.q) params.set('q', filters.q);
  if (filters.exclude_closed) params.set('exclude_closed', 'true');
  if (filters.emergency) params.set('emergency', 'true');
  if (filters.has_case) params.set('has_case', 'true');
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
export const sendMedia = (conversationId: number, input: { file: File; requestId: string; caption?: string }) => {
  const body = new FormData();
  body.append('file', input.file);
  body.append('request_id', input.requestId);
  if (input.caption) body.append('caption', input.caption);
  return apiFetch<{ ok: true; message: Message }>(`/panel/api/conversations/${conversationId}/media`, { method: 'POST', body });
};
export const retryMessage = (id: number, messageId: number) => command<{ ok: true; message: Message }>(`/panel/api/conversations/${id}/messages/${messageId}/retry`, { expected_status: 'failed', request_id: requestId() });
export interface NotificationFilters { unread?: boolean; status?: string; source?: string; }
export function listNotifications(filters: NotificationFilters = {}) { const params = new URLSearchParams(); if (filters.unread !== undefined) params.set('unread', String(filters.unread)); if (filters.status) params.set('status', filters.status); if (filters.source) params.set('source', filters.source); const query = params.toString(); return apiFetch<NotificationsResponse>(`/panel/api/notifications${query ? `?${query}` : ''}`); }
export const markNotificationRead = (id: number) => postJson<{ notification: PanelNotification }>(`/panel/api/notifications/${id}/read`);
export const markAllNotificationsRead = () => postJson<{ ok: true; read: number }>('/panel/api/notifications/read-all');
export const createChatThread = (proyecto: string) => postJson<InternalChatResponse>('/panel/api/chat/threads', { proyecto });
export const listChatThreads = (limit: number, proyecto?: string) => apiFetch<InternalChatThreadsResponse>(`/panel/api/chat/threads?limit=${encodeURIComponent(limit)}${proyecto === undefined ? '' : `&proyecto=${encodeURIComponent(proyecto)}`}`);
export const listActiveRuns = () => apiFetch<ActiveRunsResponse>('/panel/api/chat/active-runs');
export const renameChatThread = (id: number, title: string) => apiFetch<{ thread: InternalChatThreadSummary }>(`/panel/api/chat/threads/${id}`, { method: 'PATCH', body: JSON.stringify({ title }) });
export const setChatThreadProject = (id: number, proyecto: string) => apiFetch<{ thread: InternalChatThread }>(`/panel/api/chat/threads/${id}`, { method: 'PATCH', body: JSON.stringify({ proyecto }) });
export const deleteChatThread = (id: number) => apiFetch<{ ok: true }>(`/panel/api/chat/threads/${id}`, { method: 'DELETE' });
export const deleteThreadAttachment = (threadId: number, attachmentId: number): Promise<void> => apiFetch<void>(`/panel/api/chat/threads/${threadId}/attachments/${attachmentId}`, { method: 'DELETE' });
export const sendChatMessage = (id: number, content: string, attachment_ids: number[] = [], sdb_requested?: boolean) => postJson<{ message: InternalChatMessage }> (`/panel/api/chat/threads/${id}/messages`, { content, attachment_ids, ...(sdb_requested ? { sdb_requested } : {}) });
export const uploadAssistantAttachment = (id: number, file: File) => { const body = new FormData(); body.append('file', file); return apiFetch<{ attachment: AssistantAttachment }>(`/panel/api/chat/threads/${id}/attachments`, { method: 'POST', body }); };
export const attachProjectFileToThread = (threadId: number, projectFileId: number) => postJson<{ attachment: AssistantAttachment }>(`/panel/api/chat/threads/${threadId}/attachments/from-project`, { project_file_id: projectFileId });
export const getChatThread = (id: number) => apiFetch<InternalChatResponse>(`/panel/api/chat/threads/${id}`);
export const getThreadToolPolicy = (id: number) => apiFetch<ThreadToolPolicy>(`/panel/api/chat/threads/${id}/tool-policy`);
export const updateThreadToolPolicy = (id: number, optInEnabled: string[]) => apiFetch<ThreadToolPolicy>(`/panel/api/chat/threads/${id}/tool-policy`, { method: 'PUT', body: JSON.stringify({ opt_in_enabled: optInEnabled }) });
export const resetThreadToolPolicy = (id: number) => apiFetch<ThreadToolPolicy>(`/panel/api/chat/threads/${id}/tool-policy`, { method: 'DELETE' });
export const getThreadResources = (id: number) => apiFetch<ThreadResources>(`/panel/api/chat/threads/${id}/resources`);
export const updateThreadResources = (id: number, resources: ThreadResourcesSelection) => apiFetch<ThreadResources>(`/panel/api/chat/threads/${id}/resources`, { method: 'PUT', body: JSON.stringify(resources) });
export const resetThreadResources = (id: number) => apiFetch<ThreadResources>(`/panel/api/chat/threads/${id}/resources`, { method: 'DELETE' });
export const stopChatThread = (threadId: number, runId?: string) => postJson<StopThreadRunResponse>(`/panel/api/chat/threads/${threadId}/stop`, runId === undefined ? undefined : { run_id: runId });
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
export const listOverdueAppointments = () => apiFetch<OverdueAppointmentsResponse>('/panel/api/appointments/overdue');
export const bulkCloseAppointments = (appointment_ids: number[], outcome: AppointmentClosureOutcome) =>
  postJson<BulkAppointmentCloseResponse>('/panel/api/appointments/bulk-close', { appointment_ids, outcome, reason: null });
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
export function fetchClients({ includeArchived = false, onlyArchived = false, query = '', consent, sort }: { includeArchived?: boolean; onlyArchived?: boolean; query?: string; consent?: boolean; sort?: 'created_desc' | 'created_asc' } = {}) {
  const params = new URLSearchParams();
  if (query) params.set('q', query);
  if (includeArchived) params.set('include_archived', 'true');
  if (onlyArchived) params.set('only_archived', 'true');
  if (consent !== undefined) params.set('consent', String(consent));
  if (sort) params.set('sort', sort);
  const search = params.toString();
  return apiFetch<{ clients: Customer[] }>(`/panel/api/clients${search ? `?${search}` : ''}`);
}
export const createCustomer = (body: CustomerCreateRequest) => postJson<CustomerMutationResponse>('/panel/api/clients', body);
export const updateCustomerProfile = (id: number, body: CustomerProfileUpdateRequest) => apiFetch<CustomerMutationResponse>(`/panel/api/clients/${id}`, { method: 'PATCH', body: JSON.stringify(body) });
export const updateCustomerConsent = (id: number, consent: boolean) => postJson<CustomerMutationResponse>(`/panel/api/clients/${id}/consent`, { consent });
export const archiveCustomer = (id: number) => postJson<CustomerMutationResponse>(`/panel/api/clients/${id}/archive`);
export const unarchiveCustomer = (id: number) => postJson<CustomerMutationResponse>(`/panel/api/clients/${id}/unarchive`);
export const getClientFicha = (id: number, includeArchivedCases = false) => apiFetch<ClientFichaResponse>(`/panel/api/clients/${id}${includeArchivedCases ? '?include_archived_cases=true' : ''}`);
export const previewClientMerge = (id: number, otherId: number) => apiFetch<ClientMergePreview>(`/panel/api/clients/${id}/merge-preview?with=${otherId}`);
export const mergeClient = (id: number, otherId: number) => postJson<ClientMergeResponse>(`/panel/api/clients/${id}/merge`, { other_id: otherId });
export const fetchCases = () => apiFetch<CasesResponse>('/panel/api/cases');
export const createCase = (body: ManualCaseRequest) => postJson<{ ok: true; case: Case }>('/panel/api/cases', body);
export const updateCaseAmount = (id: number, amount: number | null) => postJson<{ ok: true; case: Case }>(`/panel/api/cases/${id}/update`, { amount });
export const archiveCase = (id: number) => postJson<{ ok: true; case: Case }>(`/panel/api/cases/${id}/archive`);
export const unarchiveCase = (id: number) => postJson<{ ok: true; case: Case }>(`/panel/api/cases/${id}/unarchive`);
export const changeClientState = (id: number, state: CustomerState) => postJson<ClientStateMutationResponse>(`/panel/api/clients/${id}/state`, { state });
export const addClientNote = (id: number, note: string) => postJson<ClientNoteMutationResponse>(`/panel/api/clients/${id}/notes`, { note });
export const updateClientNote = (id: number, noteId: number, note: string) => patchJson<ClientNoteMutationResponse>(`/panel/api/clients/${id}/notes/${noteId}`, { note });
export const deleteClientNote = (id: number, noteId: number) => apiFetch<{ ok: true }>(`/panel/api/clients/${id}/notes/${noteId}`, { method: 'DELETE' });
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
export const listAutomationRecipes = () => apiFetch<AutomationRecipesResponse>('/panel/api/automation-recipes');
export const listAutomationInstallations = () => apiFetch<AutomationInstallationsResponse>('/panel/api/automation-installations');
export const createAutomationInstallation = (recipe_id: string, parameters: Record<string, unknown>) => postJson<AutomationInstallationResponse>('/panel/api/automation-installations', { recipe_id, parameters });
export const updateAutomationInstallation = (id: number, parameters: Record<string, unknown>) => patchJson<AutomationInstallationResponse>(`/panel/api/automation-installations/${id}`, { parameters });
export const enableAutomationInstallation = (id: number) => postJson<{ ok: true; installation: AutomationInstallationResponse['installation'] }>(`/panel/api/automation-installations/${id}/enable`);
export const disableAutomationInstallation = (id: number) => postJson<{ ok: true; installation: AutomationInstallationResponse['installation'] }>(`/panel/api/automation-installations/${id}/disable`);
export const deleteAutomationInstallation = (id: number) => apiFetch<{ ok: true }>(`/panel/api/automation-installations/${id}`, { method: 'DELETE' });
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

export const getChatbotMetrics = (windowDays: number) =>
  apiFetch<ChatbotMetrics>(`/panel/api/analytics/chatbot?window_days=${windowDays}`);
export const getChatbotSignalConversations = (signal: string, windowDays: number, limit = 10) =>
  apiFetch<ChatbotSignalConversations>(`/panel/api/analytics/chatbot/conversations?signal=${encodeURIComponent(signal)}&window_days=${windowDays}&limit=${limit}`);
export const getDashboardToday = (timezone: string) => apiFetch<DashboardToday>(`/panel/api/dashboard/today?timezone=${encodeURIComponent(timezone)}`);export const getDashboardKpis = (windowDays: number) =>
  apiFetch<Kpis>(`/panel/api/kpis?window_days=${windowDays}`);

export const getDashboardTrend = (timezone: string, windowDays: number) => {
  const end = new Date();
  const start = new Date(end.getTime() - windowDays * 24 * 60 * 60 * 1000);
  const params = new URLSearchParams({ start: start.toISOString(), end: end.toISOString(), timezone, metric: 'contacts' });
  return apiFetch<{ buckets: DashboardTrendBucket[] }>(`/panel/api/dashboard/trend?${params}`);
};

export const fetchTechnicianAgenda = () => apiFetch<TechnicianAgendaResponse>('/panel/api/technician/agenda');

/** The technician's own visit detail (S2). Normalized to the operator
 *  `AppointmentDetail` shape so the shared page keeps one data type: the server
 *  never sends `history` or a conversation summary for a technician, so they are
 *  filled empty here and the page hides them by role. */
export const getTechnicianAppointment = (id: number): Promise<AppointmentDetail> =>
  apiFetch<TechnicianAppointmentDetail>(`/panel/api/technician/appointments/${id}`).then((detail) => ({
    ...detail,
    appointment: { ...detail.appointment, history: [] },
    conversation_summary: null,
  }));

/** The technician's own close (S4) — the operator route stays for the office. */
export function closeTechnicianAppointment(id: number, outcome: 'completed' | 'no_show') {
  return postJson<{ ok: true }>(`/panel/api/technician/appointments/${id}/close`, { outcome });
}

/** A field quick action (S5/S8). The response carries the recorded state and when
 *  a resend unlocks (S7); the customer phone never leaves the server. */
export function sendTechnicianQuickAction(id: number, action: TechnicianVisitState) {
  return postJson<{ ok: true; technician_state: TechnicianVisitState; resend_available_at: string }>(
    `/panel/api/technician/appointments/${id}/${action}`,
  );
}
export const getAssistantCapabilities = () => apiFetch<AssistantCapabilities>('/panel/api/assistant/capabilities');
export const fetchUsers = () => apiFetch<AdminUsersResponse>('/panel/api/users');
export const getAdminUser = (id: number) => apiFetch<{ user: AdminUser }>(`/panel/api/users/${id}`);
export const updateAdminUser = (id: number, body: AdminUserProfileUpdate) => patchJson<{ user: AdminUser }>(`/panel/api/users/${id}`, body);
export const unlockUser = (id: number) => postJson<{ user: AdminUser }>(`/panel/api/users/${id}/unlock`);
export const fetchTechnicians = () => apiFetch<TechniciansResponse>('/panel/api/technicians');
export const getTechnicianSchedule = (technicianId: number) => apiFetch<TechnicianScheduleResponse>(`/panel/api/technicians/${technicianId}/schedule`);
export const saveTechnicianSchedule = (technicianId: number, schedule: TechnicianScheduleEntry[]) => putJson<TechnicianScheduleResponse>(`/panel/api/technicians/${technicianId}/schedule`, { schedule });
export const createUser = (body: { username: string; password: string; role: AdminUser['role'] }) => postJson<{ user: AdminUser }>('/panel/api/users', body);
export const toggleUserActive = (id: number) => postJson<{ user: AdminUser }>(`/panel/api/users/${id}/toggle-active`);
export const deleteUser = (id: number) => apiFetch<{ ok: true }>(`/panel/api/users/${id}`, { method: 'DELETE' });
export const resetUserPassword = (id: number, password: string) => postJson<{ user: AdminUser }>(`/panel/api/users/${id}/reset-password`, { password });
export const fetchMe = () => apiFetch<SelfProfile>('/panel/api/me');
export const updateMe = (body: SelfProfileUpdate) => patchJson<SelfProfileUpdateResponse>('/panel/api/me', body);
export const changePassword = (body: SelfPasswordChange) => postJson<{ ok: true }>('/panel/api/me/password', body);
export const listProjects = () => apiFetch<ProjectsResponse>('/panel/api/projects');
export const createProject = (body: ProjectCreateRequest) => postJson<ProjectCreateResponse>('/panel/api/projects', body);
export const getProject = (slug: string) => apiFetch<ProjectDetailResponse>(`/panel/api/projects/${encodeURIComponent(slug)}`);
export const listProjectAgents = (slug: string) => apiFetch<ProjectAgentsResponse>(`/panel/api/projects/${encodeURIComponent(slug)}/agents`);
export const updateProjectConfig = (slug: string, body: ProjectConfigUpdate) => patchJson<ProjectDetailResponse>(`/panel/api/projects/${encodeURIComponent(slug)}/config`, body);
export const listGlobalSkills = () => apiFetch<SkillsCatalogResponse>('/panel/api/skills');
export const listProjectFiles = (slug: string) => apiFetch<ProjectFilesResponse>(`/panel/api/projects/${encodeURIComponent(slug)}/files`);
export const uploadProjectFile = (slug: string, file: File, folderId?: number | null) => {
  const body = new FormData();
  body.append('file', file);
  if (folderId != null) body.append('folder_id', String(folderId));
  return apiFetch<{ file: ProjectFile }>(`/panel/api/projects/${encodeURIComponent(slug)}/files`, { method: 'POST', body });
};
export const deleteProjectFile = (slug: string, fileId: number): Promise<void> =>
  apiFetch<void>(`/panel/api/projects/${encodeURIComponent(slug)}/files/${fileId}`, { method: 'DELETE' });
export const moveProjectFile = (slug: string, fileId: number, folderId: number | null) =>
  patchJson<{ file: ProjectFile }>(`/panel/api/projects/${encodeURIComponent(slug)}/files/${fileId}`, { folder_id: folderId });
export const listProjectFolders = (slug: string) => apiFetch<ProjectFoldersResponse>(`/panel/api/projects/${encodeURIComponent(slug)}/folders`);
export const createProjectFolder = (slug: string, body: { name: string; parent_id?: number | null }) => postJson<{ folder: ProjectFolder }>(`/panel/api/projects/${encodeURIComponent(slug)}/folders`, body);
export const renameProjectFolder = (slug: string, folderId: number, name: string) => patchJson<{ folder: ProjectFolder }>(`/panel/api/projects/${encodeURIComponent(slug)}/folders/${folderId}`, { name });
export const deleteProjectFolder = (slug: string, folderId: number): Promise<void> =>
  apiFetch<void>(`/panel/api/projects/${encodeURIComponent(slug)}/folders/${folderId}`, { method: 'DELETE' });
export async function downloadProjectFile(slug: string, fileId: number, filename: string): Promise<void> {
  triggerDownload(await apiFetchBlob(`/panel/api/projects/${encodeURIComponent(slug)}/files/${fileId}/download`), filename);
}
export async function downloadAssistantArtifact(threadId: number, artifactId: number, filename: string): Promise<void> {
  triggerDownload(await apiFetchBlob(`/panel/api/chat/threads/${threadId}/artifacts/${artifactId}/download`), filename);
}
export async function downloadAssistantConversation(threadId: number): Promise<void> {
  const res = await apiFetchBlobResponse(`/panel/api/chat/threads/${threadId}/export`);
  const disposition = res.headers.get('Content-Disposition');
  const filename = disposition?.match(/filename="([^"]+)"/i)?.[1] ?? `conversation-${threadId}.md`;
  triggerDownload(await res.blob(), filename);
}

export const threadAttachmentContentUrl = (threadId: number, attachmentId: number): string => `/panel/api/chat/threads/${threadId}/attachments/${attachmentId}/content`;
