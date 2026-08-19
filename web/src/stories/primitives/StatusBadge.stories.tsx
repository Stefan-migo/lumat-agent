import type { Meta, StoryObj } from "@storybook/react";
import { Matrix as MatrixGrid } from "../helpers/matrix";
import { StatusBadge } from "../../components/primitives/StatusBadge";

const meta = {
  title: "primitives/StatusBadge",
  component: StatusBadge,
  parameters: {
    docs: {
      description: {
        component:
          "Domain status badge for conversation/case states, mapping status to a `Badge` tone (DS-STORY-2).\n\n" +
          "**When to use** — the five panel statuses: bot, human, closed, pending, escalated.\n" +
          "**When not to use** — ad-hoc labels (use `Badge` directly).\n\n" +
          "**Accessibility** — the text label always renders (bot/human/closed/pending/escalated), so color is NEVER the only channel (DS-STORY-5). Contrast: tone backgrounds (`--success-bg`, `--warning-bg`, `--danger-bg`) with `--text` meet WCAG AA for normal text; `escalated` maps to danger and `human`/`pending` to warning per the component's tone map.",
      },
    },
  },
  argTypes: {
    status: {
      control: "select",
      options: ["bot", "human", "closed", "pending", "escalated"],
      description: "Domain status — mapped to a badge tone + text label.",
    },
  },
} satisfies Meta<typeof StatusBadge>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Escalated: Story = { args: { status: "escalated" } };

export const Matrix: StoryObj = {
  render: () => (
    <MatrixGrid
      cells={[
        ["bot", <StatusBadge key="b" status="bot" />],
        ["human", <StatusBadge key="h" status="human" />],
        ["closed", <StatusBadge key="c" status="closed" />],
        ["pending", <StatusBadge key="p" status="pending" />],
        ["escalated", <StatusBadge key="e" status="escalated" />],
      ]}
    />
  ),
};
