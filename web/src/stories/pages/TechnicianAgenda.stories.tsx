import type { Meta, StoryObj } from "@storybook/react";
import type { AsyncDataState } from "../../hooks/useAsyncData";
import type { TechnicianAppointment } from "../../types";
import { TechnicianShell } from "../../components/domain/TechnicianShell";
import { TechnicianAgenda } from "../../components/pages/TechnicianAgenda";
import { agendaData, agendaLong, agendaNow, agendaWithoutCustomer } from "./_shared/mockData/technicianAgenda";

// The tecnico session: TechnicianShell is its own shell (one page, phone-first),
// so this story opts out of the default PanelShell decorator.
const tecnico = { id: 4, username: "tec-agenda", role: "tecnico" as const };

/** Superficie del rol técnico tal como la ve la sesión: el shell propio
 *  envolviendo la agenda. Exportada para tests; oculta del panel de addons. */
export function TechnicianSurfaceView({ state = "ready", data = agendaData }: { state?: AsyncDataState; data?: TechnicianAppointment[] | null }) {
  return (
    <TechnicianShell user={tecnico} onLogout={() => {}}>
      <TechnicianAgenda data={data} state={state} now={agendaNow} />
    </TechnicianShell>
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
          "Agenda del rol técnico: shell propio, título único y una lista que se lee como agenda.\n\n" +
          "**Uso** — la ruta privada del técnico. El endpoint devuelve pasado, hoy y futuro en una sola lista cronológica, así que la superficie corta en hoy y agrupa por el día local de cada visita; el horario encabeza cada tarjeta.\n" +
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
