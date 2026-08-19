import type { Meta, StoryObj } from "@storybook/react";
import { Matrix as MatrixGrid } from "../helpers/matrix";
import { Badge } from "../../components/primitives/Badge";

const meta = {
  title: "primitives/Badge",
  component: Badge,
  parameters: {
    docs: {
      description: {
        component:
          "Compact status/label pill with token tones (DS-STORY-2).\n\n" +
          "**When to use** — short status labels: Pending, Success, Danger, neutral tags.\n" +
          "**When not to use** — interactive controls (use `Button`) or user identity (use `Avatar`); never as the only channel for a critical state — pair with a text label (see `StatusBadge`).\n\n" +
          "**Accessibility** — badge text is real content (never `aria-hidden`); tone colors come from `--success*`/`--warning*`/`--danger*` tokens and the badge always renders its text label so color is never the only signal. Contrast: tinted tone backgrounds (`--*-bg`) with `--text` meet WCAG AA for normal text (DS-STORY-5).",
      },
    },
  },
  argTypes: {
    tone: {
      control: "select",
      options: ["neutral", "success", "warning", "danger"],
      description: "Semantic tone mapping to token colors.",
    },
    children: { control: "text", description: "Label content." },
  },
} satisfies Meta<typeof Badge>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Warning: Story = {
  args: { tone: "warning", children: "Pending" },
};

export const Matrix: StoryObj = {
  render: () => (
    <MatrixGrid
      cells={[
        ["neutral", <Badge key="n" tone="neutral">Neutral</Badge>],
        ["success", <Badge key="s" tone="success">Success</Badge>],
        ["warning", <Badge key="w" tone="warning">Pending</Badge>],
        ["danger", <Badge key="d" tone="danger">Danger</Badge>],
      ]}
    />
  ),
};
