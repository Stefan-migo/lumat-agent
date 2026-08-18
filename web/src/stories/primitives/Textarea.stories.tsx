import type { Meta, StoryObj } from "@storybook/react";
import { Textarea } from "../../components/primitives/Textarea";

const meta = {
  title: "primitives/Textarea",
  component: Textarea,
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
