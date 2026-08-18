import type { Meta, StoryObj } from "@storybook/react";
import { Input } from "../../components/primitives/Input";

const meta = {
  title: "primitives/Input",
  component: Input,
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
