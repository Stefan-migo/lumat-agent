import type { Memory } from "../../../../types";

/** Customer memory mocks matching to_memory_dict() (MEM-6 panel
 *  /clients/{id}/memories): {id, scope, entity_id, tipo, titulo, contenido,
 *  topic_key, pin, status, created_at, updated_at} — snake_case, ISO
 *  datetimes, nullable timestamps. Realistic preferences/decisions a panel
 *  operator would keep per customer. Covers several MemoryType values and both
 *  pin states for the mark/pin control. */
export const memories: Memory[] = [
  {
    id: 1,
    scope: "customer",
    entity_id: "1",
    tipo: "customer_memo",
    titulo: "customer_memo",
    contenido:
      "acta del cierre: cliente pidio recalcular el presupuesto de instalacion del termo; conformaron aumento de cobertura.",
    topic_key: "customer_memo",
    pin: false,
    status: "active",
    created_at: "2026-08-18T18:02:00-04:00",
    updated_at: "2026-08-18T18:02:00-04:00",
  },
  {
    id: 2,
    scope: "customer",
    entity_id: "1",
    tipo: "preference",
    titulo: "horario",
    contenido: "prefiere que la contacten despues de las 18h entre semana.",
    topic_key: "contacto",
    pin: true,
    status: "active",
    created_at: "2026-08-11T10:14:00-04:00",
    updated_at: "2026-08-12T09:05:00-04:00",
  },
  {
    id: 3,
    scope: "customer",
    entity_id: "1",
    tipo: "decision",
    titulo: "presupuesto",
    contenido: "acepto el presupuesto de $340.000 para el calefont con instalacion a domicilio.",
    topic_key: "presupuesto",
    pin: false,
    status: "active",
    created_at: "2026-07-28T12:40:00-04:00",
    updated_at: "2026-07-28T12:40:00-04:00",
  },
];
