import type { Meta, StoryObj } from "@storybook/react";
import { Matrix as MatrixGrid } from "../helpers/matrix";
import { Button } from "../../components/primitives/Button";

const meta = {
  title: "primitives/Button",
  component: Button,
  parameters: {
    docs: {
      description: {
        component:
          "Primary/secondary/tertiary action button; renders an anchor when `href` is set (DS-STORY-2).\n\n" +
          "**When to use** — bulk actions (Guardar, Exportar), secondary actions (Cancelar), and low-emphasis drill-down controls.\n" +
          "**When not to use** — inline text links (use a plain `<a>` styled by the design system) or status labels (use `Badge`).\n\n" +
          "**Accessibility** — the focus indicator MUST use the design tokens: `--focus-ring`, `--focus-ring-width`, `--focus-ring-offset` (2px solid, 2px offset) so it stays visible on both `--bg` and `--surface` (WCAG 2.4.11). Contrast: primary uses `--primary-*` tokens on `--surface` (white text passes AA); secondary uses `--text` on `--surface` with `--border` — both meet WCAG AA for normal text. A disabled link is not a real HTML concept, so `disabled` is dropped when `href` is set (aria-disabled conveys it).",
      },
    },
  },
  argTypes: {
    variant: {
      control: "select",
      options: ["primary", "secondary", "tertiary"],
      description: "Visual variant; colors come from tokens only.",
    },
    children: { control: "text", description: "Button label." },
    disabled: { control: "boolean", description: "Disables the control (dropped for anchors)." },
    href: { control: "text", description: "When set, renders an <a> instead of a <button>." },
  },
} satisfies Meta<typeof Button>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Primary: Story = {
  args: { children: "Guardar", variant: "primary" },
};

export const Secondary: Story = {
  args: { children: "Cancelar", variant: "secondary" },
};

export const Tertiary: Story = {
  args: { children: "Operations", variant: "tertiary" },
};

export const Link: Story = {
  args: { children: "Exportar CSV", href: "/panel/export/clients.csv" },
};

export const Disabled: Story = {
  args: { children: "Bloqueado", disabled: true },
};

export const Matrix: StoryObj = {
  render: () => (
    <MatrixGrid
      cells={[
        ["Primary", <Button key="p" variant="primary">Guardar</Button>],
        ["Secondary", <Button key="s" variant="secondary">Cancelar</Button>],
        ["Tertiary", <Button key="t" variant="tertiary">Operations</Button>],
        ["Primary disabled", <Button key="pd" variant="primary" disabled>Guardar</Button>],
        ["Secondary disabled", <Button key="sd" variant="secondary" disabled>Cancelar</Button>],
        ["Link", <Button key="l" href="/panel/export/clients.csv">Exportar CSV</Button>],
      ]}
    />
  ),
};
