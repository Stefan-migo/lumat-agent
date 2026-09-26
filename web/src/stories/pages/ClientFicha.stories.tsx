import type { Meta, StoryObj } from "@storybook/react";
import type { ClientFichaResponse } from "../../types";
import { ClientFicha } from "../../components/pages/ClientFicha";
import { clients } from "./_shared/mockData/clients";
import { memories } from "./_shared/mockData/memories";

const customer = clients[0];

const appointment = {
  id: 4,
  service: "Reparación de calefón",
  customer_id: customer.id,
  case_id: 8,
  technician_id: 3,
  local_start: "2026-07-15T09:00:00",
  timezone: "America/Santiago",
  starts_at: "2026-07-15T12:00:00Z",
  ends_at: "2026-07-15T13:00:00Z",
  duration_minutes: 60,
  status: "booked",
  calendar_status: "synced",
  calendar_error: null,
};

const ficha: ClientFichaResponse = {
  customer,
  history: {
    conversations: [{ id: 41, state: "human", summary: "Coordinar visita por calefón", created_at: "2026-07-15T12:00:00Z", closed_at: null }],
    cases: [{ id: 8, conversation_id: 41, customer_id: customer.id, created_at: "2026-07-15T12:00:00Z", service: "Reparación calefón", priority: "alta", status: "abierto", emergency: false, responsible_id: 3, summary: "El equipo no enciende", escalated_at: null, closed_at: null, acknowledged_at: null, ack_by: null, is_open: true }],
    messages: [{ id: 91, conversation_id: 41, direction: "inbound", msg_type: "text", text: "Hola, mi calefón no enciende hace dos días", media_url: null, created_at: "2026-07-15T12:00:00Z" }],
    messages_total: 1,
    appointments: [appointment],
  },
  notes: [{ id: 3, customer_id: customer.id, note: "Confirmar por WhatsApp antes de la visita.", author: "operador", created_at: null }],
  memo: memories.find((memory) => memory.topic_key === "customer_memo")?.contenido ?? "",
  states: ["nuevo", "contactado", "pendiente", "agendado", "en_evaluacion", "finalizado", "cancelado", "postventa"],
  users: [{ id: 3, username: "operador" }],
};

export function UnansweredEmergency() {
  return <ClientFicha data={{ ...ficha, history: { ...ficha.history, cases: [{ ...ficha.history.cases[0], emergency: true }] } }} memories={memories} />;
}

export function ClientFichaView({ memo = ficha.memo }: { memo?: string }) {
  return <ClientFicha data={{ ...ficha, memo }} memories={memories} />;
}

export function NoMemo() {
  return <ClientFichaView memo="" />;
}

/** Calendar-sync failure with a recoverable retry, on the populated ficha. Exported for tests. */
export function ClientFichaCalendarFailure({ onRetryCalendar }: { onRetryCalendar?: (id: number) => void } = {}) {
  return (
    <ClientFicha
      data={{ ...ficha, history: { ...ficha.history, appointments: [{ ...appointment, calendar_status: "error", calendar_error: "Calendar provider unavailable." }] } }}
      memories={memories}
      onRetryCalendar={onRetryCalendar}
    />
  );
}

/** Loading with no payload at all. Exported for tests. */
export function ClientFichaLoading() {
  return <ClientFicha state="loading" />;
}

/** A failed read with the last payload still readable. Exported for tests. */
export function ClientFichaError() {
  return <ClientFicha data={ficha} memories={memories} state="error" />;
}

/** Permission denied. Exported for tests. */
export function ClientFichaDenied() {
  return <ClientFicha data={ficha} memories={memories} state="denied" />;
}

const meta = {
  title: "pages/ClientFicha",
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "Ficha de cliente en dos regiones: rail de resumen (identidad + estado) e historial. " +
          "Los estados de lectura, el fallo de sincronización de calendario y su reintento son parte de la matriz.",
      },
    },
  },
  excludeStories: ["ClientFichaView", "NoMemo", "ClientFichaCalendarFailure", "ClientFichaLoading", "ClientFichaError", "ClientFichaDenied", "UnansweredEmergency"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = { render: () => <ClientFichaView /> };
export const ActiveUnansweredEmergency: Story = { render: () => <UnansweredEmergency /> };
export const NoMemoState: Story = { render: () => <NoMemo /> };
export const CalendarSyncFailure: Story = { render: () => <ClientFichaCalendarFailure /> };
export const Loading: Story = { render: () => <ClientFichaLoading /> };
export const ErrorState: Story = { render: () => <ClientFichaError /> };
export const Denied: Story = { render: () => <ClientFichaDenied /> };
