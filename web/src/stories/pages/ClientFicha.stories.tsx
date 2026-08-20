import type { Meta, StoryObj } from "@storybook/react";
import { Badge } from "../../components/primitives/Badge";
import { Button } from "../../components/primitives/Button";
import { Card } from "../../components/primitives/Card";
import { Select } from "../../components/primitives/Select";
import { Textarea } from "../../components/primitives/Textarea";
import type { Column } from "./_shared/DataTable";
import { DataTable } from "./_shared/DataTable";
import { PageFrame } from "./_shared/PageFrame";
import { FlashMessage } from "./_shared/FlashMessage";
import { clients } from "./_shared/mockData/clients";
import { conversations } from "./_shared/mockData/conversations";
import {
  caseStatusLabel,
  caseStatusTone,
  conversationLabel,
  customerStateLabel,
  customerStateTone,
  directionLabel,
} from "./_shared/toneMaps";
import { memories } from "./_shared/mockData/memories";
import type { CustomerState } from "../../types";

const customer = clients[0];
const customerStates: CustomerState[] = ["nuevo", "activo", "inactivo", "bloqueado"];

/** CR-7: the living customer_memo (`topic_key='customer_memo'`) surfaced on
 *  the ficha, distinct from staff notes (the notes Card). Empty when none yet. */
const customerMemo = memories.find((m) => m.topic_key === "customer_memo");
const customerMemoText = customerMemo?.contenido ?? "";

/** History tables from the ficha serializer shapes (ClientFichaResponse.history). */
const historyConversations = conversations.map((c) => ({
  id: c.id,
  state: c.state,
  summary: c.summary ?? "—",
  created_at: c.created_at ?? "—",
  closed_at: c.closed_at,
}));

const historyCases = [
  {
    id: 501,
    conversation_id: 101,
    service: "Fuga de agua",
    priority: "alta",
    status: "escalado",
    summary: "Fuga en cocina depto 45 — derivada a tecnico",
  },
  {
    id: 502,
    conversation_id: 102,
    service: "Instalacion termo",
    priority: "media",
    status: "cerrado",
    summary: "Cotizacion aceptada y termo instalado",
  },
];

const historyMessages = [
  {
    id: 9001,
    conversation_id: 101,
    direction: "inbound",
    msg_type: "text",
    text: "Hola, tengo una fuga de agua en la cocina de mi depto.",
    media_url: null,
    created_at: "2026-08-18T09:03:00-04:00",
  },
  {
    id: 9002,
    conversation_id: 101,
    direction: "outbound",
    msg_type: "text",
    text: "Hola Marcela, ya derivamos tu caso a un tecnico.",
    media_url: null,
    created_at: "2026-08-18T09:12:00-04:00",
  },
];

const conversationColumns: Column<(typeof historyConversations)[number]>[] = [
  { key: "id", header: "#", render: (c) => `#${c.id}` },
  // Approved Spanish label, never the raw conversation state (DS-UI-LABELS).
  { key: "state", header: "Estado", render: (c) => conversationLabel(c.state) },
  { key: "summary", header: "Resumen", render: (c) => c.summary },
  { key: "created", header: "Creada", render: (c) => c.created_at.slice(0, 10) },
];

const caseColumns: Column<(typeof historyCases)[number]>[] = [
  { key: "id", header: "#", render: (c) => `#${c.id}` },
  { key: "service", header: "Servicio", render: (c) => c.service },
  { key: "priority", header: "Prioridad", render: (c) => c.priority },
  {
    key: "status",
    header: "Estado",
    // Case statuses use the case tone map, NEVER the customer map (DS-UI-TONEFIX),
    // with the approved Spanish label (DS-UI-LABELS).
    render: (c) => <Badge tone={caseStatusTone(c.status)}>{caseStatusLabel(c.status)}</Badge>,
  },
  { key: "summary", header: "Resumen", render: (c) => c.summary ?? "—" },
];

const messageColumns: Column<(typeof historyMessages)[number]>[] = [
  { key: "id", header: "#", render: (m) => `#${m.id}` },
  { key: "direction", header: "Dirección", render: (m) => directionLabel(m.direction) },
  { key: "msg_type", header: "Tipo", render: (m) => m.msg_type },
  { key: "text", header: "Mensaje", render: (m) => `${m.text}${m.media_url ? " 📎" : ""}` },
  { key: "created", header: "Fecha", render: (m) => m.created_at?.slice(0, 10) ?? "—" },
];

/** Client ficha body (customer card + state form + memo + notes + history).
 *  `isSaving` drives the customer-state form's saving state (DS-UI-STATES).
 *  `memo` overrides the mock memo (used by the NoMemo story for CR-7's empty
 *  state; defaults to the living customer_memo). Exported for tests; hidden
 *  from the addons panel. */
