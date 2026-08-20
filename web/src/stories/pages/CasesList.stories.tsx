import type { Meta, StoryObj } from "@storybook/react";
import { Badge } from "../../components/primitives/Badge";
import { Button } from "../../components/primitives/Button";
import { Select } from "../../components/primitives/Select";
import type { Column } from "./_shared/DataTable";
import { DataTable } from "./_shared/DataTable";
import { PageFrame } from "./_shared/PageFrame";
import { EmptyState } from "./_shared/EmptyState";
import { StateMessage } from "./_shared/StateMessage";
import { casesData, users } from "./_shared/mockData/cases";
import { caseStatusLabel, caseStatusTone } from "./_shared/toneMaps";
import type { Case, UserRef } from "../../types";

const CASE_STATUSES = ["abierto", "en_evaluacion", "escalado", "cerrado"];

const responsibleLabel = (id: number | null, users: UserRef[]): string => {
  const u = users.find((x) => x.id === id);
  return u ? u.username : "—";
};

/** Actions cell: inline status + responsible selects + Update; Acknowledge for
 *  unanswered emergency (T4.2, EM-4). Story-local display, non-wired. */
function CaseActions({ c }: { c: Case }) {
  const emergencyUnanswered = c.emergency && c.ack_by === null;
  return (
    <div
      style={{ display: "grid", gap: "var(--space-2)", alignItems: "end" }}
    >
      <Select
        label="Estado"
        aria-label={`Estado caso ${c.id}`}
        defaultValue={c.status}
        options={CASE_STATUSES.map((s) => ({ value: s, label: caseStatusLabel(s) }))}
        size="sm"
      />
      <Select
        label="Responsable"
        aria-label={`Responsable caso ${c.id}`}
        defaultValue={c.responsible_id ? String(c.responsible_id) : ""}
        options={[{ value: "", label: "Sin asignar" }, ...users.map((u) => ({ value: String(u.id), label: u.username }))]}
        size="sm"
      />
      <div style={{ display: "flex", gap: "var(--space-2)" }}>
        <Button variant="secondary">Actualizar</Button>
        {emergencyUnanswered ? (
          <Button variant="secondary">Reconocer</Button>
        ) : null}
      </div>
    </div>
  );
}

/** Emergency cell: announces the state via StateMessage (tone + visible label +
 *  role=status), never a raw ⚠ glyph alone (DS-UI-FRAME/STATES). */
function EmergencyCell({ c }: { c: Case }) {
  if (!c.emergency) return <span>—</span>;
  return (
    <StateMessage
      tone={c.ack_by ? "warning" : "danger"}
      role="status"
      title="Emergencia"
      detail={c.ack_by ? `Reconocida por ${c.ack_by}` : "Sin reconocer"}
    />
  );
}

const columns: Column<Case>[] = [
  { key: "id", header: "#", render: (c) => `#${c.id}` },
  {
    key: "customer",
    header: "Cliente",
    render: (c) => (
      <a href={`#/clientes/${c.customer.id}`} style={{ color: "var(--primary-700)" }}>
        {c.customer.name ?? "—"}
      </a>
    ),
  },
  { key: "service", header: "Servicio", render: (c) => c.service ?? "—" },
  {
    key: "status",
    header: "Estado",
    render: (c) => <Badge tone={caseStatusTone(c.status)}>{caseStatusLabel(c.status)}</Badge>,
  },
  { key: "summary", header: "Resumen", render: (c) => c.summary ?? "—" },
  {
    key: "emergency",
    header: "Emergencia",
    render: (c) => <EmergencyCell c={c} />,
  },
  {
    key: "responsible",
    header: "Responsable",
    render: (c) => responsibleLabel(c.responsible_id, users),
  },
];

export type CasesListState = "ready" | "loading" | "empty" | "stale" | "partial-error" | "fatal-error";

/** Cases list body (shared frame + emergency banner via StateMessage + table
 *  with inline update/ack). Exported for tests; hidden from the addons panel.
 *  Statuses render approved Spanish labels (DS-UI-LABELS); the emergency note
 *  and loading banner route through StateMessage (DS-UI-FRAME/STATES). */
export function CasesListView({ state = "ready" }: { state?: CasesListState }) {
  const unanswered = casesData.cases.filter((c) => c.emergency && c.ack_by === null).length;
  return (
    <PageFrame
      title="Casos"
      meta={`${casesData.cases.length} casos abiertos · ${unanswered} emergencias sin reconocer`}
      state={
        state === "loading" ? (
          <StateMessage tone="info" role="status" spinner title="Cargando casos" detail="Reuniendo los casos pendientes y escalados." />
        ) : state === "fatal-error" ? (
          <StateMessage tone="danger" role="alert" title="No pudimos cargar los casos" detail="Reintenta para recuperar el listado." />
        ) : state === "stale" ? (
          <StateMessage tone="warning" role="status" title="Datos posiblemente desactualizados" detail="La última consulta no pudo completarse. Mostramos la información disponible." />
        ) : state === "partial-error" ? (
          <StateMessage tone="danger" role="status" title="No pudimos actualizar parte de los casos" detail="El listado está vigente, pero un origen no respondió. Reintenta en unos minutos." />
        ) : unanswered > 0 ? (
          <StateMessage tone="danger" role="alert" title="Emergencias sin reconocer" detail={`${unanswered} casos requieren atención inmediata.`} />
        ) : null
      }
    >
      {state === "loading" ? null : (
        <DataTable
          columns={columns}
          rows={casesData.cases}
          rowKey={(c) => String(c.id)}
          actions={(c) => <CaseActions c={c} />}
        />
      )}
    </PageFrame>
  );
}

/** Cases list empty state. Exported for tests. */
export function CasesListEmpty() {
  return (
    <PageFrame title="Casos">
      <EmptyState title="No hay registros" description="No existen casos abiertos pendientes o escalados." />
    </PageFrame>
  );
}

const meta = {
  title: "pages/CasesList",
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          'Listado de casos: título en español, banner de emergencias por StateMessage y tabla con estados en etiquetas aprobadas (DS-UI-LABELS/FRAME/STATES).\n\n' +
          "**Uso** — los casos pendientes y escalados.\n" +
          "**Estados** — listo (con banner de emergencias), carga, vacío, datos obsoletos, error parcial y error fatal.\n" +
          "**Fuente** — mock page-first con la forma del serializer productivo; el wiring de producción no cambia.",
      },
    },
  },
  excludeStories: ["CasesListView", "CasesListEmpty", "EmergencyCell"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => <CasesListView />,
};

export const Stale: Story = { render: () => <CasesListView state="stale" /> };
export const PartialError: Story = { render: () => <CasesListView state="partial-error" /> };
export const FatalError: Story = { render: () => <CasesListView state="fatal-error" /> };

export const Loading: Story = {
  render: () => <CasesListView state="loading" />,
};

export const Empty: Story = {
  render: () => <CasesListEmpty />,
};
