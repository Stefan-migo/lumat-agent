import { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { FlashMessage } from "./_shared/FlashMessage";
import { PageFrame } from "./_shared/PageFrame";
import { StateMessage } from "./_shared/StateMessage";
import { Textarea } from "../../components/primitives/Textarea";
import { Button } from "../../components/primitives/Button";
import { Avatar } from "../../components/primitives/Avatar";
import { conversations, messages } from "./_shared/mockData/conversations";
import { clients } from "./_shared/mockData/clients";
import { conversationLabel } from "./_shared/toneMaps";
import type { Conversation } from "../../types";

const HOURS_24 = 24 * 60 * 60 * 1000;
const STORY_NOW = Date.parse("2026-08-20T12:00:00-04:00");

/** Pure reply-window helper (R-PRD-PG-10): a conversation is "open" when its
 *  last_message_at falls within the last 24h of `nowMs`. Exported for tests. */
export const isWithinReplyWindow = (lastMessageAt: string | null, nowMs: number): boolean => {
  if (!lastMessageAt) return false;
  return nowMs - Date.parse(lastMessageAt) < HOURS_24;
};

const customerName = (customer_id: number): string =>
  clients.find((c) => c.id === customer_id)?.name ?? "—";

const messageAuthor = (direction: "inbound" | "outbound", customer_id: number): string =>
  direction === "inbound" ? customerName(customer_id) : "Lumat";

/** State controls (R-PRD-PG-9): take -> human (pauses bot S2), close -> closed,
 *  return to agent. Only the actions relevant to the current state are shown.
 *  Labels are the approved direct action verbs (DS-UI-COPY): raw `bot` never
 *  appears on the surface. */
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
        <Button onClick={() => onStateChange("human")}>Tomar conversación</Button>
      ) : null}
      {state === "human" ? (
        <>
          <Button variant="secondary" onClick={() => onStateChange("closed")}>
            Cerrar conversación
          </Button>
          <Button variant="secondary" onClick={() => onStateChange("bot")}>
            Devolver al agente
          </Button>
        </>
      ) : null}
      {state === "closed" ? (
        <Button variant="secondary" onClick={() => onStateChange("bot")}>
          Devolver al agente
        </Button>
      ) : null}
    </div>
  );
}

/** Composer from Textarea + Button; disabled (closed / bot / outside window)
 *  per R-PRD-PG-10. `reason` labels the disabled state exactly — for a
 *  bot-state conversation the reason reflects the real transition (the agent
 *  is actively attending), never "Bot pausado" (DS-UI-COPY/DESIGN_SYSTEM). */
export function InboxComposer({
  disabled,
  reason,
}: {
  disabled: boolean;
  reason?: string;
}) {
  return (
    <div style={{ display: "grid", gap: "var(--space-2)", marginTop: "var(--space-4)" }}>
      <Textarea
        label="Escribe tu respuesta"
        disabled={disabled}
        placeholder="Escribe tu respuesta al cliente..."
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

/** Human inbox thread (design D1/D4; R-PRD-PG-9/10): shared frame, message
 *  direction bubbles, 24h-window FlashMessage, state controls and a composer.
 *  Composer availability is explicit: enabled only for a human-owned
 *  conversation inside the reply window; a disabled composer always explains
 *  the exact reason. `nowMs` is injected for deterministic window tests
 *  (defaults to the real clock in the story). */
export function InboxThreadView({
  conversation,
  nowMs = Date.now(),
  state = "ready",
}: {
  conversation: Conversation;
  nowMs?: number;
  state?: "ready" | "stale";
}) {
  const [convState, setState] = useState(conversation.state as Conversation["state"]);
  const windowOpen = isWithinReplyWindow(conversation.last_message_at, nowMs);
  const threadMsgs = messages.filter((m) => m.conversation_id === conversation.id);

  const composerEnabled = convState === "human" && windowOpen;
  const reason =
    !windowOpen || convState === "closed"
      ? "Fuera de la ventana de 24 horas"
      : convState === "bot"
        ? "El agente está atendiendo esta conversación"
        : undefined;

  return (
    <PageFrame
      title={`# ${conversation.id}`}
      meta={`${conversationLabel(convState)} · ${conversation.created_at?.slice(0, 10) ?? "—"} · ${customerName(conversation.customer_id)}`}
      state={
        state === "stale" ? (
          <StateMessage tone="warning" role="status" title="Datos posiblemente desactualizados" detail="La última consulta no pudo completarse. Mostramos la información disponible." />
        ) : null
      }
    >
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
             aria-label={`Mensaje ${m.direction === "inbound" ? "entrante" : "saliente"} de ${messageAuthor(m.direction, conversation.customer_id)}`}
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
            {m.direction === "inbound" ? <Avatar name={messageAuthor(m.direction, conversation.customer_id)} /> : null}
            <span>{m.text ?? "—"}</span>
            {m.direction === "outbound" ? <Avatar name={messageAuthor(m.direction, conversation.customer_id)} /> : null}
          </div>
        ))}
      </div>
      {convState === "human" ? (
        <div className="ai-agent-grammar__handoff" aria-label="Traspaso a atención humana">
          La conversación está en atención humana.
        </div>
      ) : null}
      <InboxThreadStateControls state={convState} onStateChange={setState} />
      <InboxComposer disabled={!composerEnabled} reason={reason} />
    </PageFrame>
  );
}

const meta = {
  title: "pages/InboxThread",
  parameters: {
    layout: "fullscreen",
    viewport: { defaultViewport: "responsive" },
    docs: {
      description: {
        component:
          'Inbox humano: marco compartido, meta con estado en etiqueta aprobada, burbujas de mensaje, aviso de ventana de 24h, controles de estado (Tomar/Cerrar/Devolver al agente) y compositor con disponibilidad explícita (DS-UI-COPY/FRAME/STATES).\n\n' +
          "**Uso** — el hilo de respuestas humanas del inbox.\n" +
          "**Estados** — compo activo (humano dentro de la ventana), fuera de ventana, cerrada o agente atendiendo; además un banner de datos obsoletos.\n" +
          "**Fuente** — mock page-first con la forma del serializer productivo; el wiring de producción no cambia.",
      },
    },
  },
  excludeStories: ["InboxThreadView", "InboxThreadStateControls", "InboxComposer"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const ComposerEnabled: Story = {
  render: () => <InboxThreadView conversation={conversations.find((c) => c.id === 103)!} nowMs={STORY_NOW} />,
};

export const ComposerDisabledClosed: Story = {
  render: () => <InboxThreadView conversation={conversations.find((c) => c.id === 102)!} nowMs={STORY_NOW} />,
};

export const ComposerDisabledBot: Story = {
  render: () => <InboxThreadView conversation={conversations.find((c) => c.id === 101)!} nowMs={STORY_NOW} />,
};

export const OutsideWindow: Story = {
  render: () => <InboxThreadView conversation={conversations.find((c) => c.id === 105)!} nowMs={STORY_NOW} />,
};

export const Stale: Story = {
  render: () => <InboxThreadView conversation={conversations.find((c) => c.id === 103)!} nowMs={STORY_NOW} state="stale" />,
};
