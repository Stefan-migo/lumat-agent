import type { Meta, StoryObj } from "@storybook/react";
import { ConversationThread, NoReplyNote } from "../../components/pages/ConversationThread";
import { PageFrame } from "./_shared/PageFrame";
import { conversations, messages } from "./_shared/mockData/conversations";
import { clients } from "./_shared/mockData/clients";

const conversation = conversations[0];
const customerName = (id: number) => clients.find((client) => client.id === id)?.name ?? "—";
const interactiveConversation = {
  ...conversation,
  customer: { id: conversation.customer_id, name: customerName(conversation.customer_id), phone_e164: conversation.wa_phone },
  case: { id: 301, service: "Fuga de agua", priority: "high", status: "open", emergency: true, summary: "Urgencia activa", acknowledged_at: null, closed_at: null },
  case_id: 301,
  emergency: true,
  acknowledged_at: null,
};
export type ConversationThreadState = "ready" | "loading" | "empty";
export function ConversationThreadView({ state = "ready" }: { state?: ConversationThreadState }) {
  return <ConversationThread data={{ conversation, messages: state === "empty" ? [] : messages }} state={state === "loading" ? "loading" : "ready"} customerName={customerName} />;
}
export function InteractiveConversationThreadView() {
  return <ConversationThread data={{ conversation: interactiveConversation, messages }} state="ready" customerName={customerName} interactive />;
}
export function ConversationThreadBubbles() {
  return <PageFrame title={`# ${conversation.id}`} meta={customerName(conversation.customer_id)}>
    <div style={{ display: "grid", gap: "var(--space-2)" }}>
      {messages.map((message) => <div key={message.id} data-bubble aria-label={message.direction}>{message.text ?? "—"}{message.media_url ? " 📎" : null}</div>)}
    </div>
    <NoReplyNote />
  </PageFrame>;
}
export { NoReplyNote };

const meta = { title: "pages/ConversationThread", parameters: { layout: "fullscreen" }, excludeStories: ["ConversationThreadView", "InteractiveConversationThreadView", "ConversationThreadBubbles", "NoReplyNote"] } satisfies Meta;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = { render: () => <ConversationThreadView /> };
export const Interactive: Story = { render: () => <InteractiveConversationThreadView /> };
export const Loading: Story = { render: () => <ConversationThreadView state="loading" /> };
export const Empty: Story = { render: () => <ConversationThreadView state="empty" /> };
export const BubbleVariant: Story = { render: () => <ConversationThreadBubbles /> };
