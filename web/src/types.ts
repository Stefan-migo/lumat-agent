/** Panel JSON API TypeScript mirrors (B5/T5.3; PDW-API).
 *
 * Shapes mirror `app/panel/api/serializers.py` + the route response dicts:
 * snake_case keys, ISO-8601 datetime strings, nullable timestamps.
 * Kept in the SPA so components never invent their own field names.
 */

export type Role = 'admin' | 'operador';

export interface User {
  username: string;
  role: Role;
}

export interface LoginResponse {
  ok: true;
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

export interface Kpis {
  contacts: number;
  motivos: Array<[string, number]>;
  derived: number;
  visit_requests: number;
  window_days: number;
  window_start: string;
}

export interface Conversation {
  id: number;
  customer_id: number;
  wa_phone: string | null;
  state: string;
  summary: string | null;
  last_message_at: string | null;
  created_at: string | null;
  closed_at: string | null;
}

export interface ConversationsResponse {
  conversations: Conversation[];
}

export type MessageDirection = 'inbound' | 'outbound';

export interface Message {
  id: number;
  conversation_id: number;
  direction: MessageDirection;
  msg_type: string;
  text: string | null;
  media_url: string | null;
  created_at: string | null;
}

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
  };
  notes: CustomerNote[];
  /** CR-7: latest customer_memo (empty string when none yet). */
  memo: string;
  states: CustomerState[];
}
