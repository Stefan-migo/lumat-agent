import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";
import { Combobox } from "../../components/primitives/Combobox";

const options = [
  { value: "ar", label: "Argentina" },
  { value: "cl", label: "Chile" },
  { value: "uy", label: "Uruguay" },
];

const meta = {
  title: "primitives/Combobox",
  component: Combobox,
  args: { label: "País", options },
  parameters: {
    docs: { description: { component: "Native input with listbox semantics for searchable choices." } },
  },
} satisfies Meta<typeof Combobox>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: { value: null, onChange: () => {} },
  render: (args) => {
    const [value, setValue] = useState<string | null>("ar");
    return <Combobox {...args} value={value} onChange={setValue} />;
  },
};

export const Disabled: Story = {
  args: { value: null, onChange: () => {} },
  render: (args) => <Combobox {...args} value={null} onChange={() => {}} disabled />,
};
