import { describe, expect, it } from "vitest";
import type { Customer, CustomerState } from "../../../../types";
import { clients } from "./clients";

const CUSTOMER_STATES: CustomerState[] = ["nuevo", "activo", "inactivo", "bloqueado"];

describe("Customer mock (clients.ts)", () => {
  it("exports a non-empty Customer[]", () => {
    const customers: Customer[] = clients;
    expect(customers.length).toBeGreaterThan(0);
  });

  it("covers every CustomerState (R-PRD-PG-7)", () => {
    const present = new Set(clients.map((c) => c.state));
    for (const state of CUSTOMER_STATES) {
      expect(present.has(state), `missing state: ${state}`).toBe(true);
    }
  });

  it("keeps serializer shape fidelity: snake_case keys + nullables (R-PRD-PG-3)", () => {
    const keys = Object.keys(clients[0]).sort();
    expect(keys).toEqual(
      [
        "address",
        "comuna",
        "consent_at",
        "consent_status",
        "created_at",
        "email",
        "id",
        "name",
        "phone_e164",
        "state",
      ].sort(),
    );
  });

  it("uses realistic Chilean phone numbers (E.164 +56)", () => {
    for (const c of clients) {
      expect(c.phone_e164).toMatch(/^\+56\d{9}$/);
    }
  });
});
