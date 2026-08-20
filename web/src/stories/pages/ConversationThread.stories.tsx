import type { Meta, StoryObj } from "@storybook/react";
import type { Column } from "./_shared/DataTable";
import { DataTable } from "./_shared/DataTable";
import { EmptyState } from "./_shared/EmptyState";
import { PageFrame } from "./_shared/PageFrame";
import { StateMessage } from "./_shared/StateMessage";
import { conversations, messages } from "./_shared/mockData/conversations";
import { clients } from "./_shared/mockData/clients";
import { conversationLabel, directionLabel } from "./_shared/toneMaps";
import type { Message } from "../../types";

const conv = conversations[0];
const customer = clients.find((c) => c.id === conv.customer_id);

const messageColumns: Column<Message>[] = [
  { key: "when", header: "Cuándo", render: (m) => m.created_at?.slice(0, 10) ?? "—" },
  {
    key: "direction",
    header: "Dirección",
    // Approved Spanish label, never the raw inbound/outbound (DS-UI-LABELS).
    render: (m) => directionLabel(m.direction),
  },
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

/** No-reply notice announced as a status region (DS-UI-STATES), never a raw ⚠
 *  glyph alone. Shared by the table and bubble variants. */
function NoReplyNote() {
  return (
    <StateMessage
      tone="info"
      role="status"
      title="Canal automático"
      detail="Este es un canal automático — no respondas a este mensaje (HH-5)."
    />
  );
}

export type ConversationThreadState = "ready" | "loading" | "empty";

/** Conversation thread body (header + read-only message table + no-reply note)
 *  onto the shared frame, with the workflow state matrix (loading/empty).
 *  Exported for tests; hidden from the addons panel. */
export function ConversationThreadView({ state = "ready" }: { state?: ConversationThreadState }) {
  return (
    <PageFrame
      title={`# ${conv.id}`}
      meta={
        <span>
          {conversationLabel(conv.state)} · {conv.created_at?.slice(0, 10) ?? "—"}
          {customer?.name ? ` · ${customer.name}` : ""}
          {conv.summary ? ` · ${conv.summary}` : ""}
        </span>
      }
      state={
        state === "loading" ? (
          <StateMessage tone="info" role="status" spinner title="Cargando conversación" detail="Reuniendo los mensajes del hilo." />
        ) : null
      }
    >
      {state === "loading" ? null : state === "empty" ? (
        <EmptyState title="No hay registros" description="Esta conversación no tiene mensajes para mostrar." />
      ) : (
        <>
          <DataTable columns={messageColumns} rows={messages} rowKey={(m) => String(m.id)} />
          <NoReplyNote />
        </>
      )}
    </PageFrame>
  );
}

/** Conversation thread bubble variant — visual, secondary to the flat table. */
export function ConversationThreadBubbles() {
  return (
    <PageFrame
      title={`# ${conv.id}`}
      meta={`${conversationLabel(conv.state)} · ${conv.created_at?.slice(0, 10) ?? "—"}`}
    >
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
      <NoReplyNote />
    </PageFrame>
  );
}

const meta = {
  title: "pages/ConversationThread",
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          'Hilo de conversación del panel: marco compartido, meta con estado en etiqueta aprobada, tabla de mensajes de solo lectura, dirección con etiqueta aprobada y aviso de canal automático como StateMessage (DS-UI-LABELS/FRAME/STATES).\n\n' +
          "**Uso** — el hilo por conversación que se abre desde el listado.\n" +
          "**Estados** — listo, carga y vacío.\n" +
          "**Fuente** — mock page-first con la forma del serializer productivo; el wiring de producción no cambia.",
      },
    },
  },
  excludeStories: ["ConversationThreadView", "ConversationThreadBubbles", "NoReplyNote"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => <ConversationThreadView />,
};

export const Loading: Story = {
  render: () => <ConversationThreadView state="loading" />,
};

export const Empty: Story = {
  render: () => <ConversationThreadView state="empty" />,
};

export const BubbleVariant: Story = {
  render: () => <ConversationThreadBubbles />,
};
