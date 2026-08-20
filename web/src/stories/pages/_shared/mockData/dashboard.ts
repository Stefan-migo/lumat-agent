import type { Kpis } from "../../../../types";

/** Dashboard mock matching `app/panel/routes/dashboard.py compute_kpis()`
 *  + `Kpis` serializer shape: contacts / motivos / derived / visit_requests /
 *  window_days / window_start (snake_case; `window_start` is an ISO date from
 *  `start.date().isoformat()`). Realistic Lumat services (R-PRD-PG-3). */
export const kpis: Kpis = {
  contacts: 128,
  motivos: [
    ["Gestión comercial", 42],
    ["Consulta técnica", 31],
    ["Cobros / facturación", 18],
    ["Soporte postventa", 15],
    ["Visita técnica", 22],
  ],
  derived: 27,
  visit_requests: 14,
  window_days: 7,
  window_start: "2026-08-12",
};
