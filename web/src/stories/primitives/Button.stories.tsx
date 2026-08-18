import type { Meta, StoryObj } from "@storybook/react";
import { Button } from "../../components/primitives/Button";

const meta = {
  title: "primitives/Button",
  component: Button,
} satisfies Meta<typeof Button>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Primary: Story = {
  args: { children: "Guardar", variant: "primary" },
};

export const Secondary: Story = {
  args: { children: "Cancelar", variant: "secondary" },
};

export const Link: Story = {
  args: { children: "Exportar CSV", href: "/panel/export/clients.csv" },
};

export const Disabled: Story = {
  args: { children: "Bloqueado", disabled: true },
};
