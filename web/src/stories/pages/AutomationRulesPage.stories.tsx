import type { Meta, StoryObj } from "@storybook/react";
import { AutomationRulesPage, type AutomationRulesPageProps } from "../../components/pages/AutomationRulesPage";
import type { Rule, User } from "../../types";

export interface AutomationRulesPageStoryProps extends AutomationRulesPageProps {
  width?: number;
}

const admin: User = { username: "ana", role: "admin" };

const rule = (overrides: Partial<Rule> = {}): Rule => ({
  id: 7,
  name: "Avisar caso nuevo",
  event_type: "case.created",
  conditions: { priority: "alta" },
  channel: "whatsapp",
  template_event: "case.created",
  cooldown_seconds: 300,
  enabled: true,
  created_by: "ana",
  created_at: "2026-09-05T12:00:00Z",
  updated_at: "2026-09-05T12:00:00Z",
  ...overrides,
});

const DATA = [
  rule(),
  rule({ id: 8, name: "Avisar visita cancelada", event_type: "appointment.cancelled", template_event: "appointment.cancelled", enabled: false }),
];

export function AutomationRulesPageStory({ width, ...props }: AutomationRulesPageStoryProps) {
  return <div style={{ maxWidth: width ? `${width}px` : undefined, width: "100%" }}><AutomationRulesPage {...props} /></div>;
}

const meta = {
  title: "pages/AutomationRulesPage",
  component: AutomationRulesPageStory,
  parameters: {
    layout: "fullscreen",
    docs: { description: { component: "Superficie de consulta y creación de reglas de automatización." } },
  },
  excludeStories: ["AutomationRulesPageStory"],
} satisfies Meta<typeof AutomationRulesPageStory>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Data: Story = { args: { data: DATA, state: "ready", user: admin, width: 1280 } };
export const Loading: Story = { args: { data: null, state: "loading", width: 1280 } };
export const Empty: Story = { args: { data: [], state: "empty", width: 1280 } };
export const Error: Story = { args: { data: null, state: "error", width: 1280 } };
export const Forbidden: Story = { args: { data: null, state: "denied", width: 1280 } };
