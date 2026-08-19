import type { Meta, StoryObj } from "@storybook/react";
import { Button } from "../../components/primitives/Button";
import { Card } from "../../components/primitives/Card";
import { Input } from "../../components/primitives/Input";
import { Textarea } from "../../components/primitives/Textarea";
import { PageHeader } from "./_shared/PageHeader";
import { FlashMessage } from "./_shared/FlashMessage";
import { settings } from "./_shared/mockData/settings";

/** Settings page body (6 form cards + spend snapshot; SS-1..SS-5).
 *  Exported for tests; hidden from the addons panel. */
export function SettingsView() {
  const { snapshot } = settings;
  // sort() keeps category=mode lines stable like the Jinja template does.
  const scopeRulesText = Object.entries(settings.scope_rules)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([cat, mode]) => `${cat}=${mode}`)
    .join("\n");
  const keywordsText = settings.keywords.join("\n");

  return (
    <div style={{ display: "grid", gap: "var(--space-4)" }}>
      <PageHeader title="Settings" meta="Preferencias globales del asistente" />
      <FlashMessage tone="success">Configuración guardada correctamente.</FlashMessage>

      <Card title="Scope rules">
        <p style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
          One rule per line: category=mode with mode bot_resolve or always_escalate.
        </p>
        <div style={{ display: "grid", gap: "var(--space-2)" }}>
          <Textarea label="Scope rules" rows={4} defaultValue={scopeRulesText} />
          <div>
            <Button variant="secondary">Save scope rules</Button>
          </div>
        </div>
      </Card>

      <Card title="Emergency keywords">
        <p style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
          One expression per line. Saved keywords are detected on the next inbound message.
        </p>
        <div style={{ display: "grid", gap: "var(--space-2)" }}>
          <Textarea label="Emergency keywords" rows={6} defaultValue={keywordsText} />
          <div>
            <Button variant="secondary">Save keywords</Button>
          </div>
        </div>
      </Card>

      <Card title="Tone">
        <div style={{ display: "grid", gap: "var(--space-2)" }}>
          <Input label="Tone" defaultValue={settings.tone} />
          <div>
            <Button variant="secondary">Save tone</Button>
          </div>
        </div>
      </Card>

      <Card title="Spend limits">
        <p style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
          Per-conversation and daily USD limits. At 80% the bot goes conservative;
          at 100% paid LLM calls stop and the conversation escalates.
        </p>
        <div style={{ display: "grid", gap: "var(--space-2)" }}>
          <Input label="Conversation limit (USD)" type="number" defaultValue={String(settings.conversation_limit)} />
          <Input label="Daily limit (USD)" type="number" defaultValue={String(settings.daily_limit)} />
          <div>
            <Button variant="secondary">Save limits</Button>
          </div>
        </div>
      </Card>

      <Card title="Meta pricing">
        <p style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
          Service-message unit cost (USD), effective 2026-10-01.
        </p>
        <div style={{ display: "grid", gap: "var(--space-2)" }}>
          <Input label="Service-message cost (USD)" type="number" defaultValue={String(settings.meta_cost)} />
          <div>
            <Button variant="secondary">Save pricing</Button>
          </div>
        </div>
      </Card>

      <Card title="Current spend">
        <table className="table">
          <thead>
            <tr>
              <th>Day</th>
              <th>Daily spend</th>
              <th>Daily limit</th>
              <th>% of limit</th>
              <th>Mode</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{snapshot.date}</td>
              <td>${snapshot.daily_spend.toFixed(4)}</td>
              <td>${snapshot.daily_limit.toFixed(2)}</td>
              <td>{snapshot.daily_percent.toFixed(1)}%</td>
              <td>{snapshot.mode}</td>
            </tr>
          </tbody>
        </table>
        {snapshot.conversation_percent !== null ? (
          <p style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
            Conversation {snapshot.conversation_percent}% of ${snapshot.conversation_limit.toFixed(2)}
          </p>
        ) : null}
      </Card>
    </div>
  );
}

const meta = {
  title: "pages/Settings",
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          'Panel settings: 6 form cards (scope rules, emergency keywords, tone, spend limits, meta pricing, current spend) + PageHeader + FlashMessage (T5.3; R-PRD-PG-6).\n\n' +
          "**When to use** — the authenticated settings manager.\n" +
          "**Source** — page-first Storybook mock; production wiring untouched.",
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
