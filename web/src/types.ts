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

export interface SelfProfile extends User {
  id: number;
  email: string | null;
  name: string | null;
  phone: string | null;
  position: string | null;
}
export interface SelfProfileUpdate { name: string | null; phone: string | null; }
export interface SelfProfileUpdateResponse { user: Pick<SelfProfile, 'name' | 'phone'>; }
export interface SelfPasswordChange { current_password: string; new_password: string; }

export interface AdminUser { id: number; username: string; role: Role; active: boolean; email: string | null; name: string | null; phone: string | null; position: string | null; locked_until: string | null; failed_logins: number; }
export type AdminUserProfileUpdate = Pick<AdminUser, 'email' | 'name' | 'phone' | 'position'>;
export interface AdminUsersResponse { users: AdminUser[]; }
export interface ProjectToolPolicy { opt_in_enabled: string[]; }
export interface ThreadToolPolicy { available: string[]; opt_in_enabled: string[]; inherited: boolean; }
export interface ProjectSkill { name: string; description: string; body: string; }
export interface GlobalSkill { name: string; description: string; scope: "global"; }
export interface SkillsCatalogResponse { skills: GlobalSkill[]; }
export interface ProjectConfig { instructions: string; tool_policy: ProjectToolPolicy; skills: ProjectSkill[]; }
export type ProjectConfigUpdate = Partial<ProjectConfig>;
export interface Project { id: number; slug: string; name: string; purpose: string; status: 'active' | 'archived'; created_at: string | null; updated_at: string | null; config?: ProjectConfig; }
export interface ProjectsResponse { projects: Project[]; }
export interface ProjectFile { id: number; project_id: number; filename: string; content_type: string; size: number; sha256: string; status: string; created_at: string | null; }
export interface ProjectFilesResponse { files: ProjectFile[]; }
export interface ProjectDetailResponse { project: Project; }
export interface ProjectAgent { key: string; name: string; role: string; description: string; read_only: boolean; }
export interface ProjectRunStatus { status: string; tool?: string | null; at?: string | null; }
export interface ProjectAgentsResponse { agents: ProjectAgent[]; latest_run: ProjectRunStatus | null; }
export interface ProjectCandidate { slug: string; name: string; similarity: number; }
export interface ProjectCreateRequest { slug: string; name: string; purpose: string; }
export interface ProjectCreateResponse { project: Project; }

export type CortexStatus = 'active' | 'closed';
export interface PlanningSession { slug: string; topic: string; status: CortexStatus; thread_id: number; opened_at: string | null; closed_at: string | null; report_key: string | null; }
export interface CortexArtifact { id: number; scope: string; entity_id: string; tipo: MemoryType; titulo: string; contenido: string; topic_key: string; status: MemoryStatus; created_at: string | null; updated_at: string | null; }
export interface PlanningSessionsResponse { sessions: PlanningSession[]; }
export interface PlanningSessionOpenResponse { session: PlanningSession; thread_id: number; }
export interface PlanningSessionCloseResponse { session: PlanningSession; report: CortexArtifact | null; }
export interface PlanningSessionDetailResponse { session: PlanningSession; thread: InternalChatThread; report: CortexArtifact | null; }

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

export type CustomerState = 'nuevo' | 'contactado' | 'pendiente' | 'agendado' | 'en_evaluacion' | 'finalizado' | 'cancelado' | 'postventa';

export interface Customer {
  id: number;
  phone_e164: string | null;
  name: string | null;
  email: string | null;
  comuna: string | null;
  address: string | null;
  state: CustomerState;
  allowed_transitions?: CustomerState[];
  consent_status: boolean;
  consent_at: string | null;
  created_at: string | null;
  archived_at?: string | null;
}

