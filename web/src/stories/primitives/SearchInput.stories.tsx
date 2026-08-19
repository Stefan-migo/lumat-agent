import type { Meta, StoryObj } from "@storybook/react";
import { Matrix as MatrixGrid } from "../helpers/matrix";
import { SearchInput } from "../../components/primitives/SearchInput";

const meta = {
  title: "primitives/SearchInput",
  component: SearchInput,
  parameters: {
    docs: {
      description: {
        component:
          "Debounced search field with a built-in magnifier glyph (DS-STORY-2).\n\n" +
          "**When to use** — client/bill search where you want to debounce keystrokes and call `onSearch` after a pause.\n" +
          "**When not to use** — an input whose value is read on submit (use `Input`).\n\n" +
          "**Accessibility** — the control exposes an `aria-label` (default `Search`) since it has no visible label; pass a specific one, e.g. `Buscar clientes`. The focus indicator MUST use the design tokens: `--focus-ring`, `--focus-ring-width`, `--focus-ring-offset` (2px solid, 2px offset) so it meets WCAG 2.4.11 on `--bg` and `--surface`.",
      },
    },
  },
  argTypes: {
    placeholder: { control: "text", description: "Placeholder hint." },
    "aria-label": { control: "text", description: "Accessible name for the search field." },
    delay: { control: "number", description: "Debounce delay in ms before onSearch fires." },
  },
} satisfies Meta<typeof SearchInput>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: { onSearch: () => {}, placeholder: "Search clients" },
};

export const Matrix: StoryObj = {
  render: () => (
    <MatrixGrid
      cells={[
        [
          "Default (debounced)",
          <SearchInput key="d" onSearch={() => {}} placeholder="Search clients" />,
        ],
      ]}
    />
  ),
};
