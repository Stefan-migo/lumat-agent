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
  captured_data: {
    canal: "WhatsApp",
    enlace_seguimiento: "https://portal.aguas.cl/ordenes/2026/cliente-301/seguimiento-reparacion-urgente-987654321",
  },
};
export type ConversationThreadState = "ready" | "loading" | "empty";
export function ConversationThreadView({ state = "ready" }: { state?: ConversationThreadState }) {
  return <ConversationThread data={{ conversation, messages: state === "empty" ? [] : messages, messages_total: messages.length }} state={state === "loading" ? "loading" : "ready"} customerName={customerName} />;
}
export function InteractiveConversationThreadView() {
  return <ConversationThread data={{ conversation: interactiveConversation, messages, messages_total: messages.length }} state="ready" customerName={customerName} interactive />;
}
export function ConversationThreadWithManyMessagesView() {
  return <ConversationThread data={{ conversation, messages, messages_total: 12 }} state="ready" customerName={customerName} />;
}
// A voice note, as the customer sends it and as Lumat sends it back (panel-polish S3 replaced the
// native player widget). The tone is generated here so the story reports a real duration instead of
// the "--:--" the player shows until the media element reports one.
function silentWav(durationSeconds: number) {
  const sampleRate = 8000;
  const samples = Math.round(sampleRate * durationSeconds);
  const buffer = new ArrayBuffer(44 + samples);
  const view = new DataView(buffer);
  const ascii = (offset: number, text: string) => {
    for (let index = 0; index < text.length; index += 1) view.setUint8(offset + index, text.charCodeAt(index));
  };
  ascii(0, "RIFF");
  view.setUint32(4, 36 + samples, true);
  ascii(8, "WAVE");
  ascii(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate, true);
  view.setUint16(32, 1, true);
  view.setUint16(34, 8, true);
  ascii(36, "data");
  view.setUint32(40, samples, true);
  // 8-bit PCM silence sits at the midpoint of the range.
  new Uint8Array(buffer).fill(128, 44);
  let binary = "";
  for (const byte of new Uint8Array(buffer)) binary += String.fromCharCode(byte);
  return `data:audio/wav;base64,${btoa(binary)}`;
}
export function ConversationThreadAudioView() {
  const voiceNote = {
    ...messages[0],
    id: 900,
    msg_type: "audio" as const,
    text: null,
    caption: null,
    media_url: null,
    media_available: true,
    media_download_url: silentWav(12),
    filename: "nota-de-voz.wav",
  };
  const reply = { ...voiceNote, id: 901, direction: "outbound" as const, delivery_status: "sent" as const };
  return <ConversationThread data={{ conversation: interactiveConversation, messages: [...messages.slice(0, 2), voiceNote, reply], messages_total: 4 }} state="ready" customerName={customerName} interactive />;
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

const meta = { title: "pages/ConversationThread", parameters: { layout: "fullscreen" }, excludeStories: ["ConversationThreadView", "InteractiveConversationThreadView", "ConversationThreadWithManyMessagesView", "ConversationThreadAudioView", "ConversationThreadBubbles", "NoReplyNote"] } satisfies Meta;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = { render: () => <ConversationThreadView /> };
export const Interactive: Story = { render: () => <InteractiveConversationThreadView /> };
export const ManyMessages: Story = { render: () => <ConversationThreadWithManyMessagesView /> };
export const Loading: Story = { render: () => <ConversationThreadView state="loading" /> };
export const Empty: Story = { render: () => <ConversationThreadView state="empty" /> };
export const AudioMessage: Story = { render: () => <ConversationThreadAudioView /> };
export const BubbleVariant: Story = { render: () => <ConversationThreadBubbles /> };
