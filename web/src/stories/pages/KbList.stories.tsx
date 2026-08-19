import type { Meta, StoryObj } from "@storybook/react";
import { Button } from "../../components/primitives/Button";
import { Card } from "../../components/primitives/Card";
import { Input } from "../../components/primitives/Input";
import { Select } from "../../components/primitives/Select";
import { Textarea } from "../../components/primitives/Textarea";
import type { Column } from "./_shared/DataTable";
import { DataTable } from "./_shared/DataTable";
import { PageHeader } from "./_shared/PageHeader";
import { EmptyState } from "./_shared/EmptyState";
import { docs } from "./_shared/mockData/kb";
import type { Doc } from "../../types";

const columns: Column<Doc>[] = [
  { key: "id", header: "#", render: (d) => `#${d.id}` },
  { key: "title", header: "Title", render: (d) => d.title },
  { key: "format", header: "Format", render: (d) => d.format },
  {
    key: "version",
    header: "Version",
    render: (d) => `${d.version} (active: ${d.active_version})`,
  },
  { key: "active", header: "Active", render: (d) => (d.active ? "yes" : "no") },
  {
    key: "provider_model",
    header: "Provider / Model",
    render: (d) => (d.provider && d.model ? `${d.provider} / ${d.model}` : "—"),
  },
  {
    key: "cost",
    header: "Cost (USD)",
    render: (d) => (d.cost_meta !== null ? `$${d.cost_meta.toFixed(6)}` : "—"),
  },
];

/** Per-doc actions cell: native <details> Edit accordion + Disable / Restore
 *  (T5.2, KB-4). Story-local display, non-wired. */
function DocActions({ d }: { d: Doc }) {
  return (
    <div style={{ display: "grid", gap: "var(--space-2)" }}>
      <details>
        <summary style={{ cursor: "pointer" }}>Edit</summary>
        <div style={{ marginTop: "var(--space-2)", display: "grid", gap: "var(--space-2)" }}>
          <Input label="Title" defaultValue={d.title} />
          <Textarea label="Content" rows={3} defaultValue={`Contenido de ${d.title}…`} />
          <Button variant="secondary">Save (new version)</Button>
        </div>
      </details>
      {d.active ? (
        <Button variant="secondary">Disable</Button>
      ) : (
        <span style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>disabled</span>
      )}
      {d.version > 1 ? (
        <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "flex-end" }}>
          <Select
            label="Restore"
            aria-label={`Restore doc ${d.id}`}
            defaultValue={String(d.active_version)}
            options={Array.from({ length: d.version }, (_, i) => ({
              value: String(i + 1),
              label: `v${i + 1}`,
            }))}
            size="sm"
          />
          <Button variant="secondary">Restore</Button>
        </div>
      ) : null}
    </div>
  );
}

/** KB list body (add-document card + docs table with edit/disable/restore).
 *  Exported for tests; hidden from the addons panel. */
export function KbListView() {
  return (
    <div style={{ display: "grid", gap: "var(--space-4)" }}>
      <PageHeader title="Knowledge Base" meta={`${docs.length} documentos`} />
      <Card title="Add document">
        <div style={{ display: "flex", gap: "var(--space-3)", alignItems: "flex-end" }}>
          <Input label="Title" placeholder="Título del documento" />
          <Input label="File (pdf / md / txt / csv)" type="file" />
          <Button>Add</Button>
        </div>
      </Card>
      <DataTable
        columns={columns}
        rows={docs}
        rowKey={(d) => String(d.id)}
        actions={(d) => <DocActions d={d} />}
      />
    </div>
  );
}

/** KB list empty state. Exported for tests. */
export function KbListEmpty() {
  return (
    <div>
      <PageHeader title="Knowledge Base" />
      <EmptyState title="No documents yet" description="Sube el primer documento para empezar." />
    </div>
  );
}

const meta = {
  title: "pages/KbList",
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          'Panel knowledge base list: add-document card + docs table with edit/disable/restore (T5.2; R-PRD-PG-6).\n\n' +
          "**When to use** — the authenticated KB manager.\n" +
          "**Source** — page-first Storybook mock; production wiring untouched.",
      },
    },
  },
  excludeStories: ["KbListView", "KbListEmpty"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => <KbListView />,
};

export const Empty: Story = {
  render: () => <KbListEmpty />,
};
