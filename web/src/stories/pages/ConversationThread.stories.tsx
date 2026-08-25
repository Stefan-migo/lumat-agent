import type { Meta, StoryObj } from "@storybook/react";
import { ConversationThread, NoReplyNote } from "../../components/pages/ConversationThread";
import { PageFrame } from "./_shared/PageFrame";
import { conversations, messages } from "./_shared/mockData/conversations";
import { clients } from "./_shared/mockData/clients";

const conversation = conversations[0];
const customerName = (id: number) => clients.find((client) => client.id === id)?.name ?? "—";
export type ConversationThreadState = "ready" | "loading" | "empty";
export function ConversationThreadView({ state = "ready" }: { state?: ConversationThreadState }) {
  return <ConversationThread data={{ conversation, messages: state === "empty" ? [] : messages }} state={state === "loading" ? "loading" : "ready"} customerName={customerName} />;
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

const meta = { title: "pages/ConversationThread", parameters: { layout: "fullscreen" }, excludeStories: ["ConversationThreadView", "ConversationThreadBubbles", "NoReplyNote"] } satisfies Meta;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = { render: () => <ConversationThreadView /> };
export const Loading: Story = { render: () => <ConversationThreadView state="loading" /> };
export const Empty: Story = { render: () => <ConversationThreadView state="empty" /> };
export const BubbleVariant: Story = { render: () => <ConversationThreadBubbles /> };
