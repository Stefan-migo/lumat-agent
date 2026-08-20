import type { Meta, StoryObj } from "@storybook/react";
import { Button } from "../../components/primitives/Button";
import { SearchInput } from "../../components/primitives/SearchInput";
import type { Column } from "./_shared/DataTable";
import { DataTable } from "./_shared/DataTable";
import { PageFrame } from "./_shared/PageFrame";
import { EmptyState } from "./_shared/EmptyState";
import { StateMessage } from "./_shared/StateMessage";
import { Badge } from "../../components/primitives/Badge";
import { clients } from "./_shared/mockData/clients";
import { customerStateLabel, customerStateTone } from "./_shared/toneMaps";
import type { Customer } from "../../types";

export type ClientesListState = "ready" | "loading" | "empty" | "stale" | "partial-error" | "fatal-error";

const columns: Column<Customer>[] = [
  {
    key: "name",
    header: "Cliente",
    render: (c) => (
      <a href={`#/clientes/${c.id}`} style={{ color: "var(--primary-700)" }}>
        {c.name ?? "—"}
      </a>
    ),
  },
  { key: "phone", header: "Teléfono", render: (c) => c.phone_e164 ?? "—" },
  {
    key: "state",
    header: "Estado",
    render: (c) => <Badge tone={customerStateTone(c.state)}>{customerStateLabel(c.state)}</Badge>,
  },
  { key: "consent", header: "Consentimiento", render: (c) => (c.consent_status ? "Sí" : "No") },
  { key: "created", header: "Creado", render: (c) => c.created_at?.slice(0, 10) ?? "—" },
];

/** Clientes list body (search + export CSV + table) on the shared frame with
 *  a complete state matrix (loading/empty/stale/partial-error/fatal-error).
 *  Exported for tests. Links use `--primary-700` (DS-UI-LINK AA contrast);
 *  state badges render approved Spanish labels (DS-UI-LABELS); banners pair
 *  a visible label and role, never color alone (DS-UI-STATES). */
export function ClientesListView({ state = "ready" }: { state?: ClientesListState }) {
  return (
    <PageFrame
      title="Clientes"
      meta={`${clients.length} clientes`}
      actions={
        <>
          <SearchInput aria-label="Buscar clientes" onSearch={() => {}} />
          <Button variant="secondary" href="data:text/csv;base64,">Exportar CSV</Button>
        </>
      }
      state={
        state === "loading" ? (
          <StateMessage tone="info" role="status" spinner title="Cargando clientes" detail="Reuniendo el padrón de clientes de la operación." />
        ) : state === "fatal-error" ? (
          <StateMessage tone="danger" role="alert" title="No pudimos cargar los clientes" detail="Reintenta para recuperar el listado." />
        ) : state === "stale" ? (
          <StateMessage tone="warning" role="status" title="Datos posiblemente desactualizados" detail="La última consulta no pudo completarse. Mostramos la información disponible." />
        ) : state === "partial-error" ? (
          <StateMessage tone="danger" role="status" title="No pudimos actualizar parte del listado" detail="El padrón está vigente, pero un origen no respondió. Reintenta en unos minutos." />
        ) : null
      }
    >
      {state === "loading" ? null : (
        <DataTable columns={columns} rows={clients} rowKey={(c) => String(c.id)} />
      )}
    </PageFrame>
  );
}

/** Clientes list empty state. Exported for tests. */
export function ClientesListEmpty() {
  return (
    <PageFrame
      title="Clientes"
      actions={<SearchInput aria-label="Buscar clientes" onSearch={() => {}} />}
    >
      <EmptyState title="No hay registros" description="Ajusta tu búsqueda o agrega nuevos clientes." />
    </PageFrame>
  );
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
