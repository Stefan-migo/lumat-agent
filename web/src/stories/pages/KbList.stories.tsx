import type { Meta, StoryObj } from "@storybook/react";
import { Badge } from "../../components/primitives/Badge";
import { Button } from "../../components/primitives/Button";
import { Card } from "../../components/primitives/Card";
import { Input } from "../../components/primitives/Input";
import { Select } from "../../components/primitives/Select";
import { Textarea } from "../../components/primitives/Textarea";
import type { Column } from "./_shared/DataTable";
import { DataTable, tabularNum } from "./_shared/DataTable";
import { PageFrame } from "./_shared/PageFrame";
import { EmptyState } from "./_shared/EmptyState";
import { StateMessage } from "./_shared/StateMessage";
import { docs } from "./_shared/mockData/kb";
import { kbStatusLabel } from "./_shared/toneMaps";
import type { Doc } from "../../types";

/** Per-doc status: derive the approved KB state from the document's `active`
 *  flag (DS-UI-LABELS; `kbStatusLabel` maps activo/deshabilitado and is ready
 *  for procesando/error too). The mock shape keeps `active: boolean`, so the
 *  full processing/error matrix surfaces via the workspace-level `state`
 *  banners (DS-UI-STATES) rather than per-row fake data. */
function docStatus(d: Doc): "activo" | "deshabilitado" {
  return d.active ? "activo" : "deshabilitado";
}

/** Per-doc actions cell: native <details> Edit accordion (holding the separated,
 *  explained advanced provider/model detail) + Disable / Restore.
 *  Story-local display, non-wired. */
function DocActions({ d }: { d: Doc }) {
  return (
    <div style={{ display: "grid", gap: "var(--space-2)" }}>
      <details>
        <summary style={{ cursor: "pointer" }}>Editar</summary>
        <div style={{ marginTop: "var(--space-2)", display: "grid", gap: "var(--space-2)" }}>
          <Input label="Título" defaultValue={d.title} />
          <Textarea label="Contenido" rows={3} defaultValue={`Contenido de ${d.title}…`} />
          <div style={{ display: "flex", gap: "var(--space-2)" }}>
            <Button variant="secondary">Guardar (nueva versión)</Button>
          </div>
          {/* Advanced machine detail separated from ordinary controls and
              explained in plain Spanish (DS-UI-COPY; raw provider/model never
              appear among ordinary controls). */}
          <div
            style={{
              marginTop: "var(--space-2)",
              padding: "var(--space-3)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-md)",
              background: "var(--surface)",
            }}
          >
            <p style={{ margin: 0, fontSize: "var(--text-sm)", fontWeight: "var(--weight-bold)" }}>
              Detalle técnico · proveedor y modelo
            </p>
            <p style={{ margin: "0 0 var(--space-2)", color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
              Metadatos avanzados del motor que responde con este documento. No es necesario
              cambiarlos en el uso habitual.
            </p>
            <p style={{ margin: 0, fontSize: "var(--text-sm)" }}>
              Proveedor: <span style={{ fontVariantNumeric: "tabular-nums" }}>{d.provider ?? "—"}</span>
              &nbsp;·&nbsp;Modelo: <span style={{ fontVariantNumeric: "tabular-nums" }}>{d.model ?? "—"}</span>
            </p>
          </div>
        </div>
      </details>
      {d.active ? (
        <Button variant="secondary">Deshabilitar</Button>
      ) : (
        <span style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>Deshabilitado</span>
      )}
      {d.version > 1 ? (
        <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "flex-end" }}>
          <Select
            label="Restaurar"
            aria-label={`Restaurar doc ${d.id}`}
            defaultValue={String(d.active_version)}
            options={Array.from({ length: d.version }, (_, i) => ({
              value: String(i + 1),
              label: `v${i + 1}`,
            }))}
            size="sm"
          />
          <Button variant="secondary">Restaurar</Button>
        </div>
      ) : null}
    </div>
  );
}

