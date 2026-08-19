import type { BadgeTone } from "../../../components/primitives/Badge";

const CASE_STATUS_TONES: Record<string, BadgeTone> = {
  abierto: "neutral",
  en_evaluacion: "warning",
  escalado: "danger",
  cerrado: "success",
};

const CUSTOMER_STATE_TONES: Record<string, BadgeTone> = {
  nuevo: "warning",
  activo: "success",
  inactivo: "neutral",
  bloqueado: "danger",
};

/** Case.status → BadgeTone (design D4; R-PRD-PG-7). Unknown → neutral. */
export function caseStatusTone(status: string): BadgeTone {
  return CASE_STATUS_TONES[status] ?? "neutral";
}

/** CustomerState → BadgeTone (design D4; R-PRD-PG-7). Unknown → neutral. */
export function customerStateTone(state: string): BadgeTone {
  return CUSTOMER_STATE_TONES[state] ?? "neutral";
}
