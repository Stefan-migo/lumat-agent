import type { Doc } from "../../../../types";

/** KB document mocks matching to_doc_dict() in app/panel/api/serializers.py
 *  (R-PRD-PG-3, KB-3/4): {id, title, format, version, active_version, active,
 *  provider, model, cost_meta, created_at} — snake_case, 6-decimal USD cost
 *  (`'%.6f' % cost_meta` in the Jinja list), ISO datetimes, nullable provider/
 *  model/cost. Covers all 3 DocFormat values, both active states, and docs
 *  with/without prior versions (Restore select). */
export const docs: Doc[] = [
  {
    id: 1,
    title: "Manual de atencion al cliente",
    format: "pdf",
    version: 3,
    active_version: 2,
    active: true,
    provider: "OpenRouter",
    model: "deepseek-chat",
    cost_meta: 0.000412,
    created_at: "2026-07-10T14:02:00-04:00",
  },
  {
    id: 2,
    title: "Procedimiento de emergencia gas",
    format: "pdf",
    version: 1,
    active_version: 1,
    active: true,
    provider: "OpenRouter",
    model: "deepseek-chat",
    cost_meta: 0.000298,
    created_at: "2026-07-14T09:30:00-04:00",
  },
  {
    id: 3,
    title: "Tarifas y planes vigentes",
    format: "md",
    version: 2,
    active_version: 2,
    active: true,
    provider: "OpenRouter",
    model: "deepseek-chat",
    cost_meta: 0.000187,
    created_at: "2026-07-21T11:45:00-04:00",
  },
  {
    id: 4,
    title: "FAQ portabilidad numerica",
    format: "md",
    version: 1,
    active_version: 1,
    active: false,
    provider: "OpenRouter",
    model: "deepseek-chat",
    cost_meta: 0.000154,
    created_at: "2026-07-28T16:20:00-04:00",
  },
  {
    id: 5,
    title: "Comunas y zonas de cobertura",
    format: "csv",
    version: 4,
    active_version: 3,
    active: true,
    provider: null,
    model: null,
    cost_meta: null,
    created_at: "2026-08-02T10:15:00-04:00",
  },
];
