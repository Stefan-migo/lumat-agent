import { describe, expect, it } from "vitest";
import type { BadgeTone } from "../../../components/primitives/Badge";
import {
  appointmentStatusLabel,
  appointmentStatusTone,
  caseStatusLabel,
  caseStatusTone,
  conversationLabel,
  customerStateLabel,
  customerStateTone,
  directionLabel,
  kbStatusLabel,
} from "./toneMaps";

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
  // All 8 CustomerState values, taken from the real domain enum `customer_state`
  // (nuevo/contactado/pendiente/agendado/en_evaluacion/finalizado/cancelado/postventa).
  // The previous four-value list was fiction: the API serialises `customer.state.value`
  // and only `nuevo` overlapped with it.
  it("maps nuevo to warning", () => {
    expect(customerStateTone("nuevo")).toBe("warning");
  });

  it("maps contactado to neutral", () => {
    expect(customerStateTone("contactado")).toBe("neutral");
  });

  it("maps pendiente to warning", () => {
    expect(customerStateTone("pendiente")).toBe("warning");
  });

  it("maps agendado to neutral", () => {
    expect(customerStateTone("agendado")).toBe("neutral");
  });

  it("maps en_evaluacion to warning", () => {
    expect(customerStateTone("en_evaluacion")).toBe("warning");
  });

  it("maps finalizado to success", () => {
    expect(customerStateTone("finalizado")).toBe("success");
  });

  it("maps cancelado to neutral", () => {
    expect(customerStateTone("cancelado")).toBe("neutral");
  });

  it("maps postventa to neutral", () => {
    expect(customerStateTone("postventa")).toBe("neutral");
  });

  it("maps every CustomerState to a valid BadgeTone", () => {
    const states: string[] = [
      "nuevo",
      "contactado",
      "pendiente",
      "agendado",
      "en_evaluacion",
      "finalizado",
      "cancelado",
      "postventa",
    ];
    expect(states.length).toBe(8);
    for (const s of states) {
      expect(VALID_TONES).toContain(customerStateTone(s));
    }
  });

  // The former "maps each distinct state to a distinct tone (no collisions)" case is gone
  // on purpose: eight domain states cannot map injectively onto four BadgeTone values, so
  // that assertion only held while the map described a four-state vocabulary that does not
  // exist in the domain.
});

describe("appointmentStatusTone", () => {
  // All Appointment.status values on the shared map: booked/cancelled/completed/no_show.
  it("maps booked to neutral", () => {
    expect(appointmentStatusTone("booked")).toBe("neutral");
  });

  it("maps cancelled to neutral", () => {
    expect(appointmentStatusTone("cancelled")).toBe("neutral");
  });

  it("maps completed to success", () => {
    expect(appointmentStatusTone("completed")).toBe("success");
  });

  it("maps no_show to danger", () => {
    expect(appointmentStatusTone("no_show")).toBe("danger");
  });

  it("reserves success for an outcome that actually happened", () => {
    // DESIGN_SYSTEM.md:416 reserves the Positive level for a confirmed successful
    // outcome, and :420 states that the business outcome decides the tone. A booking
    // has not happened yet, so it must not borrow the completed visit's green.
    for (const state of ["booked", "cancelled"]) {
      expect(appointmentStatusTone(state)).not.toBe("success");
    }
    expect(appointmentStatusTone("completed")).toBe("success");
  });

  it("maps every documented appointment status to a valid BadgeTone", () => {
    const statuses: string[] = ["booked", "cancelled", "completed", "no_show"];
    expect(statuses.length).toBeGreaterThan(0);
    for (const s of statuses) {
      expect(VALID_TONES).toContain(appointmentStatusTone(s));
    }
  });

  it("lets booked and cancelled share a tone while their labels stay distinct", () => {
    // Deliberate, and the one place this map must NOT follow the no-collision shape
    // used above: a booking and a cancellation are both routine records, so they share
    // the neutral badge. The state channel is the label, as D5 of
    // odd/tasks/technician-status.md required ("by text, not by colour alone"); the
    // tone only reinforces it. The outcome tones stay apart from them.
    expect(appointmentStatusTone("booked")).toBe(appointmentStatusTone("cancelled"));
    expect(appointmentStatusLabel("booked")).not.toBe(appointmentStatusLabel("cancelled"));
    expect(appointmentStatusTone("completed")).not.toBe(appointmentStatusTone("booked"));
    expect(appointmentStatusTone("no_show")).not.toBe(appointmentStatusTone("booked"));
  });
});

