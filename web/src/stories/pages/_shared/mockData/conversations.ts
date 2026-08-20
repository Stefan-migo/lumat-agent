import type { Conversation, Message } from "../../../../types";

/** Conversation + Message mocks matching `app/panel/api/serializers.py`
 *  to_conversation_dict()/to_message_dict() (snake_case, ISO strings,
 *  nullable timestamps). Customer id 1 references `clients.ts`
 *  ("Marcela Fuentes", +56971234501) for ficha + thread rendering
 *  consistency (R-PRD-PG-3). State domain is bot|human|closed (R-PRD-PG-14);
 *  last_message_at has a deterministic timeline where 2026-08-20T12:00 is the
 *  reference "now" so 101/102/103/104 are within the 24h reply window and
 *  105 is stale (>24h) to drive the closed-window path (R-PRD-PG-10). */
export const conversations: Conversation[] = [
  {
    id: 101,
    customer_id: 1,
    wa_phone: "+56971234501",
    state: "bot",
    summary: "Fuga de agua en cocina — derivada a tecnico",
    last_message_at: "2026-08-20T09:40:00-04:00",
    created_at: "2026-08-18T09:03:00-04:00",
    closed_at: null,
  },
  {
    id: 102,
    customer_id: 1,
    wa_phone: "+56971234501",
    state: "closed",
    summary: "Cotizacion instalacion de termo",
    last_message_at: "2026-08-07T12:15:00-04:00",
    created_at: "2026-08-02T10:00:00-04:00",
    closed_at: "2026-08-07T12:20:00-04:00",
  },
  {
    id: 103,
    customer_id: 3,
    wa_phone: "+56923456703",
    state: "human",
    summary: "Consulta por cobro duplicado de boleta",
    last_message_at: "2026-08-20T08:15:00-04:00",
    created_at: "2026-08-17T08:30:00-04:00",
    closed_at: null,
  },
  {
    id: 104,
    customer_id: 2,
    wa_phone: "+56987654302",
    state: "bot",
    summary: "Consulta por horarios de atencion",
    last_message_at: "2026-08-20T10:02:00-04:00",
    created_at: "2026-08-20T08:55:00-04:00",
    closed_at: null,
  },
  {
    id: 105,
    customer_id: 4,
    wa_phone: "+56965748304",
    state: "bot",
    summary: "Solicitud de visita técnica pendiente de respuesta",
    last_message_at: "2026-08-10T14:30:00-04:00",
    created_at: "2026-08-05T11:00:00-04:00",
    closed_at: null,
  },
];

/** Message rows for the conversation thread (ConversationThread.messages). */
export const messages: Message[] = [
  {
    id: 9001,
    conversation_id: 101,
    direction: "inbound",
    msg_type: "text",
    text: "Hola, tengo una fuga de agua en la cocina de mi depto.",
    media_url: null,
    created_at: "2026-08-18T09:03:00-04:00",
  },
  {
    id: 9002,
    conversation_id: 101,
    direction: "outbound",
    msg_type: "text",
    text: "Hola Marcela, lamento el inconveniente. ¿Nos confirmas tu comuna para agendar un tecnico?",
    media_url: null,
    created_at: "2026-08-18T09:12:00-04:00",
  },
  {
    id: 9003,
    conversation_id: 101,
    direction: "inbound",
    msg_type: "text",
    text: "Providencia, Av. Providencia 1234 depto 45. ¿Puede ser hoy en la tarde?",
    media_url: null,
    created_at: "2026-08-18T09:20:00-04:00",
  },
  {
    id: 9004,
    conversation_id: 101,
    direction: "outbound",
    msg_type: "text",
    text: "Perfecto. Nuestro tecnico te visita hoy entre 17:00 y 19:00 hrs.",
    media_url: null,
    created_at: "2026-08-18T09:24:00-04:00",
  },
  {
    id: 9005,
    conversation_id: 101,
    direction: "inbound",
    msg_type: "image",
    text: "Imagen de la fuga bajo el lavaplatos",
    media_url: "https://cdn.example.cl/media/9005-fuga.jpg",
    created_at: "2026-08-18T09:31:00-04:00",
  },
  {
    id: 9006,
    conversation_id: 101,
    direction: "outbound",
    msg_type: "text",
    text: "Gracias, con la foto el tecnico sabra que repuestos llevar. Te confirmamos el avance.",
    media_url: null,
    created_at: "2026-08-18T09:35:00-04:00",
  },
  {
    id: 9007,
    conversation_id: 103,
    direction: "outbound",
    msg_type: "text",
    text: "Hola Valentina, ya revisamos tu boleta y el cargo era de otra emision. Te enviamos la correccion por correo.",
    media_url: null,
    created_at: "2026-08-20T09:10:00-04:00",
  },
];
