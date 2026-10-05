import type { Meta, StoryObj } from "@storybook/react";
import { AppointmentDetail, type AppointmentDetailProps } from "../../components/pages/AppointmentDetail";
import type { AppointmentDetail as AppointmentDetailData } from "../../types";

const appointment: AppointmentDetailData["appointment"] = {
  id: 41,
  service: "Mantención de calefón",
  customer_id: 12,
  case_id: 27,
  technician_id: 3,
  local_start: "2026-09-28T09:00:00",
  timezone: "America/Santiago",
  starts_at: "2026-09-28T12:00:00Z",
  ends_at: "2026-09-28T13:00:00Z",
  duration_minutes: 60,
  status: "booked",
  history: [{
    id: 1,
    actor: "ana",
    action: "booked",
    from_status: null,
    to_status: "booked",
    details: null,
    created_at: "2026-09-27T12:00:00Z",
  }],
};

const detail = (conversationId: number | null, summary: string | null): AppointmentDetailData => ({
  appointment,
  customer: { id: 12, name: "Marcela Fuentes", address: "Av. Los Robles 123", comuna: "Providencia" },
  case: { id: 27, conversation_id: conversationId },
  conversation_summary: summary,
});

export function AppointmentDetailStory({ width, ...props }: AppointmentDetailProps & { width?: number }) {
  return <div style={{ maxWidth: width ? `${width}px` : undefined, width: "100%" }}><AppointmentDetail {...props} /></div>;
}

const meta = {
  title: "pages/AppointmentDetail",
  component: AppointmentDetailStory,
  parameters: {
    layout: "fullscreen",
    docs: { description: { component: "Detalle de visita, resumen de conversación e historial de cambios." } },
  },
  excludeStories: ["AppointmentDetailStory"],
} satisfies Meta<typeof AppointmentDetailStory>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ConversationSummary: Story = {
  args: { appointmentId: 41, data: detail(88, "La clienta solicita revisar el calefón antes del invierno."), state: "ready", width: 960 },
};
export const ConversationWithoutSummary: Story = {
  args: { appointmentId: 41, data: detail(88, null), state: "ready", width: 960 },
};
export const ManualCase: Story = {
  args: { appointmentId: 41, data: detail(null, null), state: "ready", width: 960 },
};
export const Mobile: Story = {
  args: { appointmentId: 41, data: detail(null, null), state: "ready", width: 390 },
};
export const CloseActions: Story = {
  args: { appointmentId: 41, data: detail(null, null), state: "ready", width: 960 },
};
export const RescheduleDialog: Story = {
  args: { appointmentId: 41, data: detail(null, null), state: "ready", width: 960 },
  play: async ({ canvasElement }) => {
    const button = Array.from(canvasElement.querySelectorAll("button")).find((item) => item.textContent === "Reprogramar");
    button?.click();
  },
};
export const Completed: Story = {
  args: { appointmentId: 41, data: { ...detail(null, null), appointment: { ...appointment, status: "completed" } }, state: "ready", width: 960 },
};
export const Loading: Story = { args: { appointmentId: 41, data: null, state: "loading", width: 960 } };
export const Error: Story = { args: { appointmentId: 41, data: null, state: "error", width: 960 } };
export const Denied: Story = { args: { appointmentId: 41, data: null, state: "denied", width: 960 } };
