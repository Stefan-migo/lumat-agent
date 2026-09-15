import type { Meta, StoryObj } from "@storybook/react";
import { Menu } from "../../components/primitives/Menu";

const items = [
  { value: "edit", label: "Editar" },
  { value: "duplicate", label: "Duplicar" },
  { value: "archive", label: "Archivar", disabled: true },
];

const meta = {
  title: "primitives/Menu",
  component: Menu,
  args: { label: "Acciones", items, onSelect: () => {} },
  parameters: {
    docs: { description: { component: "Radix-backed menu for actions with menu semantics." } },
  },
} satisfies Meta<typeof Menu>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Disabled: Story = { args: { disabled: true } };