describe("approved Spanish labels (DS-UI-LABELS)", () => {
  // Every typed state union in types.ts (plus documented conversation/case/KB
  // string values) MUST resolve to a non-empty Spanish label, and raw state
  // keys MUST NOT leak onto the surface.
  const domains: Array<[string, (key: string) => string, string[]]> = [
    // CustomerState union: the 8 real `customer_state` domain values
    [
      "customerStateLabel",
      customerStateLabel,
      ["nuevo", "contactado", "pendiente", "agendado", "en_evaluacion", "finalizado", "cancelado", "postventa"],
    ],
    // MessageDirection union: 'inbound'|'outbound'
    ["directionLabel", directionLabel, ["inbound", "outbound"]],
    // Documented Conversation.state values (bot/human/closed, plus pending/escalated)
    ["conversationLabel", conversationLabel, ["bot", "human", "closed", "pending", "escalated"]],
    // Documented Case.status values
    ["caseStatusLabel", caseStatusLabel, ["abierto", "en_evaluacion", "escalado", "cerrado"]],
    // Documented KB activity states (activo/deshabilitado/procesando/error)
    ["kbStatusLabel", kbStatusLabel, ["activo", "deshabilitado", "procesando", "error"]],
  ];

  for (const [name, label, keys] of domains) {
    it(`${name} resolves every documented state to a non-empty Spanish label`, () => {
      expect(keys.length).toBeGreaterThan(0);
      for (const key of keys) {
        const value = label(key);
        expect(value).toBeTruthy();
        expect(value.trim().length).toBeGreaterThan(0);
        expect(value).not.toBe(key);
      }
    });

    it(`${name} has no duplicate labels across distinct states`, () => {
      const labels = keys.map(label);
      expect(new Set(labels).size).toBe(keys.length);
    });
  }

  it("matches the approved LABELS table for conversation states", () => {
    expect(conversationLabel("bot")).toBe("Agente atendiendo");
    expect(conversationLabel("human")).toBe("Atención humana");
    expect(conversationLabel("closed")).toBe("Cerrada");
  });

  it("matches the approved LABELS table for customer states", () => {
    expect(customerStateLabel("nuevo")).toBe("Nuevo");
    expect(customerStateLabel("contactado")).toBe("Contactado");
    expect(customerStateLabel("pendiente")).toBe("Pendiente");
    expect(customerStateLabel("agendado")).toBe("Agendado");
    expect(customerStateLabel("en_evaluacion")).toBe("En evaluación");
    expect(customerStateLabel("finalizado")).toBe("Finalizado");
    expect(customerStateLabel("cancelado")).toBe("Cancelado");
    expect(customerStateLabel("postventa")).toBe("Postventa");
  });

  it("matches the approved LABELS table for case statuses", () => {
    expect(caseStatusLabel("abierto")).toBe("Abierto");
    expect(caseStatusLabel("en_evaluacion")).toBe("En evaluación");
    expect(caseStatusLabel("escalado")).toBe("Escalado");
    expect(caseStatusLabel("cerrado")).toBe("Cerrado");
  });

  it("matches the approved LABELS table for KB activity states", () => {
    expect(kbStatusLabel("activo")).toBe("Activo");
    expect(kbStatusLabel("deshabilitado")).toBe("Deshabilitado");
    expect(kbStatusLabel("procesando")).toBe("Procesando");
    expect(kbStatusLabel("error")).toBe("Error");
  });

  it("matches the approved LABELS table for message directions", () => {
    expect(directionLabel("inbound")).toBe("Entrante");
    expect(directionLabel("outbound")).toBe("Saliente");
  });
});
