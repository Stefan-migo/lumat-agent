import type { Meta, StoryObj } from "@storybook/react";
import type { AsyncDataState } from "../../hooks/useAsyncData";
import type { TechnicianAppointment } from "../../types";
import { PanelShell } from "../../components/domain/PanelShell";
import { TechnicianAgenda } from "../../components/pages/TechnicianAgenda";
import { agendaData, agendaLong, agendaNow, agendaWithoutCustomer } from "./_shared/mockData/technicianAgenda";

// The tecnico session runs on the shared PanelShell with a role-scoped
// navigation (task doc S1), so the story wires that real chrome — not a
// technician-only shell — around the agenda.
const tecnico = { id: 4, username: "tec-agenda", role: "tecnico" as const };

/** Superficie del rol técnico tal como la ve la sesión: el shell compartido,
 *  con la navegación filtrada por rol, envolviendo la agenda. Exportada para
 *  tests; oculta del panel de addons. */
export function TechnicianSurfaceView({ state = "ready", data = agendaData }: { state?: AsyncDataState; data?: TechnicianAppointment[] | null }) {
  return (
    <PanelShell user={tecnico} currentView="agenda">
      <TechnicianAgenda data={data} state={state} now={agendaNow} />
    </PanelShell>
  );
}

const meta = {
  title: "pages/TechnicianAgenda",
  parameters: {
    layout: "fullscreen",
    panelShell: false,
    docs: {
      description: {
        component:
          "Agenda del rol técnico montada en el shell compartido, con la navegación filtrada por rol.\n\n" +
          "**Uso** — la ruta de agenda del técnico. El endpoint devuelve pasado, hoy y futuro en una sola lista cronológica, así que la superficie corta en hoy y agrupa por el día local de cada visita; el horario encabeza cada tarjeta.\n" +
          "**Estados** — próximas visitas (con hoy marcado) y visitas anteriores, más carga, vacío y error de recuperación.\n" +
          "**Fuente** — mock con la forma del serializer `to_technician_appointment_dict`; el wiring de producción no cambia.",
      },
    },
  },
  excludeStories: ["TechnicianSurfaceView"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => <TechnicianSurfaceView />,
};

export const LongRoster: Story = {
  render: () => <TechnicianSurfaceView data={agendaLong} />,
};

export const NoCustomerData: Story = {
  render: () => <TechnicianSurfaceView data={agendaWithoutCustomer} />,
};

export const Empty: Story = {
  render: () => <TechnicianSurfaceView data={[]} state="empty" />,
};

export const Loading: Story = {
  render: () => <TechnicianSurfaceView data={null} state="loading" />,
};

export const Error: Story = {
  render: () => <TechnicianSurfaceView data={null} state="error" />,
};
