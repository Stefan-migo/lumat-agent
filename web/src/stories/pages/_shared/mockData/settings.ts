import type { Settings } from "../../../../types";

/** Settings mock matching GET /settings in app/panel/api/routes/settings.py
 *  (R-PRD-PG-3): {scope_rules, keywords, tone, messages, conversation_limit, daily_limit,
 *  meta_cost, snapshot}. `snapshot` mirrors spend_snapshot() in
 *  app/services/costs.py (SS-4) — without a conversation id the per-conversation
 *  fields are null and mode reflects only the daily scope. Values align with
 *  the settings Jinja template (SS-1..SS-5). */
export const settings: Settings = {
  model_api_key: { configured: false, source: "none", masked: "" },
  email: {
    host: "localhost",
    port: 25,
    from_address: "notificaciones@lumat.cl",
    user: "",
    tls: "none",
    password: { configured: false, masked: "" },
  },
  scope_rules: {
    atencion_masive: "bot_resolve",
    cobros: "always_escalate",
    emergencias: "always_escalate",
    visitas: "bot_resolve",
  },
  keywords: ["fuga", "corte", "emergencia", "gas", "medidor"],
  tone: "cercano",
  messages: {
    greeting: "Hola, soy el asistente virtual de Lumat.",
    greeting_short: "Hola, soy el asistente virtual de Lumat. ¿Cómo estás?",
    cannot_answer: "No puedo responder con seguridad a eso.",
    clarification: "¿Puedes elegir una opción del menú?",
    farewell: "Gracias por comunicarte con Lumat.",
    out_of_hours: "En este momento estamos fuera de horario.",
  },
  templates: [],
  hours: {
    timezone: "America/Santiago",
    schedule: [{ days: [1, 2, 3, 4, 5], open: "09:00", close: "18:00" }],
  },
  tarifa: {
    visita_tecnica: [{ desde_mes: 1, hasta_mes: 12, valor: 30000 }],
    mantencion_calefont: [
      { desde_mes: 3, hasta_mes: 10, valor: 50000 },
      { desde_mes: 11, hasta_mes: 2, valor: 40000 },
    ],
    mantencion_caldera: [
      { desde_mes: 3, hasta_mes: 10, valor: 80000 },
      { desde_mes: 11, hasta_mes: 2, valor: 60000 },
    ],
    lavado_red: [
      { desde_mes: 3, hasta_mes: 10, valor: 140000 },
      { desde_mes: 11, hasta_mes: 2, valor: 120000 },
    ],
  },
  coverage: [
    "Las Condes",
    "Ñuñoa",
    "Lo Barnechea",
    "La Reina",
    "Peñalolén",
    "Colina",
    "Huechuraba",
  ],
  persona: {
    orchestrator: "Eres Max, el asistente virtual de Lumat.",
    orchestrator_brief: "Responde en una línea cuando el costo esté ajustado.",
    customized: true,
  },
  emergency: {
    safety_instructions: [
      "Corta el suministro de gas solo si puedes hacerlo de forma segura.",
      "Abre puertas y ventanas para ventilar el lugar.",
    ],
    contacts: [
      "Emergencias: Bomberos 132 o Ambulancia 131.",
      "Lumat: +56 9 1234 5678.",
    ],
    notify_message: "Un técnico de Lumat ha sido notificado y te contactará a la brevedad.",
    customized: false,
  },
  service_durations: { Calefont: 60, Caldera: 90 },
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
