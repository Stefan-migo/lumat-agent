import { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { PageHeader } from "./_shared/PageHeader";
import { FlashMessage } from "./_shared/FlashMessage";
import { Textarea } from "../../components/primitives/Textarea";
import { Button } from "../../components/primitives/Button";
import { conversations, messages } from "./_shared/mockData/conversations";
import { clients } from "./_shared/mockData/clients";
import type { Conversation } from "../../types";

const HOURS_24 = 24 * 60 * 60 * 1000;

/** Pure reply-window helper (R-PRD-PG-10): a conversation is "open" when its
 *  last_message_at falls within the last 24h of `nowMs`. Exported for tests. */
export const isWithinReplyWindow = (lastMessageAt: string | null, nowMs: number): boolean => {
  if (!lastMessageAt) return false;
  return nowMs - Date.parse(lastMessageAt) < HOURS_24;
};

const customerName = (customer_id: number): string =>
  clients.find((c) => c.id === customer_id)?.name ?? "—";

/** State controls (R-PRD-PG-9): take -> human (pauses bot S2), close -> closed,
 *  return to bot. Only the actions relevant to the current state are shown. */
export function InboxThreadStateControls({
  state,
  onStateChange,
}: {
  state: Conversation["state"];
  onStateChange: (next: typeof state) => void;
}) {
  return (
    <div style={{ display: "flex", gap: "var(--space-2)" }}>
      {state === "bot" ? (
        <Button onClick={() => onStateChange("human")}>Tomar</Button>
      ) : null}
      {state === "human" ? (
        <>
          <Button variant="secondary" onClick={() => onStateChange("closed")}>
            Cerrar
          </Button>
          <Button variant="secondary" onClick={() => onStateChange("bot")}>
            Volver a bot
          </Button>
        </>
      ) : null}
      {state === "closed" ? (
        <Button variant="secondary" onClick={() => onStateChange("bot")}>
          Volver a bot
        </Button>
      ) : null}
    </div>
  );
}

/** Composer from Textarea + Button; disabled (closed / bot / outside window)
 *  per R-PRD-PG-10 and design D4. `reason` labels the disabled state. */
export function InboxComposer({
  disabled,
  reason,
  onSend,
}: {
  disabled: boolean;
  reason?: string;
  onSend?: (text: string) => void;
}) {
  return (
    <div style={{ display: "grid", gap: "var(--space-2)", marginTop: "var(--space-4)" }}>
      <Textarea
        label="Escribe tu respuesta"
        disabled={disabled}
        placeholder="Escribí tu respuesta al cliente..."
      />
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
        <Button disabled={disabled}>Enviar</Button>
        {reason ? (
          <span style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>{reason}</span>
        ) : null}
      </div>
    </div>
  );
}

/** Human inbox thread (design D1/D4; R-PRD-PG-9/10): bubbles grid, 24h-window
 *  FlashMessage, state controls and a composer. `nowMs` is injected for
 *  deterministic window tests (defaults to the real clock in the story). */
export function InboxThreadView({
  conversation,
  nowMs = Date.now(),
}: {
  conversation: Conversation;
  nowMs?: number;
}) {
  const [state, setState] = useState(conversation.state as Conversation["state"]);
  const windowOpen = isWithinReplyWindow(conversation.last_message_at, nowMs);
  const threadMsgs = messages.filter((m) => m.conversation_id === conversation.id);

  const composerEnabled = state === "human" && windowOpen;
  const reason =
    !windowOpen || state === "closed"
      ? "Fuera de la ventana de 24 horas"
      : state === "bot"
        ? "Bot pausado"
        : undefined;

  return (
    <div>
      <PageHeader
        title={`# ${conversation.id}`}
        meta={`${state} · ${conversation.created_at?.slice(0, 10) ?? "—"} · ${customerName(conversation.customer_id)}`}
      />
      <div style={{ marginBottom: "var(--space-3)" }}>
        <FlashMessage tone={windowOpen ? "success" : "danger"}>
          {windowOpen
            ? "Ventana de respuesta abierta — menos de 24h desde el último mensaje."
            : "Fuera de la ventana de 24 horas — ya no se pueden enviar respuestas."}
        </FlashMessage>
      </div>
      <div style={{ display: "grid", gap: "var(--space-2)" }}>
        {threadMsgs.map((m) => (
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
          </div>
        ))}
      </div>
      <InboxThreadStateControls state={state} onStateChange={setState} />
      <InboxComposer disabled={!composerEnabled} reason={reason} />
    </div>
  );
}

const meta = {
  title: "pages/InboxThread",
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          'Human inbox thread (design D1/D4; R-PRD-PG-9 / R-PRD-PG-10): message bubbles, a 24h reply-window notice, state controls (Tomar/Cerrar/Volver a bot) and a Textarea+Button composer. H1 ConversationThread stays untouched (R4).\n\n' +
          "**When to use** — the authenticated human-reply inbox thread.\n" +
          "**Source** — page-first Storybook mock; production wiring untouched.",
      },
    },
  },
  excludeStories: ["InboxThreadView", "InboxThreadStateControls", "InboxComposer"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const ComposerEnabled: Story = {
  render: () => <InboxThreadView conversation={conversations.find((c) => c.id === 103)!} />,
};

export const ComposerDisabledClosed: Story = {
  render: () => <InboxThreadView conversation={conversations.find((c) => c.id === 102)!} />,
};

export const ComposerDisabledBot: Story = {
  render: () => <InboxThreadView conversation={conversations.find((c) => c.id === 101)!} />,
};

export const OutsideWindow: Story = {
  render: () => <InboxThreadView conversation={conversations.find((c) => c.id === 105)!} />,
};
