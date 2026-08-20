import { describe, expect, it } from "vitest";
import type { UserRef } from "../../../../types";
import { users } from "./users";

describe("Users mock (users.ts, R-PRD-PG-12/D3)", () => {
  it("exports a non-empty UserRef[] of at least 3 rows", () => {
    expect(users.length).toBeGreaterThanOrEqual(3);
    const list: UserRef[] = users;
    expect(list.length).toBe(users.length);
  });

  it("keeps UserRef shape fidelity: {id, username} only (D8/R2)", () => {
    for (const u of users) {
      const keys = Object.keys(u).sort();
      expect(keys, `user id ${u.id} should expose only id/username`).toEqual(["id", "username"]);
    }
  });

  it("keeps user ids unique", () => {
    const ids = new Set(users.map((u) => u.id));
    expect(ids.size, "user ids must be unique").toBe(users.length);
  });

  it("assigns a non-empty username to every row", () => {
    for (const u of users) {
      expect(u.username.length, `user ${u.id} username must be non-empty`).toBeGreaterThan(0);
    }
  });

  it("overlaps with the existing cases.ts users so assignee lookups stay consistent", () => {
    // Design D3: cases.ts re-exports these same rows; ids 7/8/9 are the
    // responsible_id targets used by cases.ts, so at least those must exist.
    const ids = new Set(users.map((u) => u.id));
    expect(ids.has(7), "user id 7 (admin) must exist").toBe(true);
    expect(ids.has(8), "user id 8 (karla) must exist").toBe(true);
    expect(ids.has(9), "user id 9 (manuel) must exist").toBe(true);
  });
});
