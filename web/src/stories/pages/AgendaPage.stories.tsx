import type { Meta, StoryObj } from "@storybook/react";
import { AgendaPage, type AgendaPageProps } from "../../components/pages/AgendaPage";
import type { AgendaAppointment } from "../../types";

export interface AgendaPageStoryProps extends AgendaPageProps {
  width?: number;
}

const appointment = (overrides: Partial<AgendaAppointment> = {}): AgendaAppointment => ({
  id: 1,
  service: "Mantención de calefón",
  customer_id: 10,
  customer_name: "Camila Soto",
  case_id: 20,
  case_name: "Caso #20",
  technician_id: 30,
  technician_name: "Luis Pérez",
  local_start: "2026-09-05T10:00:00-04:00",
  timezone: "America/Santiago",
  starts_at: "2026-09-05T14:00:00+00:00",
  ends_at: "2026-09-05T15:00:00+00:00",
  duration_minutes: 60,
  status: "booked",
  sync: { status: "failed", error: "Proveedor de calendario no disponible", retry: true },
  ...overrides,
});

const DATA: AgendaAppointment[] = [
  appointment(),
  appointment({
    id: 2,
    service: "Revisión de fuga",
    status: "cancelled",
    sync: { status: "synced", error: null, retry: false },
  }),
  appointment({
    id: 3,
    service: "Instalación de cocina",
    local_start: "2026-09-06T09:00:00-04:00",
    starts_at: "2026-09-06T13:00:00+00:00",
    ends_at: "2026-09-06T14:00:00+00:00",
    status: "completed",
    sync: { status: "synced", error: null, retry: false },
  }),
  appointment({
    id: 4,
    service: "Visita de diagnóstico",
    local_start: "2026-09-07T11:00:00-04:00",
    starts_at: "2026-09-07T15:00:00+00:00",
    ends_at: "2026-09-07T16:00:00+00:00",
    status: "no_show",
    sync: { status: "pending", error: null, retry: true },
  }),
];

export function AgendaPageStory({ width, ...props }: AgendaPageStoryProps) {
  return (
    <div style={{ maxWidth: width ? `${width}px` : undefined, width: "100%" }}>
      <AgendaPage {...props} />
    </div>
  );
}

const meta = {
  title: "pages/AgendaPage",
  component: AgendaPageStory,
  parameters: {
    layout: "fullscreen",
    docs: { description: { component: "Agenda operativa con estados de visitas y sincronización de calendario." } },
  },
  excludeStories: ["AgendaPageStory"],
} satisfies Meta<typeof AgendaPageStory>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Data: Story = { args: { data: DATA, state: "ready", width: 1280 } };
export const Loading: Story = { args: { data: null, state: "loading", width: 1280 } };
export const Empty: Story = { args: { data: [], state: "empty", width: 1280 } };
export const SectionEmpty: Story = { args: { data: [DATA[2]], state: "ready", width: 1280 } };
export const Error: Story = { args: { data: null, state: "error", width: 1280 } };
export const Forbidden: Story = { args: { data: null, state: "denied", width: 1280 } };
export const Stale: Story = { args: { data: DATA, state: "stale", width: 1280 } };
export const CancelConfirmation: Story = {
  args: { data: DATA, state: "ready", width: 1280 },
  play: async ({ canvasElement }) => {
    const button = Array.from(canvasElement.querySelectorAll("button")).find((item) => item.textContent === "Cancelar visita");
    button?.click();
  },
};
export const SyncFailure: Story = {
  args: { data: [DATA[0]], state: "ready", width: 640 },
  parameters: { viewport: { defaultViewport: "bp-sm" } },
};
export const KeyboardActions: Story = { args: { data: DATA, state: "ready", width: 1024 } };
export const Mobile: Story = {
  args: { data: DATA, state: "ready", width: 390 },
  parameters: { viewport: { defaultViewport: "mobile-compact" } },
};
