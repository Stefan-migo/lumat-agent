import type { Meta, StoryObj } from "@storybook/react";
import type { Column } from "./_shared/DataTable";
import { DataTable } from "./_shared/DataTable";
import { StatCard } from "./_shared/StatCard";
import { PageHeader } from "./_shared/PageHeader";
import { kpis } from "./_shared/mockData/dashboard";

/** Dashboard body (3 KPI cards + Motivos table + window caption).
 *  Exported so tests can render it directly; hidden from the addons panel. */
export function DashboardOverview() {
  const motivosColumns: Column<[string, number]>[] = [
    { key: "service", header: "Motivo", render: ([service]) => service },
    { key: "count", header: "Cantidad", align: "right", render: ([, count]) => count },
  ];

  return (
    <div>
      <PageHeader
        title="Dashboard"
        meta={`KPI window: last ${kpis.window_days} days (${kpis.window_start})`}
      />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "var(--space-3)", marginBottom: "var(--space-4)" }}>
        <StatCard label="Contactos" value={kpis.contacts} />
        <StatCard label="Derivados" value={kpis.derived} />
        <StatCard label="Solicitudes de visita" value={kpis.visit_requests} />
      </div>
      <DataTable columns={motivosColumns} rows={kpis.motivos} rowKey={([service]) => service} />
    </div>
  );
}

const meta = {
  title: "pages/Dashboard",
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          'Panel dashboard: KPI cards, Motivos breakdown table and the KPI window caption (R-PRD-PG-6).\n\n' +
          "**When to use** — the authenticated panel home.\n" +
          "**Source** — page-first Storybook mock; production wiring untouched.",
      },
    },
  },
  excludeStories: ["DashboardOverview"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Overview: Story = {
  render: () => <DashboardOverview />,
};
