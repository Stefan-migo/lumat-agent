import { describe, expect, it } from "vitest";
import type { Case } from "../../../../types";
import { casesData, users } from "./cases";
import { clients } from "./clients";

/** Serializer keys from to_case_dict() + embedded customer (R-PRD-PG-3). */
const CASE_KEYS = [
  "ack_by",
  "acknowledged_at",
  "closed_at",
  "conversation_id",
  "created_at",
  "customer",
  "customer_id",
  "emergency",
  "escalated_at",
  "id",
  "priority",
  "responsible_id",
  "service",
  "status",
  "summary",
].sort();

// All 4 case statuses per design D4 + Jinja cases list template.
const CASE_STATUSES: string[] = ["abierto", "en_evaluacion", "escalado", "cerrado"];

describe("Cases mock (cases.ts)", () => {
  it("exports a non-empty CasesResponse with cases and users", () => {
    expect(casesData.cases.length).toBeGreaterThan(0);
    expect(users.length).toBeGreaterThan(0);
  });

  it("covers every CaseStatus incl. emergency flag (T4.1)", () => {
    const present = new Set(casesData.cases.map((c) => c.status));
    for (const status of CASE_STATUSES) {
      expect(present.has(status), `missing case status: ${status}`).toBe(true);
    }
    expect(casesData.cases.some((c) => c.emergency)).toBe(true);
    expect(casesData.cases.some((c) => !c.emergency)).toBe(true);
  });

  it("keeps serializer shape fidelity: snake_case keys + embedded customer (R-PRD-PG-3)", () => {
    const keys = Object.keys(casesData.cases[0]).sort();
    expect(keys).toEqual(CASE_KEYS);
  });

  it("keeps UserRef shape fidelity: {id, username} only (D8)", () => {
    for (const u of users) {
      const keys = Object.keys(u).sort();
      expect(keys).toEqual(["id", "username"]);
    }
  });

  it("references a real Customer from clients.ts by embedded customer id", () => {
    for (const c of casesData.cases) {
      expect(c.customer.id, `case ${c.id} customer should exist`).toBeGreaterThan(0);
      expect(
        clients.some((k) => k.id === c.customer.id),
        `case ${c.id} -> customer id ${c.customer.id} should exist in clients.ts`,
      ).toBe(true);
    }
  });

  it("uses realistic Chilean phone numbers (E.164 +56) on embedded customers", () => {
    for (const c of casesData.cases) {
      if (c.customer.phone_e164) {
        expect(c.customer.phone_e164).toMatch(/^\+56\d{9}$/);
      }
    }
  });

  it("assigns a responsible from the users list when responsible_id set", () => {
    const ids = new Set(users.map((u) => u.id));
    for (const c of casesData.cases) {
      if (c.responsible_id !== null) {
        expect(
          ids.has(c.responsible_id),
          `case ${c.id} -> responsible_id ${c.responsible_id} should exist in users`,
        ).toBe(true);
      }
    }
  });

  it("escaped/escalated emergency cases carry status escalado per EM-4", () => {
    const emergency = casesData.cases.filter((c) => c.emergency);
    for (const c of emergency) {
      expect(c.status).toBe("escalado");
      expect(c.escalated_at).not.toBeNull();
    }
  });

  it("closed cases record closed_at", () => {
    const closed = casesData.cases.filter((c) => c.status === "cerrado");
    for (const c of closed) {
      expect(c.closed_at).not.toBeNull();
    }
  });

  it("casts casesData to Case[] for the page-story consumers", () => {
    const list: Case[] = casesData.cases;
    expect(list.length).toBe(casesData.cases.length);
  });
});
