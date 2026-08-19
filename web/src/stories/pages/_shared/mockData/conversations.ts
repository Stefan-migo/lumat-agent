import type { Conversation, Message } from "../../../../types";

/** Conversation + Message mocks matching `app/panel/api/serializers.py`
 *  to_conversation_dict()/to_message_dict() (snake_case, ISO strings,
 *  nullable timestamps). Customer id 1 references `clients.ts`
 *  ("Marcela Fuentes", +56971234501) for ficha + thread rendering
 *  consistency (R-PRD-PG-3). Covers Conversation state values used by the
 *  thread page (open/closed/human/bot) and MessageDirection in/out. */
export const conversations: Conversation[] = [
  {
    id: 101,
    customer_id: 1,
    wa_phone: "+56971234501",
    state: "open",
    summary: "Fuga de agua en cocina — derivada a tecnico",
    last_message_at: "2026-08-18T18:42:00-04:00",
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
    last_message_at: "2026-08-18T16:05:00-04:00",
    created_at: "2026-08-17T08:30:00-04:00",
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
];
