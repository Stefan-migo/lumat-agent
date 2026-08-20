import type { Meta, StoryObj } from "@storybook/react";
import { PageFrame } from "./_shared/PageFrame";
import { Textarea } from "../../components/primitives/Textarea";
import { Button } from "../../components/primitives/Button";
import { Avatar } from "../../components/primitives/Avatar";
import { agentChatMessages, agentStatus, type AgentChatRole } from "./_shared/mockData/chat";

/** Friendly label + avatar initials per chat role (R-PRD-PG-12/D2). Distinct
 *  names so the per-message Avatar initials differ between admin and agent.
 *  Spanish, approved (DS-UI-COPY); the admin initials stay "A". */
const roleLabel: Record<AgentChatRole, string> = {
  admin: "Administrador",
  agent: "Agente Lumat",
};

/** Suggestion chips (R-PRD-PG-11) rendered as Buttons from the panel tokens.
 *  Mock-only: selection is a no-op here (production wiring untouched). */
export function SuggestionChips({ chips }: { chips: string[] }) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
      {chips.map((c) => (
        <Button key={c} variant="secondary" onClick={() => {}}>
          {c}
        </Button>
      ))}
    </div>
  );
}

/** Agent status bar (design D7; R-PRD-PG-11): idle shows a plain caption,
 *  processing shows the reusable `.spinner` + thinking copy. Copy is Spanish
 *  from the `agentStatus` map (DS-UI-COPY); the data shape is preserved. */
export function AgentStatusBar({ status }: { status: "idle" | "processing" }) {
  if (status === "processing") {
    return (
      <div
        className="spinner"
        role="status"
        style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}
      >
        <span className="spinner__indicator" aria-hidden="true" />
        <span>{agentStatus.processing}</span>
      </div>
    );
  }
  return (
    <div style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
      {agentStatus.idle}
    </div>
  );
}

/** Chat-with-agent page (design D2/D7; R-PRD-PG-11): shared frame, bubble list with
 *  per-message Avatars, AgentStatusBar, suggestion chips and a Textarea+Button
 *  composer. `status` drives the idle/processing indicator and the composer's
 *  disabled state the way the AgentThinking variant exercises it. */
export function ChatWithAgentView({ status }: { status: "idle" | "processing" }) {
  const composerEnabled = status === "idle";
  return (
    <PageFrame
      title="Asistente Lumat"
      meta="Chat con el agente virtual — responde en tiempo real."
    >
      <AgentStatusBar status={status} />
      <div style={{ display: "grid", gap: "var(--space-2)", marginTop: "var(--space-3)" }}>
        {agentChatMessages.map((m) => (
          <div
            key={m.id}
            style={{
              display: "flex",
              justifyContent: m.role === "agent" ? "flex-start" : "flex-end",
            }}
          >
            <div
              data-bubble
              aria-label={`Mensaje de ${
                m.role === "admin" ? "administrador" : "agente"
              }`}
              style={{
                display: "flex",
                alignItems: "flex-start",
                maxWidth: "70%",
                gap: "var(--space-2)",
              }}
            >
              <Avatar name={roleLabel[m.role]} />
              <div
                style={{
                  padding: "var(--space-2) var(--space-3)",
                  border: m.role === "agent" ? "1px solid var(--border)" : "1px solid var(--primary-800)",
                  borderRadius: "var(--radius-md)",
                  background: m.role === "agent" ? "var(--surface)" : "var(--primary-800)",
                  color: m.role === "agent" ? "var(--text)" : "var(--surface)",
                  fontSize: "var(--text-md)",
                }}
              >
                {m.text}
              </div>
            </div>
          </div>
        ))}
      </div>
      <div style={{ marginTop: "var(--space-4)", display: "grid", gap: "var(--space-3)" }}>
        <SuggestionChips
          chips={[
            "Agendar visita técnica",
            "Revisar mi boleta",
            "Cómo abro un reclamo",
          ]}
        />
        <div style={{ display: "grid", gap: "var(--space-2)" }}>
          <Textarea
            label="Escribe un mensaje"
            disabled={!composerEnabled}
            placeholder="Escribe tu mensaje al asistente..."
          />
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
            <Button disabled={!composerEnabled}>Enviar</Button>
            {!composerEnabled ? (
              <span style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
                Esperando respuesta del asistente...
              </span>
            ) : null}
          </div>
        </div>
      </div>
    </PageFrame>
  );
}

const meta = {
  title: "pages/ChatWithAgent",
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          'Chat con el asistente virtual (design D2/D7; R-PRD-PG-11): encabezado, lista de mensajes con avatares por mensaje, una barra de estado del asistente (en espera / pensando), chips de sugerencia y un diseñador con Textarea + Button.\n\n' +
          "**Cuándo usar** — la vista de panel H4 con el asistente virtual autenticado.\n" +
          "**Fuente** — mock de Storybook basado en la página; el cableado de producción no se toca.",
      },
    },
  },
  excludeStories: ["ChatWithAgentView", "SuggestionChips", "AgentStatusBar"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => <ChatWithAgentView status="idle" />,
};

export const AgentThinking: Story = {
  render: () => <ChatWithAgentView status="processing" />,
};
