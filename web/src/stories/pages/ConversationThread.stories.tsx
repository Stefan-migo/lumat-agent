import type { Meta, StoryObj } from "@storybook/react";
import type { Column } from "./_shared/DataTable";
import { DataTable } from "./_shared/DataTable";
import { PageHeader } from "./_shared/PageHeader";
import { conversations, messages } from "./_shared/mockData/conversations";
import { clients } from "./_shared/mockData/clients";
import type { Message } from "../../types";

const conv = conversations[0];
const customer = clients.find((c) => c.id === conv.customer_id);

const messageColumns: Column<Message>[] = [
  { key: "when", header: "Cuándo", render: (m) => m.created_at?.slice(0, 10) ?? "—" },
  { key: "direction", header: "Dirección", render: (m) => m.direction },
  { key: "type", header: "Tipo", render: (m) => m.msg_type },
  {
    key: "content",
    header: "Contenido",
    render: (m) => (
      <>
        {m.text ?? "—"}
        {m.media_url ? " 📎" : null}
      </>
    ),
  },
  { key: "attachment", header: "Adjunto", render: (m) => (m.media_url ? "📎" : "—") },
];

/** Conversation thread body (header + read-only message table + no-reply note).
 *  Exported for tests; hidden from the addons panel. */
export function ConversationThreadView() {
  return (
    <div>
      <PageHeader
        title={`# ${conv.id}`}
        meta={
          <span>
            {conv.state} · {conv.created_at?.slice(0, 10) ?? "—"}
            {customer?.name ? ` · ${customer.name}` : ""}
            {conv.summary ? ` · ${conv.summary}` : ""}
          </span>
        }
      />
      <DataTable columns={messageColumns} rows={messages} rowKey={(m) => String(m.id)} />
      <p
        style={{
          marginTop: "var(--space-4)",
          color: "var(--text-muted)",
          fontSize: "var(--text-sm)",
        }}
      >
        ⚠️ Este es un canal automático — no respondas a este mensaje (HH-5).
      </p>
    </div>
  );
}

/** Conversation thread bubble variant — visual, secondary to the flat table. */
export function ConversationThreadBubbles() {
  return (
    <div>
      <PageHeader
        title={`# ${conv.id}`}
        meta={`${conv.state} · ${conv.created_at?.slice(0, 10) ?? "—"}`}
      />
      <div style={{ display: "grid", gap: "var(--space-2)" }}>
        {messages.map((m) => (
          <div
            key={m.id}
            data-bubble
            aria-label={m.direction}
            style={{
              alignSelf: m.direction === "inbound" ? "flex-start" : "flex-end",
              justifySelf: m.direction === "inbound" ? "flex-start" : "flex-end",
              maxWidth: "70%",
              padding: "var(--space-2) var(--space-3)",
              border: m.direction === "inbound" ? "1px solid var(--border)" : "1px solid var(--primary-800)",
              borderRadius: "var(--radius-md)",
              background: m.direction === "inbound" ? "var(--surface)" : "var(--primary-800)",
              color: m.direction === "inbound" ? "var(--text)" : "var(--surface)",
              fontSize: "var(--text-md)",
            }}
          >
            {m.text ?? "—"}
            {m.media_url ? " 📎" : null}
          </div>
        ))}
      </div>
      <p
        style={{
          marginTop: "var(--space-4)",
          color: "var(--text-muted)",
          fontSize: "var(--text-sm)",
        }}
      >
        ⚠️ Este es un canal automático — no respondas a este mensaje (HH-5).
      </p>
    </div>
  );
}

const meta = {
  title: "pages/ConversationThread",
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          'Panel conversation thread: header + read-only message table + no-reply footer (R-PRD-PG-5, R-PRD-PG-6).\n\n' +
          "**When to use** — the per-conversation thread view reached from the conversations list.\n" +
          "**Source** — page-first Storybook mock; production wiring untouched.",
      },
    },
  },
  excludeStories: ["ConversationThreadView", "ConversationThreadBubbles"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => <ConversationThreadView />,
};

export const BubbleVariant: Story = {
  render: () => <ConversationThreadBubbles />,
};
