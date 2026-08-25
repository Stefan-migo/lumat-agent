import type { Meta, StoryObj } from "@storybook/react";
import { ClientesList, type ClientesListState } from "../../components/pages/ClientesList";
import { clients } from "./_shared/mockData/clients";

/** Clientes list body (search + export CSV + table) on the shared frame with
 *  a complete state matrix (loading/empty/stale/partial-error/fatal-error).
 *  Exported for tests. Links use `--primary-700` (DS-UI-LINK AA contrast);
 *  state badges render approved Spanish labels (DS-UI-LABELS); banners pair
 *  a visible label and role, never color alone (DS-UI-STATES). */
export function ClientesListView({ state = "ready" }: { state?: ClientesListState }) {
  return <ClientesList data={state === "empty" ? [] : clients} state={state} />;
}

/** Clientes list empty state. Exported for tests. */
export function ClientesListEmpty() {
  return <ClientesList data={[]} state="empty" />;
}

/** Clientes list loading state. */
function ClientesListLoading() {
  return <ClientesListView state="loading" />;
}

const meta = {
  title: "pages/ClientesList",
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          'Listado de clientes: búsqueda + exportar CSV + tabla de clientes con estados en etiquetas aprobadas de español (DS-UI-LABELS), enlaces accesibles (DS-UI-LINK) y matriz completa de estados (DS-UI-STATES).\n\n' +
          "**Uso** — el padrón autenticado de clientes.\n" +
          "**Estados** — listo, carga, vacío, datos obsoletos, error parcial y error fatal.\n" +
          "**Fuente** — mock page-first con la forma del serializer productivo; el wiring de producción no cambia.",
      },
    },
  },
  excludeStories: ["ClientesListView", "ClientesListEmpty"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => <ClientesListView />,
};

export const Stale: Story = { render: () => <ClientesListView state="stale" /> };
export const PartialError: Story = { render: () => <ClientesListView state="partial-error" /> };
export const FatalError: Story = { render: () => <ClientesListView state="fatal-error" /> };

export const Loading: Story = {
  render: () => <ClientesListLoading />,
};

export const Empty: Story = {
  render: () => <ClientesListEmpty />,
};
