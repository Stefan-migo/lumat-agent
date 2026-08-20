import { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react";
import type { Column } from "./_shared/DataTable";
import { DataTable } from "./_shared/DataTable";
import { PageHeader } from "./_shared/PageHeader";
import { EmptyState } from "./_shared/EmptyState";
import { Select } from "../../components/primitives/Select";
import { StatusBadge, statusTone } from "../../components/primitives/StatusBadge";
import type { Status } from "../../components/primitives/StatusBadge";
import { conversations } from "./_shared/mockData/conversations";
import { clients } from "./_shared/mockData/clients";
import { users } from "./_shared/mockData/users";
import type { Conversation } from "../../types";

const customerName = (customer_id: number): string =>
  clients.find((c) => c.id === customer_id)?.name ?? "—";

/** Story-local assignee mapping (design D3/R2 — a Conversation has no
 *  `responsible_id` field; the inbox list assigns rows for demo only and
 *  resolves the username from the canonical users mock). */
const ASSIGNEE_BY_CONV: Record<number, number> = {
  101: 7,
  102: 8,
  103: 9,
  104: 7,
  105: 8,
};

export const assigneeForConversation = (c: Conversation): string => {
  const uid = ASSIGNEE_BY_CONV[c.id];
  const u = users.find((x) => x.id === uid);
  return u ? u.username : "—";
};

const FILTER_OPTIONS = [
  { value: "all", label: "Todos" },
  ...Object.keys(statusTone).map((s) => ({ value: s, label: s })),
];

/** Conversation list columns (design D5; R-PRD-PG-6, R-PRD-PG-8). The thread
 *  page (ConversationThread) is the only live view today — GET /conversations
 *  list endpoint does NOT exist on the backend (flagged in apply notes). */
const columns: Column<Conversation>[] = [
  { key: "id", header: "#", render: (c) => `#${c.id}` },
  {
    key: "customer",
    header: "Cliente",
    render: (c) => (
      <span>
        <a href={`#/clientes/${c.customer_id}`} style={{ color: "var(--primary-600)" }}>
          {customerName(c.customer_id)}
        </a>{" "}
        <span style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
          {c.wa_phone ?? "—"}
        </span>
      </span>
    ),
  },
  {
    key: "state",
    header: "Estado",
    render: (c) => <StatusBadge status={c.state as Status} />,
  },
  {
    key: "assignee",
    header: "Asignado",
    render: (c) => assigneeForConversation(c),
  },
  { key: "summary", header: "Resumen", render: (c) => c.summary ?? "—" },
  {
    key: "last_message",
    header: "Último mensaje",
    render: (c) => c.last_message_at?.slice(0, 10) ?? "—",
  },
  { key: "created", header: "Creada", render: (c) => c.created_at?.slice(0, 10) ?? "—" },
];

/** Conversations list body (design D5; R-PRD-PG-8): state badge + assignee
 *  columns, human-row highlight, and a filter-by-state Select. Exported for
 *  tests; hidden from the addons panel. */
export function ConversationsListView({
  initialFilter = "all",
}: {
  initialFilter?: string;
} = {}) {
  const [filter, setFilter] = useState(initialFilter);
  const rows =
    filter === "all"
      ? conversations
      : conversations.filter((c) => c.state === filter);

  return (
    <div>
      <PageHeader title="Conversations" meta={`${rows.length} conversaciones`} />
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          marginBottom: "var(--space-3)",
        }}
      >
        <Select
          label="Filtrar por estado"
          aria-label="Filtrar por estado"
          defaultValue={filter}
          onChange={(e) => setFilter(e.target.value)}
          options={FILTER_OPTIONS}
          size="sm"
        />
      </div>
      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(c) => String(c.id)}
        rowStyle={(c) => (c.state === "human" ? { background: "var(--warning-bg)" } : undefined)}
      />
    </div>
  );
}

/** Conversations list empty state. Exported for tests. */
export function ConversationsListEmpty() {
  return (
    <div>
      <PageHeader title="Conversations" />
      <EmptyState title="No conversations found" description="No existen conversaciones para mostrar." />
    </div>
  );
}

const meta = {
  title: "pages/ConversationsList",
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          'Panel conversations list (design D5): header + conversation table with state badge, assignee, last-message timestamps and a filter-by-state control (T4.3 + T1.6; R-PRD-PG-6 / R-PRD-PG-8).\n\n' +
          "**When to use** — the authenticated conversations list.\n" +
          "**Source** — page-first Storybook mock; production wiring untouched.\n" +
          "**Backend gap** — GET /conversations list endpoint does not exist; only the thread GET is live.",
      },
    },
  },
  excludeStories: ["ConversationsListView", "ConversationsListEmpty"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => <ConversationsListView />,
};

/** Pre-filtered to human-ever-assigned rows (R-PRD-PG-8 scenario 2). */
export const FilterByState: Story = {
  render: () => <ConversationsListView initialFilter="human" />,
};

export const Empty: Story = {
  render: () => <ConversationsListEmpty />,
};
