import { afterEach, describe, expect, it, vi } from "vitest";
import {
  RealtimeClient,
  initialRealtimeState,
  reduceRealtimeState,
  type FakeWebSocket,
  type RealtimeEnvelope,
  coalesceSnapshotRefresh,
} from "./realtime";

class Socket implements FakeWebSocket {
  static instances: Socket[] = [];
  readyState = 0;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  close = vi.fn(() => { this.readyState = 3; this.onclose?.(); });
  constructor() { Socket.instances.push(this); }
  open() { this.readyState = 1; this.onopen?.(); }
  closeUnexpectedly() { this.readyState = 3; this.onclose?.(); }
  sendEnvelope(envelope: RealtimeEnvelope) { this.onmessage?.({ data: JSON.stringify(envelope) }); }
}

afterEach(() => {
  Socket.instances = [];
  vi.useRealTimers();
});

describe("realtime reducer", () => {
  it("updates a conversation and appends persisted activity without losing history", () => {
    const state = reduceRealtimeState(initialRealtimeState, {
      type: "snapshot",
      data: { conversations: [{ id: 4, customer_id: 8, state: "bot" }], activity: [] },
    });
    const next = reduceRealtimeState(state, { type: "conversation", conversation_id: 4, data: { state: "human" } });
    const withActivity = reduceRealtimeState(next, { type: "activity", conversation_id: 4, data: { event: "classified", actor: "agent" } });
    expect(withActivity.conversations[0].state).toBe("human");
    expect(withActivity.activity[4]).toHaveLength(1);
    expect(withActivity.activity[4][0].event).toBe("classified");
  });

  it("appends a committed message and replaces a repeated id in place", () => {
    let state = reduceRealtimeState(initialRealtimeState, { type: "message", conversation_id: 12, data: { id: 9, thread_id: 12, author: "agent", content: "Hello", status: "processed" } });
    expect(state.chats[12].messages[0].content).toBe("Hello");
    state = reduceRealtimeState(state, { type: "message", conversation_id: 12, data: { id: 9, thread_id: 12, author: "agent", content: "Hello, edited", status: "processed" } });
    expect(state.chats[12].messages).toHaveLength(1);
    expect(state.chats[12].messages[0].content).toBe("Hello, edited");
  });
});

describe("RealtimeClient", () => {
  it("immediately publishes the current connected status to new subscribers", () => {
    const client = new RealtimeClient({ factory: () => new Socket() });
    client.connect();
    Socket.instances[0].open();
    const listener = vi.fn();

    client.subscribeStatus(listener);

    expect(listener).toHaveBeenCalledWith("connected");
    client.disconnect();
  });

  it("reconnects with bounded backoff and recovers only after REST refresh", async () => {
    vi.useFakeTimers();
    const recover = vi.fn(async () => undefined);
    const statuses: string[] = [];
    const client = new RealtimeClient({ factory: () => new Socket(), onStatus: (status) => statuses.push(status), onReconnect: recover, baseDelay: 10, maxDelay: 20 });
    client.connect();
    Socket.instances[0].open();
    Socket.instances[0].closeUnexpectedly();
    expect(statuses).toContain("disconnected");
    await vi.advanceTimersByTimeAsync(10);
    expect(Socket.instances).toHaveLength(2);
    Socket.instances[1].open();
    await vi.waitFor(() => expect(recover).toHaveBeenCalledTimes(1));
    await vi.waitFor(() => expect(statuses.at(-1)).toBe("connected"));
    client.disconnect();
    expect(Socket.instances[1].close).toHaveBeenCalledTimes(1);
  });

  it("stops reconnecting and removes listeners during cleanup", async () => {
    vi.useFakeTimers();
    const client = new RealtimeClient({ factory: () => new Socket(), baseDelay: 10 });
    const listener = vi.fn();
    client.subscribe(listener);
    client.connect();
    Socket.instances[0].closeUnexpectedly();
    client.disconnect();
    await vi.advanceTimersByTimeAsync(100);
    expect(Socket.instances).toHaveLength(1);
    Socket.instances[0].sendEnvelope({ type: "message", conversation_id: 1, data: { id: 1, thread_id: 1, author: "agent", content: "ignored", status: "processed" } });
    expect(listener).not.toHaveBeenCalled();
  });

  it("surfaces notification envelopes to subscribers", () => {
    const client = new RealtimeClient({ factory: () => new Socket() });
    const listener = vi.fn();
    client.subscribe(listener);
    client.connect();
    Socket.instances[0].sendEnvelope({ type: "notification", data: { source: "appointment" } });

    expect(listener).toHaveBeenCalledWith({ type: "notification", data: { source: "appointment" } });
    client.disconnect();
  });

  it("coalesces a burst of snapshot refresh requests into one callback", () => {
    vi.useFakeTimers();
    const refresh = vi.fn();
    const schedule = coalesceSnapshotRefresh(refresh, 100);

    schedule();
    schedule();
    schedule();
    vi.advanceTimersByTime(99);
    expect(refresh).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(refresh).toHaveBeenCalledTimes(1);
  });
});
