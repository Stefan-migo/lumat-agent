import type { Meta, StoryObj } from "@storybook/react";
import { Matrix as MatrixGrid } from "../helpers/matrix";
import { Select } from "../../components/primitives/Select";

const options = [
  { value: "nuevo", label: "Nuevo" },
  { value: "activo", label: "Activo" },
  { value: "finalizado", label: "Finalizado" },
];

const meta = {
  title: "primitives/Select",
  component: Select,
  parameters: {
    docs: {
      description: {
        component:
          "Labelled native `<select>` dropdown with token styling (DS-STORY-2).\n\n" +
          "**When to use** — bounded, known choices (status, role, state).\n" +
          "**When not to use** — free-form text (use `Input`); more than ~8 options with search (consider a searchable combobox in a later slice).\n\n" +
          "**Accessibility** — the visible label is rendered via `FieldShell` and wired with `htmlFor`/`id`; errors render as `aria-describedby`-linked inline text. The focus indicator MUST use the design tokens: `--focus-ring`, `--focus-ring-width`, `--focus-ring-offset` (2px solid, 2px offset) so it meets WCAG 2.4.11 on `--bg` and `--surface`. `options` is intentionally not a control — the option list is static data, not a story arg (DS-STORY-3).",
      },
    },
  },
  argTypes: {
    label: { control: "text", description: "Visible label (FieldShell)." },
    size: {
      control: "select",
      options: ["sm", "md"],
      description: "Control density (data-bx-size token concern).",
    },
    error: { control: "text", description: "Inline validation message via aria-describedby." },
    disabled: { control: "boolean", description: "Disables the control." },
    options: { control: false, description: "Static option list — not interactive." },
  },
} satisfies Meta<typeof Select>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: { label: "Estado", options, defaultValue: "nuevo" },
};

export const Small: Story = {
  args: { label: "Estado", options, defaultValue: "nuevo", size: "sm" },
};

export const WithError: Story = {
  args: {
    label: "Estado",
    options: [],
    defaultValue: "",
    error: "Seleccione un estado",
  },
};

export const Disabled: Story = {
  args: { label: "Estado", options, defaultValue: "nuevo", disabled: true },
};

export const Matrix: StoryObj = {
  render: () => (
    <MatrixGrid
      cells={[
        [
          "sm default",
          <Select key="sm" label="Estado" options={options} defaultValue="nuevo" size="sm" />,
        ],
        [
          "md default",
          <Select key="md" label="Estado" options={options} defaultValue="nuevo" />,
        ],
        [
          "md error",
          <Select key="err" label="Estado" options={options} error="Seleccione un estado" />,
        ],
        [
          "sm disabled",
          <Select key="dis" label="Estado" options={options} defaultValue="nuevo" size="sm" disabled />,
        ],
      ]}
    />
  ),
};