export interface CustomerEquipment {
  id: number;
  customer_id: number;
  equipment_type: string | null;
  brand: string | null;
  model: string | null;
  age: string | null;
  details: string | null;
  source_conversation_id: number | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface CustomerCreateRequest { phone: string; name?: string; email?: string; comuna?: string; address?: string; }
export interface CustomerProfileUpdateRequest { name?: string | null; email?: string | null; comuna?: string | null; address?: string | null; }
export interface CustomerMutationResponse { customer: Customer; }
export interface ClientMergeCounts { conversations: number; cases: number; customer_notes: number; customer_equipment: number; appointments: number; }
export interface ClientMergePreview { survivor_id: number; loser_id: number; moved: ClientMergeCounts; memory_conflicts: number; scalar_conflicts: string[]; }
export interface ClientMergeResponse { survivor: Customer; moved: ClientMergeCounts; }

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

export type MemoryRelationKind = 'supersedes' | 'conflicts' | 'related' | 'compatible' | 'scoped' | 'not_conflict';
export interface MemoryRelation {
  id: number;
  memory_a: Memory;
  memory_b: Memory;
  relation: MemoryRelationKind;
  confidence: number;
  reason: string | null;
  source: string;
  human_resolved_at: string | null;
  created_at: string | null;
}
export interface PendingMemoryRelationsResponse { relations: MemoryRelation[]; }

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
export interface AssistantEvidence { tool?: string | null; status: string; detail?: string; }
export type AssistantEventType = 'plan' | 'approval' | 'tool' | 'evidence' | 'status' | 'response' | 'error' | 'timeout';
export interface AssistantEvent { type: AssistantEventType; thread_id: number; run_id: string; sequence: number; plan?: AssistantPlan; approval?: AssistantApproval | null; status?: string; tool?: string | null; evidence?: AssistantEvidence[]; content?: string; error?: string; }
export interface AssistantState { stage?: string; recoverable?: boolean; execution_status?: string; approval?: AssistantApproval | null; events?: AssistantEvent[]; cortex_session?: PlanningSession; }
export interface InternalChatThread { id: number; user_id?: number; proyecto?: string | null; status: string; assistant_state?: AssistantState; current_plan?: AssistantPlan | null; active_run_id?: string | null; created_at?: string | null; updated_at?: string | null; }
export interface InternalChatMessage { id: number; thread_id?: number; author: Role | 'agent'; content: string; status: InternalChatStatus; error?: string | null; assistant_metadata?: { run_id?: string; approval?: AssistantApproval | null }; created_at?: string | null; completed_at?: string | null; }
export interface InternalChatResponse { thread: InternalChatThread; messages: InternalChatMessage[]; attachments?: AssistantAttachment[]; artifacts?: AssistantArtifact[]; }
export interface InternalChatThreadSummary {
  id: number;
  title: string | null;
  created_at: string | null;
  updated_at: string | null;
  run_status: string | null;
  approval_status: string | null;
}
export interface InternalChatThreadsResponse { threads: InternalChatThreadSummary[]; }
export interface AssistantAttachment { id: number; thread_id: number; filename: string; kind: string; content_type: string; size: number; created_at?: string | null; }
export interface AssistantArtifact { id: number; thread_id: number; filename: string; content_type: string; size: number; created_at?: string | null; }
export interface AssistantCapabilityTool { name: string; description: string; read_only: boolean; write: boolean; }
export interface AssistantCapabilities { tools: AssistantCapabilityTool[]; personas: string[]; prompts: string[]; kb_available: boolean; memory_available: boolean; }

export type RealtimeEnvelopeType = 'message' | 'conversation' | 'activity' | 'snapshot';
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

export type CustomerSummary = Pick<Customer, 'id' | 'name' | 'phone_e164'> & { comuna?: string | null; address?: string | null };
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
  messages_total: number;
}

export interface UserRef {
  id: number;
  username: string;
}

export interface TechniciansResponse { technicians: UserRef[]; }

export interface Case {
  id: number;
  conversation_id: number | null;
  customer_id: number | null;
  created_at: string | null;
  service: string | null;
  amount: number | null;
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

export interface ManualCaseRequest { customer_id: number; service: string; summary?: string; }

export type DocFormat = 'pdf' | 'md' | 'csv' | 'docx' | 'xlsx';
export type KbVisibility = 'customer' | 'internal';

export interface Doc {
  id: number;
  project_id: number | null;
  title: string;
  format: DocFormat;
  version: number;
  active_version: number;
  active: boolean;
  visibility: KbVisibility;
  provider: string | null;
  model: string | null;
  cost_meta: number | null;
  created_at: string | null;
}

export interface KbDocument extends Doc {
  content: string;
}

export interface DocsResponse {
  docs: Doc[];
}
export interface KbMutationResponse { ok: true; doc: Doc; }
export interface KbSearchResult {
  document_id: number;
  title: string;
  version: number;
  chunk_index: number;
  content: string;
  source_meta: Record<string, unknown> | null;
  similarity: number;
}
export interface KbSearchResponse { results: KbSearchResult[]; }

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
  messages: {
    greeting: string;
    cannot_answer: string;
    clarification: string;
    farewell: string;
    out_of_hours: string;
  };
  hours: {
    timezone: string;
    schedule: Array<{ days: number[]; open: string; close: string }>;
  };
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
      customer_id: number | null;
      created_at: string | null;
      service: string;
      amount: number | null;
      priority: string;
      status: string;
      emergency: boolean;
      responsible_id: number | null;
      summary: string | null;
      escalated_at: string | null;
      closed_at: string | null;
      acknowledged_at: string | null;
      ack_by: string | null;
      is_open: boolean;
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
    messages_total: number;
    appointments?: Appointment[];
  };
  notes: CustomerNote[];
  /** CR-7: latest customer_memo (empty string when none yet). */
  memo: string;
  states: CustomerState[];
  users: UserRef[];
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

export interface AppointmentHistoryEntry {
  id: number;
  actor: string;
  action: string;
  from_status: string | null;
  to_status: string;
  details: Record<string, unknown> | null;
  created_at: string;
}

export interface AppointmentDetail {
  appointment: Appointment & { history: AppointmentHistoryEntry[] };
  customer: { id: number; name: string | null; address: string | null; comuna: string | null };
  case: { id: number; conversation_id: number | null };
  conversation_summary: string | null;
}

export type AppointmentSyncStatus = 'pending' | 'synced' | 'failed';

export interface AgendaAppointment {
  id: number;
  service: string;
  customer_id: number;
  customer_name: string | null;
  customer_address?: string | null;
  customer_comuna?: string | null;
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

export interface AppointmentCreateRequest {
  service: string;
  customer_id: number;
  case_id: number;
  technician_id: number;
  local_date: string;
  local_time: string;
  timezone: string;
  duration_minutes: number;
}

export interface AppointmentMutationResponse {
  ok: true;
  appointment: Appointment;
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
  /** `booked | cancelled | completed | no_show` — the technician must be able to
   *  tell a cancelled visit from a booked one without leaving the agenda. */
  status: string;
  /** Safety properties of the visit, distinct from the appointment workflow status. */
  emergency: boolean;
  priority: string | null;
  customer: TechnicianCustomer;
  case_summary: string | null;
}

export interface TechnicianAgendaResponse {
  appointments: TechnicianAppointment[];
}
