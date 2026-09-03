import { describe, expect, it } from "vitest";
import type { Conversation, ConversationThread } from "../../../../types";
import { conversations, messages } from "./conversations";
import { clients } from "./clients";

const CONVERSATION_KEYS = [
  "id",
  "customer_id",
  "wa_phone",
  "state",
  "summary",
  "latest_inbound_at",
  "reply_window_open",
  "delivery_summary",
  "last_message_at",
  "created_at",
  "closed_at",
].sort();

const MESSAGE_KEYS = [
  "id",
  "conversation_id",
  "direction",
  "msg_type",
  "text",
  "media_url",
  "created_at",
].sort();

// Conversation.state domain (R-PRD-PG-8/R-PRD-PG-14): bot | human | closed.
const CONV_STATES: string[] = ["bot", "human", "closed"];

// Deterministic "now" reference aligned to the mock timeline (2026-08-20).
// The 24h reply window (R-PRD-PG-10) is open when now - last_message_at < 24h.
const NOW_MS = Date.parse("2026-08-20T12:00:00-04:00");
const HOURS_24 = 24 * 60 * 60 * 1000;

describe("Conversation mock (conversations.ts)", () => {
  it("exports a non-empty Conversation[]", () => {
    const list: Conversation[] = conversations;
    expect(list.length).toBeGreaterThan(0);
  });

  it("keeps serializer shape fidelity: snake_case keys + nullables (R-PRD-PG-3)", () => {
    const keys = Object.keys(conversations[0]).sort();
    expect(keys).toEqual(CONVERSATION_KEYS);
  });

  it("exports a non-empty Message[] decodable as ConversationThread.messages", () => {
    const thread: Pick<ConversationThread, "messages"> = { messages };
    expect(thread.messages.length).toBeGreaterThan(0);
  });

  it("keeps Message serializer shape fidelity (R-PRD-PG-3)", () => {
    const keys = Object.keys(messages[0]).sort();
    expect(keys).toEqual(MESSAGE_KEYS);
  });

  it("references a real Customer from clients.ts by id", () => {
    const first = conversations[0];
    const customer = clients.find((c) => c.id === first.customer_id);
    expect(customer, `customer id ${first.customer_id} should exist in clients.ts`).toBeDefined();
  });

  it("uses realistic Chilean wa_phone prefixes (E.164 +56)", () => {
    for (const c of conversations) {
      if (c.wa_phone) {
        expect(c.wa_phone).toMatch(/^\+56\d{9}$/);
      }
    }
  });

  it("assigns every message to a conversation in the mock", () => {
    const ids = new Set(conversations.map((c) => c.id));
    for (const m of messages) {
      expect(ids.has(m.conversation_id), `message ${m.id} -> conv ${m.conversation_id}`).toBe(true);
    }
  });
});

describe("Conversation state domain (R-PRD-PG-8 / R-PRD-PG-14)", () => {
  it("keeps every conversation state within bot|human|closed and no 'open' remains", () => {
    for (const c of conversations) {
      expect(
        CONV_STATES.includes(c.state),
        `conversation ${c.id} has invalid state '${c.state}'`,
      ).toBe(true);
    }
    expect(conversations.some((c) => c.state === "open"), "no conversation can stay 'open'").toBe(false);
  });

  it("covers every state bot, human and closed at least once (R-PRD-PG-8)", () => {
    const present = new Set(conversations.map((c) => c.state));
    for (const state of CONV_STATES) {
      expect(present.has(state), `missing conversation state: ${state}`).toBe(true);
    }
  });

  it("contains a stale conversation older than the 24h reply window (R-PRD-PG-10)", () => {
    const stale = conversations.filter((c) => {
      if (!c.last_message_at) return false;
      return NOW_MS - Date.parse(c.last_message_at) >= HOURS_24;
    });
    // Triangulation: at least one stale row exists AND at least one is still
    // within the window (open) so the closed-window path has real data to act on.
    expect(stale.length, "at least one conversation must be outside the 24h window").toBeGreaterThan(0);
    const open = conversations.filter((c) => {
      if (!c.last_message_at) return false;
      return NOW_MS - Date.parse(c.last_message_at) < HOURS_24;
    });
    expect(open.length, "at least one conversation must still fall inside the 24h window").toBeGreaterThan(0);
  });

  it("a human-state conversation carries an outbound human-reply message (D6)", () => {
    const humanIds = new Set(
      conversations.filter((c) => c.state === "human").map((c) => c.id),
    );
    expect(humanIds.size, "mock needs a human-state conversation").toBeGreaterThan(0);
    const humanOutbound = messages.filter(
      (m) => humanIds.has(m.conversation_id) && m.direction === "outbound",
    );
    expect(
      humanOutbound.length,
      "a human-state conversation must have an outbound human-reply message",
    ).toBeGreaterThan(0);
  });
});
