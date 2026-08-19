import type { Meta, StoryObj } from "@storybook/react";
import { Matrix as MatrixGrid } from "../helpers/matrix";
import { Card } from "../../components/primitives/Card";

const meta = {
  title: "primitives/Card",
  component: Card,
  parameters: {
    docs: {
      description: {
        component:
          "Surface container with optional title, used to group related content (DS-STORY-2).\n\n" +
          "**When to use** — dashboards, list items, form sections that need a visual boundary on `--bg`.\n" +
          "**When not to use** — interactive rows (use `Button`/list semantics) or full-page layouts (use `AppShell`).\n\n" +
          "**Accessibility** — the optional title renders as an `<h2>` so heading order must follow the page structure; cards are `section` elements, so a title (or an `aria-label`) SHOULD be present to name the region. Contrast: card surface is `--surface` on `--bg` — text inside MUST use `--text`/`--text-muted` tokens (DS-STORY-5).",
      },
    },
  },
  argTypes: {
    title: { control: "text", description: "Optional section heading (renders an <h2>)." },
    children: { control: "text", description: "Card body content." },
  },
} satisfies Meta<typeof Card>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: { title: "Client", children: "Camila Soto" },
};

export const Matrix: StoryObj = {
  render: () => (
    <MatrixGrid
      cells={[
        ["With title", <Card key="t" title="Client">Camila Soto</Card>],
        ["Without title", <Card key="n">Camila Soto</Card>],
      ]}
    />
  ),
};
