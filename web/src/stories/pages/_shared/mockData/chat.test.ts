import { describe, expect, it } from "vitest";
import { agentChatMessages, agentStatus } from "./chat";

const MESSAGE_KEYS = ["id", "role", "text", "created_at"].sort();
const ROLES = ["admin", "agent"];

describe("Chat mock (chat.ts, R-PRD-PG-12/D2)", () => {
  it("exports a non-empty AgentChatMessage[]", () => {
    expect(agentChatMessages.length).toBeGreaterThan(0);
  });

  it("keeps AgentChatMessage shape fidelity: {id, role, text, created_at} only (D2/R3)", () => {
    for (const m of agentChatMessages) {
      const keys = Object.keys(m).sort();
      expect(keys, `chat message id ${m.id} should expose only id/role/text/created_at`).toEqual(
        MESSAGE_KEYS,
      );
    }
  });

  it("constrains every role within 'admin'|'agent' and covers both values", () => {
    const present = new Set<string>();
    for (const m of agentChatMessages) {
      expect(ROLES.includes(m.role), `message ${m.id} has invalid role '${m.role}'`).toBe(true);
      present.add(m.role);
    }
    for (const role of ROLES) {
      expect(present.has(role), `chat mock must contain at least one '${role}' message`).toBe(
        true,
      );
    }
  });

  it("keeps message ids unique and assigns non-empty text to every row", () => {
    const ids = new Set(agentChatMessages.map((m) => m.id));
    expect(ids.size, "chat message ids must be unique").toBe(agentChatMessages.length);
    for (const m of agentChatMessages) {
      expect(m.text.length, `chat message ${m.id} text must be non-empty`).toBeGreaterThan(0);
    }
  });

  it("sorts messages chronologically by created_at (oldest first)", () => {
    const times = agentChatMessages.map((m) => Date.parse(m.created_at));
    for (let i = 1; i < times.length; i++) {
      expect(times[i]).toBeGreaterThanOrEqual(times[i - 1]);
    }
  });
});

describe("AgentStatus (chat.ts, R-PRD-PG-12)", () => {
  it("covers exactly idle and processing", () => {
    const keys = Object.keys(agentStatus).sort();
    expect(keys).toEqual(["idle", "processing"]);
  });
});
