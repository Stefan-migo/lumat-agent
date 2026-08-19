import type { Meta, StoryObj } from "@storybook/react";
import { Matrix as MatrixGrid } from "../helpers/matrix";
import { Textarea } from "../../components/primitives/Textarea";

const meta = {
  title: "primitives/Textarea",
  component: Textarea,
  parameters: {
    docs: {
      description: {
        component:
          "Labelled multi-line text area with token sizing (DS-STORY-2).\n\n" +
          "**When to use** — longer free-form content: service summaries, notes, descriptions.\n" +
          "**When not to use** — single-line short text (use `Input`).\n\n" +
          "**Accessibility** — the visible label is rendered via `FieldShell` and wired with `htmlFor`/`id`; errors render as `aria-describedby`-linked inline text. The focus indicator MUST use the design tokens: `--focus-ring`, `--focus-ring-width`, `--focus-ring-offset` (2px solid, 2px offset) so it meets WCAG 2.4.11 on `--bg` and `--surface`.",
      },
    },
  },
  argTypes: {
    label: { control: "text", description: "Visible label (FieldShell)." },
    placeholder: { control: "text", description: "Placeholder hint." },
    error: { control: "text", description: "Inline validation message via aria-describedby." },
    disabled: { control: "boolean", description: "Disables the control." },
  },
} satisfies Meta<typeof Textarea>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: { label: "Resumen", placeholder: "Describa el servicio…" },
};

export const WithError: Story = {
  args: { label: "Resumen", error: "Campo obligatorio" },
};

export const Disabled: Story = {
  args: { label: "Resumen", disabled: true, defaultValue: "Texto no editable" },
};

export const Matrix: StoryObj = {
  render: () => (
    <MatrixGrid
      cells={[
        [
          "Default",
          <Textarea key="d" label="Resumen" placeholder="Describa el servicio…" />,
        ],
        [
          "Error",
          <Textarea key="e" label="Resumen" error="Campo obligatorio" />,
        ],
        [
          "Disabled",
          <Textarea key="dis" label="Resumen" disabled defaultValue="Texto no editable" />,
        ],
      ]}
    />
  ),
};
