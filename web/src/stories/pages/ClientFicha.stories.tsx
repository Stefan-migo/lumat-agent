import type { Meta, StoryObj } from "@storybook/react";
import { Badge } from "../../components/primitives/Badge";
import { Button } from "../../components/primitives/Button";
import { Card } from "../../components/primitives/Card";
import { Select } from "../../components/primitives/Select";
import { Textarea } from "../../components/primitives/Textarea";
import type { Column } from "./_shared/DataTable";
import { DataTable } from "./_shared/DataTable";
import { PageHeader } from "./_shared/PageHeader";
import { FlashMessage } from "./_shared/FlashMessage";
import { clients } from "./_shared/mockData/clients";
import { conversations } from "./_shared/mockData/conversations";
import { customerStateTone } from "./_shared/toneMaps";
import type { CustomerState } from "../../types";

const customer = clients[0];
const customerStates: CustomerState[] = ["nuevo", "activo", "inactivo", "bloqueado"];

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
  { key: "state", header: "Estado", render: (c) => c.state },
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
    render: (c) => <Badge tone={customerStateTone(c.status)}>{c.status}</Badge>,
  },
  { key: "summary", header: "Resumen", render: (c) => c.summary ?? "—" },
];

const messageColumns: Column<(typeof historyMessages)[number]>[] = [
  { key: "id", header: "#", render: (m) => `#${m.id}` },
  { key: "direction", header: "Dirección", render: (m) => m.direction },
  { key: "msg_type", header: "Tipo", render: (m) => m.msg_type },
  { key: "text", header: "Mensaje", render: (m) => `${m.text}${m.media_url ? " 📎" : ""}` },
  { key: "created", header: "Fecha", render: (m) => m.created_at?.slice(0, 10) ?? "—" },
];

/** Client ficha body (customer card + state form + notes + history).
 *  Exported for tests; hidden from the addons panel. */
export function ClientFichaView() {
  return (
    <div>
      <div style={{ display: "grid", gap: "var(--space-4)" }}>
        <Card>
          <PageHeader title={`Ficha: ${customer.name ?? customer.phone_e164 ?? "—"}`} />
          <div>
            <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
              {customer.phone_e164 ?? "—"}
            </p>
            <div style={{ marginTop: "var(--space-2)" }}>
              <Badge tone={customerStateTone(customer.state)}>{customer.state}</Badge>
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

        <Card title="Estado del cliente">
          <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "flex-end" }}>
            <Select
              label="Estado"
              aria-label="Cambiar estado"
              options={customerStates.map((s) => ({ value: s, label: s }))}
              defaultValue={customer.state}
            />
            <Button variant="secondary">Cambiar estado</Button>
          </div>
        </Card>

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
      </div>
    </div>
  );
}

const meta = {
  title: "pages/ClientFicha",
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          'Panel client ficha: customer card + state form + notes + histories (R-PRD-PG-6, R-PRD-PG-7).\n\n' +
          "**When to use** — the per-customer detail view reached from the clientes list.\n" +
          "**Source** — page-first Storybook mock; production wiring untouched.",
      },
    },
  },
  excludeStories: ["ClientFichaView"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => <ClientFichaView />,
};
