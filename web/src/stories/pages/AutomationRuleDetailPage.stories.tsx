import type { Meta, StoryObj } from "@storybook/react";
import { AutomationRuleDetailPage, type AutomationRuleDetailPageProps } from "../../components/pages/AutomationRuleDetailPage";
import type { Rule, User } from "../../types";

export interface AutomationRuleDetailPageStoryProps extends AutomationRuleDetailPageProps {
  width?: number;
}

const admin: User = { username: "ana", role: "admin" };

const rule: Rule = {
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
};

export function AutomationRuleDetailPageStory({ width, ...props }: AutomationRuleDetailPageStoryProps) {
  return <div style={{ maxWidth: width ? `${width}px` : undefined, width: "100%" }}><AutomationRuleDetailPage {...props} /></div>;
}

const meta = {
  title: "pages/AutomationRuleDetailPage",
  component: AutomationRuleDetailPageStory,
  parameters: {
    layout: "fullscreen",
    docs: { description: { component: "Detalle, edición y cambio confirmado de estado de una regla." } },
  },
  excludeStories: ["AutomationRuleDetailPageStory"],
} satisfies Meta<typeof AutomationRuleDetailPageStory>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Data: Story = { args: { ruleId: 7, user: admin, data: rule, state: "ready", width: 720 } };
export const Loading: Story = { args: { ruleId: 7, user: admin, data: null, state: "loading", width: 720 } };
export const NotFound: Story = { args: { ruleId: 7, user: admin, data: null, state: "ready", width: 720 } };
export const Error: Story = { args: { ruleId: 7, user: admin, data: null, state: "error", width: 720 } };
export const Forbidden: Story = { args: { ruleId: 7, user: admin, data: null, state: "denied", width: 720 } };
export const Create: Story = { args: { ruleId: null, user: admin, width: 720 } };
export const Edit: Story = { args: { ruleId: 7, user: admin, data: rule, state: "ready", width: 720 } };
export const OperatorData: Story = { args: { ruleId: 7, user: { username: "vero", role: "operador" }, data: rule, state: "ready", width: 720 } };
export const Confirmation: Story = {
  args: { ruleId: 7, user: admin, data: rule, state: "ready", width: 720 },
  play: async ({ canvasElement }) => {
    const button = Array.from(canvasElement.querySelectorAll("button")).find((item) => item.textContent === "Deshabilitar regla");
    button?.click();
  },
};
