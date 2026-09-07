/** Chat-with-agent mock (design D2 / R3; R-PRD-PG-12). A dedicated H4 system
 *  view on a human↔agent conversation — deliberately NOT the WhatsApp
 *  Conversation/Message model (R3). `role` is the panel user ('admin'/'agent');
 *  `created_at` is an ISO string matching the serializer convention.
 *  `agentStatus` drives the ChatWithAgent idle/processing indicator (D7). */
export type AgentChatRole = "admin" | "agent";

export interface AgentChatMessage {
  id: number;
  role: AgentChatRole;
  text: string;
  created_at: string;
}

export const agentStatus: Record<"idle" | "processing", string> = {
  idle: "Agente en espera",
  processing: "Procesando respuesta",
};

export const agentChatMessages: AgentChatMessage[] = [
  {
    id: 8001,
    role: "agent",
    text: "Hola, soy el asistente de Lumat. ¿En qué puedo ayudarte hoy?",
    created_at: "2026-08-20T13:00:00-04:00",
  },
  {
    id: 8002,
    role: "admin",
    text: "Tengo una fuga de agua en mi depto y necesito agendar un técnico.",
    created_at: "2026-08-20T13:01:00-04:00",
  },
  {
    id: 8003,
    role: "agent",
    text: "Claro, te ayudo con eso. ¿En qué comuna está el departamento y podrías confirmarme tu número de boleta?",
    created_at: "2026-08-20T13:01:40-04:00",
  },
  {
    id: 8004,
    role: "admin",
    text: "Providencia, Av. Providencia 1234 dpto 45. La boleta es la 88231.",
    created_at: "2026-08-20T13:02:15-04:00",
  },
  {
    id: 8005,
    role: "agent",
    text: "Perfecto. Agendé la visita técnica para hoy entre 17:00 y 19:00 hrs. ¿Te sirve?",
    created_at: "2026-08-20T13:02:50-04:00",
  },
  {
    id: 8006,
    role: "admin",
    text: "Sí, perfecto. Gracias.",
    created_at: "2026-08-20T13:03:10-04:00",
  },
];
