import type { Meta, StoryObj } from "@storybook/react";
import { Badge } from "../../components/primitives/Badge";
const meta = { title: "primitives/Badge", component: Badge } satisfies Meta<
  typeof Badge
>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Warning: Story = {
  args: { tone: "warning", children: "Pending" },
};
