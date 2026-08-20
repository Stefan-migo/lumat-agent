import { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react";
import type { Column } from "./_shared/DataTable";
import { DataTable } from "./_shared/DataTable";
import { PageFrame } from "./_shared/PageFrame";
import { EmptyState } from "./_shared/EmptyState";
import { StateMessage } from "./_shared/StateMessage";
import { Select } from "../../components/primitives/Select";
import { StatusBadge, statusTone } from "../../components/primitives/StatusBadge";
import type { Status } from "../../components/primitives/StatusBadge";
import { conversations } from "./_shared/mockData/conversations";
import { clients } from "./_shared/mockData/clients";
import { users } from "./_shared/mockData/users";
import { conversationLabel } from "./_shared/toneMaps";
import type { Conversation } from "../../types";

const customerName = (customer_id: number): string =>
  clients.find((c) => c.id === customer_id)?.name ?? "—";

/** Story-local assignee mapping (design D3/R2 — a Conversation has no
 *  `responsible_id` field; the inbox list assigns rows for demo only and
 *  resolves the username from the canonical users mock). */
const ASSIGNEE_BY_CONV: Record<number, number> = {
  101: 7,
  102: 8,
  103: 9,
  104: 7,
  105: 8,
};

export const assigneeForConversation = (c: Conversation): string => {
  const uid = ASSIGNEE_BY_CONV[c.id];
  const u = users.find((x) => x.id === uid);
  return u ? u.username : "—";
};

/** Filter options render the approved Spanish label, never the raw state key
 *  (DS-UI-LABELS holds on the filter select surface too — raw values MUST NOT
 *  appear on non-technical views). */
const FILTER_OPTIONS = [
  { value: "all", label: "Todos" },
  ...Object.keys(statusTone).map((s) => ({ value: s, label: conversationLabel(s) })),
];

/** Conversation list columns (design D5; R-PRD-PG-6, R-PRD-PG-8). The thread
 *  page (ConversationThread) is the only live view today — GET /conversations
 *  list endpoint does NOT exist on the backend (flagged in apply notes). */
const columns: Column<Conversation>[] = [
  { key: "id", header: "#", render: (c) => `#${c.id}` },
  {
    key: "customer",
    header: "Cliente",
    render: (c) => (
      <span>
        <a href={`#/clientes/${c.customer_id}`} style={{ color: "var(--primary-700)" }}>
          {customerName(c.customer_id)}
        </a>{" "}
        <span style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
          {c.wa_phone ?? "—"}
        </span>
      </span>
    ),
  },
  {
    key: "state",
    header: "Estado",
    render: (c) => <StatusBadge status={c.state as Status} />,
  },
  {
    key: "assignee",
    header: "Asignado",
    render: (c) => assigneeForConversation(c),
  },
  { key: "summary", header: "Resumen", render: (c) => c.summary ?? "—" },
  {
    key: "last_message",
    header: "Último mensaje",
    render: (c) => c.last_message_at?.slice(0, 10) ?? "—",
  },
  { key: "created", header: "Creada", render: (c) => c.created_at?.slice(0, 10) ?? "—" },
];

export type ConversationsListState =
  | "ready"
  | "loading"
  | "empty"
  | "stale"
  | "partial-error"
  | "fatal-error";

/** Conversations list body (design D5; R-PRD-PG-8): shared frame shell, state
 *  badge + assignee columns, a filter-by-state Select, and the workflow state
 *  matrix (loading/stale/partial-error/fatal-error) via StateMessage banners
 *  (DS-UI-FRAME/STATES). Human-assigned rows carry a warning leading rail whose
 *  meaning is never color-only — it pairs with the approved "Atención humana"
 *  badge in the Estado column (DS-UI-FRAME). Exported for tests; hidden from
 *  the addons panel. */
export function ConversationsListView({
  initialFilter = "all",
  state = "ready",
}: {
  initialFilter?: string;
  state?: ConversationsListState;
} = {}) {
  const [filter, setFilter] = useState(initialFilter);
  const rows =
    filter === "all"
      ? conversations
      : conversations.filter((c) => c.state === filter);

  return (
    <PageFrame
      title="Conversaciones"
      meta={`${rows.length} conversaciones`}
      state={
        state === "loading" ? (
          <StateMessage tone="info" role="status" spinner title="Cargando conversaciones" detail="Reuniendo las conversaciones disponibles." />
        ) : state === "fatal-error" ? (
          <StateMessage tone="danger" role="alert" title="No pudimos cargar las conversaciones" detail="Reintenta para recuperar el listado." />
        ) : state === "stale" ? (
          <StateMessage tone="warning" role="status" title="Datos posiblemente desactualizados" detail="La última consulta no pudo completarse. Mostramos la información disponible." />
        ) : state === "partial-error" ? (
          <StateMessage tone="danger" role="status" title="No pudimos actualizar parte de las conversaciones" detail="El listado está vigente, pero un origen no respondió. Reintenta en unos minutos." />
        ) : null
      }
    >
      {state === "loading" ? null : (
        <>
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              marginBottom: "var(--space-3)",
            }}
          >
            <Select
              label="Filtrar por estado"
              aria-label="Filtrar por estado"
              defaultValue={filter}
              onChange={(e) => setFilter(e.target.value)}
              options={FILTER_OPTIONS}
              size="sm"
            />
          </div>
          <DataTable
            columns={columns}
            rows={rows}
            rowKey={(c) => String(c.id)}
            rowStyle={(c) =>
              c.state === "human"
                ? { borderLeft: "var(--space-1) solid var(--warning)", background: "var(--warning-bg)" }
                : undefined
            }
          />
        </>
      )}
    </PageFrame>
  );
}

/** Conversations list empty state. Exported for tests. */
export function ConversationsListEmpty() {
  return (
    <PageFrame title="Conversaciones">
      <EmptyState title="No hay registros" description="No existen conversaciones para mostrar." />
    </PageFrame>
  );
}

const meta = {
  title: "pages/ConversationsList",
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          'Listado de conversaciones: título en español, marco compartido y tabla con estado en etiquetas aprobadas (DS-UI-LABELS/FRAME/STATES).\n\n' +
          "**Uso** — las conversaciones del panel.\n" +
          "**Estado** — el asistente responde (Agente atendiendo), requiere atención humana (Atención humana, fila con acento de advertencia) o está cerrada.\n" +
          "**Filtro** — por estado con etiquetas aprobadas, nunca con claves técnicas (bot/human/closed).\n" +
          "**Estados** — listo, carga, vacío, datos obsoletos, error parcial y error fatal.\n" +
          "**Fuente** — mock page-first con la forma del serializer productivo; el wiring de producción no cambia.\n" +
          "**Gap backend** — el endpoint GET /conversations de listado no existe; solo está vivo el thread.",
      },
    },
  },
  excludeStories: ["ConversationsListView", "ConversationsListEmpty"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => <ConversationsListView />,
};

export const Stale: Story = { render: () => <ConversationsListView state="stale" /> };
export const PartialError: Story = { render: () => <ConversationsListView state="partial-error" /> };
export const FatalError: Story = { render: () => <ConversationsListView state="fatal-error" /> };

export const Loading: Story = {
  render: () => <ConversationsListView state="loading" />,
};

/** Pre-filtered to human-ever-assigned rows (R-PRD-PG-8 scenario 2). */
export const FilterByState: Story = {
  render: () => <ConversationsListView initialFilter="human" />,
};

export const Empty: Story = {
  render: () => <ConversationsListEmpty />,
};
