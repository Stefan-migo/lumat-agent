import type { Meta, StoryObj } from "@storybook/react";
import { Matrix as MatrixGrid } from "../helpers/matrix";
import { Input } from "../../components/primitives/Input";

const meta = {
  title: "primitives/Input",
  component: Input,
  parameters: {
    docs: {
      description: {
        component:
          "Labelled single-line text input with token styling (DS-STORY-2).\n\n" +
          "**When to use** — free-form short text: names, emails, phones, search terms.\n" +
          "**When not to use** — multi-line content (use `Textarea`), bounded choices (use `Select`).\n\n" +
          "**Accessibility** — the visible label is rendered via `FieldShell` and wired with `htmlFor`/`id`. Errors render as `aria-describedby`-linked inline text. The focus indicator MUST use the design tokens: `--focus-ring`, `--focus-ring-width`, `--focus-ring-offset` (2px solid, 2px offset) so it meets WCAG 2.4.11 on both `--bg` and `--surface`.",
      },
    },
  },
  argTypes: {
    label: { control: "text", description: "Visible label (FieldShell)." },
    placeholder: { control: "text", description: "Placeholder hint." },
    size: {
      control: "select",
      options: ["sm", "md"],
      description: "Control density (data-bx-size token concern).",
    },
    error: { control: "text", description: "Inline validation message via aria-describedby." },
    disabled: { control: "boolean", description: "Disables the control." },
  },
} satisfies Meta<typeof Input>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: { label: "Nombre", placeholder: "Ana Pérez" },
};

export const Small: Story = {
  args: { label: "Nombre", size: "sm", placeholder: "Ana Pérez" },
};

export const WithError: Story = {
  args: {
    label: "Email",
    error: "Formato de correo inválido",
    defaultValue: "no-es-un-email",
  },
};

export const Disabled: Story = {
  args: { label: "Teléfono", disabled: true, defaultValue: "+569 1234 5678" },
};

export const Matrix: StoryObj = {
  render: () => (
    <MatrixGrid
      cells={[
        [
          "sm default",
          <Input key="sm" label="Nombre" size="sm" placeholder="Ana Pérez" />,
        ],
        [
          "md default",
          <Input key="md" label="Nombre" placeholder="Ana Pérez" />,
        ],
        [
          "md error",
          <Input key="err" label="Email" error="Formato de correo inválido" defaultValue="no-es-un-email" />,
        ],
        [
          "sm disabled",
          <Input key="dis" label="Teléfono" size="sm" disabled defaultValue="+569 1234 5678" />,
        ],
      ]}
    />
  ),
};