const columns: Column<Doc>[] = [
  { key: "id", header: "#", render: (d) => `#${d.id}` },
  { key: "title", header: "Título", render: (d) => d.title },
  { key: "format", header: "Formato", render: (d) => d.format },
  {
    key: "version",
    header: "Versión",
    render: (d) => `${d.version} (activa: ${d.active_version})`,
  },
  {
    key: "status",
    header: "Estado",
    render: (d) => (
      <Badge tone={d.active ? "success" : "neutral"}>{kbStatusLabel(docStatus(d))}</Badge>
    ),
  },
  {
    key: "cost",
    header: "Costo",
    render: (d) => (d.cost_meta !== null ? tabularNum(`$${d.cost_meta.toFixed(6)}`) : "—"),
  },
];

export type KbListState = "ready" | "empty" | "processing" | "error" | "disable-confirmation";

/** KB list body (add-document card + docs table with edit/disable/restore).
 *  Exported for tests; hidden from the addons panel. Spanish copy (DS-UI-COPY),
 *  per-doc states via kbStatusLabel (DS-UI-LABELS), advanced provider/model
 *  separated + explained, and processing/error/disable-confirmation states via
 *  the workspace banners (DS-UI-STATES). */
export function KbListView({ state = "ready" }: { state?: KbListState }) {
  const content =
    state === "processing" || state === "error" ? (
      null
    ) : (
      <>
        <Card title="Agregar documento">
          <div style={{ display: "flex", gap: "var(--space-3)", alignItems: "flex-end", flexWrap: "wrap" }}>
            <Input label="Título" placeholder="Título del documento" />
            <Input label="Archivo (pdf / md / txt / csv)" type="file" />
            <Button>Agregar</Button>
          </div>
        </Card>
        <DataTable
          columns={columns}
          rows={docs}
          rowKey={(d) => String(d.id)}
          actions={(d) => <DocActions d={d} />}
        />
      </>
    );

  return (
    <PageFrame
      title="Base de conocimientos"
      meta={`${docs.length} documentos`}
      state={
        state === "processing" ? (
          <StateMessage
            tone="info"
            role="status"
            spinner
            title="Procesando documento"
            detail="Revisando el formato, tamaño y contenido. Verificá el estado en unos momentos."
          />
        ) : state === "error" ? (
          <StateMessage
            tone="danger"
            role="alert"
            title="No pudimos procesar el documento"
            detail="El archivo no cumple con el formato, tamaño o estado permitido. Revisalo e intentá de nuevo."
          />
        ) : null
      }
    >
      {content}
      {state === "disable-confirmation" ? (
        <StateMessage
          tone="warning"
          role="alert"
          title="Confirmá la desactivación"
          detail={`Al deshabilitar «${docs.find((d) => d.active)?.title ?? "este documento"}», el agente dejará de responder con él. Podés volver a activarlo cuando quieras.`}
        />
      ) : null}
    </PageFrame>
  );
}

/** KB list empty state. Exported for tests. */
export function KbListEmpty() {
  return (
    <PageFrame title="Base de conocimientos">
      <EmptyState title="No hay documentos" description="Subí el primer documento para empezar." />
    </PageFrame>
  );
}

const meta = {
  title: "pages/KbList",
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          'Panel de la base de conocimientos: tarjeta para agregar documentos, tabla con estados aprobados, y estados de procesamiento, error y confirmación de desactivación (DS-UI-COPY/STATES/LABELS).\n\n' +
          "**Uso** — el administrador de la base de conocimientos.\n" +
          "**Estados** — listo, procesando, error, confirmación de desactivación y vacío.\n" +
          "**Fuente** — mock page-first con la forma del serializer productivo; el wiring de producción no cambia.",
      },
    },
  },
  excludeStories: ["KbListView", "KbListEmpty"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => <KbListView />,
};

export const Processing: Story = {
  render: () => <KbListView state="processing" />,
};
export const Error: Story = { render: () => <KbListView state="error" /> };
export const DisableConfirmation: Story = {
  render: () => <KbListView state="disable-confirmation" />,
};

export const Empty: Story = {
  render: () => <KbListEmpty />,
};
