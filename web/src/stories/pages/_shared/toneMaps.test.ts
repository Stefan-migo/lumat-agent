import { describe, expect, it } from "vitest";
import type { BadgeTone } from "../../../components/primitives/Badge";
import { caseStatusTone, customerStateTone } from "./toneMaps";

const VALID_TONES: BadgeTone[] = ["neutral", "success", "warning", "danger"];

describe("caseStatusTone", () => {
  // All Case.status values per design D4: abierto/en_evaluacion/escalado/cerrado.
  it("maps abierto to neutral", () => {
    expect(caseStatusTone("abierto")).toBe("neutral");
  });

  it("maps en_evaluacion to warning", () => {
    expect(caseStatusTone("en_evaluacion")).toBe("warning");
  });

  it("maps escalado to danger", () => {
    expect(caseStatusTone("escalado")).toBe("danger");
  });

  it("maps cerrado to success", () => {
    expect(caseStatusTone("cerrado")).toBe("success");
  });

  it("maps every documentable case status to a valid BadgeTone", () => {
    const statuses: string[] = ["abierto", "en_evaluacion", "escalado", "cerrado"];
    expect(statuses.length).toBeGreaterThan(0);
    for (const s of statuses) {
      expect(VALID_TONES).toContain(caseStatusTone(s));
    }
  });

  it("maps each distinct status to a distinct tone (no collisions)", () => {
    const tones = ["abierto", "en_evaluacion", "escalado", "cerrado"].map(caseStatusTone);
    expect(new Set(tones).size).toBe(4);
  });
});

describe("customerStateTone", () => {
  // All CustomerState values per design D4: nuevo/activo/inactivo/bloqueado.
  it("maps nuevo to warning", () => {
    expect(customerStateTone("nuevo")).toBe("warning");
  });

  it("maps activo to success", () => {
    expect(customerStateTone("activo")).toBe("success");
  });

  it("maps inactivo to neutral", () => {
    expect(customerStateTone("inactivo")).toBe("neutral");
  });

  it("maps bloqueado to danger", () => {
    expect(customerStateTone("bloqueado")).toBe("danger");
  });

  it("maps every CustomerState to a valid BadgeTone", () => {
    const states: string[] = ["nuevo", "activo", "inactivo", "bloqueado"];
    expect(states.length).toBeGreaterThan(0);
    for (const s of states) {
      expect(VALID_TONES).toContain(customerStateTone(s));
    }
  });

  it("maps each distinct state to a distinct tone (no collisions)", () => {
    const tones = ["nuevo", "activo", "inactivo", "bloqueado"].map(customerStateTone);
    expect(new Set(tones).size).toBe(4);
  });
});