export function ClientFichaView({
  isSaving = false,
  memo = customerMemoText,
}: {
  isSaving?: boolean;
  memo?: string;
}) {
  const identity = (
    <Card>
      <div>
        <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
          {customer.phone_e164 ?? "—"}
        </p>
        <div style={{ marginTop: "var(--space-2)" }}>
          <Badge tone={customerStateTone(customer.state)}>{customerStateLabel(customer.state)}</Badge>
        </div>
        <p style={{ margin: "var(--space-2) 0 0", fontSize: "var(--text-sm)" }}>
          Consentimiento: {customer.consent_status ? "Sí" : "No"}
        </p>
        {customer.email ? (
          <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
            {customer.email}
          </p>
        ) : null}
        {customer.comuna ? (
          <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
            {customer.comuna}
          </p>
        ) : null}
        {customer.address ? (
          <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
            {customer.address}
          </p>
        ) : null}
        <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
          Creado: {customer.created_at?.slice(0, 10) ?? "—"}
        </p>
        <div style={{ marginTop: "var(--space-3)" }}>
          <FlashMessage tone="success">
            Estado actualizado el {customer.consent_at?.slice(0, 10) ?? "—"}
          </FlashMessage>
        </div>
      </div>
    </Card>
  );
      </div>
    </Card>
  );

  const stateControl = (
    <Card title="Estado del cliente">
      <div style={{ display: "grid", gap: "var(--space-2)" }}>
        <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "flex-end" }}>
          <Select
            label="Estado"
            aria-label="Cambiar estado"
            options={customerStates.map((s) => ({ value: s, label: customerStateLabel(s) }))}
            defaultValue={customer.state}
          />
          <Button variant="secondary" disabled={isSaving}>
            Guardar estado
          </Button>
        </div>
        {isSaving ? (
          <p
            role="status"
            style={{ margin: 0, display: "flex", alignItems: "center", gap: "var(--space-2)" }}
          >
            <span className="spinner__indicator" aria-hidden="true" />
            Guardando estado…
          </p>
        ) : null}
      </div>
    </Card>
  );

  const notes = (
    <Card title="Notas">
      <div style={{ display: "grid", gap: "var(--space-3)" }}>
        <div style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
          Marcela Fuentes · ago 18
        </div>
        <Textarea label="Nueva nota" placeholder="Escribe una nota sobre este cliente…" />
        <div>
          <Button>Agregar</Button>
        </div>
      </div>
    </Card>
  );

  const history = (
    <Card title="Historial">
      <h3 style={{ color: "var(--text)", fontSize: "var(--text-lg)" }}>Conversaciones</h3>
      <DataTable
        columns={conversationColumns}
        rows={historyConversations}
        rowKey={(c) => String(c.id)}
      />
      <h3 style={{ color: "var(--text)", fontSize: "var(--text-lg)" }}>Casos</h3>
      <DataTable columns={caseColumns} rows={historyCases} rowKey={(c) => String(c.id)} />
      <h3 style={{ color: "var(--text)", fontSize: "var(--text-lg)" }}>Mensajes</h3>
      <DataTable
        columns={messageColumns}
        rows={historyMessages}
        rowKey={(m) => String(m.id)}
      />
    </Card>
  );

  const memoCard = (
    <Card title="Memo del cliente">
      <div style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
        Acta generada automáticamente al cierre de la conversación (CR-7)
      </div>
      {memo ? (
        <p style={{ margin: "var(--space-2) 0 0" }}>{memo}</p>
      ) : (
        <p style={{ margin: "var(--space-2) 0 0", color: "var(--text-muted)" }}>
          Todavía no hay memo para este cliente.
        </p>
      )}
      <div style={{ marginTop: "var(--space-3)" }}>
        <Badge tone="neutral">customer_memo</Badge>
      </div>
    </Card>
  );

  return (
    <PageFrame title={`Ficha: ${customer.name ?? customer.phone_e164 ?? "—"}`}>
      <div style={{ display: "grid", gap: "var(--space-4)" }}>
        {identity}
        {stateControl}
        {memoCard}
        {notes}
        {history}
      </div>
    </PageFrame>
  );
}

const meta = {
  title: "pages/ClientFicha",
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          'Ficha de cliente del panel: tarjeta de identidad + control de estado + memo + notas + historiales (R-PRD-PG-6, R-PRD-PG-7).\n\n' +
          "**Cuándo usar** — la vista de detalle por cliente a la que se llega desde la lista de clientes.\n" +
          "**Estados** — identidad, consentimiento, control de estado (guardando/validación/deshabilitado), memo del cliente (CR-7), notas e historial.\n" +
          "**Fuente** — mock de Storybook basado en la página; el cableado de producción no se toca.",
      },
    },
  },
  excludeStories: ["ClientFichaView", "NoMemo"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => <ClientFichaView />,
};

export const SavingState: Story = {
  render: () => <ClientFichaView isSaving />,
};

/** CR-7 edge: a customer with no closed conversation producing a memo shows an
 *  empty memo surface, no error. */
export const NoMemo: Story = {
  render: () => <ClientFichaView memo="" />,
};
};
