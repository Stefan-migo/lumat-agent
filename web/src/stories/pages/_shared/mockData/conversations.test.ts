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
