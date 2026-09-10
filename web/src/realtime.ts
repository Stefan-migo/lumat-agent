import type { Conversation, ConversationThread, InternalChatMessage, RealtimeActivity, RealtimeEnvelope, RealtimeSnapshot } from './types';
export type { RealtimeEnvelope } from './types';

export interface FakeWebSocket {
  readyState: number;
  onopen: (() => void) | null;
  onclose: (() => void) | null;
  onerror: (() => void) | null;
  onmessage: ((event: { data: string }) => void) | null;
  close: () => void;
}
export type WebSocketFactory = (url: string) => FakeWebSocket;
export type ConnectionStatus = 'disconnected' | 'connecting' | 'reconnecting' | 'connected';
export interface RealtimeState {
  conversations: Conversation[];
  threads: Record<number, ConversationThread>;
  activity: Record<number, RealtimeActivity[]>;
  tokens: Record<number, string>;
  chats: Record<number, { messages: InternalChatMessage[] }>;
  status: ConnectionStatus;
}
export const initialRealtimeState: RealtimeState = { conversations: [], threads: {}, activity: {}, tokens: {}, chats: {}, status: 'disconnected' };

export function coalesceSnapshotRefresh(refresh: () => void, delay = 100) {
  let timer: ReturnType<typeof setTimeout> | null = null;
  const schedule = (() => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => { timer = null; refresh(); }, delay);
  }) as (() => void) & { cancel: () => void };
  schedule.cancel = () => { if (timer) clearTimeout(timer); timer = null; };
  return schedule;
}

export function reduceRealtimeState(state: RealtimeState, envelope: RealtimeEnvelope): RealtimeState {
  const id = envelope.conversation_id;
  if (envelope.type === 'snapshot') {
    const snapshot = envelope.data as RealtimeSnapshot;
    const activity = { ...state.activity };
    for (const event of snapshot.activity ?? []) {
      if (event.conversation_id !== undefined) activity[event.conversation_id] = [...(activity[event.conversation_id] ?? []), event];
    }
    return { ...state, conversations: snapshot.conversations ?? [], activity };
  }
  if (id === undefined || id === null) return state;
  if (envelope.type === 'conversation') {
    const data = envelope.data as Partial<Conversation>;
    return { ...state, conversations: state.conversations.map((conversation) => conversation.id === id ? { ...conversation, ...data } : conversation) };
  }
  if (envelope.type === 'activity') return { ...state, activity: { ...state.activity, [id]: [...(state.activity[id] ?? []), { ...(envelope.data as RealtimeActivity), conversation_id: id }] } };
  if (envelope.type === 'token') {
    const token = typeof envelope.data === 'string' ? envelope.data : String((envelope.data as { token?: unknown }).token ?? '');
    return { ...state, tokens: { ...state.tokens, [id]: `${state.tokens[id] ?? ''}${token}` } };
  }
  if (envelope.type === 'message') {
    const message = envelope.data as InternalChatMessage;
    const chat = state.chats[id] ?? { messages: [] };
    return { ...state, tokens: Object.fromEntries(Object.entries(state.tokens).filter(([key]) => Number(key) !== id)), chats: { ...state.chats, [id]: { messages: [...chat.messages.filter((item) => item.id !== message.id), message] } } };
  }
  return state;
}

interface RealtimeClientOptions {
  url?: string;
  factory?: WebSocketFactory;
  onStatus?: (status: ConnectionStatus) => void;
  onReconnect?: () => Promise<void>;
  baseDelay?: number;
  maxDelay?: number;
}
export class RealtimeClient {
  private socket: FakeWebSocket | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private attempts = 0;
  private stopped = true;
  private readonly listeners = new Set<(envelope: RealtimeEnvelope) => void>();
  private readonly statusListeners = new Set<(status: ConnectionStatus) => void>();
  private readonly recoveryListeners = new Set<() => Promise<void>>();
  private readonly options: Required<Pick<RealtimeClientOptions, 'url' | 'factory' | 'baseDelay' | 'maxDelay'>> & RealtimeClientOptions;
  constructor(options: RealtimeClientOptions = {}) {
    this.options = { url: '/panel/ws', factory: (url) => new WebSocket(new URL(url, globalThis.location?.origin ?? 'http://localhost').toString().replace(/^http/, 'ws')) as unknown as FakeWebSocket, baseDelay: 250, maxDelay: 5000, ...options };
  }
  subscribe(listener: (envelope: RealtimeEnvelope) => void) { this.listeners.add(listener); return () => this.listeners.delete(listener); }
  subscribeStatus(listener: (status: ConnectionStatus) => void) { this.statusListeners.add(listener); return () => this.statusListeners.delete(listener); }
  registerRecovery(listener: () => Promise<void>) { this.recoveryListeners.add(listener); return () => this.recoveryListeners.delete(listener); }
  connect() { if (!this.stopped && this.socket) return; this.stopped = false; this.open(false); }
  disconnect() { this.stopped = true; if (this.timer) clearTimeout(this.timer); this.timer = null; this.socket?.close(); this.socket = null; this.setStatus('disconnected'); this.listeners.clear(); this.statusListeners.clear(); this.recoveryListeners.clear(); }
  private setStatus(status: ConnectionStatus) { this.options.onStatus?.(status); this.statusListeners.forEach((listener) => listener(status)); }
  private open(reconnecting: boolean) {
    if (this.stopped) return;
    this.setStatus(reconnecting ? 'reconnecting' : 'connecting');
    const socket = this.options.factory(this.options.url);
    this.socket = socket;
    socket.onopen = () => { void (async () => { if (reconnecting) { await this.options.onReconnect?.(); await Promise.all([...this.recoveryListeners].map((listener) => listener())); } this.attempts = 0; this.setStatus('connected'); })().catch(() => this.setStatus('disconnected')); };
    socket.onmessage = (event) => { try { const envelope = JSON.parse(event.data) as RealtimeEnvelope; this.listeners.forEach((listener) => listener(envelope)); } catch { /* best-effort stream */ } };
    socket.onerror = () => socket.close();
    socket.onclose = () => { if (this.socket !== socket) return; this.socket = null; if (!this.stopped) { this.setStatus('disconnected'); this.scheduleReconnect(); } };
  }
  private scheduleReconnect() { const delay = Math.min(this.options.maxDelay, this.options.baseDelay * 2 ** this.attempts++); this.timer = setTimeout(() => this.open(true), delay); }
}
export const realtimeClient = new RealtimeClient();
