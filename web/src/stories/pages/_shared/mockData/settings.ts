import type { Settings } from "../../../../types";

/** Settings mock matching GET /settings in app/panel/api/routes/settings.py
 *  (R-PRD-PG-3): {scope_rules, keywords, tone, conversation_limit, daily_limit,
 *  meta_cost, snapshot}. `snapshot` mirrors spend_snapshot() in
 *  app/services/costs.py (SS-4) — without a conversation id the per-conversation
 *  fields are null and mode reflects only the daily scope. Values align with
 *  the settings Jinja template (SS-1..SS-5). */
export const settings: Settings = {
  scope_rules: {
    atencion_masive: "bot_resolve",
    cobros: "always_escalate",
    emergencias: "always_escalate",
    visitas: "bot_resolve",
  },
  keywords: ["fuga", "corte", "emergencia", "gas", "medidor"],
  tone: "cercana y clara, lenguaje simple",
  conversation_limit: 1.5,
  daily_limit: 5.0,
  meta_cost: 0.01,
  snapshot: {
    date: "2026-08-19",
    conversation_spend: null,
    conversation_limit: 1.5,
    conversation_percent: null,
    daily_spend: 1.8745,
    daily_limit: 5.0,
    daily_percent: 37.49,
    mode: "normal",
  },
};
