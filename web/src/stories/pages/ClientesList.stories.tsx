import type { Meta, StoryObj } from "@storybook/react";
import { Badge } from "../../components/primitives/Badge";
import { Button } from "../../components/primitives/Button";
import { SearchInput } from "../../components/primitives/SearchInput";
import type { Column } from "./_shared/DataTable";
import { DataTable } from "./_shared/DataTable";
import { PageHeader } from "./_shared/PageHeader";
import { EmptyState } from "./_shared/EmptyState";
import { clients } from "./_shared/mockData/clients";
import { customerStateTone } from "./_shared/toneMaps";
import type { Customer } from "../../types";

const columns: Column<Customer>[] = [
  {
    key: "name",
    header: "Cliente",
    render: (c) => (
      <a href={`#/clientes/${c.id}`} style={{ color: "var(--primary-600)" }}>
        {c.name ?? "—"}
      </a>
    ),
  },
  { key: "phone", header: "Teléfono", render: (c) => c.phone_e164 ?? "—" },
  {
    key: "state",
    header: "Estado",
    render: (c) => <Badge tone={customerStateTone(c.state)}>{c.state}</Badge>,
  },
  { key: "consent", header: "Consentimiento", render: (c) => (c.consent_status ? "Sí" : "No") },
  { key: "created", header: "Creado", render: (c) => c.created_at?.slice(0, 10) ?? "—" },
];

/** Clientes list body (search + export CSV + table). Exported for tests. */
export function ClientesListView() {
  return (
    <div>
      <PageHeader
        title="Clientes"
        meta={`${clients.length} clientes`}
        actions={
          <>
            <SearchInput aria-label="Buscar clientes" onSearch={() => {}} />
            <Button variant="secondary" href="data:text/csv;base64,">Exportar CSV</Button>
          </>
        }
      />
      <DataTable columns={columns} rows={clients} rowKey={(c) => String(c.id)} />
    </div>
  );
}

/** Clientes list empty state. Exported for tests. */
export function ClientesListEmpty() {
  return (
    <div>
      <PageHeader title="Clientes" actions={<SearchInput aria-label="Buscar clientes" onSearch={() => {}} />} />
      <EmptyState title="No customers found" description="Ajusta tu búsqueda o agrega nuevos clientes." />
    </div>
  );
}

/** Clientes list loading state. */
function ClientesListLoading() {
  return (
    <div>
      <PageHeader title="Clientes" />
      <div className="spinner" aria-label="Cargando" role="status" />
    </div>
  );
}

const meta = {
  title: "pages/ClientesList",
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          'Panel clientes list: search + export CSV + customer table with tone-wired state badges (R-PRD-PG-6, R-PRD-PG-7).\n\n' +
          "**When to use** — the authenticated clientele list.\n" +
          "**Source** — page-first Storybook mock; production wiring untouched.",
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

export const Loading: Story = {
  render: () => <ClientesListLoading />,
};

export const Empty: Story = {
  render: () => <ClientesListEmpty />,
};
