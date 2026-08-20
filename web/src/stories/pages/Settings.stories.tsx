import type { Meta, StoryObj } from "@storybook/react";
import { Button } from "../../components/primitives/Button";
import { Card } from "../../components/primitives/Card";
import { Input } from "../../components/primitives/Input";
import { Textarea } from "../../components/primitives/Textarea";
import type { Column } from "./_shared/DataTable";
import { DataTable, tabularNum } from "./_shared/DataTable";
import { PageFrame } from "./_shared/PageFrame";
import { StateMessage } from "./_shared/StateMessage";
import { settings } from "./_shared/mockData/settings";

/** Settings page body grouped by business consequence (design §Configuración).
 *  Plain-Spanish effect explanations precede every input; each independently
 *  persisted group has ONE save action; advanced `category=mode` syntax is
 *  separated, explained, and validated before saving; the Spend snapshot uses
 *  a numeric DataTable with tabular/right-aligned numerals (DS-UI-TABLES).
 *  Exported for tests; hidden from the addons panel. */
export type SettingsState =
  | "ready"
  | "saved"
  | "saving"
  | "validation"
  | "server-error"
  | "stale";

export function SettingsView({ state = "ready" }: { state?: SettingsState }) {
  const { snapshot } = settings;
  // sort() keeps the advanced category=mode lines stable like the Jinja template does.
  const scopeRulesText = Object.entries(settings.scope_rules)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([cat, mode]) => `${cat}=${mode}`)
    .join("\n");
  const keywordsText = settings.keywords.join("\n");

  const columns: Column<{ label: string; value: string }>[] = [
    { key: "label", header: "Fecha", render: (r) => r.label },
    {
      key: "daily_spend",
      header: "Gasto diario",
      render: (r) => tabularNum(r.value),
      align: "right",
    },
  ];

  const spendRows = [
    { label: snapshot.date, value: `$${snapshot.daily_spend.toFixed(4)}` },
    { label: "Límite diario", value: `$${snapshot.daily_limit.toFixed(2)}` },
    { label: "% del límite", value: `${snapshot.daily_percent.toFixed(1)}%` },
  ];

  const banner =
    state === "saved" ? (
      <StateMessage tone="success" role="status" title="Configuración guardada" detail="Los cambios quedaron aplicados." />
    ) : state === "saving" ? (
      <StateMessage tone="info" role="status" spinner title="Guardando cambios" detail="Aplicando la configuración seleccionada." />
    ) : state === "validation" ? (
      <StateMessage
        tone="danger"
        role="alert"
        title="Sintaxis no válida"
        detail="Revisá las reglas avanzadas: cada línea debe tener categoría=mode con mode bot_resolve o always_escalate."
      />
    ) : state === "server-error" ? (
      <StateMessage tone="danger" role="alert" title="No pudimos guardar los cambios" detail="Ocurrió un error del servidor. Reintentá en unos minutos." />
    ) : state === "stale" ? (
      <StateMessage tone="warning" role="status" title="Datos posiblemente desactualizados" detail="La última consulta no pudo completarse. Mostramos la información disponible." />
    ) : null;

  return (
    <PageFrame title="Configuración" meta="Preferencias globales del asistente" state={banner}>
      <Card title="Alcance del agente">
        <p style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
          Define en qué categorías el agente responde de forma automática y en cuáles siempre deriva a una persona.
        </p>
        <details style={{ marginBottom: "var(--space-2)" }}>
          <summary style={{ cursor: "pointer", fontSize: "var(--text-sm)" }}>Sintaxis avanzada · categoría=mode</summary>
          <p style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
            Formato técnico: una regla por línea con categoría=mode, donde mode es bot_resolve
            (el agente responde solo) o always_escalate (siempre pasa a una persona). No lo cambies
            sin conocer el efecto en las respuestas.
          </p>
        </details>
        <div style={{ display: "grid", gap: "var(--space-2)" }}>
          <Textarea label="Reglas de alcance" rows={4} defaultValue={scopeRulesText} />
          <div>
            <Button variant="secondary">Guardar alcance</Button>
          </div>
        </div>
      </Card>

      <Card title="Detección de emergencias">
        <p style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
          Palabras que activan un aviso de emergencia. Se detectan en el próximo mensaje entrante.
        </p>
        <div style={{ display: "grid", gap: "var(--space-2)" }}>
          <Textarea label="Palabras clave de emergencia" rows={6} defaultValue={keywordsText} />
          <div>
            <Button variant="secondary">Guardar palabras clave</Button>
          </div>
        </div>
      </Card>

      <Card title="Tono">
        <p style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
          Define cómo suenan las respuestas del agente en cada conversación.
        </p>
        <div style={{ display: "grid", gap: "var(--space-2)" }}>
          <Input label="Tono" defaultValue={settings.tone} />
          <div>
            <Button variant="secondary">Guardar tono</Button>
          </div>
        </div>
      </Card>

      <Card title="Límites de gasto">
        <p style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
          Topes de gasto por conversación y por día. Al 80% el agente se vuelve más conservador;
          al 100% se detienen las llamadas de pago y la conversación pasa a una persona.
        </p>
        <div style={{ display: "grid", gap: "var(--space-2)" }}>
          <Input label="Límite por conversación (USD)" type="number" defaultValue={String(settings.conversation_limit)} />
          <Input label="Límite diario (USD)" type="number" defaultValue={String(settings.daily_limit)} />
          <div>
            <Button variant="secondary">Guardar límites</Button>
          </div>
        </div>
      </Card>

      <Card title="Precio Meta">
        <p style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
          Costo por mensaje de servicio (USD), vigente desde 2026-10-01.
        </p>
        <div style={{ display: "grid", gap: "var(--space-2)" }}>
          <Input label="Costo por mensaje (USD)" type="number" defaultValue={String(settings.meta_cost)} />
          <div>
            <Button variant="secondary">Guardar precio</Button>
          </div>
        </div>
      </Card>

      <Card title="Gasto actual">
        <DataTable columns={columns} rows={spendRows} rowKey={(r) => r.label} />
        {snapshot.conversation_percent !== null ? (
          <p style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
            Conversación {snapshot.conversation_percent}% de ${snapshot.conversation_limit.toFixed(2)}
          </p>
        ) : null}
      </Card>
    </PageFrame>
  );
}

const meta = {
  title: "pages/Settings",
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          'Panel de configuración agrupado por consecuencia de negocio, con explicaciones en español, una acción de guardado por grupo persistido, sintaxis avanzada separada/validada y gasto en tabla numérica (DS-UI-COPY/STATES/TABLES).\n\n' +
          "**Uso** — el administrador de la configuración.\n" +
          "**Estados** — listo, guardado, guardando, validación, error de servidor y datos obsoletos.\n" +
          "**Fuente** — mock page-first con la forma del serializer productivo; el wiring de producción no cambia.",
      },
    },
  },
  excludeStories: ["SettingsView"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => <SettingsView />,
};

export const Saved: Story = { render: () => <SettingsView state="saved" /> };
export const Saving: Story = { render: () => <SettingsView state="saving" /> };
export const Validation: Story = { render: () => <SettingsView state="validation" /> };
export const ServerError: Story = { render: () => <SettingsView state="server-error" /> };
export const Stale: Story = { render: () => <SettingsView state="stale" /> };
