import { describe, expect, it } from "vitest";
import type { Memory, MemoryStatus, MemoryType } from "../../../../types";
import { memories } from "./memories";

const MEMORY_TYPES: MemoryType[] = [
  "decision",
  "discovery",
  "pattern",
  "preference",
  "customer_memo",
  "summary",
  "session",
  "prompt",
];
const MEMORY_STATUSES: MemoryStatus[] = ["active", "needs_review", "archived"];

describe("Customer memory mock (memories.ts)", () => {
  it("exports a non-empty Memory[]", () => {
    const rows: Memory[] = memories;
    expect(rows.length).toBeGreaterThan(0);
  });

  it("keeps serializer shape fidelity: snake_case keys + nullables (MEM-6)", () => {
    const keys = Object.keys(memories[0]).sort();
    expect(keys).toEqual(
      [
        "contenido",
        "created_at",
        "entity_id",
        "id",
        "pin",
        "scope",
        "status",
        "tipo",
        "titulo",
        "topic_key",
        "updated_at",
      ].sort(),
    );
  });

  it("uses only known MemoryType and MemoryStatus values", () => {
    for (const m of memories) {
      expect(MEMORY_TYPES).toContain(m.tipo);
      expect(MEMORY_STATUSES).toContain(m.status);
    }
  });

  it("includes the customer_memo topic (CR-7 ficha surface)", () => {
    expect(memories.some((m) => m.topic_key === "customer_memo")).toBe(true);
  });

  it("parses ISO-8601 datetimes", () => {
    for (const m of memories) {
      if (m.created_at) expect(!Number.isNaN(Date.parse(m.created_at))).toBe(true);
      if (m.updated_at) expect(!Number.isNaN(Date.parse(m.updated_at))).toBe(true);
    }
  });
});
