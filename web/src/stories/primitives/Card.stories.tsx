import type { Meta, StoryObj } from "@storybook/react";
import { Card } from "../../components/primitives/Card";
const meta = { title: "primitives/Card", component: Card } satisfies Meta<
  typeof Card
>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {
  args: { title: "Client", children: "Camila Soto" },
};
