import type { Meta, StoryObj } from "@storybook/react";
import { StatusBadge } from "../../components/primitives/StatusBadge";
const meta = {
  title: "primitives/StatusBadge",
  component: StatusBadge,
} satisfies Meta<typeof StatusBadge>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Escalated: Story = { args: { status: "escalated" } };
