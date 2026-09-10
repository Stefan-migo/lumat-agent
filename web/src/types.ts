/** Panel JSON API TypeScript mirrors (B5/T5.3; PDW-API).
 *
 * Shapes mirror `app/panel/api/serializers.py` + the route response dicts:
 * snake_case keys, ISO-8601 datetime strings, nullable timestamps.
 * Kept in the SPA so components never invent their own field names.
 */

export type Role = 'admin' | 'operador' | 'tecnico';

export interface User {
  id?: number;
  username: string;
  role: Role;
}

export interface AdminUser { id: number; username: string; role: Role; active: boolean; }
export interface AdminUsersResponse { users: AdminUser[]; }

export interface Rule {
  id: number;
  name: string;
  event_type: string;
  conditions: Record<string, string | number | boolean | null>;
  channel: string;
  template_event: string;
  cooldown_seconds: number;
  enabled: boolean;
  created_by: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface AutomationRulesResponse { rules: Rule[]; }
export interface AutomationRuleResponse { rule: Rule; }

export interface LoginResponse {
  ok: true;
  id: number;
  role: Role;
}

export type CustomerState = 'nuevo' | 'activo' | 'inactivo' | 'bloqueado';

export interface Customer {
  id: number;
  phone_e164: string | null;
  name: string | null;
  email: string | null;
  comuna: string | null;
  address: string | null;
  state: CustomerState;
  consent_status: boolean;
  consent_at: string | null;
  created_at: string | null;
}

export interface CustomerNote {
  id: number;
  customer_id: number;
  note: string;
  author: string | null;
  created_at: string | null;
}

export interface ClientStateMutationResponse { ok: true; state: CustomerState; }
export interface ClientNoteMutationResponse { ok: true; note: CustomerNote; }

export type MemoryType =
  | 'decision'
  | 'discovery'
  | 'pattern'
  | 'preference'
  | 'customer_memo'
  | 'summary'
  | 'session'
  | 'prompt';

export type MemoryStatus = 'active' | 'needs_review' | 'archived';

/** Memory row mirroring to_memory_dict() (MEM-6 panel /clients/{id}/memories). */
export interface Memory {
  id: number;
  scope: string;
  entity_id: string;
  tipo: MemoryType;
  titulo: string;
  contenido: string;
  topic_key: string;
  pin: boolean;
  status: MemoryStatus;
  created_at: string | null;
  updated_at: string | null;
}

export interface MemoriesResponse {
  memories: Memory[];
}

export interface PanelNotification { id: number; user_id: number; operation_id: number; title: string; content: string; source: string; channel: string | null; status: string; read_at: string | null; created_at: string | null; }
export interface NotificationsResponse { notifications: PanelNotification[]; }

export type InternalChatStatus = 'processing' | 'processed' | 'failed' | 'approval_pending' | 'rejected';
export interface AssistantPlan { tool?: string | null; arguments?: Record<string, unknown>; summary?: string; status?: string; requires_approval?: boolean; }
export interface AssistantApproval {
  token?: string;
  token_sha256?: string;
  tool?: string | null;
  arguments?: Record<string, unknown>;
  arguments_sha256?: string;
  expires_at?: string;
  status?: string;
  consumed_at?: string | null;
}
export interface AssistantEvidence { tool?: string | null; status: string; detail?: string; result?: unknown; }
export type AssistantEventType = 'plan' | 'approval' | 'tool' | 'evidence' | 'status' | 'response' | 'error';
export interface AssistantEvent { type: AssistantEventType; thread_id: number; run_id: string; sequence: number; plan?: AssistantPlan; approval?: AssistantApproval | null; status?: string; tool?: string | null; evidence?: AssistantEvidence[]; content?: string; error?: string; }
export interface AssistantState { stage?: string; recoverable?: boolean; execution_status?: string; approval?: AssistantApproval | null; events?: AssistantEvent[]; }
export interface InternalChatThread { id: number; user_id?: number; status: string; assistant_state?: AssistantState; current_plan?: AssistantPlan | null; active_run_id?: string | null; created_at?: string | null; updated_at?: string | null; }
export interface InternalChatMessage { id: number; thread_id?: number; author: 'admin' | 'agent'; content: string; status: InternalChatStatus; error?: string | null; assistant_metadata?: { run_id?: string; approval?: AssistantApproval | null }; created_at?: string | null; completed_at?: string | null; }
export interface InternalChatResponse { thread: InternalChatThread; messages: InternalChatMessage[]; attachments?: AssistantAttachment[]; }
export interface AssistantAttachment { id: number; thread_id: number; filename: string; kind: string; content_type: string; size: number; created_at?: string | null; }
export interface AssistantCapabilityTool { name: string; description: string; read_only: boolean; write: boolean; }
export interface AssistantCapabilities { tools: AssistantCapabilityTool[]; personas: string[]; prompts: string[]; kb_available: boolean; memory_available: boolean; }

export type RealtimeEnvelopeType = 'token' | 'message' | 'conversation' | 'activity' | 'snapshot';
export interface RealtimeEnvelope<T = unknown> { type: RealtimeEnvelopeType; conversation_id?: number | null; data: T; }
export interface RealtimeActivity { id?: number; conversation_id?: number; event: string; cause?: string | null; actor?: string | null; created_at?: string; }
export interface RealtimeSnapshot { conversations: Conversation[]; activity: RealtimeActivity[]; }

export interface Kpis {
  contacts: number;
  motivos: Array<[string, number]>;
  derived: number;
  visit_requests: number;
  window_days: number;
  window_start: string;
  new_customers?: number;
  trend?: DashboardTrendBucket[];
  today?: DashboardToday;
}

export interface DashboardToday {
  tz: string;
  local_date: string;
  appointments_today: Array<{ id: number; service: string; customer_name: string | null; local_start: string; starts_at: string; ends_at: string }>;
  unanswered_conversations: Array<{ id: number; customer_name: string | null; last_message_at: string | null; state: string }>;
  urgent_cases: Array<{ id: number; customer_name: string | null; service: string | null; summary: string | null; emergency: boolean; escalated_at: string | null }>;
}

export interface DashboardPeriod { start: string; end: string; timezone: string; }
export interface DashboardTrendBucket { start: string; count: number; }
export interface DashboardDrilldownRow { service?: string; count?: number; [key: string]: unknown; }
export interface DashboardMetrics {
  contacts: number;
  cases: number;
  appointments: number;
  notification_health: Record<string, number>;
  automation_outcomes: Record<string, number>;
}
export interface AdvancedDashboardData {
  period: DashboardPeriod;
  metrics: DashboardMetrics;
  trend: DashboardTrendBucket[];
  drilldown?: DashboardDrilldownRow[];
}

export interface Conversation {
  id: number;
  customer_id: number;
  wa_phone: string | null;
  state: string;
  responsible_id?: number | null;
  version?: number;
  latest_inbound_at: string | null;
  reply_window_open: boolean;
  delivery_summary: Record<DeliveryStatus, number>;
  summary: string | null;
  last_message_at: string | null;
  created_at: string | null;
  closed_at: string | null;
  customer?: CustomerSummary | null;
  case?: CaseSummary | null;
  case_id?: number | null;
  emergency?: boolean;
  acknowledged_at?: string | null;
  case_status?: string | null;
  case_priority?: string | null;
  captured_data?: Record<string, unknown> | null;
}

export type CustomerSummary = Pick<Customer, 'id' | 'name' | 'phone_e164'>;
export interface CaseSummary {
  id: number;
  service: string;
  priority: string;
  status: string;
  emergency: boolean;
  summary: string | null;
  acknowledged_at: string | null;
  closed_at: string | null;
}

export interface QueueCounts {
  all: number;
  human: number;
  emergency: number;
  case: number;
  closed: number;
}

export interface ConversationsResponse {
  items?: Conversation[];
  total?: number;
  offset?: number;
  limit?: number;
  counts?: QueueCounts;
  conversations?: Conversation[];
}

export interface ActiveConversation {
  id: number;
  customer_name: string | null;
  state: ConversationState | string;
  last_message_at: string | null;
}
export interface ActiveConversationsResponse { conversations: ActiveConversation[]; }

export type MessageDirection = 'inbound' | 'outbound';

export interface Message {
  id: number;
  conversation_id: number;
  direction: MessageDirection;
  msg_type: string;
  text: string | null;
  media_url: string | null;
  created_at: string | null;
  author_id?: number | null;
  request_id?: string | null;
  delivery_status?: DeliveryStatus | null;
  delivery_error?: string | null;
  delivery_attempts?: number;
  delivered_at?: string | null;
}

export type ConversationState = 'bot' | 'human' | 'closed';
export type DeliveryStatus = 'pending' | 'sending' | 'sent' | 'failed' | 'unknown';

export interface ConversationThread {
  conversation: Conversation;
  messages: Message[];
}

export interface UserRef {
  id: number;
  username: string;
}

export interface Case {
  id: number;
  conversation_id: number | null;
  customer_id: number | null;
  created_at: string | null;
  service: string;
  priority: string;
  status: string;
  emergency: boolean;
  responsible_id: number | null;
  summary: string | null;
  escalated_at: string | null;
  closed_at: string | null;
  acknowledged_at: string | null;
  ack_by: string | null;
  customer: Customer;
}

export interface CasesResponse {
  cases: Case[];
  users: UserRef[];
}

export type DocFormat = 'pdf' | 'md' | 'csv';

export interface Doc {
  id: number;
  title: string;
  format: DocFormat;
  version: number;
  active_version: number;
  active: boolean;
  provider: string | null;
  model: string | null;
  cost_meta: number | null;
  created_at: string | null;
}

export interface DocsResponse {
  docs: Doc[];
}
export interface KbMutationResponse { ok: true; doc: Doc; }

export interface SpendSnapshot {
  date: string;
  conversation_spend: number | null;
  conversation_limit: number;
  conversation_percent: number | null;
  daily_spend: number;
  daily_limit: number;
  daily_percent: number;
  mode: string;
}

export interface Settings {
  scope_rules: Record<string, string>;
  keywords: string[];
  tone: string;
  conversation_limit: number;
  daily_limit: number;
  meta_cost: number;
  snapshot: SpendSnapshot;
}

export interface ClientFichaResponse {
  customer: Customer;
  history: {
    conversations: Array<{
      id: number;
      state: string;
      summary: string | null;
      created_at: string | null;
      closed_at: string | null;
    }>;
    cases: Array<{
      id: number;
      conversation_id: number | null;
      service: string;
      priority: string;
      status: string;
      summary: string | null;
    }>;
    messages: Array<{
      id: number;
      conversation_id: number;
      direction: string;
      msg_type: string;
      text: string | null;
      media_url: string | null;
      created_at: string | null;
    }>;
    appointments?: Appointment[];
    visit_history?: VisitHistoryEvent[];
  };
  notes: CustomerNote[];
  /** CR-7: latest customer_memo (empty string when none yet). */
  memo: string;
  states: CustomerState[];
}

export interface Appointment {
  id: number;
  service: string;
  customer_id: number;
  case_id: number;
  technician_id: number;
  local_start: string;
  timezone: string;
  starts_at: string;
  ends_at: string;
  duration_minutes: number;
  status: string;
  calendar_status?: string | null;
  calendar_error?: string | null;
}

export type AppointmentSyncStatus = 'pending' | 'synced' | 'failed';

export interface AgendaAppointment {
  id: number;
  service: string;
  customer_id: number;
  customer_name: string | null;
  case_id: number | null;
  case_name: string | null;
  technician_id: number | null;
  technician_name: string | null;
  local_start: string;
  timezone: string;
  starts_at: string;
  ends_at: string;
  duration_minutes?: number;
  status: string;
  sync: { status: AppointmentSyncStatus; error: string | null; retry: boolean };
}

export interface AgendaResponse {
  appointments: AgendaAppointment[];
}

export interface TechnicianCustomer {
  name: string | null;
  address: string | null;
  comuna: string | null;
  phone: string | null;
}

export interface TechnicianAppointment {
  id: number;
  service: string;
  local_start: string;
  starts_at: string;
  ends_at: string;
  timezone: string;
  customer: TechnicianCustomer;
  case_summary: string | null;
}

export interface TechnicianAgendaResponse {
  appointments: TechnicianAppointment[];
}

export interface VisitHistoryEvent {
  id: number;
  appointment_id: number;
  actor: string;
  action: string;
  from_status?: string | null;
  to_status: string;
  status: string;
  details?: Record<string, unknown> | null;
  created_at: string | null;
}
