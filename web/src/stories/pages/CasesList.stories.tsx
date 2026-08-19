import type { Meta, StoryObj } from "@storybook/react";
import { Badge } from "../../components/primitives/Badge";
import { Button } from "../../components/primitives/Button";
import { Select } from "../../components/primitives/Select";
import type { Column } from "./_shared/DataTable";
import { DataTable } from "./_shared/DataTable";
import { PageHeader } from "./_shared/PageHeader";
import { FlashMessage } from "./_shared/FlashMessage";
import { EmptyState } from "./_shared/EmptyState";
import { casesData, users } from "./_shared/mockData/cases";
import { caseStatusTone } from "./_shared/toneMaps";
import type { Case, UserRef } from "../../types";

const CASE_STATUSES = ["abierto", "en_evaluacion", "escalado", "cerrado"];

const responsibleLabel = (id: number | null, users: UserRef[]): string => {
  const u = users.find((x) => x.id === id);
  return u ? u.username : "—";
};

/** Actions cell: inline status + responsible selects + Update; Acknowledge for
 *  unanswered emergency (T4.2, EM-4). Story-local display, non-wired. */
function CaseActions({ c }: { c: Case }) {
  const emergencyUnanswered = c.emergency && c.ack_by === null;
  return (
    <div
      style={{ display: "grid", gap: "var(--space-2)", alignItems: "end" }}
    >
      <Select
        label="Estado"
        aria-label={`Estado caso ${c.id}`}
        defaultValue={c.status}
        options={CASE_STATUSES.map((s) => ({ value: s, label: s }))}
        size="sm"
      />
      <Select
        label="Responsable"
        aria-label={`Responsable caso ${c.id}`}
        defaultValue={c.responsible_id ? String(c.responsible_id) : ""}
        options={[{ value: "", label: "Sin asignar" }, ...users.map((u) => ({ value: String(u.id), label: u.username }))]}
        size="sm"
      />
      <div style={{ display: "flex", gap: "var(--space-2)" }}>
        <Button variant="secondary">Actualizar</Button>
        {emergencyUnanswered ? (
          <Button variant="secondary">Reconocer</Button>
        ) : null}
      </div>
    </div>
  );
}

const columns: Column<Case>[] = [
  { key: "id", header: "#", render: (c) => `#${c.id}` },
  {
    key: "customer",
    header: "Cliente",
    render: (c) => (
      <a href={`#/clientes/${c.customer.id}`} style={{ color: "var(--primary-600)" }}>
        {c.customer.name ?? "—"}
      </a>
    ),
  },
  { key: "service", header: "Servicio", render: (c) => c.service ?? "—" },
  {
    key: "status",
    header: "Estado",
    render: (c) => <Badge tone={caseStatusTone(c.status)}>{c.status}</Badge>,
  },
  { key: "summary", header: "Resumen", render: (c) => c.summary ?? "—" },
  {
    key: "emergency",
    header: "Emergencia",
    render: (c) =>
      c.emergency ? (
        <span>
          ⚠ {c.ack_by ? `Reconocido por ${c.ack_by}` : "Sin reconocer"}
        </span>
      ) : (
        "—"
      ),
  },
  {
    key: "responsible",
    header: "Responsable",
    render: (c) => responsibleLabel(c.responsible_id, users),
  },
];

/** Cases list body (header + flash + table with inline update/ack).
 *  Exported for tests; hidden from the addons panel. */
export function CasesListView() {
  return (
    <div>
      <PageHeader
        title="Cases (pending / escalated)"
        meta={`${casesData.cases.length} casos abiertos`}
      />
      <div style={{ marginBottom: "var(--space-3)" }}>
        <FlashMessage tone="warning">
          Hay {casesData.cases.filter((c) => c.emergency && c.ack_by === null).length} emergencias sin reconocer.
        </FlashMessage>
      </div>
      <DataTable
        columns={columns}
        rows={casesData.cases}
        rowKey={(c) => String(c.id)}
        actions={(c) => <CaseActions c={c} />}
      />
    </div>
  );
}

/** Cases list empty state. Exported for tests. */
export function CasesListEmpty() {
  return (
    <div>
      <PageHeader title="Cases (pending / escalated)" />
      <EmptyState title="No cases found" description="No existen casos abiertos pendientes o escalados." />
    </div>
  );
}

const meta = {
  title: "pages/CasesList",
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          'Panel cases list: header + flash + case table with inline update/ack actions (T4.2; R-PRD-PG-6).\n\n' +
          "**When to use** — the authenticated cases list (pending/escalated).\n" +
          "**Source** — page-first Storybook mock; production wiring untouched.",
      },
    },
  },
  excludeStories: ["CasesListView", "CasesListEmpty"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => <CasesListView />,
};

export const Empty: Story = {
  render: () => <CasesListEmpty />,
};
