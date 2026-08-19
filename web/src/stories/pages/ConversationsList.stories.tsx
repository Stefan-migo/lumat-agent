import type { Meta, StoryObj } from "@storybook/react";
import type { Column } from "./_shared/DataTable";
import { DataTable } from "./_shared/DataTable";
import { PageHeader } from "./_shared/PageHeader";
import { EmptyState } from "./_shared/EmptyState";
import { conversations } from "./_shared/mockData/conversations";
import { clients } from "./_shared/mockData/clients";
import type { Conversation } from "../../types";

const customerName = (customer_id: number): string =>
  clients.find((c) => c.id === customer_id)?.name ?? "—";

/** Conversation list columns (design D5; R-PRD-PG-6). The thread page
 *  (ConversationThread) is the only live view today — GET /conversations
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
  { key: "state", header: "Estado", render: (c) => c.state },
  { key: "summary", header: "Resumen", render: (c) => c.summary ?? "—" },
  {
    key: "last_message",
    header: "Último mensaje",
    render: (c) => c.last_message_at?.slice(0, 10) ?? "—",
  },
  { key: "created", header: "Creada", render: (c) => c.created_at?.slice(0, 10) ?? "—" },
];

/** Conversations list body (design D5: built from Customer/Conversation shapes).
 *  Exported for tests; hidden from the addons panel. */
export function ConversationsListView() {
  return (
    <div>
      <PageHeader title="Conversations" meta={`${conversations.length} conversaciones`} />
      <DataTable columns={columns} rows={conversations} rowKey={(c) => String(c.id)} />
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
          'Panel conversations list (design D5): header + conversation table with last-message timestamps (T4.3; R-PRD-PG-6).\n\n' +
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

export const Empty: Story = {
  render: () => <ConversationsListEmpty />,
};
