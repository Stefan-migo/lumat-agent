import type { Meta, StoryObj } from "@storybook/react";
import { Settings, type SettingsState } from "../../components/pages/Settings";
import { PushSettings } from "../../components/pages/PushSettings";
import { settings } from "./_shared/mockData/settings";
import type { AssistantCapabilities } from "../../types";

const capabilities: AssistantCapabilities = {
  tools: [{ name: "agenda", description: "Consulta horarios", read_only: true, write: false }],
  personas: ["Cercana"],
  prompts: ["Atención inicial"],
  kb_available: true,
  memory_available: true,
};

/** Settings page body grouped by business consequence (design §Configuración).
 *  Plain-Spanish effect explanations precede every input; each independently
 *  persisted group has ONE save action; advanced `category=mode` syntax is
 *  separated, explained, and validated before saving; the Spend snapshot uses
 *  a numeric DataTable with tabular/right-aligned numerals (DS-UI-TABLES).
 *  Exported for tests; hidden from the addons panel. */
export type { SettingsState };

export function SettingsView({ state = "ready" }: { state?: SettingsState }) {
  return <Settings data={settings} state={state} capabilities={capabilities} />;
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

export const PushPermission: Story = {
  render: () => <PushSettings embedded supported />,
};

export const PushFallback: Story = {
  render: () => <PushSettings embedded supported={false} />,
};
